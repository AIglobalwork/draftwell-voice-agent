import json
import logging

import pytest

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
