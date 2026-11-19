from pathlib import Path

import pytest

from draftwell.config import load_price_list
from draftwell.pricing import QuoteParams, calculate_quote, estimate_vents

CONFIG = Path(__file__).resolve().parent.parent / "config"
PRICES = load_price_list(CONFIG / "pricing.yaml")


def test_site_example_is_718():  # matches the website and the hero dialog
    q = calculate_quote(QuoteParams(systems=1, vents=14, square_feet=None, dryer_vent=True), PRICES)
    assert [l.amount for l in q.lines] == [449, 140, 129] and q.total == 718
    assert not q.vents_estimated


def test_two_systems_with_all_addons():
    q = calculate_quote(QuoteParams(2, 25, None, blower=True, antimicrobial=True), PRICES)
    assert q.total == 1529  # 449+349 + 5×35 + 2×179 + 2×99


def test_fewer_vents_than_included_has_no_extra_line():
    q = calculate_quote(QuoteParams(1, 6, None), PRICES)
    assert q.total == 449 and len(q.lines) == 1


@pytest.mark.parametrize("sqft,vents", [(1200, 10), (1500, 10), (1501, 14), (2500, 14), (3800, 18)])
def test_estimate_vents(sqft, vents):
    assert estimate_vents(sqft, PRICES) == vents


def test_square_feet_used_when_vents_unknown():
    q = calculate_quote(QuoteParams(1, None, 2000), PRICES)
    assert q.total == 589 and q.vents_estimated


@pytest.mark.parametrize("params", [QuoteParams(0, 10, None), QuoteParams(1, None, None), QuoteParams(1, 0, None), QuoteParams(1, None, -5)])
def test_invalid_params_raise(params):
    with pytest.raises(ValueError):
        calculate_quote(params, PRICES)
