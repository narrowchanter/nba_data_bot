"""
Tennis feature builder.

Combines schedule, rankings, Elo ratings, and availability notes into a simple
matchup feature table.
"""

from __future__ import annotations

import math
import re

import pandas as pd

from .tennis_injuries import get_tennis_injury_report
from .tennis_rankings import get_tennis_rankings
from .tennis_schedule import get_tennis_schedule
from .tennis_stats import get_tennis_player_stats

FEATURE_COLUMNS = [
    "MATCH_ID",
    "TOUR",
    "EVENT_NAME",
    "ROUND",
    "SCHEDULED_UTC",
    "SURFACE",
    "PLAYER_A",
    "PLAYER_B",
    "PLAYER_A_RANK",
    "PLAYER_B_RANK",
    "RANK_DELTA",
    "PLAYER_A_ELO",
    "PLAYER_B_ELO",
    "ELO_DELTA_GLOBAL",
    "ELO_DELTA_SURFACE",
    "HOLD_BREAK_COMPOSITE_DELTA",
    "FORM_DELTA",
    "FATIGUE_DELTA",
    "INJURY_STATUS_A",
    "INJURY_STATUS_B",
    "INJURY_FLAG_A",
    "INJURY_FLAG_B",
    "WITHDRAWAL_RISK_SCORE_A",
    "WITHDRAWAL_RISK_SCORE_B",
    "MODEL_WIN_PROB_A",
    "MODEL_WIN_PROB_B",
    "CONFIDENCE_GRADE",
    "QUALITY_STATE",
]

INJURY_SCORES = {
    "available": 0.0,
    "questionable": 0.35,
    "likely_out": 0.75,
    "withdrawn": 1.0,
}


def _normalize_player_name(value: str | None) -> str:
    """Generate a loose player-name key for cross-source joins."""
    if not value:
        return ""
    return re.sub(r"[^a-z0-9]+", "", value.lower())


def _safe_float(value: object) -> float | None:
    """Convert a scalar to float when possible."""
    if value is None or value is pd.NA:
        return None
    if pd.isna(value):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _build_lookup(df: pd.DataFrame) -> dict[tuple[str, str], dict]:
    """Index a DataFrame by tour and normalized player name."""
    lookup: dict[tuple[str, str], dict] = {}
    if df.empty:
        return lookup

    for _, row in df.iterrows():
        player_name = row.get("PLAYER_NAME")
        key = (str(row.get("TOUR", "")).upper(), _normalize_player_name(player_name))
        if not key[0] or not key[1]:
            continue
        lookup[key] = row.to_dict()

    return lookup


def _build_injury_lookup(df: pd.DataFrame) -> dict[tuple[str, str], dict]:
    """Collapse multiple news hits into one severity-ranked injury record."""
    lookup: dict[tuple[str, str], dict] = {}
    if df.empty:
        return lookup

    ordered = df.sort_values(
        ["CONFIDENCE", "SOURCE_TS"],
        ascending=[False, False],
        na_position="last",
    )

    for _, row in ordered.iterrows():
        key = (str(row.get("TOUR", "")).upper(), _normalize_player_name(row.get("PLAYER_NAME")))
        if not key[0] or not key[1]:
            continue

        severity = INJURY_SCORES.get(row.get("STATUS"), 0.0)
        current = lookup.get(key)
        if current is None or severity > current["severity"]:
            payload = row.to_dict()
            payload["severity"] = severity
            lookup[key] = payload

    return lookup


def _surface_elo(stats_row: dict | None, surface: object) -> float | None:
    """Select the most relevant Elo for a match surface."""
    if not stats_row:
        return None

    surface_name = str(surface).lower() if surface is not None and surface is not pd.NA else ""
    if surface_name == "clay":
        return _safe_float(stats_row.get("ELO_CLAY"))
    if surface_name == "grass":
        return _safe_float(stats_row.get("ELO_GRASS"))
    if surface_name in {"hard", "indoor_hard"}:
        return _safe_float(stats_row.get("ELO_HARD"))

    # TODO: use tournament-level surface metadata so this does not have to
    # fall back to a generic rating for hard/indoor-hard ambiguity.
    return _safe_float(stats_row.get("ELO_GLOBAL"))


def _grade_confidence(
    quality_state: str,
    surface_known: bool,
    injury_status_a: str,
    injury_status_b: str,
) -> str:
    """Assign a simple confidence grade to a feature row."""
    if "withdrawn" in {injury_status_a, injury_status_b}:
        return "C"
    if quality_state == "complete" and surface_known:
        return "A"
    if quality_state in {"complete", "partial"}:
        return "B"
    return "C"


def build_tennis_features(
    schedule_df: pd.DataFrame | None = None,
    rankings_df: pd.DataFrame | None = None,
    stats_df: pd.DataFrame | None = None,
    injuries_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Build matchup features from the available tennis source tables.

    This is intentionally heuristic: it provides a stable scaffold for future
    feature engineering without pretending to be a production tennis model.
    """
    if schedule_df is None:
        schedule_df = get_tennis_schedule(include_completed=False)
    if rankings_df is None:
        rankings_df = get_tennis_rankings(limit=None)
    if stats_df is None:
        stats_df = get_tennis_player_stats()
    if injuries_df is None:
        injuries_df = get_tennis_injury_report()

    if schedule_df.empty:
        return pd.DataFrame(columns=FEATURE_COLUMNS)

    ranking_lookup = _build_lookup(rankings_df)
    stats_lookup = _build_lookup(stats_df)
    injury_lookup = _build_injury_lookup(injuries_df)

    rows = []
    for _, match in schedule_df.iterrows():
        tour = str(match.get("TOUR", "")).upper()
        player_a = match.get("PLAYER_A")
        player_b = match.get("PLAYER_B")

        key_a = (tour, _normalize_player_name(player_a))
        key_b = (tour, _normalize_player_name(player_b))

        ranking_a = ranking_lookup.get(key_a, {})
        ranking_b = ranking_lookup.get(key_b, {})
        stats_a = stats_lookup.get(key_a, {})
        stats_b = stats_lookup.get(key_b, {})
        injury_a = injury_lookup.get(key_a)
        injury_b = injury_lookup.get(key_b)

        rank_a = _safe_float(ranking_a.get("RANK"))
        rank_b = _safe_float(ranking_b.get("RANK"))
        elo_global_a = _safe_float(stats_a.get("ELO_GLOBAL"))
        elo_global_b = _safe_float(stats_b.get("ELO_GLOBAL"))
        elo_surface_a = _surface_elo(stats_a, match.get("SURFACE"))
        elo_surface_b = _surface_elo(stats_b, match.get("SURFACE"))

        rank_delta = (rank_b - rank_a) if rank_a is not None and rank_b is not None else None
        elo_delta_global = (
            elo_global_a - elo_global_b
            if elo_global_a is not None and elo_global_b is not None
            else None
        )
        elo_delta_surface = (
            elo_surface_a - elo_surface_b
            if elo_surface_a is not None and elo_surface_b is not None
            else None
        )

        injury_status_a = injury_a.get("STATUS", "available") if injury_a else "available"
        injury_status_b = injury_b.get("STATUS", "available") if injury_b else "available"
        risk_a = injury_a.get("severity", 0.0) if injury_a else 0.0
        risk_b = injury_b.get("severity", 0.0) if injury_b else 0.0

        if injury_status_a == "withdrawn":
            model_win_prob_a = 0.01
        elif injury_status_b == "withdrawn":
            model_win_prob_a = 0.99
        else:
            score = 0.0
            if elo_delta_surface is not None:
                score += 0.7 * elo_delta_surface
            if elo_delta_global is not None:
                score += (0.3 if elo_delta_surface is not None else 1.0) * elo_delta_global
            if rank_delta is not None:
                score += max(min(rank_delta, 75.0), -75.0) * 4.0
            score += (risk_b - risk_a) * 120.0
            model_win_prob_a = 1.0 / (1.0 + math.pow(10.0, -score / 400.0))

        model_win_prob_b = 1.0 - model_win_prob_a

        completeness = sum(
            value is not None
            for value in [rank_a, rank_b, elo_global_a, elo_global_b]
        )
        if completeness == 4:
            quality_state = "complete"
        elif completeness >= 2:
            quality_state = "partial"
        else:
            quality_state = "sparse"

        surface_value = match.get("SURFACE")
        surface_known = bool(surface_value is not None and surface_value is not pd.NA and not pd.isna(surface_value))

        rows.append({
            "MATCH_ID": match.get("MATCH_ID"),
            "TOUR": tour,
            "EVENT_NAME": match.get("EVENT_NAME"),
            "ROUND": match.get("ROUND"),
            "SCHEDULED_UTC": match.get("SCHEDULED_UTC"),
            "SURFACE": match.get("SURFACE"),
            "PLAYER_A": player_a,
            "PLAYER_B": player_b,
            "PLAYER_A_RANK": rank_a,
            "PLAYER_B_RANK": rank_b,
            "RANK_DELTA": rank_delta if rank_delta is not None else pd.NA,
            "PLAYER_A_ELO": elo_surface_a if elo_surface_a is not None else elo_global_a,
            "PLAYER_B_ELO": elo_surface_b if elo_surface_b is not None else elo_global_b,
            "ELO_DELTA_GLOBAL": elo_delta_global if elo_delta_global is not None else pd.NA,
            "ELO_DELTA_SURFACE": elo_delta_surface if elo_delta_surface is not None else pd.NA,
            # TODO: populate these once hold/break and recent-form sources are wired in.
            "HOLD_BREAK_COMPOSITE_DELTA": pd.NA,
            "FORM_DELTA": pd.NA,
            "FATIGUE_DELTA": pd.NA,
            "INJURY_STATUS_A": injury_status_a,
            "INJURY_STATUS_B": injury_status_b,
            "INJURY_FLAG_A": injury_status_a != "available",
            "INJURY_FLAG_B": injury_status_b != "available",
            "WITHDRAWAL_RISK_SCORE_A": risk_a,
            "WITHDRAWAL_RISK_SCORE_B": risk_b,
            "MODEL_WIN_PROB_A": round(model_win_prob_a, 4),
            "MODEL_WIN_PROB_B": round(model_win_prob_b, 4),
            "CONFIDENCE_GRADE": _grade_confidence(
                quality_state=quality_state,
                surface_known=surface_known,
                injury_status_a=injury_status_a,
                injury_status_b=injury_status_b,
            ),
            "QUALITY_STATE": quality_state,
        })

    return pd.DataFrame(rows, columns=FEATURE_COLUMNS)


def get_tennis_features(
    schedule_df: pd.DataFrame | None = None,
    rankings_df: pd.DataFrame | None = None,
    stats_df: pd.DataFrame | None = None,
    injuries_df: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Alias for the tennis feature builder."""
    return build_tennis_features(
        schedule_df=schedule_df,
        rankings_df=rankings_df,
        stats_df=stats_df,
        injuries_df=injuries_df,
    )


if __name__ == "__main__":
    print(build_tennis_features().head(20).to_string())
