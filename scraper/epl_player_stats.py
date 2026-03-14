"""
EPL player season stats ingestion.
"""

from __future__ import annotations

import pandas as pd
import requests

from .epl_common import resolve_season_start_year

PLAYER_STATS_URL = "https://understat.com/main/getPlayersStats/"

PLAYER_STATS_COLUMNS = [
    "PLAYER_ID",
    "PLAYER_NAME",
    "TEAM",
    "POSITION",
    "APPEARANCES",
    "MINUTES",
    "GOALS",
    "ASSISTS",
    "YELLOW_CARDS",
    "RED_CARDS",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36",
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "X-Requested-With": "XMLHttpRequest",
}


def empty_player_stats_frame() -> pd.DataFrame:
    """Return an empty player-stats DataFrame with stable columns and dtypes."""
    return _coerce_player_stats_dtypes(pd.DataFrame(columns=PLAYER_STATS_COLUMNS))


def get_epl_player_stats(season_start_year: int | None = None) -> pd.DataFrame:
    """
    Fetch EPL player season stats.

    The upstream Understat payload includes season-level player rows with
    appearances, minutes, goals, assists, yellow cards, and red cards.
    Network, JSON, or payload-shape errors return an empty DataFrame with the
    expected schema.
    """
    if season_start_year is None:
        season_start_year = resolve_season_start_year()

    payload = {
        "league": "EPL",
        "season": str(season_start_year),
    }
    headers = {
        **HEADERS,
        "Referer": f"https://understat.com/league/EPL/{season_start_year}",
    }

    try:
        response = requests.post(
            PLAYER_STATS_URL,
            headers=headers,
            data=payload,
            timeout=30,
        )
        response.raise_for_status()
        body = response.json()
    except (requests.RequestException, ValueError):
        return empty_player_stats_frame()

    players = body.get("players") if isinstance(body, dict) else None
    if not isinstance(players, list):
        return empty_player_stats_frame()

    rows = []

    try:
        for item in players:
            if not isinstance(item, dict):
                continue

            rows.append(
                {
                    "PLAYER_ID": _coerce_text(item.get("id")),
                    "PLAYER_NAME": _coerce_text(item.get("player_name")),
                    "TEAM": _coerce_text(item.get("team_title")),
                    "POSITION": _coerce_text(item.get("position")),
                    "APPEARANCES": _coerce_nullable_int(item.get("games")),
                    "MINUTES": _coerce_nullable_int(item.get("time")),
                    "GOALS": _coerce_nullable_int(item.get("goals")),
                    "ASSISTS": _coerce_nullable_int(item.get("assists")),
                    "YELLOW_CARDS": _coerce_nullable_int(item.get("yellow_cards")),
                    "RED_CARDS": _coerce_nullable_int(item.get("red_cards")),
                }
            )
    except (TypeError, ValueError):
        return empty_player_stats_frame()

    df = pd.DataFrame(rows, columns=PLAYER_STATS_COLUMNS)
    if df.empty:
        return empty_player_stats_frame()

    df = _coerce_player_stats_dtypes(df)
    df = df.sort_values(
        by=[
            "GOALS",
            "ASSISTS",
            "MINUTES",
            "APPEARANCES",
            "PLAYER_NAME",
            "TEAM",
            "PLAYER_ID",
        ],
        ascending=[False, False, False, False, True, True, True],
        kind="mergesort",
        na_position="last",
    ).reset_index(drop=True)
    return df


def _coerce_text(value: object) -> str:
    return " ".join(str(value or "").split())


def _coerce_nullable_int(value: object) -> int | None:
    if value in (None, ""):
        return None

    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Could not parse integer value: {value}") from exc


def _coerce_player_stats_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    numeric_columns = [
        "APPEARANCES",
        "MINUTES",
        "GOALS",
        "ASSISTS",
        "YELLOW_CARDS",
        "RED_CARDS",
    ]
    text_columns = ["PLAYER_ID", "PLAYER_NAME", "TEAM", "POSITION"]

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce").astype("Int64")

    for column in text_columns:
        df[column] = df[column].fillna("").astype("string")

    return df[PLAYER_STATS_COLUMNS]


__all__ = ["PLAYER_STATS_COLUMNS", "empty_player_stats_frame", "get_epl_player_stats"]
