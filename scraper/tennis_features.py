"""
Derived tennis feature builder.
"""

import math
import re

import pandas as pd

from .tennis_injuries import get_tennis_injuries
from .tennis_rankings import get_tennis_rankings
from .tennis_schedule import get_tennis_schedule
from .tennis_stats import get_tennis_stats


FEATURE_COLUMNS = [
    "MATCH_ID",
    "TOUR",
    "TOURNAMENT",
    "DRAW",
    "ROUND",
    "START_TIME_UTC",
    "PLAYER_1",
    "PLAYER_2",
    "PLAYER_1_RANK",
    "PLAYER_2_RANK",
    "RANK_CHANGE",
    "PLAYER_1_WIN_PCT",
    "PLAYER_2_WIN_PCT",
    "WIN_PCT_DELTA",
    "PLAYER_1_TITLES",
    "PLAYER_2_TITLES",
    "TITLE_DELTA",
    "PLAYER_1_INJURY_ARTICLES",
    "PLAYER_2_INJURY_ARTICLES",
    "PLAYER_1_HAS_INJURY_SIGNAL",
    "PLAYER_2_HAS_INJURY_SIGNAL",
    "PLAYER_1_LATEST_INJURY",
    "PLAYER_2_LATEST_INJURY",
    "MODEL_WIN_PROB_1",
    "MODEL_WIN_PROB_2",
    "QUALITY_STATE",
]


def _normalize_name(value: str | None) -> str:
    """Normalize a player name for loose cross-source joins."""
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _player_key(tour: str, player_id: str | None, player_name: str | None) -> tuple[str, str]:
    """Build a lookup key using ESPN ids when possible."""
    if player_id:
        return tour, str(player_id)
    return tour, _normalize_name(player_name)


def _ranking_lookup(df: pd.DataFrame) -> dict[tuple[str, str], dict]:
    """Index ranking rows by tour and player key."""
    lookup = {}
    if df.empty:
        return lookup

    for _, row in df.iterrows():
        key = _player_key(row.get("TOUR"), row.get("PLAYER_ID"), row.get("PLAYER"))
        if not key[1]:
            continue
        lookup[key] = row.to_dict()

    return lookup


def _stats_lookup(df: pd.DataFrame) -> dict[tuple[str, str], dict]:
    """Index stats rows by tour and player key."""
    lookup = {}
    if df.empty:
        return lookup

    for _, row in df.iterrows():
        key = _player_key(row.get("TOUR"), row.get("PLAYER_ID"), row.get("PLAYER"))
        if not key[1]:
            continue
        lookup[key] = row.to_dict()

    return lookup


def _injury_lookup(df: pd.DataFrame) -> dict[tuple[str, str], dict]:
    """Collapse injury rows into one summary per player."""
    lookup = {}
    if df.empty:
        return lookup

    injury_players = df.copy()
    injury_players = injury_players.sort_values("PUBLISHED_UTC", ascending=False)
    for _, row in injury_players.iterrows():
        key = _player_key(row.get("TOUR"), row.get("PLAYER_ID"), row.get("PLAYER"))
        if not key[1]:
            continue

        current = lookup.get(key)
        if current is None:
            lookup[key] = {
                "count": 1,
                "headline": row.get("HEADLINE"),
            }
            continue

        current["count"] += 1

    return lookup


def _safe_number(value: object) -> float | None:
    """Convert a scalar into a float when possible."""
    if value is None or value is pd.NA:
        return None
    if pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def get_tennis_features(
    schedule_df: pd.DataFrame | None = None,
    rankings_df: pd.DataFrame | None = None,
    stats_df: pd.DataFrame | None = None,
    injuries_df: pd.DataFrame | None = None,
    top_n: int | None = 64,
) -> pd.DataFrame:
    """
    Build a lightweight matchup feature table from schedule, rankings, stats, and injury signals.
    """
    schedule_df = schedule_df if schedule_df is not None else get_tennis_schedule(include_completed=False)
    rankings_df = rankings_df if rankings_df is not None else get_tennis_rankings(limit=top_n)
    stats_df = stats_df if stats_df is not None else get_tennis_stats(limit=top_n)
    injuries_df = injuries_df if injuries_df is not None else get_tennis_injuries()

    if schedule_df.empty:
        return pd.DataFrame(columns=FEATURE_COLUMNS)

    ranking_lookup = _ranking_lookup(rankings_df)
    stats_lookup = _stats_lookup(stats_df)
    injury_lookup = _injury_lookup(injuries_df)

    rows = []
    for _, match in schedule_df.iterrows():
        tour = match.get("TOUR")
        player_1 = match.get("PLAYER_1")
        player_2 = match.get("PLAYER_2")

        key_1 = _player_key(tour, match.get("PLAYER_1_ID"), player_1)
        key_2 = _player_key(tour, match.get("PLAYER_2_ID"), player_2)

        ranking_1 = ranking_lookup.get(key_1, {})
        ranking_2 = ranking_lookup.get(key_2, {})
        stats_1 = stats_lookup.get(key_1, {})
        stats_2 = stats_lookup.get(key_2, {})
        injury_1 = injury_lookup.get(key_1, {})
        injury_2 = injury_lookup.get(key_2, {})

        rank_1 = _safe_number(ranking_1.get("RANK"))
        rank_2 = _safe_number(ranking_2.get("RANK"))
        rank_change = (rank_2 - rank_1) if rank_1 is not None and rank_2 is not None else None

        win_pct_1 = _safe_number(stats_1.get("WIN_PCT"))
        win_pct_2 = _safe_number(stats_2.get("WIN_PCT"))
        win_pct_delta = (win_pct_1 - win_pct_2) if win_pct_1 is not None and win_pct_2 is not None else None

        titles_1 = _safe_number(stats_1.get("SINGLES_TITLES"))
        titles_2 = _safe_number(stats_2.get("SINGLES_TITLES"))
        title_delta = (titles_1 - titles_2) if titles_1 is not None and titles_2 is not None else None

        injury_count_1 = int(injury_1.get("count", 0))
        injury_count_2 = int(injury_2.get("count", 0))

        score = 0.0
        available_signals = 0
        if rank_change is not None:
            score += max(min(rank_change, 100.0), -100.0) * 0.03
            available_signals += 1
        if win_pct_delta is not None:
            score += win_pct_delta * 2.5
            available_signals += 1
        if title_delta is not None:
            score += max(min(title_delta, 5.0), -5.0) * 0.15
            available_signals += 1

        score += (injury_count_2 - injury_count_1) * 0.2
        model_win_prob_1 = 1.0 / (1.0 + math.exp(-score))
        model_win_prob_2 = 1.0 - model_win_prob_1

        if available_signals >= 3:
            quality_state = "complete"
        elif available_signals >= 1:
            quality_state = "partial"
        else:
            quality_state = "sparse"

        rows.append(
            {
                "MATCH_ID": match.get("MATCH_ID"),
                "TOUR": tour,
                "TOURNAMENT": match.get("TOURNAMENT"),
                "DRAW": match.get("DRAW"),
                "ROUND": match.get("ROUND"),
                "START_TIME_UTC": match.get("START_TIME_UTC"),
                "PLAYER_1": player_1,
                "PLAYER_2": player_2,
                "PLAYER_1_RANK": rank_1,
                "PLAYER_2_RANK": rank_2,
                "RANK_CHANGE": rank_change,
                "PLAYER_1_WIN_PCT": win_pct_1,
                "PLAYER_2_WIN_PCT": win_pct_2,
                "WIN_PCT_DELTA": win_pct_delta,
                "PLAYER_1_TITLES": titles_1,
                "PLAYER_2_TITLES": titles_2,
                "TITLE_DELTA": title_delta,
                "PLAYER_1_INJURY_ARTICLES": injury_count_1,
                "PLAYER_2_INJURY_ARTICLES": injury_count_2,
                "PLAYER_1_HAS_INJURY_SIGNAL": injury_count_1 > 0,
                "PLAYER_2_HAS_INJURY_SIGNAL": injury_count_2 > 0,
                "PLAYER_1_LATEST_INJURY": injury_1.get("headline"),
                "PLAYER_2_LATEST_INJURY": injury_2.get("headline"),
                "MODEL_WIN_PROB_1": round(model_win_prob_1, 4),
                "MODEL_WIN_PROB_2": round(model_win_prob_2, 4),
                "QUALITY_STATE": quality_state,
            }
        )

    return pd.DataFrame(rows, columns=FEATURE_COLUMNS).sort_values(
        ["START_TIME_UTC", "TOUR", "TOURNAMENT", "ROUND"]
    ).reset_index(drop=True)


def build_tennis_features(
    schedule_df: pd.DataFrame | None = None,
    rankings_df: pd.DataFrame | None = None,
    stats_df: pd.DataFrame | None = None,
    injuries_df: pd.DataFrame | None = None,
    top_n: int | None = 64,
) -> pd.DataFrame:
    """Backward-compatible alias for the tennis feature builder."""
    return get_tennis_features(
        schedule_df=schedule_df,
        rankings_df=rankings_df,
        stats_df=stats_df,
        injuries_df=injuries_df,
        top_n=top_n,
    )
