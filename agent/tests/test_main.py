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
