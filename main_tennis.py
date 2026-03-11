#!/usr/bin/env python3
"""
Tennis Data Bot - CLI tool for extracting tennis schedule, rankings, and features.

Usage:
    python main_tennis.py all                 # Fetch all tennis sources
    python main_tennis.py schedule            # ATP/WTA singles schedule
    python main_tennis.py rankings            # ATP/WTA rankings
    python main_tennis.py stats               # Elo and stat placeholders
    python main_tennis.py injuries            # Availability and withdrawal news
    python main_tennis.py features            # Matchup feature rows
    python main_tennis.py markdown            # Consolidated tennis markdown

Options:
    --format csv|json     Output format (default: csv)
    --output DIR          Output directory (default: ./output)
    --tour all|ATP|WTA    Tour scope (default: all)
"""

from __future__ import annotations

import argparse
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from scraper import (
    build_tennis_features,
    get_tennis_injury_report,
    get_tennis_player_stats,
    get_tennis_rankings,
    get_tennis_schedule,
)


def save_dataframe(df: pd.DataFrame, name: str, output_dir: str, fmt: str, timestamp: str = None) -> str:
    """Save DataFrame to disk and return the output path."""
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    if fmt == "csv":
        filepath = os.path.join(output_dir, f"{name}_{timestamp}.csv")
        df.to_csv(filepath, index=False)
    else:
        filepath = os.path.join(output_dir, f"{name}_{timestamp}.json")
        df.to_json(filepath, orient="records", indent=2)

    return filepath


def df_to_markdown(df: pd.DataFrame, columns: list[str] = None) -> str:
    """Render a DataFrame as a markdown table."""
    if columns:
        available = [column for column in columns if column in df.columns]
        df = df[available]
    return df.to_markdown(index=False)


def _selected_tours(args) -> tuple[str, ...]:
    """Map CLI tour flags into the scraper tour arguments."""
    if args.tour == "all":
        return ("ATP", "WTA")
    return (args.tour,)


def cmd_schedule(args):
    """Fetch the current tennis schedule."""
    print("Fetching tennis schedule...")
    df = get_tennis_schedule(tours=_selected_tours(args), include_completed=args.include_completed)
    filepath = save_dataframe(df, "tennis_schedule", args.output, args.format)
    print(f"Saved {len(df)} matches to {filepath}")
    return df


def cmd_rankings(args):
    """Fetch ATP/WTA rankings."""
    print("Fetching tennis rankings...")
    df = get_tennis_rankings(tours=_selected_tours(args))
    filepath = save_dataframe(df, "tennis_rankings", args.output, args.format)
    print(f"Saved {len(df)} ranking rows to {filepath}")
    return df


def cmd_stats(args):
    """Fetch tennis Elo ratings and stat placeholders."""
    print("Fetching tennis player stats...")
    df = get_tennis_player_stats(tours=_selected_tours(args))
    filepath = save_dataframe(df, "tennis_stats", args.output, args.format)
    print(f"Saved {len(df)} player stat rows to {filepath}")
    return df


def cmd_injuries(args):
    """Fetch tennis injury and availability notes."""
    print("Fetching tennis injury and availability feed...")
    df = get_tennis_injury_report(tours=_selected_tours(args))
    filepath = save_dataframe(df, "tennis_injuries", args.output, args.format)
    print(f"Saved {len(df)} availability rows to {filepath}")
    return df


def cmd_features(args):
    """Build tennis matchup features."""
    print("Building tennis features...")
    df = build_tennis_features(
        schedule_df=get_tennis_schedule(tours=_selected_tours(args), include_completed=False),
        rankings_df=get_tennis_rankings(tours=_selected_tours(args), limit=None),
        stats_df=get_tennis_player_stats(tours=_selected_tours(args)),
        injuries_df=get_tennis_injury_report(tours=_selected_tours(args)),
    )
    filepath = save_dataframe(df, "tennis_features", args.output, args.format)
    print(f"Saved {len(df)} feature rows to {filepath}")
    return df


def cmd_all(args):
    """Fetch every tennis source and build features."""
    results = {}

    print("=" * 50)
    print("TENNIS DATA BOT - Fetching All Sources")
    print("=" * 50)

    print("\n[1/5] Schedule")
    try:
        results["schedule"] = cmd_schedule(args)
    except Exception as e:
        print(f"  Error: {e}")
        results["schedule"] = None

    print("\n[2/5] Rankings")
    try:
        results["rankings"] = cmd_rankings(args)
    except Exception as e:
        print(f"  Error: {e}")
        results["rankings"] = None

    print("\n[3/5] Player Stats")
    try:
        results["stats"] = cmd_stats(args)
    except Exception as e:
        print(f"  Error: {e}")
        results["stats"] = None

    print("\n[4/5] Injuries")
    try:
        results["injuries"] = cmd_injuries(args)
    except Exception as e:
        print(f"  Error: {e}")
        results["injuries"] = None

    print("\n[5/5] Features")
    try:
        results["features"] = cmd_features(args)
    except Exception as e:
        print(f"  Error: {e}")
        results["features"] = None

    print("\n" + "=" * 50)
    print("COMPLETE")
    print("=" * 50)

    for name, df in results.items():
        if df is not None and len(df) > 0:
            print(f"  {name}: {len(df)} rows")
        else:
            print(f"  {name}: FAILED or empty")

    return results


def cmd_markdown(args):
    """Write a consolidated tennis markdown snapshot."""
    print("Fetching tennis data for markdown export...")

    schedule = get_tennis_schedule(tours=_selected_tours(args), include_completed=False)
    rankings = get_tennis_rankings(tours=_selected_tours(args), limit=20)
    stats = get_tennis_player_stats(tours=_selected_tours(args))
    injuries = get_tennis_injury_report(tours=_selected_tours(args))
    features = build_tennis_features(
        schedule_df=schedule,
        rankings_df=get_tennis_rankings(tours=_selected_tours(args), limit=None),
        stats_df=stats,
        injuries_df=injuries,
    )

    now = datetime.now(timezone.utc)
    md_lines = [
        "# Tennis Data Snapshot",
        "",
        f"**Last Updated:** {now.strftime('%Y-%m-%d %H:%M')} UTC",
        "",
        "## Source Status",
        "",
        "| Source | Status | Records |",
        "|--------|--------|---------|",
    ]

    source_rows = [
        ("Schedule", schedule),
        ("Rankings", rankings),
        ("Stats", stats),
        ("Injuries", injuries),
        ("Features", features),
    ]

    for name, df in source_rows:
        status = "OK" if df is not None and len(df) > 0 else "EMPTY"
        count = len(df) if df is not None else 0
        md_lines.append(f"| {name} | {status} | {count} |")

    md_lines.extend(["", "## Upcoming Matches", ""])
    if len(schedule) > 0:
        md_lines.extend([
            df_to_markdown(
                schedule,
                ["TOUR", "EVENT_NAME", "ROUND", "PLAYER_A", "PLAYER_B", "SCHEDULED_UTC", "STATUS"],
            ),
            "",
        ])
    else:
        md_lines.extend(["No upcoming singles matches found.", ""])

    md_lines.extend(["## Rankings", ""])
    if len(rankings) > 0:
        for tour in rankings["TOUR"].dropna().unique():
            tour_df = rankings[rankings["TOUR"] == tour]
            md_lines.extend([
                f"### {tour}",
                "",
                df_to_markdown(tour_df, ["RANK", "PLAYER_NAME", "POINTS", "COUNTRY"]),
                "",
            ])
    else:
        md_lines.extend(["No ranking rows found.", ""])

    md_lines.extend(["## Elo Ratings", ""])
    if len(stats) > 0:
        stats_view = stats.sort_values(["TOUR", "ELO_RANK"]).groupby("TOUR").head(10)
        md_lines.extend([
            df_to_markdown(stats_view, ["TOUR", "PLAYER_NAME", "ELO_GLOBAL", "ELO_HARD", "ELO_CLAY", "ELO_GRASS"]),
            "",
        ])
    else:
        md_lines.extend(["No stat rows found.", ""])

    if len(injuries) > 0:
        md_lines.extend([
            "## Injury / Availability Notes",
            "",
            df_to_markdown(injuries, ["TOUR", "PLAYER_NAME", "STATUS", "CONFIDENCE", "HEADLINE"]),
            "",
        ])

    md_lines.extend(["## Matchup Features", ""])
    if len(features) > 0:
        feature_view = features.sort_values(["CONFIDENCE_GRADE", "MODEL_WIN_PROB_A"], ascending=[True, False])
        md_lines.extend([
            df_to_markdown(
                feature_view,
                [
                    "TOUR",
                    "PLAYER_A",
                    "PLAYER_B",
                    "RANK_DELTA",
                    "ELO_DELTA_GLOBAL",
                    "MODEL_WIN_PROB_A",
                    "CONFIDENCE_GRADE",
                    "QUALITY_STATE",
                ],
            ),
            "",
        ])
    else:
        md_lines.extend(["No feature rows built.", ""])

    Path(args.output).mkdir(parents=True, exist_ok=True)
    filepath = os.path.join(args.output, "tennis_data.md")
    with open(filepath, "w") as f:
        f.write("\n".join(md_lines))

    print(f"Saved consolidated markdown to {filepath}")
    return {
        "schedule": schedule,
        "rankings": rankings,
        "stats": stats,
        "injuries": injuries,
        "features": features,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Tennis Data Bot - Extract schedule, rankings, and matchup features",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument(
        "command",
        choices=["all", "schedule", "rankings", "stats", "injuries", "features", "markdown"],
        help="Data source to fetch (use 'markdown' for a consolidated file)",
    )

    parser.add_argument(
        "--format",
        choices=["csv", "json"],
        default="csv",
        help="Output format (default: csv)",
    )

    parser.add_argument(
        "--output",
        default="./output",
        help="Output directory (default: ./output)",
    )

    parser.add_argument(
        "--tour",
        choices=["all", "ATP", "WTA"],
        default="all",
        help="Tour scope (default: all)",
    )

    parser.add_argument(
        "--include-completed",
        action="store_true",
        help="Include completed matches when fetching schedule data",
    )

    args = parser.parse_args()

    commands = {
        "all": cmd_all,
        "schedule": cmd_schedule,
        "rankings": cmd_rankings,
        "stats": cmd_stats,
        "injuries": cmd_injuries,
        "features": cmd_features,
        "markdown": cmd_markdown,
    }

    try:
        commands[args.command](args)
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
