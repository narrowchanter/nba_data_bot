"""
EPL fixtures and results ingestion.
"""

from __future__ import annotations

import pandas as pd

from .epl_common import MATCH_COLUMNS, fetch_match_feed


def get_epl_fixtures_results(season_start_year: int | None = None) -> pd.DataFrame:
    """
    Fetch all EPL matches for a season.

    Returns a deterministic DataFrame sorted by kickoff, then match number.
    Errors return an empty DataFrame with the expected schema.
    """
    return fetch_match_feed(season_start_year=season_start_year)


def get_epl_results(season_start_year: int | None = None) -> pd.DataFrame:
    """
    Fetch completed EPL matches for a season.

    Errors return an empty DataFrame with the expected schema.
    """
    df = fetch_match_feed(season_start_year=season_start_year)
    return df[df["STATUS"] == "completed"].reset_index(drop=True)[MATCH_COLUMNS]


def get_epl_fixtures(season_start_year: int | None = None) -> pd.DataFrame:
    """
    Fetch upcoming EPL fixtures for a season.

    Errors return an empty DataFrame with the expected schema.
    """
    df = fetch_match_feed(season_start_year=season_start_year)
    return df[df["STATUS"] == "scheduled"].reset_index(drop=True)[MATCH_COLUMNS]


__all__ = [
    "get_epl_fixtures_results",
    "get_epl_results",
    "get_epl_fixtures",
]
