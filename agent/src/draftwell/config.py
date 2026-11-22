"""Load the owner-editable YAML files into small frozen dataclasses."""

from dataclasses import dataclass
from datetime import date, time
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

DAY_NUMBERS = {"mon": 0, "tue": 1, "wed": 2, "thu": 3, "fri": 4, "sat": 5, "sun": 6}


@dataclass(frozen=True)
class VentEstimate:
    max_sqft: int | None  # None means "no upper limit"
    vents: int


@dataclass(frozen=True)
class PriceList:
    system_base: int
    included_vents_per_system: int
    extra_vent: int
    additional_system: int
    dryer_vent: int
    blower_per_system: int
    antimicrobial_per_system: int
    vent_estimates: tuple[VentEstimate, ...]


@dataclass(frozen=True)
class BusinessConfig:
    company_name: str
    phone: str
    timezone: ZoneInfo
    work_days: frozenset[int]  # 0 = Monday
    slot_starts: tuple[time, ...]
    slot_hours: int
    min_days_ahead: int
    max_days_ahead: int
    service_zips: frozenset[str]
    max_call_seconds: int
    closed_dates: frozenset[date]  # no appointments on these days


def _read_yaml(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_price_list(path: Path) -> PriceList:
    data = _read_yaml(path)
    estimates = tuple(VentEstimate(row["max_sqft"], row["vents"]) for row in data.pop("vent_estimates"))
    return PriceList(**data, vent_estimates=estimates)


def load_business_config(path: Path) -> BusinessConfig:
    data = _read_yaml(path)
    return BusinessConfig(
        company_name=data["company_name"],
        phone=data["phone"],
        timezone=ZoneInfo(data["timezone"]),
        work_days=frozenset(DAY_NUMBERS[day] for day in data["work_days"]),
        slot_starts=tuple(time.fromisoformat(s) for s in data["slot_starts"]),
        slot_hours=data["slot_hours"],
        min_days_ahead=data["min_days_ahead"],
        max_days_ahead=data["max_days_ahead"],
        service_zips=frozenset(data["service_zips"]),
        max_call_seconds=data["max_call_seconds"],
        closed_dates=frozenset(date.fromisoformat(d) for d in data["closed_dates"]),
    )
