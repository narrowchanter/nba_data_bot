"""
Tennis player stats scraper.

Uses Tennis Abstract Elo reports for basic cross-tour player rating enrichment.
"""

from __future__ import annotations

import re
from io import StringIO
from typing import Iterable

import pandas as pd
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

ELO_URLS = {
    "ATP": "https://www.tennisabstract.com/reports/atp_elo_ratings.html",
    "WTA": "https://www.tennisabstract.com/reports/wta_elo_ratings.html",
}

STATS_COLUMNS = [
    "TOUR",
    "PLAYER_NAME",
    "AGE",
    "ELO_RANK",
    "ELO_GLOBAL",
    "ELO_HARD",
    "ELO_CLAY",
    "ELO_GRASS",
    "PEAK_ELO",
    "PEAK_MONTH",
    "OFFICIAL_RANK",
    "LOG_DIFF",
    "HOLD_PCT",
    "BREAK_PCT",
    "SPW_PCT",
    "RPW_PCT",
    "TB_WIN_PCT",
    "RETIREMENT_RATE_52W",
    "SOURCE_UPDATED_AT",
    "SOURCE",
    "SOURCE_URL",
]


def _normalize_tours(tours: Iterable[str]) -> tuple[str, ...]:
    """Validate and normalize requested tours."""
    normalized = []
    for tour in tours:
        upper = str(tour).upper()
        if upper not in ELO_URLS:
            raise ValueError(f"Unsupported tennis tour: {tour}")
        if upper not in normalized:
            normalized.append(upper)
    return tuple(normalized)


def _clean_column_name(value: object) -> str:
    """Collapse whitespace and non-breaking spaces in table headers."""
    text = str(value).replace("\xa0", " ")
    return re.sub(r"\s+", " ", text).strip()


def _find_elo_table(html: str) -> pd.DataFrame:
    """Locate the player Elo table from the HTML response."""
    for table in pd.read_html(StringIO(html)):
        columns = [_clean_column_name(column) for column in table.columns]
        if "Player" in columns and "Elo Rank" in columns:
            table.columns = columns
            return table

    raise ValueError("Could not find Tennis Abstract Elo table")


def _coerce_numeric(series: pd.Series) -> pd.Series:
    """Convert a Series to numeric where possible."""
    return pd.to_numeric(series, errors="coerce")


def _rows_for_tour(tour: str) -> list[dict]:
    """Fetch and normalize a Tennis Abstract Elo table."""
    response = requests.get(ELO_URLS[tour], headers=HEADERS, timeout=30)
    response.raise_for_status()

    html = response.text
    table = _find_elo_table(html)
    updated_match = re.search(r"Last update:\s*(\d{4}-\d{2}-\d{2})", html)
    updated_at = updated_match.group(1) if updated_match else None

    official_rank_col = next(
        (column for column in table.columns if column in {"ATP Rank", "WTA Rank"}),
        None,
    )

    result = pd.DataFrame({
        "TOUR": tour,
        "PLAYER_NAME": table["Player"].astype(str).str.replace("\xa0", " ", regex=False).str.strip(),
        "AGE": _coerce_numeric(table["Age"]),
        "ELO_RANK": _coerce_numeric(table["Elo Rank"]),
        "ELO_GLOBAL": _coerce_numeric(table["Elo"]),
        "ELO_HARD": _coerce_numeric(table["hElo"]),
        "ELO_CLAY": _coerce_numeric(table["cElo"]),
        "ELO_GRASS": _coerce_numeric(table["gElo"]),
        "PEAK_ELO": _coerce_numeric(table["Peak Elo"]),
        "PEAK_MONTH": table["Peak Month"],
        "OFFICIAL_RANK": _coerce_numeric(table[official_rank_col]) if official_rank_col else pd.NA,
        "LOG_DIFF": _coerce_numeric(table["Log diff"]) if "Log diff" in table.columns else pd.NA,
        # TODO: add stable source(s) for hold%, break%, service/return points won,
        # and retirement-rate windows. Tennis Abstract Elo pages do not expose them.
        "HOLD_PCT": pd.NA,
        "BREAK_PCT": pd.NA,
        "SPW_PCT": pd.NA,
        "RPW_PCT": pd.NA,
        "TB_WIN_PCT": pd.NA,
        "RETIREMENT_RATE_52W": pd.NA,
        "SOURCE_UPDATED_AT": updated_at,
        "SOURCE": "Tennis Abstract Elo",
        "SOURCE_URL": ELO_URLS[tour],
    })

    return result[STATS_COLUMNS].to_dict("records")


def get_tennis_player_stats(tours: Iterable[str] = ("ATP", "WTA")) -> pd.DataFrame:
    """
    Fetch ATP/WTA player Elo ratings and stat placeholders.

    Args:
        tours: Iterable of tours to include

    Returns:
        DataFrame with global and surface-specific Elo ratings.
    """
    rows = []
    for tour in _normalize_tours(tours):
        rows.extend(_rows_for_tour(tour))

    df = pd.DataFrame(rows, columns=STATS_COLUMNS)
    if df.empty:
        return df

    return df.sort_values(["TOUR", "ELO_RANK"], na_position="last").reset_index(drop=True)


def get_tennis_stats(tours: Iterable[str] = ("ATP", "WTA")) -> pd.DataFrame:
    """Backward-friendly alias for the tennis player stats feed."""
    return get_tennis_player_stats(tours=tours)


if __name__ == "__main__":
    print(get_tennis_player_stats().head(20).to_string())
