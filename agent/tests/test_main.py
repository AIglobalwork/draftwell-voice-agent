import asyncio
import json
import logging

import pytest

from draftwell import main
from draftwell.main import check_service_account_json

GOOD = {
    "type": "service_account",
    "client_email": "bot@example.iam.gserviceaccount.com",
    "private_key": "-----BEGIN PRIVATE KEY-----\nSECRETVALUE\n-----END PRIVATE KEY-----\n",
}


def run_check(monkeypatch, caplog, value):
    if value is None:
        monkeypatch.delenv("GOOGLE_SERVICE_ACCOUNT_JSON", raising=False)
    else:
        monkeypatch.setenv("GOOGLE_SERVICE_ACCOUNT_JSON", value)
    with caplog.at_level(logging.INFO, logger="draftwell"):
        check_service_account_json(None)
    return caplog.text


def test_good_json_logs_shape_not_values(monkeypatch, caplog):
    text = run_check(monkeypatch, caplog, json.dumps(GOOD))
    assert "3 keys" in text
    assert "type is service_account: True" in text
    assert "private key looks complete: True" in text
    assert "SECRETVALUE" not in text and "bot@example" not in text


@pytest.mark.parametrize(
    "value",
    [None, "", "{broken", "null", "[1, 2]", '{"private_key": null}', '{"private_key": 5}'],
)
def test_bad_input_logs_and_does_not_crash(monkeypatch, caplog, value):
    text = run_check(monkeypatch, caplog, value)
    assert "GOOGLE_SERVICE_ACCOUNT_JSON" in text
    assert "looks complete: True" not in text


class FakeHandle:
    def __init__(self, interrupted=False, never_ends=False):
        self.interrupted = interrupted
        self.never_ends = never_ends

    async def wait_for_playout(self):
        if self.never_ends:
            await asyncio.Event().wait()


class FakeInput:
    def __init__(self, events):
        self.events = events

    def set_audio_enabled(self, enabled):
        self.events.append(("audio", enabled))


class FakeSession:
    """Records what the call timer does, in order."""

    def __init__(self, goodbye_handle=None, goodbye_error=None, warning_error=None):
        self.events = []
        self.input = FakeInput(self.events)
        self.goodbye_handle = goodbye_handle or FakeHandle()
        self.goodbye_error = goodbye_error
        self.warning_error = warning_error

    def generate_reply(self, instructions):
        if "goodbye" in instructions:
            self.events.append(("reply", "goodbye"))
            if self.goodbye_error:
                raise self.goodbye_error
            return self.goodbye_handle
        self.events.append(("reply", "warning"))
        if self.warning_error:
            raise self.warning_error
        return FakeHandle()

    def shutdown(self):
        self.events.append(("shutdown",))


@pytest.fixture
def fast_sleep(monkeypatch):
    """Skips the real waiting but records how long the timer asked to sleep."""
    real_sleep = asyncio.sleep
    sleeps = []

    async def fake_sleep(seconds):
        sleeps.append(seconds)
        await real_sleep(0)

    monkeypatch.setattr(main.asyncio, "sleep", fake_sleep)
    return sleeps


async def test_timer_warns_30_s_before_the_end_then_mutes_and_says_goodbye(fast_sleep):
    session = FakeSession()
    await main.end_call_after(session, 300)
    assert fast_sleep == [270, 30]
    assert session.events == [
        ("reply", "warning"),
        ("audio", False),  # muted before the goodbye, so the caller cannot interrupt it
        ("reply", "goodbye"),
        ("shutdown",),
    ]


async def test_interrupted_goodbye_is_logged_and_call_still_ends(fast_sleep, caplog):
    session = FakeSession(goodbye_handle=FakeHandle(interrupted=True))
    with caplog.at_level(logging.WARNING, logger="draftwell"):
        await main.end_call_after(session, 300)
    assert "Goodbye was interrupted" in caplog.text
    assert session.events[-1] == ("shutdown",)


async def test_goodbye_that_does_not_finish_in_time_is_logged_and_call_still_ends(fast_sleep, caplog, monkeypatch):
    monkeypatch.setattr(main, "GOODBYE_WAIT_SECONDS", 0.01)
    session = FakeSession(goodbye_handle=FakeHandle(never_ends=True))
    with caplog.at_level(logging.WARNING, logger="draftwell"):
        await main.end_call_after(session, 300)
    assert "Goodbye did not finish" in caplog.text
    assert session.events[-1] == ("shutdown",)


async def test_call_ends_even_if_the_goodbye_fails(fast_sleep):
    session = FakeSession(goodbye_error=RuntimeError("model down"))
    with pytest.raises(RuntimeError):
        await main.end_call_after(session, 300)
    assert session.events[-1] == ("shutdown",)


async def test_failed_warning_is_logged_and_goodbye_and_shutdown_still_follow(fast_sleep, caplog):
    session = FakeSession(warning_error=RuntimeError("model down"))
    with caplog.at_level(logging.WARNING, logger="draftwell"):
        await main.end_call_after(session, 300)
    assert "Time warning failed: RuntimeError" in caplog.text
    assert session.events == [
        ("reply", "warning"),
        ("audio", False),
        ("reply", "goodbye"),
        ("shutdown",),
    ]


def test_room_is_deleted_when_the_session_ends():
    # Without this the agent stays in the room after the goodbye and keeps using agent minutes.
    assert main.room_options().delete_room_on_close is True


# Voice provider. "livekit" (default) runs Gemini Live through LiveKit Inference;
# "google" calls the Gemini API directly with a separate free-tier key.
VOICE_KEY = "test-voice-key-not-real"


@pytest.fixture
def voice_env(monkeypatch):
    # Dummy LiveKit credentials: inference.RealtimeModel needs them to be built (no network is used).
    monkeypatch.setenv("LIVEKIT_API_KEY", "test-livekit-key")
    monkeypatch.setenv("LIVEKIT_API_SECRET", "test-livekit-secret")
    for name in ("VOICE_PROVIDER", "VOICE_MODEL", "GOOGLE_VOICE_API_KEY", "GOOGLE_GENAI_USE_VERTEXAI"):
        monkeypatch.delenv(name, raising=False)
    # The test key for the conversation tests must never be used for voice.
    monkeypatch.setenv("GOOGLE_API_KEY", "test-key-for-text-tests")
    return monkeypatch


@pytest.mark.parametrize("provider", [None, "", "livekit"])
def test_default_voice_provider_is_livekit_inference(voice_env, provider):
    if provider is not None:
        voice_env.setenv("VOICE_PROVIDER", provider)
    model = main.voice_model()
    assert isinstance(model, main.inference.RealtimeModel)
    assert model.model == "google/gemini-3.8-live"


def test_livekit_provider_uses_voice_model(voice_env):
    voice_env.setenv("VOICE_MODEL", "google/gemini-3.8-live-extended-thinking")
    assert main.voice_model().model == "google/gemini-3.8-live-extended-thinking"


def test_google_provider_calls_the_gemini_api_with_its_own_key(voice_env):
    voice_env.setenv("VOICE_PROVIDER", "google")
    voice_env.setenv("GOOGLE_VOICE_API_KEY", VOICE_KEY)
    voice_env.setenv("GOOGLE_GENAI_USE_VERTEXAI", "true")  # must not switch us to billed Vertex AI
    model = main.voice_model()
    assert isinstance(model, main.google.realtime.RealtimeModel)
    assert model.model == "gemini-3.8-live"
    assert model.provider == "Gemini"  # the Gemini API, not Vertex AI
    assert model._opts.api_key == VOICE_KEY  # the plugin has no public getter for the key


def test_google_provider_without_its_key_does_not_fall_back(voice_env):
    voice_env.setenv("VOICE_PROVIDER", "google")
    with pytest.raises(RuntimeError, match="GOOGLE_VOICE_API_KEY"):
        main.voice_model()


def test_unknown_voice_provider_fails(voice_env):
    voice_env.setenv("VOICE_PROVIDER", "openai")
    with pytest.raises(ValueError, match="VOICE_PROVIDER"):
        main.voice_model()


def test_voice_provider_is_logged_but_the_key_is_not(voice_env, caplog):
    voice_env.setenv("VOICE_PROVIDER", "google")
    voice_env.setenv("GOOGLE_VOICE_API_KEY", VOICE_KEY)
    with caplog.at_level(logging.DEBUG):
        main.voice_model()
    assert "Voice: gemini-3.8-live via the Gemini API" in caplog.text
    assert VOICE_KEY not in caplog.text


def test_google_provider_uses_an_api_version_that_serves_live(voice_env):
    # Without api_version the plugin falls back to google-genai's default "v1", where the Live API
    # WebSocket returns HTTP 404; gemini-3.8-live connects on v1beta (scripts/check_gemini_live.py).
    voice_env.setenv("VOICE_PROVIDER", "google")
    voice_env.setenv("GOOGLE_VOICE_API_KEY", VOICE_KEY)
    assert main.voice_model()._opts.api_version == "v1beta"
