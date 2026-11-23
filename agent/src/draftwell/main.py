"""LiveKit entrypoint: builds the dependencies from env, starts the voice session."""

import asyncio
import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path

from dotenv import load_dotenv
from livekit.agents import AgentServer, AgentSession, JobContext, JobProcess, cli, inference, room_io
from livekit.plugins import ai_coustics

from draftwell.agent import DraftwellAgent
from draftwell.calendar_client import GoogleCalendarClient
from draftwell.config import load_business_config, load_price_list
from draftwell.flows import Deps, wait_for_background
from draftwell.notify import Notifier, NotifySettings

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"

logger = logging.getLogger("draftwell")

# Notifications can take a while (each SMTP send has a 10 s timeout), so give them 20 s at hang-up
# and raise the framework's shutdown limit (default 10 s) above that, or the process is killed first.
NOTIFY_WAIT_SECONDS = 20
SHUTDOWN_TIMEOUT_SECONDS = NOTIFY_WAIT_SECONDS + 5

# Demo call limit: a short warning this many seconds before the end, then a goodbye.
WARNING_BEFORE_END_SECONDS = 30
GOODBYE_WAIT_SECONDS = 15


def check_service_account_json(proc: JobProcess) -> None:
    """Runs once in each worker process at startup, so a broken secret shows in the logs before
    the first call. Logs only the shape of the JSON, never its values."""
    try:
        data = json.loads(os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", ""))
    except json.JSONDecodeError as e:
        logger.error("GOOGLE_SERVICE_ACCOUNT_JSON is not valid JSON (line %d, column %d)", e.lineno, e.colno)
        return
    if not isinstance(data, dict):
        logger.error("GOOGLE_SERVICE_ACCOUNT_JSON is valid JSON but not an object")
        return
    key = data.get("private_key")
    logger.info(
        "GOOGLE_SERVICE_ACCOUNT_JSON parsed: %d keys, type is service_account: %s, private key looks complete: %s",
        len(data),
        data.get("type") == "service_account",
        isinstance(key, str)
        and key.startswith("-----BEGIN PRIVATE KEY-----")
        and key.rstrip().endswith("-----END PRIVATE KEY-----"),
    )


server = AgentServer(shutdown_process_timeout=SHUTDOWN_TIMEOUT_SECONDS, setup_fnc=check_service_account_json)


async def end_call_after(session: AgentSession, seconds: int) -> None:
    """Demo limit: warn the caller 30 s before the end, then say goodbye and end the call.
    The realtime model has no separate TTS, so say() does not work; ask the model to speak instead."""
    await asyncio.sleep(seconds - WARNING_BEFORE_END_SECONDS)
    session.generate_reply(
        instructions="Tell the caller in one short sentence that about 30 seconds of demo time are left, so let's wrap up."
    )
    await asyncio.sleep(WARNING_BEFORE_END_SECONDS)
    try:
        # Gemini Live detects the caller's speech on its server, so allow_interruptions=False is ignored.
        # Muting the caller is what stops a word or a noise from cutting the goodbye short.
        session.input.set_audio_enabled(False)
        handle = session.generate_reply(
            instructions="Tell the caller in one short sentence that the demo time limit is reached, thank them for calling Draftwell and say goodbye."
        )
        await asyncio.wait_for(handle.wait_for_playout(), GOODBYE_WAIT_SECONDS)  # do not wait forever
        if handle.interrupted:
            logger.warning("Goodbye was interrupted before it finished")
    except TimeoutError:
        logger.warning("Goodbye did not finish in %s s", GOODBYE_WAIT_SECONDS)
    finally:
        session.shutdown()  # always end the call, even if the goodbye failed


def log_timer_failure(task: asyncio.Task) -> None:
    if not task.cancelled() and task.exception() is not None:
        logger.error("Call timer failed: %s", type(task.exception()).__name__)


def room_options() -> room_io.RoomOptions:
    return room_io.RoomOptions(
        audio_input=room_io.AudioInputOptions(
            noise_cancellation=ai_coustics.audio_enhancement(model=ai_coustics.EnhancerModel.QUAIL_VF_S),
        ),
        # Ends the call for both sides when the session closes (goodbye, hang-up, error).
        # Without it the agent stays in the room and keeps using agent minutes.
        delete_room_on_close=True,
    )


@server.rtc_session(agent_name="draftwell")
async def entrypoint(ctx: JobContext) -> None:
    config = load_business_config(CONFIG_DIR / "business.yaml")

    async def publish(event: dict) -> None:
        await ctx.room.local_participant.send_text(json.dumps(event), topic="draftwell.panel")

    deps = Deps(
        prices=load_price_list(CONFIG_DIR / "pricing.yaml"),
        config=config,
        calendar=GoogleCalendarClient(
            os.environ["GOOGLE_CALENDAR_ID"], json.loads(os.environ["GOOGLE_SERVICE_ACCOUNT_JSON"])
        ),
        notifier=Notifier(NotifySettings.from_env(), config),
        publish=publish,
        now=lambda: datetime.now(UTC),
    )

    session = AgentSession(
        llm=inference.RealtimeModel(model=os.environ.get("VOICE_MODEL", "google/gemini-3.8-live"), voice="Puck")
    )
    await session.start(
        agent=DraftwellAgent(deps),
        room=ctx.room,
        room_options=room_options(),
    )
    await ctx.connect()
    timer = asyncio.create_task(end_call_after(session, config.max_call_seconds))
    timer.add_done_callback(log_timer_failure)
    ctx.add_shutdown_callback(lambda: _cancel(timer))

    async def finish_notifications() -> None:
        # A booking made just before hang-up still gets its emails and Slack message.
        await wait_for_background(deps, NOTIFY_WAIT_SECONDS)

    ctx.add_shutdown_callback(finish_notifications)

    await session.generate_reply(
        instructions=f"Greet the caller: say you are the virtual assistant of {config.company_name} and ask how you can help."
    )


async def _cancel(task: asyncio.Task) -> None:
    task.cancel()


if __name__ == "__main__":
    cli.run_app(server)
