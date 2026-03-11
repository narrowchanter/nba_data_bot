"""
Shared helpers for ESPN-backed tennis scrapers.
"""

from functools import lru_cache
from typing import Iterable

import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
}

DEFAULT_TOURS = ("ATP", "WTA")

TOUR_LABELS = {
    "atp": "ATP",
    "wta": "WTA",
    "ATP": "ATP",
    "WTA": "WTA",
}

SITE_API_BASE = "https://site.api.espn.com/apis/site/v2/sports/tennis"
CORE_API_BASE = "https://sports.core.api.espn.com/v2/sports/tennis"


def normalize_ref(ref: str) -> str:
    """Convert ESPN API refs to HTTPS URLs."""
    return ref.replace("http://", "https://")


def normalize_tours(tours: Iterable[str] | str) -> tuple[str, ...]:
    """Validate and normalize requested tours."""
    if isinstance(tours, str):
        tours = (tours,)

    normalized = []
    for tour in tours:
        upper = str(tour).upper()
        if upper not in {"ATP", "WTA"}:
            raise ValueError(f"Unsupported tennis tour: {tour}")
        if upper not in normalized:
            normalized.append(upper)

    return tuple(normalized)


def tour_slug(tour: str) -> str:
    """Convert a normalized tour name into the ESPN URL slug."""
    return normalize_tours((tour,))[0].lower()


@lru_cache(maxsize=512)
def fetch_json(url: str) -> dict:
    """Fetch and cache a JSON document."""
    response = requests.get(url, headers=HEADERS, timeout=30)
    response.raise_for_status()
    return response.json()
