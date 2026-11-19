"""Price calculation. All arithmetic lives here, never in the AI model."""

from dataclasses import dataclass

from draftwell.config import PriceList


@dataclass(frozen=True)
class QuoteParams:
    systems: int
    vents: int | None
    square_feet: int | None
    dryer_vent: bool = False
    blower: bool = False
    antimicrobial: bool = False


@dataclass(frozen=True)
class QuoteLine:
    label: str
    amount: int


@dataclass(frozen=True)
class Quote:
    lines: tuple[QuoteLine, ...]
    total: int
    vents_estimated: bool


def estimate_vents(square_feet: int, prices: PriceList) -> int:
    """First row whose max_sqft is big enough wins; None means no limit."""
    for row in prices.vent_estimates:
        if row.max_sqft is None or square_feet <= row.max_sqft:
            return row.vents
    raise ValueError("The price list has no vent estimate for this size")


def calculate_quote(params: QuoteParams, prices: PriceList) -> Quote:
    if params.systems < 1:
        raise ValueError("There must be at least one system")
    if params.vents is not None and params.vents < 1:
        raise ValueError("The vent count must be at least 1")

    vents_estimated = params.vents is None
    if params.vents is not None:
        vents = params.vents
    elif params.square_feet is not None and params.square_feet > 0:
        vents = estimate_vents(params.square_feet, prices)
    else:
        raise ValueError("Need either a vent count or the square footage")

    included = prices.included_vents_per_system
    lines = [QuoteLine(f"Whole system, first {included} vents", prices.system_base)]
    if params.systems > 1:
        extra_systems = params.systems - 1
        lines.append(QuoteLine(f"Additional system ×{extra_systems}", prices.additional_system * extra_systems))

    extra_vents = max(0, vents - included * params.systems)
    if extra_vents > 0:
        lines.append(QuoteLine(f"{extra_vents} extra vents", prices.extra_vent * extra_vents))
    if params.dryer_vent:
        lines.append(QuoteLine("Dryer vent", prices.dryer_vent))
    if params.blower:
        lines.append(QuoteLine(f"Blower ×{params.systems}", prices.blower_per_system * params.systems))
    if params.antimicrobial:
        lines.append(QuoteLine(f"Antimicrobial ×{params.systems}", prices.antimicrobial_per_system * params.systems))

    total = sum(line.amount for line in lines)
    return Quote(tuple(lines), total, vents_estimated)
