"""Build EPL matchup features from ingest tables and validate candidate rows."""

from __future__ import annotations

from typing import Iterable, Sequence

import pandas as pd

FIXTURE_COLUMNS = (
    "match_id",
    "season",
    "kickoff_ts",
    "home_team",
    "away_team",
    "home_score",
    "away_score",
    "updated_at",
)

TEAM_STRENGTH_COLUMNS = (
    "season",
    "team",
    "matches_played",
    "points",
    "goal_diff",
    "goals_for",
    "goals_against",
    "home_matches",
    "home_points",
    "home_goal_diff",
    "away_matches",
    "away_points",
    "away_goal_diff",
    "updated_at",
)

TEAM_FORM_COLUMNS = (
    "season",
    "team",
    "window_matches",
    "window_points",
    "window_goal_diff",
    "updated_at",
)

DEFAULT_CANDIDATE_KEY_COLUMNS = ("season", "match_id")

DEFAULT_CANDIDATE_REQUIRED_COLUMNS = (
    "match_id",
    "season",
    "kickoff_ts",
    "home_team",
    "away_team",
    "home_score",
    "away_score",
    "strength_points_per_match_delta",
    "strength_goal_diff_per_match_delta",
    "form_points_per_match_delta",
    "form_goal_diff_per_match_delta",
    "home_advantage_points_per_match_delta",
    "home_advantage_goal_diff_per_match_delta",
    "oldest_source_updated_at",
    "latest_source_updated_at",
)


class EPLSanityCheckError(ValueError):
    """Raised when candidate rows fail a sanity check."""


def _require_columns(df: pd.DataFrame, df_name: str, required_columns: Iterable[str]) -> None:
    missing = sorted(set(required_columns) - set(df.columns))
    if missing:
        raise ValueError(f"{df_name} is missing required columns: {', '.join(missing)}")


def _assert_unique_key(df: pd.DataFrame, df_name: str, key_columns: Sequence[str]) -> None:
    duplicated = df.duplicated(list(key_columns), keep=False)
    if duplicated.any():
        sample = df.loc[duplicated, list(key_columns)].head(5).to_dict("records")
        raise ValueError(f"{df_name} must be unique on {list(key_columns)}; duplicates: {sample}")


def _coerce_utc(series: pd.Series, column_name: str) -> pd.Series:
    converted = pd.to_datetime(series, utc=True, errors="coerce")
    if converted.isna().any():
        raise ValueError(f"{column_name} contains invalid timestamps")
    return converted


def _coerce_numeric(df: pd.DataFrame, column_names: Iterable[str]) -> pd.DataFrame:
    converted = df.copy()
    for column_name in column_names:
        converted[column_name] = pd.to_numeric(converted[column_name], errors="coerce")
    return converted


def _safe_divide(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    denominator = pd.to_numeric(denominator, errors="coerce")
    denominator = denominator.where(denominator != 0)
    return pd.to_numeric(numerator, errors="coerce") / denominator


def _rename_for_side(df: pd.DataFrame, team_column_name: str, prefix: str) -> pd.DataFrame:
    renamed = df.rename(columns={"team": team_column_name})
    metric_columns = [column for column in renamed.columns if column not in {"season", team_column_name}]
    return renamed.rename(columns={column: f"{prefix}_{column}" for column in metric_columns})


def _normalize_current_time(current_time: object | None) -> pd.Timestamp:
    if current_time is None:
        return pd.Timestamp.now(tz="UTC")
    timestamp = pd.Timestamp(current_time)
    if timestamp.tzinfo is None:
        return timestamp.tz_localize("UTC")
    return timestamp.tz_convert("UTC")


def build_matchup_features(
    fixtures: pd.DataFrame,
    team_strength: pd.DataFrame,
    team_form: pd.DataFrame,
    *,
    feature_generated_at: object | None = None,
) -> pd.DataFrame:
    """Join EPL ingest tables into one candidate-ready feature row per matchup.

    Expected schemas:
    - fixtures: match_id, season, kickoff_ts, home_team, away_team, home_score, away_score, updated_at
    - team_strength: season, team, matches_played, points, goal_diff, goals_for, goals_against,
      home_matches, home_points, home_goal_diff, away_matches, away_points, away_goal_diff, updated_at
    - team_form: season, team, window_matches, window_points, window_goal_diff, updated_at
    """

    _require_columns(fixtures, "fixtures", FIXTURE_COLUMNS)
    _require_columns(team_strength, "team_strength", TEAM_STRENGTH_COLUMNS)
    _require_columns(team_form, "team_form", TEAM_FORM_COLUMNS)
    _assert_unique_key(fixtures, "fixtures", DEFAULT_CANDIDATE_KEY_COLUMNS)
    _assert_unique_key(team_strength, "team_strength", ("season", "team"))
    _assert_unique_key(team_form, "team_form", ("season", "team"))

    fixtures_copy = fixtures.copy()
    fixtures_copy["kickoff_ts"] = _coerce_utc(fixtures_copy["kickoff_ts"], "fixtures.kickoff_ts")
    fixtures_copy["updated_at"] = _coerce_utc(fixtures_copy["updated_at"], "fixtures.updated_at")
    fixtures_copy = _coerce_numeric(fixtures_copy, ("home_score", "away_score"))

    strength_copy = team_strength.copy()
    strength_copy["updated_at"] = _coerce_utc(strength_copy["updated_at"], "team_strength.updated_at")
    strength_copy = _coerce_numeric(
        strength_copy,
        (
            "matches_played",
            "points",
            "goal_diff",
            "goals_for",
            "goals_against",
            "home_matches",
            "home_points",
            "home_goal_diff",
            "away_matches",
            "away_points",
            "away_goal_diff",
        ),
    )
    strength_copy["strength_points_per_match"] = _safe_divide(
        strength_copy["points"], strength_copy["matches_played"]
    )
    strength_copy["strength_goal_diff_per_match"] = _safe_divide(
        strength_copy["goal_diff"], strength_copy["matches_played"]
    )
    strength_copy["strength_goals_for_per_match"] = _safe_divide(
        strength_copy["goals_for"], strength_copy["matches_played"]
    )
    strength_copy["strength_goals_against_per_match"] = _safe_divide(
        strength_copy["goals_against"], strength_copy["matches_played"]
    )
    strength_copy["home_points_per_match"] = _safe_divide(
        strength_copy["home_points"], strength_copy["home_matches"]
    )
    strength_copy["home_goal_diff_per_match"] = _safe_divide(
        strength_copy["home_goal_diff"], strength_copy["home_matches"]
    )
    strength_copy["away_points_per_match"] = _safe_divide(
        strength_copy["away_points"], strength_copy["away_matches"]
    )
    strength_copy["away_goal_diff_per_match"] = _safe_divide(
        strength_copy["away_goal_diff"], strength_copy["away_matches"]
    )
    strength_features = strength_copy[
        [
            "season",
            "team",
            "strength_points_per_match",
            "strength_goal_diff_per_match",
            "strength_goals_for_per_match",
            "strength_goals_against_per_match",
            "home_points_per_match",
            "home_goal_diff_per_match",
            "away_points_per_match",
            "away_goal_diff_per_match",
            "updated_at",
        ]
    ]

    form_copy = team_form.copy()
    form_copy["updated_at"] = _coerce_utc(form_copy["updated_at"], "team_form.updated_at")
    form_copy = _coerce_numeric(form_copy, ("window_matches", "window_points", "window_goal_diff"))
    form_copy["form_points_per_match"] = _safe_divide(
        form_copy["window_points"], form_copy["window_matches"]
    )
    form_copy["form_goal_diff_per_match"] = _safe_divide(
        form_copy["window_goal_diff"], form_copy["window_matches"]
    )
    form_features = form_copy[
        [
            "season",
            "team",
            "form_points_per_match",
            "form_goal_diff_per_match",
            "updated_at",
        ]
    ]

    home_strength = _rename_for_side(strength_features, "home_team", "home_strength")
    away_strength = _rename_for_side(strength_features, "away_team", "away_strength")
    home_form = _rename_for_side(form_features, "home_team", "home_form")
    away_form = _rename_for_side(form_features, "away_team", "away_form")

    candidate_rows = fixtures_copy.merge(
        home_strength,
        on=["season", "home_team"],
        how="left",
    )
    candidate_rows = candidate_rows.merge(
        away_strength,
        on=["season", "away_team"],
        how="left",
    )
    candidate_rows = candidate_rows.merge(
        home_form,
        on=["season", "home_team"],
        how="left",
    )
    candidate_rows = candidate_rows.merge(
        away_form,
        on=["season", "away_team"],
        how="left",
    )

    candidate_rows["strength_points_per_match_delta"] = (
        candidate_rows["home_strength_strength_points_per_match"]
        - candidate_rows["away_strength_strength_points_per_match"]
    )
    candidate_rows["strength_goal_diff_per_match_delta"] = (
        candidate_rows["home_strength_strength_goal_diff_per_match"]
        - candidate_rows["away_strength_strength_goal_diff_per_match"]
    )
    candidate_rows["strength_goals_for_per_match_delta"] = (
        candidate_rows["home_strength_strength_goals_for_per_match"]
        - candidate_rows["away_strength_strength_goals_for_per_match"]
    )
    candidate_rows["strength_goals_against_per_match_delta"] = (
        candidate_rows["home_strength_strength_goals_against_per_match"]
        - candidate_rows["away_strength_strength_goals_against_per_match"]
    )
    candidate_rows["form_points_per_match_delta"] = (
        candidate_rows["home_form_form_points_per_match"]
        - candidate_rows["away_form_form_points_per_match"]
    )
    candidate_rows["form_goal_diff_per_match_delta"] = (
        candidate_rows["home_form_form_goal_diff_per_match"]
        - candidate_rows["away_form_form_goal_diff_per_match"]
    )
    candidate_rows["home_advantage_points_per_match_delta"] = (
        candidate_rows["home_strength_home_points_per_match"]
        - candidate_rows["away_strength_away_points_per_match"]
    )
    candidate_rows["home_advantage_goal_diff_per_match_delta"] = (
        candidate_rows["home_strength_home_goal_diff_per_match"]
        - candidate_rows["away_strength_away_goal_diff_per_match"]
    )
    candidate_rows["result_goal_diff"] = candidate_rows["home_score"] - candidate_rows["away_score"]
    candidate_rows["result_total_goals"] = candidate_rows["home_score"] + candidate_rows["away_score"]
    candidate_rows["result_home_win"] = (candidate_rows["result_goal_diff"] > 0).astype("Int64")
    candidate_rows["result_draw"] = (candidate_rows["result_goal_diff"] == 0).astype("Int64")
    candidate_rows["result_away_win"] = (candidate_rows["result_goal_diff"] < 0).astype("Int64")

    timestamp_columns = [
        "updated_at",
        "home_strength_updated_at",
        "away_strength_updated_at",
        "home_form_updated_at",
        "away_form_updated_at",
    ]
    candidate_rows = candidate_rows.rename(columns={"updated_at": "fixtures_updated_at"})
    timestamp_columns[0] = "fixtures_updated_at"

    candidate_rows["oldest_source_updated_at"] = candidate_rows[timestamp_columns].min(axis=1)
    candidate_rows["latest_source_updated_at"] = candidate_rows[timestamp_columns].max(axis=1)
    candidate_rows["feature_generated_at"] = _normalize_current_time(feature_generated_at)

    ordered_columns = [
        "match_id",
        "season",
        "kickoff_ts",
        "home_team",
        "away_team",
        "home_score",
        "away_score",
        "strength_points_per_match_delta",
        "strength_goal_diff_per_match_delta",
        "strength_goals_for_per_match_delta",
        "strength_goals_against_per_match_delta",
        "form_points_per_match_delta",
        "form_goal_diff_per_match_delta",
        "home_advantage_points_per_match_delta",
        "home_advantage_goal_diff_per_match_delta",
        "result_goal_diff",
        "result_total_goals",
        "result_home_win",
        "result_draw",
        "result_away_win",
        "fixtures_updated_at",
        "home_strength_updated_at",
        "away_strength_updated_at",
        "home_form_updated_at",
        "away_form_updated_at",
        "oldest_source_updated_at",
        "latest_source_updated_at",
        "feature_generated_at",
    ]
    return candidate_rows[ordered_columns].sort_values(["season", "kickoff_ts", "match_id"]).reset_index(drop=True)


def sanity_check_candidate_rows(
    candidate_rows: pd.DataFrame,
    *,
    expected_rows: int | None = None,
    required_columns: Sequence[str] = DEFAULT_CANDIDATE_REQUIRED_COLUMNS,
    key_columns: Sequence[str] = DEFAULT_CANDIDATE_KEY_COLUMNS,
    score_columns: Sequence[str] = ("home_score", "away_score"),
    score_bounds: tuple[int, int] = (0, 20),
    timestamp_column: str = "oldest_source_updated_at",
    current_time: object | None = None,
    max_staleness: str | pd.Timedelta = "3D",
) -> dict[str, object]:
    """Validate candidate rows before model fitting or export.

    Raises EPLSanityCheckError when any check fails. On success, returns a small summary dict.
    """

    required = set(required_columns) | set(key_columns) | set(score_columns) | {timestamp_column}
    _require_columns(candidate_rows, "candidate_rows", required)

    issues: list[str] = []
    row_count = len(candidate_rows)
    if expected_rows is not None and row_count != expected_rows:
        issues.append(f"row count mismatch: expected {expected_rows}, found {row_count}")

    null_counts = candidate_rows[list(required_columns)].isna().sum()
    failing_nulls = {column: int(count) for column, count in null_counts.items() if count}
    if failing_nulls:
        issues.append(f"required column nulls: {failing_nulls}")

    duplicated = candidate_rows.duplicated(list(key_columns), keep=False)
    if duplicated.any():
        sample = candidate_rows.loc[duplicated, list(key_columns)].head(5).to_dict("records")
        issues.append(f"duplicate candidate keys on {list(key_columns)}: {sample}")

    lower_bound, upper_bound = score_bounds
    for column_name in score_columns:
        values = pd.to_numeric(candidate_rows[column_name], errors="coerce")
        invalid = values.isna() | (values < lower_bound) | (values > upper_bound) | ((values % 1) != 0)
        invalid = invalid.fillna(True)
        if invalid.any():
            sample = candidate_rows.loc[invalid, list(key_columns) + [column_name]].head(5).to_dict("records")
            issues.append(
                f"{column_name} outside score bounds {score_bounds} or non-integer values present: {sample}"
            )

    timestamps = _coerce_utc(candidate_rows[timestamp_column], f"candidate_rows.{timestamp_column}")
    now = _normalize_current_time(current_time)
    allowed_age = pd.Timedelta(max_staleness)
    stale = timestamps.isna() | ((now - timestamps) > allowed_age)
    if stale.any():
        sample = candidate_rows.loc[stale, list(key_columns) + [timestamp_column]].head(5).to_dict("records")
        issues.append(f"stale source timestamps older than {allowed_age}: {sample}")

    if issues:
        raise EPLSanityCheckError("; ".join(issues))

    oldest_timestamp = timestamps.min() if row_count else pd.NaT
    latest_timestamp = timestamps.max() if row_count else pd.NaT
    oldest_age_hours = 0.0 if row_count == 0 else round((now - oldest_timestamp).total_seconds() / 3600, 3)

    return {
        "row_count": row_count,
        "key_columns": list(key_columns),
        "oldest_source_updated_at": oldest_timestamp,
        "latest_source_updated_at": latest_timestamp,
        "oldest_source_age_hours": oldest_age_hours,
    }
