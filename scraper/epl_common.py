"""
Shared helpers for EPL data ingestion.
"""

from __future__ import annotations

from datetime import date, datetime, timezone

import pandas as pd
import requests

FEED_URL_TEMPLATE = "https://fixturedownload.com/feed/json/epl-{season_start_year}"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
}

MATCH_COLUMNS = [
    "MATCH_NUMBER",
    "ROUND_NUMBER",
    "KICKOFF_UTC",
    "LOCATION",
    "HOME_TEAM",
    "AWAY_TEAM",
    "STATUS",
    "HOME_SCORE",
    "AWAY_SCORE",
    "RESULT",
]


def resolve_season_start_year(as_of: date | None = None) -> int:
    """
    Resolve the EPL season start year for a given date.

    EPL seasons begin in the latter half of the calendar year, so dates from
    January through June belong to the previous season start year.
    """
    if as_of is None:
        as_of = datetime.now(timezone.utc).date()

    return as_of.year if as_of.month >= 7 else as_of.year - 1


def empty_match_frame() -> pd.DataFrame:
    """Return an empty matches DataFrame with stable columns and dtypes."""
    return _coerce_match_dtypes(pd.DataFrame(columns=MATCH_COLUMNS))


def fetch_match_feed(season_start_year: int | None = None) -> pd.DataFrame:
    """
    Fetch the EPL fixtures/results feed.

    Network, JSON, or payload-shape errors are handled by returning an empty
    DataFrame with the expected schema.
    """
    if season_start_year is None:
        season_start_year = resolve_season_start_year()

    url = FEED_URL_TEMPLATE.format(season_start_year=season_start_year)

    try:
        response = requests.get(url, headers=HEADERS, timeout=30)
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError):
        return empty_match_frame()

    if not isinstance(payload, list):
        return empty_match_frame()

    rows = []

    try:
        for item in payload:
            if not isinstance(item, dict):
                continue

            home_score = _coerce_nullable_int(item.get("HomeTeamScore"))
            away_score = _coerce_nullable_int(item.get("AwayTeamScore"))
            is_completed = home_score is not None and away_score is not None

            rows.append(
                {
                    "MATCH_NUMBER": _coerce_nullable_int(item.get("MatchNumber")),
                    "ROUND_NUMBER": _coerce_nullable_int(item.get("RoundNumber")),
                    "KICKOFF_UTC": _parse_kickoff(item.get("DateUtc")),
                    "LOCATION": str(item.get("Location") or ""),
                    "HOME_TEAM": str(item.get("HomeTeam") or ""),
                    "AWAY_TEAM": str(item.get("AwayTeam") or ""),
                    "STATUS": "completed" if is_completed else "scheduled",
                    "HOME_SCORE": home_score,
                    "AWAY_SCORE": away_score,
                    "RESULT": _derive_result(home_score, away_score) if is_completed else "",
                }
            )
    except (TypeError, ValueError):
        return empty_match_frame()

    df = pd.DataFrame(rows, columns=MATCH_COLUMNS)
    if df.empty:
        return empty_match_frame()

    df = _coerce_match_dtypes(df)
    df = df.sort_values(
        by=["KICKOFF_UTC", "MATCH_NUMBER", "HOME_TEAM", "AWAY_TEAM"],
        kind="mergesort",
        na_position="last",
    ).reset_index(drop=True)
    return df


def _parse_kickoff(value: object) -> str:
    if not value:
        raise ValueError("Missing DateUtc value")

    parsed = datetime.strptime(str(value), "%Y-%m-%d %H:%M:%SZ").replace(tzinfo=timezone.utc)
    return parsed.strftime("%Y-%m-%dT%H:%M:%SZ")


def _coerce_nullable_int(value: object) -> int | None:
    if value in (None, ""):
        return None

    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Could not parse integer value: {value}") from exc


def _derive_result(home_score: int | None, away_score: int | None) -> str:
    if home_score is None or away_score is None:
        return ""
    if home_score > away_score:
        return "H"
    if away_score > home_score:
        return "A"
    return "D"


def _coerce_match_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    numeric_columns = ["MATCH_NUMBER", "ROUND_NUMBER", "HOME_SCORE", "AWAY_SCORE"]
    text_columns = ["KICKOFF_UTC", "LOCATION", "HOME_TEAM", "AWAY_TEAM", "STATUS", "RESULT"]

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce").astype("Int64")

    for column in text_columns:
        df[column] = df[column].fillna("").astype("string")

    return df[MATCH_COLUMNS]
