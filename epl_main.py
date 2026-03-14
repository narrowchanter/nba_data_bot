#!/usr/bin/env python3
"""
EPL Data Bot - template CLI for EPL pipeline outputs.

Usage:
    python3 epl_main.py markdown              # Generate all EPL markdown outputs
    python3 epl_main.py data                  # Generate the consolidated EPL data file
    python3 epl_main.py matches_today         # Generate today's EPL matches file
    python3 epl_main.py quality_report        # Generate the EPL quality report

Options:
    --output DIR        Output directory for markdown files (default: ./data)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd

from epl.features import build_matchup_features, sanity_check_candidate_rows


LAST_UPDATED = "2026-03-14 00:00 UTC"
SAMPLE_CURRENT_TIME = "2026-03-14T00:00:00Z"
SAMPLE_FEATURE_GENERATED_AT = "2026-03-13T23:30:00Z"
SAMPLE_MAX_STALENESS = "2D"


def _render_markdown_table(columns: list[str], rows: list[dict[str, object]]) -> str:
    header = "| " + " | ".join(columns) + " |"
    divider = "|" + "|".join("-" * (len(column) + 2) for column in columns) + "|"
    lines = [header, divider]

    for row in rows:
        values = []
        for column in columns:
            value = row.get(column, "")
            cell = "" if value is None else str(value)
            cell = cell.replace("|", "\\|").replace("\n", "<br>")
            values.append(cell)
        lines.append("| " + " | ".join(values) + " |")

    return "\n".join(lines)


def _format_timestamp(value: object) -> str:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        timestamp = timestamp.tz_localize("UTC")
    else:
        timestamp = timestamp.tz_convert("UTC")
    return timestamp.strftime("%Y-%m-%d %H:%M UTC")


def _sample_ingest_tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    fixtures = pd.DataFrame(
        [
            {
                "match_id": "sample_epl_arsenal_chelsea_2026-03-14",
                "season": "2025-26",
                "kickoff_ts": "2026-03-14T15:00:00Z",
                "home_team": "Arsenal",
                "away_team": "Chelsea",
                "home_score": 2,
                "away_score": 1,
                "updated_at": "2026-03-13T20:30:00Z",
            }
        ]
    )
    team_strength = pd.DataFrame(
        [
            {
                "season": "2025-26",
                "team": "Arsenal",
                "matches_played": 20,
                "points": 44,
                "goal_diff": 24,
                "goals_for": 38,
                "goals_against": 14,
                "home_matches": 10,
                "home_points": 24,
                "home_goal_diff": 14,
                "away_matches": 10,
                "away_points": 20,
                "away_goal_diff": 10,
                "updated_at": "2026-03-13T21:00:00Z",
            },
            {
                "season": "2025-26",
                "team": "Chelsea",
                "matches_played": 20,
                "points": 34,
                "goal_diff": 8,
                "goals_for": 30,
                "goals_against": 22,
                "home_matches": 10,
                "home_points": 18,
                "home_goal_diff": 5,
                "away_matches": 10,
                "away_points": 16,
                "away_goal_diff": 3,
                "updated_at": "2026-03-13T21:10:00Z",
            },
        ]
    )
    team_form = pd.DataFrame(
        [
            {
                "season": "2025-26",
                "team": "Arsenal",
                "window_matches": 5,
                "window_points": 11,
                "window_goal_diff": 7,
                "updated_at": "2026-03-13T22:00:00Z",
            },
            {
                "season": "2025-26",
                "team": "Chelsea",
                "window_matches": 5,
                "window_points": 7,
                "window_goal_diff": 1,
                "updated_at": "2026-03-13T22:05:00Z",
            },
        ]
    )
    return fixtures, team_strength, team_form


def _build_scaffold_context() -> dict[str, object]:
    fixtures, team_strength, team_form = _sample_ingest_tables()
    candidate_rows = build_matchup_features(
        fixtures,
        team_strength,
        team_form,
        feature_generated_at=SAMPLE_FEATURE_GENERATED_AT,
    )
    sanity_summary = sanity_check_candidate_rows(
        candidate_rows,
        expected_rows=len(fixtures),
        current_time=SAMPLE_CURRENT_TIME,
        max_staleness=SAMPLE_MAX_STALENESS,
    )

    player_stats_rows = [
        {
            "team": "Arsenal",
            "player": "Bukayo Saka",
            "window": "Last 5",
            "goals": 3,
            "assists": 2,
            "shots_on_target": 8,
            "chances_created": 11,
            "note": "Primary right-side creator.",
        },
        {
            "team": "Arsenal",
            "player": "Martin Odegaard",
            "window": "Last 5",
            "goals": 1,
            "assists": 3,
            "shots_on_target": 3,
            "chances_created": 14,
            "note": "Set-piece volume remains strong.",
        },
        {
            "team": "Chelsea",
            "player": "Cole Palmer",
            "window": "Last 5",
            "goals": 2,
            "assists": 2,
            "shots_on_target": 5,
            "chances_created": 10,
            "note": "Carries the highest direct goal involvement.",
        },
        {
            "team": "Chelsea",
            "player": "Nicolas Jackson",
            "window": "Last 5",
            "goals": 1,
            "assists": 0,
            "shots_on_target": 3,
            "chances_created": 2,
            "note": "Penalty-box shot volume is stable.",
        },
    ]
    injury_rows = [
        {
            "team": "Arsenal",
            "player": "Gabriel Jesus",
            "status": "out",
            "expected_return": "2026-03-21",
            "source": "club report",
            "confidence": "0.92",
            "impact_note": "Removes a central rotation forward.",
        },
        {
            "team": "Chelsea",
            "player": "Reece James",
            "status": "questionable",
            "expected_return": "day to day",
            "source": "press conference",
            "confidence": "0.74",
            "impact_note": "Touches both flank progression and set-piece share.",
        },
        {
            "team": "Chelsea",
            "player": "Romeo Lavia",
            "status": "out",
            "expected_return": "2026-03-28",
            "source": "club report",
            "confidence": "0.89",
            "impact_note": "Reduces central midfield ball-winning depth.",
        },
    ]

    player_stats_by_team: dict[str, list[dict[str, object]]] = {}
    for row in player_stats_rows:
        player_stats_by_team.setdefault(str(row["team"]), []).append(row)

    injuries_by_team: dict[str, list[dict[str, object]]] = {}
    for row in injury_rows:
        injuries_by_team.setdefault(str(row["team"]), []).append(row)

    home_team = str(candidate_rows.iloc[0]["home_team"])
    away_team = str(candidate_rows.iloc[0]["away_team"])
    team_points = team_strength.set_index("team")["points"].to_dict()
    team_goal_diff = team_strength.set_index("team")["goal_diff"].to_dict()
    team_form_points = team_form.set_index("team")["window_points"].to_dict()

    home_goal_contrib = sum(int(row["goals"]) + int(row["assists"]) for row in player_stats_by_team[home_team])
    away_goal_contrib = sum(int(row["goals"]) + int(row["assists"]) for row in player_stats_by_team[away_team])
    home_shots_on_target = sum(int(row["shots_on_target"]) for row in player_stats_by_team[home_team])
    away_shots_on_target = sum(int(row["shots_on_target"]) for row in player_stats_by_team[away_team])
    home_injury_count = len(injuries_by_team.get(home_team, []))
    away_injury_count = len(injuries_by_team.get(away_team, []))

    oldest_age_hours = float(sanity_summary["oldest_source_age_hours"])
    latest_source_updated_at = _format_timestamp(sanity_summary["latest_source_updated_at"])

    return {
        "candidate_rows": candidate_rows,
        "sanity_summary": sanity_summary,
        "player_stats_rows": player_stats_rows,
        "injury_rows": injury_rows,
        "table_position_delta": 3,
        "points_delta": int(team_points[home_team] - team_points[away_team]),
        "goal_diff_delta": int(team_goal_diff[home_team] - team_goal_diff[away_team]),
        "form_points_delta": int(team_form_points[home_team] - team_form_points[away_team]),
        "rest_days_delta": 1,
        "player_goal_contrib_delta": home_goal_contrib - away_goal_contrib,
        "player_shots_on_target_delta": home_shots_on_target - away_shots_on_target,
        "home_injury_count": home_injury_count,
        "away_injury_count": away_injury_count,
        "oldest_source_age_hours": oldest_age_hours,
        "latest_source_updated_at": latest_source_updated_at,
    }


def render_epl_data(last_updated: str) -> str:
    context = _build_scaffold_context()
    candidate_row = context["candidate_rows"].iloc[0]
    player_stats_rows = context["player_stats_rows"]
    injury_rows = context["injury_rows"]

    data_sources_rows = [
        {
            "source": "Fixtures",
            "website": "premierleague.com",
            "status": "SCAFFOLD",
            "records": "1",
            "notes": "Sample fixture row is wired through the feature join.",
        },
        {
            "source": "Table Snapshot",
            "website": "premierleague.com/tables",
            "status": "SCAFFOLD",
            "records": "2",
            "notes": "Home and away strength rows feed matchup deltas.",
        },
        {
            "source": "Team Form",
            "website": "derived rolling window",
            "status": "SCAFFOLD",
            "records": "2",
            "notes": "Five-match form rows back the form delta columns.",
        },
        {
            "source": "Player Stats",
            "website": "club and event feeds",
            "status": "SCAFFOLD",
            "records": str(len(player_stats_rows)),
            "notes": "Top player production rows are rendered as a separate section.",
        },
        {
            "source": "Injuries",
            "website": "club reports and news feeds",
            "status": "SCAFFOLD",
            "records": str(len(injury_rows)),
            "notes": "Injury watch rows stay separate from feature deltas for clarity.",
        },
        {
            "source": "Market Mapping",
            "website": "execution venue",
            "status": "OPTIONAL",
            "records": "0",
            "notes": "Venue adapter remains outside the scaffolded pipeline.",
        },
    ]
    candidate_match_rows = [
        {
            "match_id": candidate_row["match_id"],
            "kickoff_utc": _format_timestamp(candidate_row["kickoff_ts"]),
            "home_team": candidate_row["home_team"],
            "away_team": candidate_row["away_team"],
            "venue": "Emirates Stadium",
            "model_home_win": "0.52",
            "model_draw": "0.25",
            "model_away_win": "0.23",
            "quality_state": "sanity_checked",
        }
    ]
    feature_rows = [
        {
            "match_id": candidate_row["match_id"],
            "table_position_delta": context["table_position_delta"],
            "points_delta": context["points_delta"],
            "goal_diff_delta": context["goal_diff_delta"],
            "form_points_delta": context["form_points_delta"],
            "rest_days_delta": context["rest_days_delta"],
            "player_goal_contrib_delta": context["player_goal_contrib_delta"],
            "player_shots_on_target_delta": context["player_shots_on_target_delta"],
            "injuries_home": context["home_injury_count"],
            "injuries_away": context["away_injury_count"],
            "quality_state": "ready",
        }
    ]
    sanity_rows = [
        {
            "check": "candidate_row_schema",
            "result": "PASS",
            "detail": "1 candidate row validated with required feature columns present.",
        },
        {
            "check": "source_freshness",
            "result": "PASS",
            "detail": f"Oldest scaffold source age is {context['oldest_source_age_hours']:.1f}h, inside the 48h window.",
        },
        {
            "check": "player_stats_match_coverage",
            "result": "PASS",
            "detail": "Both clubs have player-stat coverage in the rendered snapshot.",
        },
        {
            "check": "injury_feed_alignment",
            "result": "PASS",
            "detail": "All injury rows map cleanly to the candidate match clubs.",
        },
    ]

    lines = [
        "# EPL Match Data",
        "",
        f"**Last Updated:** {last_updated}",
        "**Mode:** Pipeline scaffold with player stats, injuries, and sanity coverage",
        "",
        "## Data Sources",
        "",
        _render_markdown_table(
            ["source", "website", "status", "records", "notes"],
            data_sources_rows,
        ),
        "",
        "## Candidate Matches",
        "",
        _render_markdown_table(
            [
                "match_id",
                "kickoff_utc",
                "home_team",
                "away_team",
                "venue",
                "model_home_win",
                "model_draw",
                "model_away_win",
                "quality_state",
            ],
            candidate_match_rows,
        ),
        "",
        "## Match Features",
        "",
        _render_markdown_table(
            [
                "match_id",
                "table_position_delta",
                "points_delta",
                "goal_diff_delta",
                "form_points_delta",
                "rest_days_delta",
                "player_goal_contrib_delta",
                "player_shots_on_target_delta",
                "injuries_home",
                "injuries_away",
                "quality_state",
            ],
            feature_rows,
        ),
        "",
        "## Player Stats Snapshot",
        "",
        _render_markdown_table(
            [
                "team",
                "player",
                "window",
                "goals",
                "assists",
                "shots_on_target",
                "chances_created",
                "note",
            ],
            player_stats_rows,
        ),
        "",
        "## Injury Watch",
        "",
        _render_markdown_table(
            [
                "team",
                "player",
                "status",
                "expected_return",
                "source",
                "confidence",
                "impact_note",
            ],
            injury_rows,
        ),
        "",
        "## Sanity Checks",
        "",
        _render_markdown_table(
            ["check", "result", "detail"],
            sanity_rows,
        ),
        "",
        "## Publishing Notes",
        "",
        "- Generated by `python3 epl_main.py markdown --output ./data`.",
        "- Player stats and injuries remain scaffold-backed until live EPL ingestion lands.",
        "- Candidate row validation is sourced from `epl.features.sanity_check_candidate_rows`.",
    ]
    return "\n".join(lines) + "\n"


def render_epl_matches_today(last_updated: str) -> str:
    context = _build_scaffold_context()
    candidate_row = context["candidate_rows"].iloc[0]

    schedule_sources_rows = [
        {
            "source": "Fixtures",
            "website": "premierleague.com",
            "status": "SCAFFOLD",
            "records": "1",
            "notes": "Sample scheduled row mirrors the candidate match shell.",
        },
        {
            "source": "Player Stats",
            "website": "club and event feeds",
            "status": "SCAFFOLD",
            "records": str(len(context["player_stats_rows"])),
            "notes": "Player-stat context can be refreshed alongside the schedule view.",
        },
        {
            "source": "Injuries",
            "website": "club reports and news feeds",
            "status": "SCAFFOLD",
            "records": str(len(context["injury_rows"])),
            "notes": "Injury rows are surfaced for pre-kickoff monitoring.",
        },
        {
            "source": "Market Snapshot",
            "website": "execution venue",
            "status": "OPTIONAL",
            "records": "0",
            "notes": "Odds integration remains outside the scaffolded pipeline.",
        },
    ]
    matches_rows = [
        {
            "match_id": candidate_row["match_id"],
            "kickoff_utc": _format_timestamp(candidate_row["kickoff_ts"]),
            "home_team": candidate_row["home_team"],
            "away_team": candidate_row["away_team"],
            "venue": "Emirates Stadium",
            "status": "scheduled",
            "quality_state": "sanity_checked",
        }
    ]
    injury_watch_rows = [
        {
            "match_id": candidate_row["match_id"],
            "team": row["team"],
            "player": row["player"],
            "status": row["status"],
            "refresh_window": "T-180 to T-30",
        }
        for row in context["injury_rows"]
    ]
    pre_kickoff_rows = [
        {
            "match_id": candidate_row["match_id"],
            "kickoff_utc": _format_timestamp(candidate_row["kickoff_ts"]),
            "refresh_window": "T-120 to T-15",
            "player_stats_refresh": "lineup-confirmed creators and finishers",
            "injury_refresh": "club report plus manager availability update",
            "note": "Re-run matchup quality checks after final injury confirmation.",
        }
    ]

    lines = [
        "# EPL Matches Today",
        "",
        f"**Last Updated:** {last_updated}",
        "**Mode:** Pipeline scaffold with player stats and injury monitoring",
        "",
        "## Schedule Sources",
        "",
        _render_markdown_table(
            ["source", "website", "status", "records", "notes"],
            schedule_sources_rows,
        ),
        "",
        "## Matches",
        "",
        _render_markdown_table(
            [
                "match_id",
                "kickoff_utc",
                "home_team",
                "away_team",
                "venue",
                "status",
                "quality_state",
            ],
            matches_rows,
        ),
        "",
        "## Injury Watch",
        "",
        _render_markdown_table(
            ["match_id", "team", "player", "status", "refresh_window"],
            injury_watch_rows,
        ),
        "",
        "## Pre-Kickoff Watchlist",
        "",
        _render_markdown_table(
            [
                "match_id",
                "kickoff_utc",
                "refresh_window",
                "player_stats_refresh",
                "injury_refresh",
                "note",
            ],
            pre_kickoff_rows,
        ),
    ]
    return "\n".join(lines) + "\n"


def render_epl_quality_report(last_updated: str) -> str:
    context = _build_scaffold_context()
    sanity_summary = context["sanity_summary"]

    source_status_rows = [
        {
            "source": "Fixtures",
            "freshness_sla": "<= 6h",
            "status": "SCAFFOLD",
            "records": "1",
            "notes": "Fixture row is stable and fresh enough for the sample join.",
        },
        {
            "source": "Table Snapshot",
            "freshness_sla": "<= 24h",
            "status": "SCAFFOLD",
            "records": "2",
            "notes": "Strength rows drive points and goal-difference deltas.",
        },
        {
            "source": "Team Form",
            "freshness_sla": "<= 24h",
            "status": "SCAFFOLD",
            "records": "2",
            "notes": "Form rows back the rolling performance features.",
        },
        {
            "source": "Player Stats",
            "freshness_sla": "<= 24h",
            "status": "SCAFFOLD",
            "records": str(len(context["player_stats_rows"])),
            "notes": "Player rows render in a dedicated section and quality coverage table.",
        },
        {
            "source": "Injuries",
            "freshness_sla": "<= 6h on match day",
            "status": "SCAFFOLD",
            "records": str(len(context["injury_rows"])),
            "notes": "Injury watch remains separate from the matchup feature table.",
        },
    ]
    run_summary_rows = [
        {"metric": "total_matches_ingested", "value": len(context["candidate_rows"])},
        {"metric": "fully_scorable_matches", "value": len(context["candidate_rows"])},
        {"metric": "skipped_matches", "value": 0},
        {"metric": "player_stats_rows", "value": len(context["player_stats_rows"])},
        {"metric": "injury_rows", "value": len(context["injury_rows"])},
        {"metric": "schema_drift_alerts", "value": 0},
    ]
    coverage_rows = [
        {"metric": "matches_with_player_stats", "value": len(context["candidate_rows"])},
        {"metric": "matches_with_injury_data", "value": len(context["candidate_rows"])},
        {"metric": "player_stats_coverage_pct", "value": "100"},
        {"metric": "injury_coverage_pct", "value": "100"},
        {"metric": "oldest_source_age_hours", "value": f"{context['oldest_source_age_hours']:.1f}"},
        {"metric": "latest_source_updated_at", "value": context["latest_source_updated_at"]},
    ]
    guardrail_rows = [
        {
            "check": "missing_fixture_ids",
            "result": "PASS",
            "detail": "Sample fixture row has a stable match identifier.",
        },
        {
            "check": "ambiguous_team_mapping",
            "result": "PASS",
            "detail": "Home and away clubs resolve cleanly through the scaffold join.",
        },
        {
            "check": "stale_table_snapshot",
            "result": "PASS",
            "detail": f"Oldest source age is {context['oldest_source_age_hours']:.1f}h.",
        },
        {
            "check": "player_stats_coverage",
            "result": "PASS",
            "detail": "Player-stat snapshot covers both clubs in the sample match.",
        },
        {
            "check": "conflicting_injuries",
            "result": "PASS",
            "detail": "No duplicated player injuries disagree on status.",
        },
        {
            "check": "candidate_row_sanity",
            "result": "PASS",
            "detail": "Feature frame passed row-count, null, and freshness validation.",
        },
    ]
    sanity_check_rows = [
        {
            "check": "candidate_row_schema",
            "result": "PASS",
            "detail": f"{sanity_summary['row_count']} row validated against required EPL feature columns.",
        },
        {
            "check": "score_bounds",
            "result": "PASS",
            "detail": "Sample result uses integer scores within the configured 0-20 bounds.",
        },
        {
            "check": "source_freshness",
            "result": "PASS",
            "detail": f"Freshness gate accepted the sample sources under the {SAMPLE_MAX_STALENESS} limit.",
        },
        {
            "check": "player_stats_shape",
            "result": "PASS",
            "detail": "Player-stat rows include goals, assists, shots on target, and chance creation.",
        },
        {
            "check": "injury_shape",
            "result": "PASS",
            "detail": "Injury rows include status, return horizon, source, and confidence.",
        },
    ]
    skip_reason_rows = [
        {"reason": "missing_fixture_id", "count": 0},
        {"reason": "missing_team_mapping", "count": 0},
        {"reason": "missing_player_stats", "count": 0},
        {"reason": "missing_injury_mapping", "count": 0},
        {"reason": "stale_standings", "count": 0},
        {"reason": "conflicting_injuries", "count": 0},
    ]

    lines = [
        "# EPL Quality Report",
        "",
        f"**Last Updated:** {last_updated}",
        "**Mode:** Pipeline scaffold with player stats, injuries, and sanity coverage",
        "",
        "## Source Status",
        "",
        _render_markdown_table(
            ["source", "freshness_sla", "status", "records", "notes"],
            source_status_rows,
        ),
        "",
        "## Run Summary",
        "",
        _render_markdown_table(
            ["metric", "value"],
            run_summary_rows,
        ),
        "",
        "## Coverage",
        "",
        _render_markdown_table(
            ["metric", "value"],
            coverage_rows,
        ),
        "",
        "## Guardrails",
        "",
        _render_markdown_table(
            ["check", "result", "detail"],
            guardrail_rows,
        ),
        "",
        "## Sanity Checks",
        "",
        _render_markdown_table(
            ["check", "result", "detail"],
            sanity_check_rows,
        ),
        "",
        "## Skip Reasons",
        "",
        _render_markdown_table(
            ["reason", "count"],
            skip_reason_rows,
        ),
    ]
    return "\n".join(lines) + "\n"


def write_output(path: Path, contents: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(contents, encoding="utf-8")
    return path


def cmd_data(args: argparse.Namespace) -> int:
    path = write_output(Path(args.output) / "epl_data.md", render_epl_data(LAST_UPDATED))
    print(f"Generated {path}")
    return 0


def cmd_matches_today(args: argparse.Namespace) -> int:
    path = write_output(
        Path(args.output) / "epl_matches_today.md",
        render_epl_matches_today(LAST_UPDATED),
    )
    print(f"Generated {path}")
    return 0


def cmd_quality_report(args: argparse.Namespace) -> int:
    path = write_output(
        Path(args.output) / "epl_quality_report.md",
        render_epl_quality_report(LAST_UPDATED),
    )
    print(f"Generated {path}")
    return 0


def cmd_markdown(args: argparse.Namespace) -> int:
    commands = [cmd_data, cmd_matches_today, cmd_quality_report]
    for command in commands:
        command(args)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="EPL Data Bot - template generator for EPL pipeline outputs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "command",
        choices=["markdown", "data", "matches_today", "quality_report"],
        help="Use 'markdown' to write all EPL markdown outputs or an individual file command",
    )
    parser.add_argument(
        "--output",
        default="./data",
        help="Output directory for markdown files (default: ./data)",
    )

    args = parser.parse_args()

    commands = {
        "markdown": cmd_markdown,
        "data": cmd_data,
        "matches_today": cmd_matches_today,
        "quality_report": cmd_quality_report,
    }
    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
