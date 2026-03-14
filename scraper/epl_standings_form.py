"""
EPL standings and recent form ingestion.
"""

from __future__ import annotations

import pandas as pd

from .epl_common import fetch_match_feed

STANDINGS_COLUMNS = [
    "POSITION",
    "TEAM",
    "PLAYED",
    "WINS",
    "DRAWS",
    "LOSSES",
    "GOALS_FOR",
    "GOALS_AGAINST",
    "GOAL_DIFF",
    "POINTS",
    "FORM",
    "FORM_POINTS",
]


def get_epl_standings_form(season_start_year: int | None = None) -> pd.DataFrame:
    """
    Build EPL standings and last-five form from completed matches.

    The table uses a deterministic final sort order of points, goal difference,
    goals scored, then team name. Errors return an empty DataFrame with the
    expected schema.
    """
    matches = fetch_match_feed(season_start_year=season_start_year)
    if matches.empty:
        return empty_standings_frame()

    teams = sorted(set(matches["HOME_TEAM"].tolist()) | set(matches["AWAY_TEAM"].tolist()))
    if not teams:
        return empty_standings_frame()

    stats = {
        team: {
            "TEAM": team,
            "PLAYED": 0,
            "WINS": 0,
            "DRAWS": 0,
            "LOSSES": 0,
            "GOALS_FOR": 0,
            "GOALS_AGAINST": 0,
            "GOAL_DIFF": 0,
            "POINTS": 0,
            "_form_history": [],
        }
        for team in teams
    }

    completed = matches[matches["STATUS"] == "completed"].copy()

    for row in completed.itertuples(index=False):
        home_score = int(row.HOME_SCORE)
        away_score = int(row.AWAY_SCORE)
        home_team = row.HOME_TEAM
        away_team = row.AWAY_TEAM

        home_stats = stats[home_team]
        away_stats = stats[away_team]

        home_stats["PLAYED"] += 1
        away_stats["PLAYED"] += 1

        home_stats["GOALS_FOR"] += home_score
        home_stats["GOALS_AGAINST"] += away_score
        away_stats["GOALS_FOR"] += away_score
        away_stats["GOALS_AGAINST"] += home_score

        if home_score > away_score:
            home_stats["WINS"] += 1
            away_stats["LOSSES"] += 1
            home_stats["POINTS"] += 3
            home_stats["_form_history"].append("W")
            away_stats["_form_history"].append("L")
        elif away_score > home_score:
            away_stats["WINS"] += 1
            home_stats["LOSSES"] += 1
            away_stats["POINTS"] += 3
            home_stats["_form_history"].append("L")
            away_stats["_form_history"].append("W")
        else:
            home_stats["DRAWS"] += 1
            away_stats["DRAWS"] += 1
            home_stats["POINTS"] += 1
            away_stats["POINTS"] += 1
            home_stats["_form_history"].append("D")
            away_stats["_form_history"].append("D")

    rows = []
    for team in teams:
        team_stats = stats[team]
        team_stats["GOAL_DIFF"] = team_stats["GOALS_FOR"] - team_stats["GOALS_AGAINST"]

        recent_form = team_stats.pop("_form_history")[-5:]
        rows.append(
            {
                "TEAM": team_stats["TEAM"],
                "PLAYED": team_stats["PLAYED"],
                "WINS": team_stats["WINS"],
                "DRAWS": team_stats["DRAWS"],
                "LOSSES": team_stats["LOSSES"],
                "GOALS_FOR": team_stats["GOALS_FOR"],
                "GOALS_AGAINST": team_stats["GOALS_AGAINST"],
                "GOAL_DIFF": team_stats["GOAL_DIFF"],
                "POINTS": team_stats["POINTS"],
                "FORM": "".join(recent_form),
                "FORM_POINTS": sum(3 if result == "W" else 1 if result == "D" else 0 for result in recent_form),
            }
        )

    standings = pd.DataFrame(rows)
    standings = standings.sort_values(
        by=["POINTS", "GOAL_DIFF", "GOALS_FOR", "TEAM"],
        ascending=[False, False, False, True],
        kind="mergesort",
    ).reset_index(drop=True)
    standings.insert(0, "POSITION", range(1, len(standings) + 1))

    return _coerce_standings_dtypes(standings)


def empty_standings_frame() -> pd.DataFrame:
    """Return an empty standings DataFrame with stable columns and dtypes."""
    return _coerce_standings_dtypes(pd.DataFrame(columns=STANDINGS_COLUMNS))


def _coerce_standings_dtypes(df: pd.DataFrame) -> pd.DataFrame:
    numeric_columns = [
        "POSITION",
        "PLAYED",
        "WINS",
        "DRAWS",
        "LOSSES",
        "GOALS_FOR",
        "GOALS_AGAINST",
        "GOAL_DIFF",
        "POINTS",
        "FORM_POINTS",
    ]
    text_columns = ["TEAM", "FORM"]

    for column in numeric_columns:
        df[column] = pd.to_numeric(df[column], errors="coerce").astype("Int64")

    for column in text_columns:
        df[column] = df[column].fillna("").astype("string")

    return df[STANDINGS_COLUMNS]


__all__ = ["get_epl_standings_form", "empty_standings_frame", "STANDINGS_COLUMNS"]
