"""
EPL player availability ingestion from official Premier League bootstrap feeds.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

import pandas as pd
import requests

from .epl import normalize_team_name

BOOTSTRAP_URLS = (
    "https://draft.premierleague.com/api/bootstrap-static",
    "https://fantasy.premierleague.com/api/bootstrap-static/",
)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    "Accept": "application/json, text/plain, */*",
}

STATUS_BUCKETS = ("available", "questionable", "out", "suspended", "unknown")

AVAILABILITY_COLUMNS = [
    "PLAYER_ID",
    "PLAYER_NAME",
    "TEAM",
    "POSITION",
    "STATUS_BUCKET",
    "RAW_STATUS",
    "CHANCE_OF_PLAYING_THIS_ROUND",
    "CHANCE_OF_PLAYING_NEXT_ROUND",
    "REASON",
    "SOURCE",
    "STATUS_TIMESTAMP",
    "FETCHED_AT",
]

STATUS_SORT_ORDER = {
    "out": 0,
    "suspended": 1,
    "questionable": 2,
    "unknown": 3,
    "available": 4,
}

SUSPENSION_KEYWORDS = (
    "suspend",
    "suspension",
    "banned",
    "ban",
    "red card",
)


@dataclass(frozen=True)
class AvailabilityEntry:
    player_id: int | None
    player_name: str
    team: str
    position: str
    status_bucket: str
    raw_status: str
    chance_of_playing_this_round: int | None
    chance_of_playing_next_round: int | None
    reason: str
    source: str
    status_timestamp: str
    fetched_at: str


def empty_availability_frame() -> pd.DataFrame:
    """Return an empty availability DataFrame with stable columns and dtypes."""
    return _coerce_availability_dtypes(pd.DataFrame(columns=AVAILABILITY_COLUMNS))


def normalize_status_bucket(
    raw_status: object,
    *,
    reason: object = "",
    chance_of_playing_this_round: object = None,
    chance_of_playing_next_round: object = None,
) -> str:
    """
    Normalize official Premier League availability flags into stable buckets.
    """
    status_code = _clean_text(raw_status).lower()
    reason_text = _clean_text(reason).lower()
    chance_values = [
        value
        for value in (
            _coerce_nullable_int(chance_of_playing_this_round),
            _coerce_nullable_int(chance_of_playing_next_round),
        )
        if value is not None
    ]
    highest_known_chance = max(chance_values) if chance_values else None

    if any(keyword in reason_text for keyword in SUSPENSION_KEYWORDS) or status_code == "s":
        return "suspended"

    if status_code == "a":
        return "available"

    if status_code == "d":
        return "questionable"

    if highest_known_chance is not None:
        if highest_known_chance >= 100:
            return "available"
        if highest_known_chance > 0:
            return "questionable"
        return "out"

    if status_code in {"i", "u", "n"}:
        return "out"

    return "unknown"


def get_epl_availability_report(
    *,
    fetched_at: object | None = None,
) -> pd.DataFrame:
    """
    Fetch EPL availability data from the official Premier League bootstrap feed.

    The scraper tries the official Draft bootstrap feed first and falls back to
    the standard Fantasy bootstrap feed if the primary source is unavailable or
    malformed. Any unrecoverable error returns an empty DataFrame with the
    expected schema.
    """
    fetched_timestamp = _normalize_timestamp(fetched_at)
    payload, source_url = _fetch_bootstrap_payload()

    if payload is None or source_url is None:
        return empty_availability_frame()

    entries = _parse_bootstrap_payload(
        payload,
        source_url=source_url,
        fetched_at=fetched_timestamp.isoformat().replace("+00:00", "Z"),
    )

    if not entries:
        return empty_availability_frame()

    df = pd.DataFrame(
        [
            {
                "PLAYER_ID": entry.player_id,
                "PLAYER_NAME": entry.player_name,
                "TEAM": entry.team,
                "POSITION": entry.position,
                "STATUS_BUCKET": entry.status_bucket,
                "RAW_STATUS": entry.raw_status,
                "CHANCE_OF_PLAYING_THIS_ROUND": entry.chance_of_playing_this_round,
                "CHANCE_OF_PLAYING_NEXT_ROUND": entry.chance_of_playing_next_round,
                "REASON": entry.reason,
                "SOURCE": entry.source,
                "STATUS_TIMESTAMP": entry.status_timestamp,
                "FETCHED_AT": entry.fetched_at,
            }
            for entry in entries
        ],
        columns=AVAILABILITY_COLUMNS,
    )
    df = _coerce_availability_dtypes(df)
    df["_status_sort"] = df["STATUS_BUCKET"].map(STATUS_SORT_ORDER).fillna(99)
    df = df.sort_values(
        by=["TEAM", "_status_sort", "PLAYER_NAME"],
        kind="mergesort",
        na_position="last",
    ).drop(columns="_status_sort")
    return df.reset_index(drop=True)


def summarize_availability_by_team(df: pd.DataFrame) -> dict[str, dict[str, list[str]]]:
    """
    Summarize EPL availability rows by team and normalized status bucket.
    """
    summary: dict[str, dict[str, list[str]]] = {}

    for team in sorted(df["TEAM"].dropna().unique()):
        team_df = df[df["TEAM"] == team]
        team_summary: dict[str, list[str]] = {}

        for bucket in STATUS_BUCKETS:
            players = team_df.loc[team_df["STATUS_BUCKET"] == bucket, "PLAYER_NAME"].tolist()
            if players:
                team_summary[bucket] = players

        if team_summary:
            summary[team] = team_summary

    return summary


def _fetch_bootstrap_payload() -> tuple[dict | None, str | None]:
    for url in BOOTSTRAP_URLS:
        try:
            response = requests.get(url, headers=HEADERS, timeout=30)
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError):
            continue

        if _is_bootstrap_payload(payload):
            return payload, url

    return None, None


def _is_bootstrap_payload(payload: object) -> bool:
    if not isinstance(payload, dict):
        return False

    return isinstance(payload.get("elements"), list) and isinstance(payload.get("teams"), list)


def _parse_bootstrap_payload(
    payload: dict,
    *,
    source_url: str,
    fetched_at: str,
) -> list[AvailabilityEntry]:
    if not _is_bootstrap_payload(payload):
        return []

    team_lookup = _build_team_lookup(payload.get("teams", []))
    if not team_lookup:
        return []

    position_lookup = _build_position_lookup(payload.get("element_types", []))
    entries: list[AvailabilityEntry] = []

    for element in payload.get("elements", []):
        if not isinstance(element, dict):
            continue

        team_id = _coerce_nullable_int(element.get("team"))
        if team_id is None:
            continue

        team_name = team_lookup.get(team_id)
        if not team_name:
            continue

        player_name = _build_player_name(element)
        if not player_name:
            continue

        chance_this_round = _coerce_nullable_int(element.get("chance_of_playing_this_round"))
        chance_next_round = _coerce_nullable_int(element.get("chance_of_playing_next_round"))
        reason = _clean_text(element.get("news"))
        raw_status = _clean_text(element.get("status")).lower()
        status_timestamp = _first_valid_timestamp(
            element.get("news_updated"),
            element.get("news_added"),
            element.get("news_return"),
        )
        position = position_lookup.get(
            _coerce_nullable_int(element.get("element_type")),
            "",
        )

        entries.append(
            AvailabilityEntry(
                player_id=_coerce_nullable_int(element.get("id")),
                player_name=player_name,
                team=team_name,
                position=position,
                status_bucket=normalize_status_bucket(
                    raw_status,
                    reason=reason,
                    chance_of_playing_this_round=chance_this_round,
                    chance_of_playing_next_round=chance_next_round,
                ),
                raw_status=raw_status,
                chance_of_playing_this_round=chance_this_round,
                chance_of_playing_next_round=chance_next_round,
                reason=reason,
                source=source_url,
                status_timestamp=status_timestamp,
                fetched_at=fetched_at,
            )
        )

    return entries


def _build_team_lookup(teams: Iterable[object]) -> dict[int, str]:
    team_lookup: dict[int, str] = {}

    for team in teams:
        if not isinstance(team, dict):
            continue

        team_id = _coerce_nullable_int(team.get("id"))
        if team_id is None:
            continue

        raw_team_name = _clean_text(team.get("name")) or _clean_text(team.get("short_name"))
        if not raw_team_name:
            continue

        try:
            team_lookup[team_id] = normalize_team_name(raw_team_name)
        except ValueError:
            team_lookup[team_id] = raw_team_name

    return team_lookup


def _build_position_lookup(element_types: Iterable[object]) -> dict[int, str]:
    position_lookup: dict[int, str] = {}

    for element_type in element_types:
        if not isinstance(element_type, dict):
            continue

        position_id = _coerce_nullable_int(element_type.get("id"))
        if position_id is None:
            continue

        position_lookup[position_id] = _clean_text(
            element_type.get("plural_name_short")
            or element_type.get("singular_name_short")
            or element_type.get("singular_name")
        )

    return position_lookup


def _build_player_name(element: dict) -> str:
    first_name = _clean_text(element.get("first_name"))
    second_name = _clean_text(element.get("second_name"))
    full_name = " ".join(part for part in (first_name, second_name) if part)

    if full_name:
        return full_name

    return _clean_text(element.get("web_name"))


def _first_valid_timestamp(*values: object) -> str:
    for value in values:
        normalized = _normalize_optional_timestamp(value)
        if normalized:
            return normalized
    return ""


def _normalize_timestamp(value: object | None) -> pd.Timestamp:
    if value is None:
        return pd.Timestamp.now(tz="UTC")

    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        return timestamp.tz_localize("UTC")
    return timestamp.tz_convert("UTC")


def _normalize_optional_timestamp(value: object) -> str:
    cleaned_value = _clean_text(value)
    if not cleaned_value:
        return ""

    try:
        return _normalize_timestamp(cleaned_value).isoformat().replace("+00:00", "Z")
    except (TypeError, ValueError):
        return ""


def _coerce_nullable_int(value: object) -> int | None:
    if value in (None, ""):
        return None

    if pd.isna(value):
        return None

    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _clean_text(value: object) -> str:
    if value is None:
        return ""

    if isinstance(value, str):
        return value.strip()

    return str(value).strip()


def _coerce_availability_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    numeric_columns = [
        "PLAYER_ID",
        "CHANCE_OF_PLAYING_THIS_ROUND",
        "CHANCE_OF_PLAYING_NEXT_ROUND",
    ]
    text_columns = [
        "PLAYER_NAME",
        "TEAM",
        "POSITION",
        "STATUS_BUCKET",
        "RAW_STATUS",
        "REASON",
        "SOURCE",
        "STATUS_TIMESTAMP",
        "FETCHED_AT",
    ]

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce").astype("Int64")

    for column in text_columns:
        df[column] = df[column].fillna("").astype("string")

    return df[AVAILABILITY_COLUMNS]


__all__ = [
    "AVAILABILITY_COLUMNS",
    "BOOTSTRAP_URLS",
    "HEADERS",
    "STATUS_BUCKETS",
    "empty_availability_frame",
    "get_epl_availability_report",
    "normalize_status_bucket",
    "summarize_availability_by_team",
]
