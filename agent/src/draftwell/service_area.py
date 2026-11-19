import re

from draftwell.config import BusinessConfig


def normalize_zip(raw: str) -> str | None:
    """Return the 5-digit ZIP from '30307' or '30307-1234' (spaces ignored), else None."""
    cleaned = "".join(raw.split())
    if re.fullmatch(r"[0-9]{5}(-[0-9]{4})?", cleaned):
        return cleaned[:5]
    return None


def is_in_service_area(raw_zip: str, config: BusinessConfig) -> bool:
    zip_code = normalize_zip(raw_zip)
    return zip_code is not None and zip_code in config.service_zips
