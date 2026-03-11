"""
Tennis rankings scraper.

Uses ESPN's public rankings feed for ATP/WTA player rankings.
"""

from __future__ import annotations

from typing import Iterable

import pandas as pd
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

RANKINGS_URLS = {
    "ATP": "https://site.api.espn.com/apis/site/v2/sports/tennis/atp/rankings",
    "WTA": "https://site.api.espn.com/apis/site/v2/sports/tennis/wta/rankings",
}

RANKING_COLUMNS = [
    "TOUR",
    "RANK",
    "PREVIOUS_RANK",
    "POINTS",
    "TREND",
    "PLAYER_ID",
    "PLAYER_NAME",
    "SHORT_NAME",
    "AGE",
    "ACTIVE",
    "COUNTRY",
    "COUNTRY_CODE",
    "BIRTH_PLACE",
    "RANKING_DATE",
    "SOURCE",
    "SOURCE_URL",
]


def _normalize_tours(tours: Iterable[str]) -> tuple[str, ...]:
    """Validate and normalize requested tours."""
    normalized = []
    for tour in tours:
        upper = str(tour).upper()
        if upper not in RANKINGS_URLS:
            raise ValueError(f"Unsupported tennis tour: {tour}")
        if upper not in normalized:
            normalized.append(upper)
    return tuple(normalized)


def _extract_country_code(flag_url: str | None) -> str | None:
    """Extract a country code from ESPN's flag asset URL."""
    if not flag_url:
        return None
    filename = flag_url.rsplit("/", 1)[-1]
    return filename.split(".", 1)[0].upper()


def _rows_for_tour(tour: str, limit: int | None) -> list[dict]:
    """Fetch and normalize rankings for a single tour."""
    response = requests.get(RANKINGS_URLS[tour], headers=HEADERS, timeout=30)
    response.raise_for_status()
    payload = response.json()

    ranking_blocks = payload.get("rankings", [])
    if not ranking_blocks:
        return []

    ranking_block = ranking_blocks[0]
    ranking_date = ranking_block.get("update")
    ranks = ranking_block.get("ranks", [])
    if limit is not None:
        ranks = ranks[:limit]

    rows = []
    for item in ranks:
        athlete = item.get("athlete", {})
        rows.append({
            "TOUR": tour,
            "RANK": item.get("current"),
            "PREVIOUS_RANK": item.get("previous"),
            "POINTS": item.get("points"),
            "TREND": item.get("trend"),
            "PLAYER_ID": athlete.get("id"),
            "PLAYER_NAME": athlete.get("displayName"),
            "SHORT_NAME": athlete.get("shortname") or athlete.get("shortName"),
            "AGE": athlete.get("age"),
            "ACTIVE": athlete.get("active"),
            "COUNTRY": athlete.get("flagAltText") or athlete.get("citizenshipCountry"),
            "COUNTRY_CODE": _extract_country_code(athlete.get("flag")),
            "BIRTH_PLACE": athlete.get("birthPlace", {}).get("summary"),
            "RANKING_DATE": ranking_date,
            "SOURCE": "ESPN rankings",
            "SOURCE_URL": RANKINGS_URLS[tour],
        })

    return rows


def get_tennis_rankings(
    tours: Iterable[str] = ("ATP", "WTA"),
    limit: int | None = 250,
) -> pd.DataFrame:
    """
    Fetch ATP/WTA player rankings.

    Args:
        tours: Iterable of tours to include
        limit: Maximum players per tour, or None for all available entries

    Returns:
        DataFrame with ATP/WTA rankings and basic player metadata.
    """
    rows = []
    for tour in _normalize_tours(tours):
        rows.extend(_rows_for_tour(tour, limit=limit))

    df = pd.DataFrame(rows, columns=RANKING_COLUMNS)
    if df.empty:
        return df

    return df.sort_values(["TOUR", "RANK"], na_position="last").reset_index(drop=True)


if __name__ == "__main__":
    print(get_tennis_rankings(limit=10).to_string())
