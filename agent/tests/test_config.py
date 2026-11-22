from datetime import date, time
from pathlib import Path

from draftwell.config import load_business_config, load_price_list

CONFIG = Path(__file__).resolve().parent.parent / "config"


def test_loads_real_config_files():
    p = load_price_list(CONFIG / "pricing.yaml")
    assert (p.system_base, p.extra_vent, p.additional_system) == (449, 35, 349)
    assert (p.dryer_vent, p.blower_per_system, p.antimicrobial_per_system) == (129, 179, 99)
    b = load_business_config(CONFIG / "business.yaml")
    assert b.timezone.key == "America/New_York"
    assert b.slot_starts == (time(8), time(13)) and b.slot_hours == 4
    assert date(2026, 12, 25) in b.closed_dates
    assert 6 not in b.work_days and {"30307", "30030", "30080"} <= b.service_zips
