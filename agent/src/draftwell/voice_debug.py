"""Temporary voice diagnostics, on only with VOICE_DEBUG=1 (VOICE_PROVIDER=google).
Logs counts and field names only: never the key, transcripts or audio samples."""

import asyncio
import logging
import os
import time

import numpy as np
from google.genai import live
from livekit.agents import inference, vad
from livekit.plugins.google.realtime import realtime_api

logger = logging.getLogger("draftwell.voice_debug")


class _PerSecond:
    """Counts what passes through and logs one line per second."""

    def __init__(self, label: str) -> None:
        self.label = label
        self.start = time.monotonic()
        self.calls = self.samples = self.bytes = self.peak = 0
        self.rate = 0

    def add(self, *, samples: int = 0, nbytes: int = 0, peak: int = 0, rate: int = 0) -> None:
        self.calls += 1
        self.samples += samples
        self.bytes += nbytes
        self.peak = max(self.peak, peak)
        self.rate = rate or self.rate
        if (now := time.monotonic()) - self.start >= 1.0:
            logger.info(
                "[voice-debug] %s: %d calls/s, %d samples/s at %d Hz, %d bytes/s, peak %d",
                self.label, self.calls, self.samples, self.rate, self.bytes, self.peak,
            )
            self.start, self.calls, self.samples, self.bytes, self.peak = now, 0, 0, 0, 0


def _field_names(message) -> str:
    """Names of the fields set in a server message, e.g. server_content[input_transcription]."""
    parts = []
    for name, value in message.model_dump(exclude_none=True, exclude_defaults=True).items():
        if name == "server_content" and isinstance(value, dict):
            flags = [k if not isinstance(v, bool) else f"{k}={v}" for k, v in value.items()]
            parts.append(f"server_content[{', '.join(flags)}]")
        elif name == "voice_activity" and isinstance(value, dict):
            parts.append(f"voice_activity={value.get('voice_activity_type')}")
        else:
            parts.append(name)
    return ", ".join(parts) or "(empty)"


def enable() -> None:
    # The console screen can hide log lines, so the diagnostics can also go to a file.
    logger.setLevel(logging.INFO)
    if path := os.environ.get("VOICE_DEBUG_LOG"):
        handler = logging.FileHandler(path, encoding="utf-8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(message)s"))
        logger.addHandler(handler)
    pushed = _PerSecond("audio into push_audio")
    sent = _PerSecond("audio sent to Gemini")

    original_push = realtime_api.RealtimeSession.push_audio
    local = {}  # a local silero VAD on the same frames, for comparison with Gemini's voice_activity

    async def log_local_vad(stream) -> None:
        async for ev in stream:
            if ev.type in (vad.VADEventType.START_OF_SPEECH, vad.VADEventType.END_OF_SPEECH):
                logger.info("[voice-debug] local VAD: %s", ev.type.name)

    def push_audio(self, frame):
        if "stream" not in local:
            local["stream"] = inference.VAD(model="silero").stream()
            local["task"] = asyncio.ensure_future(log_local_vad(local["stream"]))
        local["stream"].push_frame(frame)
        samples = np.frombuffer(frame.data, dtype=np.int16)
        pushed.add(
            samples=frame.samples_per_channel,
            peak=int(np.abs(samples).max()) if samples.size else 0,
            rate=frame.sample_rate,
        )
        return original_push(self, frame)

    original_send = live.AsyncSession.send_realtime_input

    async def send_realtime_input(self, **kwargs):
        if (audio := kwargs.get("audio")) is not None:
            sent.add(nbytes=len(audio.data or b""))
        else:
            logger.info("[voice-debug] sent realtime input: %s", ", ".join(kwargs))
        return await original_send(self, **kwargs)

    original_client_content = live.AsyncSession.send_client_content

    async def send_client_content(self, **kwargs):
        logger.info("[voice-debug] sent client content, turn_complete=%s", kwargs.get("turn_complete"))
        return await original_client_content(self, **kwargs)

    original_receive = live.AsyncSession.receive

    async def receive(self):
        async for message in original_receive(self):
            names = _field_names(message)
            if names != "server_content[model_turn]":  # audio chunks: too many to log one by one
                logger.info("[voice-debug] server: %s", names)
            yield message

    realtime_api.RealtimeSession.push_audio = push_audio
    live.AsyncSession.send_realtime_input = send_realtime_input
    live.AsyncSession.send_client_content = send_client_content
    live.AsyncSession.receive = receive
    logger.info("[voice-debug] on")


def watch_session(session) -> None:
    """Provider-independent view: what the framework thinks the caller and the agent are doing."""
    session.on("user_state_changed", lambda e: logger.info("[voice-debug] user: %s -> %s", e.old_state, e.new_state))
    session.on("agent_state_changed", lambda e: logger.info("[voice-debug] agent: %s -> %s", e.old_state, e.new_state))
    session.on("user_input_transcribed", lambda e: logger.info("[voice-debug] user transcript, final=%s", e.is_final))
