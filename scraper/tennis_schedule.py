"""
Tennis schedule scraper.

Uses ESPN's public tennis scoreboard feed as a lightweight ATP/WTA singles
schedule source.
"""

from __future__ import annotations

import re
from typing import Iterable

import pandas as pd
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

SCOREBOARD_URLS = {
    "ATP": "https://site.api.espn.com/apis/site/v2/sports/tennis/atp/scoreboard",
    "WTA": "https://site.api.espn.com/apis/site/v2/sports/tennis/wta/scoreboard",
}

TOUR_GROUPING_SLUGS = {
    "ATP": {"mens-singles", "men-singles"},
    "WTA": {"womens-singles", "women-singles"},
}

SCHEDULE_COLUMNS = [
    "MATCH_ID",
    "EVENT_ID",
    "COMPETITION_ID",
    "EVENT_NAME",
    "TOUR",
    "MATCH_TYPE",
    "ROUND",
    "SURFACE",
    "SCHEDULED_UTC",
    "EVENT_START_UTC",
    "BEST_OF",
    "STATUS",
    "STATUS_STATE",
    "EVENT_LOCATION",
    "COURT",
    "PLAYER_A_ID",
    "PLAYER_A",
    "PLAYER_A_COUNTRY",
    "PLAYER_B_ID",
    "PLAYER_B",
    "PLAYER_B_COUNTRY",
    "PLAYER_A_WINNER",
    "PLAYER_B_WINNER",
    "SCORE",
    "SOURCE",
    "SOURCE_URL",
]


def _normalize_tours(tours: Iterable[str]) -> tuple[str, ...]:
    """Validate and normalize requested tours."""
    normalized = []
    for tour in tours:
        upper = str(tour).upper()
        if upper not in SCOREBOARD_URLS:
            raise ValueError(f"Unsupported tennis tour: {tour}")
        if upper not in normalized:
            normalized.append(upper)
    return tuple(normalized)


def _slugify(value: str) -> str:
    """Convert a label into a stable slug fragment."""
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _build_match_id(
    event_name: str,
    round_name: str | None,
    scheduled_utc: str | None,
    player_a: str,
    player_b: str,
) -> str:
    """Build a deterministic match identifier."""
    date_key = ""
    if scheduled_utc:
        date_key = scheduled_utc.split("T", 1)[0]

    parts = [
        _slugify(part)
        for part in [date_key, event_name, round_name or "tbd", player_a, player_b]
        if part
    ]
    return "-".join(parts)


def _format_score(competitors: list[dict]) -> str:
    """Render ESPN linescores as a compact tennis score string."""
    if not competitors:
        return ""

    max_sets = max(len(player.get("linescores", [])) for player in competitors)
    set_scores = []

    for set_index in range(max_sets):
        scores = []
        for competitor in competitors:
            linescores = competitor.get("linescores", [])
            if set_index >= len(linescores):
                scores.append("-")
                continue

            value = linescores[set_index].get("value")
            if value is None:
                scores.append("-")
                continue

            try:
                numeric = float(value)
            except (TypeError, ValueError):
                scores.append(str(value))
                continue

            scores.append(str(int(numeric)) if numeric.is_integer() else str(numeric))

        if any(score != "-" for score in scores):
            set_scores.append("-".join(scores))

    return " ".join(set_scores)


def _competition_to_row(tour: str, event: dict, competition: dict) -> dict | None:
    """Convert an ESPN competition payload into a flat match row."""
    competitors = sorted(competition.get("competitors", []), key=lambda item: item.get("order", 99))
    if len(competitors) < 2:
        return None

    player_a = competitors[0]
    player_b = competitors[1]
    athlete_a = player_a.get("athlete", {})
    athlete_b = player_b.get("athlete", {})

    scheduled_utc = competition.get("startDate") or competition.get("date")
    round_name = competition.get("round", {}).get("displayName")
    source_url = next(
        (link.get("href") for link in event.get("links", []) if "summary" in link.get("rel", [])),
        None,
    )

    return {
        "MATCH_ID": _build_match_id(
            event.get("name", ""),
            round_name,
            scheduled_utc,
            athlete_a.get("displayName", ""),
            athlete_b.get("displayName", ""),
        ),
        "EVENT_ID": event.get("id"),
        "COMPETITION_ID": competition.get("id"),
        "EVENT_NAME": event.get("name"),
        "TOUR": tour,
        "MATCH_TYPE": competition.get("type", {}).get("text"),
        "ROUND": round_name,
        # TODO: enrich surface from stable tournament metadata once a source with
        # predictable machine-readable surface fields is selected.
        "SURFACE": pd.NA,
        "SCHEDULED_UTC": scheduled_utc,
        "EVENT_START_UTC": event.get("date"),
        "BEST_OF": competition.get("format", {}).get("regulation", {}).get("periods"),
        "STATUS": (
            competition.get("status", {}).get("type", {}).get("detail")
            or competition.get("status", {}).get("type", {}).get("description")
            or competition.get("status", {}).get("type", {}).get("shortDetail")
        ),
        "STATUS_STATE": competition.get("status", {}).get("type", {}).get("state"),
        "EVENT_LOCATION": competition.get("venue", {}).get("fullName") or event.get("venue", {}).get("displayName"),
        "COURT": competition.get("venue", {}).get("court"),
        "PLAYER_A_ID": athlete_a.get("id") or player_a.get("id"),
        "PLAYER_A": athlete_a.get("displayName"),
        "PLAYER_A_COUNTRY": athlete_a.get("flag", {}).get("alt"),
        "PLAYER_B_ID": athlete_b.get("id") or player_b.get("id"),
        "PLAYER_B": athlete_b.get("displayName"),
        "PLAYER_B_COUNTRY": athlete_b.get("flag", {}).get("alt"),
        "PLAYER_A_WINNER": player_a.get("winner"),
        "PLAYER_B_WINNER": player_b.get("winner"),
        "SCORE": _format_score(competitors),
        "SOURCE": "ESPN scoreboard",
        "SOURCE_URL": source_url,
    }


def get_tennis_schedule(
    tours: Iterable[str] = ("ATP", "WTA"),
    include_completed: bool = True,
) -> pd.DataFrame:
    """
    Fetch the current ATP/WTA singles schedule.

    Args:
        tours: Iterable of tours to include, e.g. ("ATP", "WTA")
        include_completed: Whether to keep completed matches from the active draw

    Returns:
        DataFrame with one row per singles match in the active scoreboard window.
    """
    rows = []
    seen: set[tuple[str, str | None]] = set()

    for tour in _normalize_tours(tours):
        response = requests.get(SCOREBOARD_URLS[tour], headers=HEADERS, timeout=30)
        response.raise_for_status()
        payload = response.json()

        for event in payload.get("events", []):
            for grouping in event.get("groupings", []):
                slug = grouping.get("grouping", {}).get("slug")
                if slug not in TOUR_GROUPING_SLUGS[tour]:
                    continue

                for competition in grouping.get("competitions", []):
                    state = competition.get("status", {}).get("type", {}).get("state")
                    if not include_completed and state == "post":
                        continue

                    key = (tour, competition.get("id"))
                    if key in seen:
                        continue

                    row = _competition_to_row(tour, event, competition)
                    if row is not None:
                        rows.append(row)
                        seen.add(key)

    df = pd.DataFrame(rows, columns=SCHEDULE_COLUMNS)
    if df.empty:
        return df

    return df.sort_values(
        ["SCHEDULED_UTC", "TOUR", "EVENT_NAME", "ROUND", "PLAYER_A"],
        na_position="last",
    ).reset_index(drop=True)


if __name__ == "__main__":
    print(get_tennis_schedule(include_completed=False).head(20).to_string())
