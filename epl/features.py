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

PLAYER_STATS_COLUMNS = (
    "season",
    "team",
    "player",
    "minutes_played",
    "goals",
    "assists",
    "shots_on_target",
    "chances_created",
    "updated_at",
)

PLAYER_STATS_COLUMN_ALIASES = {
    "player": ("player_name",),
    "minutes_played": ("minutes", "mins_played"),
    "shots_on_target": ("shots_on_target_total", "shots_on_targets"),
    "chances_created": ("key_passes",),
}

PLAYER_AVAILABILITY_COLUMNS = (
    "season",
    "team",
    "player",
    "status",
    "updated_at",
)

PLAYER_AVAILABILITY_COLUMN_ALIASES = {
    "player": ("player_name", "PLAYER_NAME"),
    "status": ("availability_status", "current_status", "CURRENT_STATUS"),
    "updated_at": ("availability_updated_at",),
    "availability_weight": ("availability_probability", "availability_pct", "status_weight"),
}

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
    "player_influence_proxy_delta",
    "availability_adjusted_player_influence_proxy_delta",
    "player_availability_headwind_proxy_delta",
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


def _normalize_optional_schema(
    df: pd.DataFrame | None,
    *,
    df_name: str,
    required_columns: Sequence[str],
    column_aliases: dict[str, Sequence[str]],
) -> pd.DataFrame:
    if df is None:
        return pd.DataFrame(columns=list(required_columns))

    normalized = df.copy()
    rename_map: dict[str, str] = {}
    for canonical_name, aliases in column_aliases.items():
        if canonical_name in normalized.columns:
            continue
        for alias_name in aliases:
            if alias_name in normalized.columns:
                rename_map[alias_name] = canonical_name
                break

    if rename_map:
        normalized = normalized.rename(columns=rename_map)

    _require_columns(normalized, df_name, required_columns)
    return normalized


def _normalize_availability_weights(
    availability: pd.DataFrame,
) -> pd.Series:
    raw_weights = (
        pd.to_numeric(availability["availability_weight"], errors="coerce")
        if "availability_weight" in availability.columns
        else pd.Series(index=availability.index, dtype="Float64")
    )
    if not raw_weights.dropna().empty and raw_weights.dropna().abs().gt(1).any():
        raw_weights = raw_weights / 100.0
    raw_weights = raw_weights.clip(lower=0.0, upper=1.0)

    statuses = availability["status"].fillna("").astype(str).str.strip().str.lower()
    status_weights = pd.Series(1.0, index=availability.index, dtype="float64")
    status_weights = status_weights.mask(statuses.str.contains("prob"), 0.9)
    status_weights = status_weights.mask(statuses.str.contains("question"), 0.5)
    status_weights = status_weights.mask(statuses.str.contains("doubt"), 0.25)
    status_weights = status_weights.mask(
        statuses.str.contains("out|unavailable|suspend|injur"),
        0.0,
    )
    return raw_weights.fillna(status_weights).fillna(1.0)


def _build_player_influence_proxy(player_stats: pd.DataFrame) -> pd.Series:
    return (
        player_stats["minutes_played"].fillna(0.0) / 900.0
        + player_stats["goals"].fillna(0.0) * 2.0
        + player_stats["assists"].fillna(0.0) * 1.5
        + player_stats["shots_on_target"].fillna(0.0) * 0.15
        + player_stats["chances_created"].fillna(0.0) * 0.10
    )


def _empty_player_team_features() -> pd.DataFrame:
    return pd.DataFrame(
        columns=[
            "season",
            "team",
            "player_total_influence_proxy",
            "availability_adjusted_player_influence_proxy",
            "player_availability_headwind_proxy",
            "player_stats_updated_at",
            "player_stats_updated_at_min",
            "player_availability_updated_at",
            "player_availability_updated_at_min",
        ]
    )


def _build_player_team_features(
    player_stats: pd.DataFrame | None,
    player_availability: pd.DataFrame | None,
) -> pd.DataFrame:
    stats_copy = _normalize_optional_schema(
        player_stats,
        df_name="player_stats",
        required_columns=PLAYER_STATS_COLUMNS,
        column_aliases=PLAYER_STATS_COLUMN_ALIASES,
    )
    availability_copy = _normalize_optional_schema(
        player_availability,
        df_name="player_availability",
        required_columns=PLAYER_AVAILABILITY_COLUMNS,
        column_aliases=PLAYER_AVAILABILITY_COLUMN_ALIASES,
    )

    _assert_unique_key(stats_copy, "player_stats", ("season", "team", "player"))
    _assert_unique_key(availability_copy, "player_availability", ("season", "team", "player"))

    if stats_copy.empty and availability_copy.empty:
        return _empty_player_team_features()

    if not stats_copy.empty:
        stats_copy["updated_at"] = _coerce_utc(stats_copy["updated_at"], "player_stats.updated_at")
        stats_copy = _coerce_numeric(
            stats_copy,
            ("minutes_played", "goals", "assists", "shots_on_target", "chances_created"),
        )
        stats_copy["player_influence_proxy"] = _build_player_influence_proxy(stats_copy)
        stats_team_summary = (
            stats_copy.groupby(["season", "team"], as_index=False)
            .agg(
                player_total_influence_proxy=("player_influence_proxy", "sum"),
                player_stats_updated_at=("updated_at", "max"),
                player_stats_updated_at_min=("updated_at", "min"),
            )
            .reset_index(drop=True)
        )
    else:
        stats_team_summary = _empty_player_team_features()[["season", "team"]].copy()
        stats_team_summary["player_total_influence_proxy"] = pd.Series(dtype="float64")
        stats_team_summary["player_stats_updated_at"] = pd.Series(dtype="datetime64[ns, UTC]")
        stats_team_summary["player_stats_updated_at_min"] = pd.Series(dtype="datetime64[ns, UTC]")

    if not availability_copy.empty:
        availability_copy["updated_at"] = _coerce_utc(
            availability_copy["updated_at"],
            "player_availability.updated_at",
        )
        availability_copy["availability_weight"] = _normalize_availability_weights(availability_copy)
        availability_team_summary = (
            availability_copy.groupby(["season", "team"], as_index=False)
            .agg(
                player_availability_updated_at=("updated_at", "max"),
                player_availability_updated_at_min=("updated_at", "min"),
            )
            .reset_index(drop=True)
        )
    else:
        availability_team_summary = _empty_player_team_features()[["season", "team"]].copy()
        availability_team_summary["player_availability_updated_at"] = pd.Series(
            dtype="datetime64[ns, UTC]"
        )
        availability_team_summary["player_availability_updated_at_min"] = pd.Series(
            dtype="datetime64[ns, UTC]"
        )

    if not stats_copy.empty:
        joined_players = stats_copy.merge(
            availability_copy[["season", "team", "player", "availability_weight"]],
            on=["season", "team", "player"],
            how="left",
        )
        joined_players["availability_weight"] = joined_players["availability_weight"].fillna(1.0)
        joined_players["availability_adjusted_player_influence_proxy"] = (
            joined_players["player_influence_proxy"] * joined_players["availability_weight"]
        )
        joined_players["player_availability_headwind_proxy"] = (
            joined_players["player_influence_proxy"]
            - joined_players["availability_adjusted_player_influence_proxy"]
        )
        joined_team_summary = (
            joined_players.groupby(["season", "team"], as_index=False)
            .agg(
                availability_adjusted_player_influence_proxy=(
                    "availability_adjusted_player_influence_proxy",
                    "sum",
                ),
                player_availability_headwind_proxy=("player_availability_headwind_proxy", "sum"),
            )
            .reset_index(drop=True)
        )
    else:
        joined_team_summary = _empty_player_team_features()[["season", "team"]].copy()
        joined_team_summary["availability_adjusted_player_influence_proxy"] = pd.Series(dtype="float64")
        joined_team_summary["player_availability_headwind_proxy"] = pd.Series(dtype="float64")

    player_team_features = stats_team_summary.merge(
        joined_team_summary,
        on=["season", "team"],
        how="outer",
    )
    player_team_features = player_team_features.merge(
        availability_team_summary,
        on=["season", "team"],
        how="outer",
    )

    for column_name in (
        "player_total_influence_proxy",
        "availability_adjusted_player_influence_proxy",
        "player_availability_headwind_proxy",
    ):
        player_team_features[column_name] = (
            pd.to_numeric(player_team_features[column_name], errors="coerce").fillna(0.0)
        )

    return player_team_features


def _rename_player_side_columns(candidate_rows: pd.DataFrame) -> pd.DataFrame:
    rename_map = {
        "home_player_player_total_influence_proxy": "home_player_influence_proxy",
        "away_player_player_total_influence_proxy": "away_player_influence_proxy",
        "home_player_availability_adjusted_player_influence_proxy": (
            "home_player_availability_adjusted_influence_proxy"
        ),
        "away_player_availability_adjusted_player_influence_proxy": (
            "away_player_availability_adjusted_influence_proxy"
        ),
        "home_player_player_availability_headwind_proxy": "home_player_availability_headwind_proxy",
        "away_player_player_availability_headwind_proxy": "away_player_availability_headwind_proxy",
        "home_player_player_stats_updated_at": "home_player_stats_updated_at",
        "away_player_player_stats_updated_at": "away_player_stats_updated_at",
        "home_player_player_stats_updated_at_min": "home_player_stats_updated_at_min",
        "away_player_player_stats_updated_at_min": "away_player_stats_updated_at_min",
        "home_player_player_availability_updated_at": "home_player_availability_updated_at",
        "away_player_player_availability_updated_at": "away_player_availability_updated_at",
        "home_player_player_availability_updated_at_min": "home_player_availability_updated_at_min",
        "away_player_player_availability_updated_at_min": "away_player_availability_updated_at_min",
    }
    return candidate_rows.rename(columns=rename_map)


def _rowwise_datetime_reduce(df: pd.DataFrame, reducer: str) -> pd.Series:
    if df.empty:
        return pd.Series(dtype="datetime64[ns, UTC]")
    return df.apply(
        lambda row: getattr(row.dropna(), reducer)() if row.dropna().shape[0] else pd.NaT,
        axis=1,
    )


def build_matchup_features(
    fixtures: pd.DataFrame,
    team_strength: pd.DataFrame,
    team_form: pd.DataFrame,
    player_stats: pd.DataFrame | None = None,
    player_availability: pd.DataFrame | None = None,
    *,
    feature_generated_at: object | None = None,
    availability: pd.DataFrame | None = None,
    injury_availability: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """Join EPL ingest tables into one candidate-ready feature row per matchup.

    Expected schemas:
    - fixtures: match_id, season, kickoff_ts, home_team, away_team, home_score, away_score, updated_at
    - team_strength: season, team, matches_played, points, goal_diff, goals_for, goals_against,
      home_matches, home_points, home_goal_diff, away_matches, away_points, away_goal_diff, updated_at
    - team_form: season, team, window_matches, window_points, window_goal_diff, updated_at
    - player_stats (optional): season, team, player, minutes_played, goals, assists,
      shots_on_target, chances_created, updated_at
    - player_availability / availability / injury_availability (optional): season, team, player,
      status, updated_at, with an optional availability_weight / availability_probability column
    """

    availability_sources = [source for source in (player_availability, availability, injury_availability) if source is not None]
    if len(availability_sources) > 1:
        raise ValueError("Provide only one of player_availability, availability, or injury_availability")
    if player_availability is None:
        player_availability = availability if availability is not None else injury_availability

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

    player_team_features = _build_player_team_features(player_stats, player_availability)

    home_strength = _rename_for_side(strength_features, "home_team", "home_strength")
    away_strength = _rename_for_side(strength_features, "away_team", "away_strength")
    home_form = _rename_for_side(form_features, "home_team", "home_form")
    away_form = _rename_for_side(form_features, "away_team", "away_form")
    home_player_features = _rename_for_side(player_team_features, "home_team", "home_player")
    away_player_features = _rename_for_side(player_team_features, "away_team", "away_player")

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
    candidate_rows = candidate_rows.merge(
        home_player_features,
        on=["season", "home_team"],
        how="left",
    )
    candidate_rows = candidate_rows.merge(
        away_player_features,
        on=["season", "away_team"],
        how="left",
    )
    candidate_rows = candidate_rows.rename(columns={"updated_at": "fixtures_updated_at"})
    candidate_rows = _rename_player_side_columns(candidate_rows)

    for column_name in (
        "home_player_influence_proxy",
        "away_player_influence_proxy",
        "home_player_availability_adjusted_influence_proxy",
        "away_player_availability_adjusted_influence_proxy",
        "home_player_availability_headwind_proxy",
        "away_player_availability_headwind_proxy",
    ):
        candidate_rows[column_name] = pd.to_numeric(
            candidate_rows[column_name],
            errors="coerce",
        ).fillna(0.0)

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
    candidate_rows["player_influence_proxy_delta"] = (
        candidate_rows["home_player_influence_proxy"] - candidate_rows["away_player_influence_proxy"]
    )
    candidate_rows["availability_adjusted_player_influence_proxy_delta"] = (
        candidate_rows["home_player_availability_adjusted_influence_proxy"]
        - candidate_rows["away_player_availability_adjusted_influence_proxy"]
    )
    candidate_rows["player_availability_headwind_proxy_delta"] = (
        candidate_rows["home_player_availability_headwind_proxy"]
        - candidate_rows["away_player_availability_headwind_proxy"]
    )
    candidate_rows["result_goal_diff"] = candidate_rows["home_score"] - candidate_rows["away_score"]
    candidate_rows["result_total_goals"] = candidate_rows["home_score"] + candidate_rows["away_score"]
    candidate_rows["result_home_win"] = (candidate_rows["result_goal_diff"] > 0).astype("Int64")
    candidate_rows["result_draw"] = (candidate_rows["result_goal_diff"] == 0).astype("Int64")
    candidate_rows["result_away_win"] = (candidate_rows["result_goal_diff"] < 0).astype("Int64")

    oldest_timestamp_columns = [
        "fixtures_updated_at",
        "home_strength_updated_at",
        "away_strength_updated_at",
        "home_form_updated_at",
        "away_form_updated_at",
        "home_player_stats_updated_at_min",
        "away_player_stats_updated_at_min",
        "home_player_availability_updated_at_min",
        "away_player_availability_updated_at_min",
    ]
    latest_timestamp_columns = [
        "fixtures_updated_at",
        "home_strength_updated_at",
        "away_strength_updated_at",
        "home_form_updated_at",
        "away_form_updated_at",
        "home_player_stats_updated_at",
        "away_player_stats_updated_at",
        "home_player_availability_updated_at",
        "away_player_availability_updated_at",
    ]

    candidate_rows["oldest_source_updated_at"] = _rowwise_datetime_reduce(
        candidate_rows[oldest_timestamp_columns],
        "min",
    )
    candidate_rows["latest_source_updated_at"] = _rowwise_datetime_reduce(
        candidate_rows[latest_timestamp_columns],
        "max",
    )
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
        "player_influence_proxy_delta",
        "availability_adjusted_player_influence_proxy_delta",
        "player_availability_headwind_proxy_delta",
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
        "home_player_stats_updated_at",
        "away_player_stats_updated_at",
        "home_player_availability_updated_at",
        "away_player_availability_updated_at",
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
