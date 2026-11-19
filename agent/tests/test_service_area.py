from pathlib import Path

import pytest

from draftwell.config import load_business_config
from draftwell.service_area import is_in_service_area, normalize_zip

CONFIG = Path(__file__).resolve().parent.parent / "config"
CFG = load_business_config(CONFIG / "business.yaml")


@pytest.mark.parametrize("raw,expected", [("30307", "30307"), ("30307-1234", "30307"), (" 30 307 ", "30307"), ("3030", None), ("abcde", None)])
def test_normalize_zip_forms(raw, expected):
    assert normalize_zip(raw) == expected


def test_service_area():
    assert is_in_service_area("30030", CFG) and not is_in_service_area("10001", CFG)
