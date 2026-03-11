"""
Tennis injury and availability scraper.

This is a best-effort ATP/WTA availability feed built from ESPN tennis news.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import re
from typing import Iterable

import pandas as pd
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

NEWS_URLS = {
    "ATP": "https://site.api.espn.com/apis/site/v2/sports/tennis/atp/news",
    "WTA": "https://site.api.espn.com/apis/site/v2/sports/tennis/wta/news",
}

STATUS_PATTERNS = [
    (
        "withdrawn",
        0.95,
        [
            r"\bwithdraw(?:s|n|al)?\b",
            r"\bpulls?\s+out\b",
        ],
    ),
    (
        "likely_out",
        0.8,
        [
            r"\bout\s+for\b",
            r"\bout\s+with\b",
            r"\bwill\s+miss\b",
            r"\bmiss(?:es|ing)?\b",
            r"\bsurgery\b",
            r"\billness\b",
            r"\bretire(?:s|d|ment)?\b",
        ],
    ),
    (
        "questionable",
        0.55,
        [
            r"\bmedical timeout\b",
            r"\binjury scare\b",
            r"\bfitness concern\b",
            r"\bhampered by\b",
            r"\bnursing\b",
            r"\bphysical issue\b",
        ],
    ),
]

INJURY_COLUMNS = [
    "TOUR",
    "PLAYER_ID",
    "PLAYER_NAME",
    "STATUS",
    "CONFIDENCE",
    "SOURCE_TS",
    "HEADLINE",
    "SUMMARY",
    "SOURCE",
    "SOURCE_URL",
]


def _normalize_tours(tours: Iterable[str]) -> tuple[str, ...]:
    """Validate and normalize requested tours."""
    normalized = []
    for tour in tours:
        upper = str(tour).upper()
        if upper not in NEWS_URLS:
            raise ValueError(f"Unsupported tennis tour: {tour}")
        if upper not in normalized:
            normalized.append(upper)
    return tuple(normalized)


def _parse_timestamp(value: str | None) -> datetime | None:
    """Parse an ISO-8601 timestamp into a timezone-aware datetime."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _classify_status(text: str) -> tuple[str | None, float | None]:
    """Map headline/description text into a normalized status bucket."""
    lowered = text.lower()
    for status, confidence, patterns in STATUS_PATTERNS:
        if any(re.search(pattern, lowered) for pattern in patterns):
            return status, confidence
    return None, None


def _extract_players(article: dict) -> list[tuple[int | None, str]]:
    """Extract player metadata from ESPN article categories."""
    players = []
    seen = set()

    for category in article.get("categories", []):
        if category.get("type") != "athlete":
            continue

        athlete_id = category.get("athleteId") or category.get("athlete", {}).get("id")
        player_name = category.get("description") or category.get("athlete", {}).get("description")
        if not player_name:
            continue

        key = (athlete_id, player_name)
        if key in seen:
            continue

        seen.add(key)
        players.append(key)

    return players


def get_tennis_injury_report(
    tours: Iterable[str] = ("ATP", "WTA"),
    lookback_days: int = 14,
) -> pd.DataFrame:
    """
    Fetch a best-effort tennis availability feed.

    Args:
        tours: Iterable of tours to include
        lookback_days: Only keep recent availability/injury articles

    Returns:
        DataFrame keyed by player/article mention with normalized status labels.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    rows = []

    for tour in _normalize_tours(tours):
        response = requests.get(NEWS_URLS[tour], headers=HEADERS, timeout=30)
        response.raise_for_status()
        payload = response.json()

        for article in payload.get("articles", []):
            source_ts = _parse_timestamp(article.get("published") or article.get("lastModified"))
            if source_ts is not None and source_ts < cutoff:
                continue

            headline = article.get("headline", "")
            summary = article.get("description", "")
            status, confidence = _classify_status(f"{headline} {summary}")
            if not status:
                continue

            players = _extract_players(article)
            if not players:
                continue

            source_url = article.get("links", {}).get("web", {}).get("href")
            for player_id, player_name in players:
                rows.append({
                    "TOUR": tour,
                    "PLAYER_ID": player_id,
                    "PLAYER_NAME": player_name,
                    "STATUS": status,
                    "CONFIDENCE": confidence,
                    "SOURCE_TS": source_ts.isoformat() if source_ts else None,
                    "HEADLINE": headline,
                    "SUMMARY": summary,
                    # TODO: replace this keyword classifier with official withdrawal
                    # lists or medical-status feeds once a stable source is chosen.
                    "SOURCE": "ESPN news keyword classifier",
                    "SOURCE_URL": source_url,
                })

    df = pd.DataFrame(rows, columns=INJURY_COLUMNS)
    if df.empty:
        return df

    return df.sort_values(
        ["SOURCE_TS", "TOUR", "PLAYER_NAME"],
        ascending=[False, True, True],
        na_position="last",
    ).reset_index(drop=True)


if __name__ == "__main__":
    print(get_tennis_injury_report().to_string())
