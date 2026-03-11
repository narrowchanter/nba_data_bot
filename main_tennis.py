#!/usr/bin/env python3
"""
Tennis Data Bot - CLI tool for extracting tennis schedule, rankings, stats, and injury signals.

Usage:
    python main_tennis.py all                # Fetch all tennis sources
    python main_tennis.py schedule           # ESPN scoreboard schedule snapshot
    python main_tennis.py rankings           # ATP/WTA rankings
    python main_tennis.py stats              # Season stats for top-ranked players
    python main_tennis.py injuries           # News-based injury and withdrawal signals
    python main_tennis.py features           # Derived player feature table
    python main_tennis.py markdown           # Consolidated markdown report

Options:
    --format csv|json     Output format (default: csv)
    --output DIR          Output directory (default: ./output)
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

from scraper import (
    get_tennis_features,
    get_tennis_injuries,
    get_tennis_rankings,
    get_tennis_schedule,
    get_tennis_stats,
)


def save_dataframe(df: pd.DataFrame, name: str, output_dir: str, fmt: str, timestamp: str = None) -> str:
    """Save a DataFrame and return the output path."""
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


def df_to_markdown(df: pd.DataFrame, columns: list[str] = None, limit: int = None) -> str:
    """Convert a DataFrame to a markdown table."""
    if columns:
        available_columns = [column for column in columns if column in df.columns]
        df = df[available_columns]
    if limit is not None:
        df = df.head(limit)
    return df.to_markdown(index=False)


def cmd_schedule(args):
    """Fetch the current tennis schedule snapshot."""
    print("Fetching tennis schedule from ESPN...")
    df = get_tennis_schedule()
    filepath = save_dataframe(df, "tennis_schedule", args.output, args.format)
    print(f"Saved {len(df)} matches to {filepath}")
    return df


def cmd_rankings(args):
    """Fetch the latest ATP and WTA rankings."""
    print("Fetching tennis rankings from ESPN...")
    df = get_tennis_rankings()
    filepath = save_dataframe(df, "tennis_rankings", args.output, args.format)
    print(f"Saved {len(df)} player rankings to {filepath}")
    return df


def cmd_stats(args):
    """Fetch season stats for top-ranked players."""
    print("Fetching tennis season stats from ESPN...")
    df = get_tennis_stats()
    filepath = save_dataframe(df, "tennis_stats", args.output, args.format)
    print(f"Saved {len(df)} player stat rows to {filepath}")
    return df


def cmd_injuries(args):
    """Fetch news-based injury signals."""
    print("Fetching tennis injury signals from ESPN news...")
    df = get_tennis_injuries()
    filepath = save_dataframe(df, "tennis_injuries", args.output, args.format)
    print(f"Saved {len(df)} injury signal rows to {filepath}")
    return df


def cmd_features(args):
    """Build the merged tennis feature table."""
    print("Building tennis feature table...")
    df = get_tennis_features()
    filepath = save_dataframe(df, "tennis_features", args.output, args.format)
    print(f"Saved {len(df)} player feature rows to {filepath}")
    return df


def cmd_all(args):
    """Fetch all tennis data sources."""
    results = {}

    print("=" * 50)
    print("TENNIS DATA BOT - Fetching All Sources")
    print("=" * 50)

    commands = [
        ("schedule", "Schedule", cmd_schedule),
        ("rankings", "Rankings", cmd_rankings),
        ("stats", "Season Stats", cmd_stats),
        ("injuries", "Injury Signals", cmd_injuries),
        ("features", "Feature Table", cmd_features),
    ]

    for index, (key, label, command) in enumerate(commands, start=1):
        print(f"\n[{index}/{len(commands)}] {label}")
        try:
            results[key] = command(args)
        except Exception as exc:
            print(f"  Error: {exc}")
            results[key] = None

    print("\n" + "=" * 50)
    print("COMPLETE")
    print("=" * 50)

    for key, df in results.items():
        if df is not None and len(df) > 0:
            print(f"  {key}: {len(df)} rows")
        else:
            print(f"  {key}: FAILED or empty")

    return results


def cmd_markdown(args):
    """Fetch all tennis data and write a consolidated markdown report."""
    from datetime import timezone

    print("Fetching all tennis data for markdown export...")

    results = {}
    fetchers = [
        ("schedule", "Schedule", get_tennis_schedule),
        ("rankings", "Rankings", get_tennis_rankings),
        ("stats", "Season Stats", get_tennis_stats),
        ("injuries", "Injury Signals", get_tennis_injuries),
        ("features", "Feature Table", get_tennis_features),
    ]

    for index, (key, label, fetcher) in enumerate(fetchers, start=1):
        print(f"  [{index}/{len(fetchers)}] {label}...")
        try:
            results[key] = fetcher()
        except Exception as exc:
            print(f"    Error: {exc}")
            results[key] = None

    now = datetime.now(timezone.utc)
    md_lines = [
        "# Tennis Data Snapshot",
        "",
        f"**Last Updated:** {now.strftime('%Y-%m-%d %H:%M')} UTC",
        "",
        "## Data Sources",
        "",
        "| Source | Website | Status | Records |",
        "|--------|---------|--------|---------|",
    ]

    sources = [
        ("Schedule", "site.api.espn.com", "schedule"),
        ("Rankings", "sports.core.api.espn.com", "rankings"),
        ("Season Stats", "sports.core.api.espn.com", "stats"),
        ("Injury Signals", "site.api.espn.com/news", "injuries"),
        ("Feature Table", "derived", "features"),
    ]

    for source_name, website, key in sources:
        df = results.get(key)
        if df is not None and len(df) > 0:
            md_lines.append(f"| {source_name} | {website} | OK | {len(df)} |")
        else:
            md_lines.append(f"| {source_name} | {website} | FAILED | 0 |")

    md_lines.append("")

    if results.get("schedule") is not None and len(results["schedule"]) > 0:
        md_lines.extend(
            [
                "## Schedule",
                "",
                df_to_markdown(
                    results["schedule"],
                    [
                        "TOUR",
                        "TOURNAMENT",
                        "DRAW",
                        "ROUND",
                        "START_TIME_UTC",
                        "STATUS_DETAIL",
                        "PLAYER_1",
                        "PLAYER_2",
                    ],
                    limit=20,
                ),
                "",
            ]
        )

    if results.get("rankings") is not None and len(results["rankings"]) > 0:
        md_lines.extend(
            [
                "## Rankings",
                "",
                df_to_markdown(
                    results["rankings"],
                    ["TOUR", "RANK", "PLAYER", "COUNTRY", "RANK_POINTS", "TREND"],
                    limit=20,
                ),
                "",
            ]
        )

    if results.get("stats") is not None and len(results["stats"]) > 0:
        md_lines.extend(
            [
                "## Season Stats",
                "",
                df_to_markdown(
                    results["stats"],
                    [
                        "TOUR",
                        "RANK",
                        "PLAYER",
                        "SINGLES_WON",
                        "SINGLES_LOST",
                        "WIN_PCT",
                        "SINGLES_TITLES",
                        "PRIZE_MONEY_USD",
                    ],
                    limit=20,
                ),
                "",
            ]
        )

    if results.get("injuries") is not None and len(results["injuries"]) > 0:
        md_lines.extend(
            [
                "## Injury Signals",
                "",
                df_to_markdown(
                    results["injuries"],
                    ["TOUR", "PLAYER", "PUBLISHED_UTC", "SIGNAL_KEYWORDS", "HEADLINE"],
                    limit=20,
                ),
                "",
            ]
        )

    if results.get("features") is not None and len(results["features"]) > 0:
        md_lines.extend(
            [
                "## Feature Table",
                "",
                df_to_markdown(
                    results["features"],
                    [
                        "TOUR",
                        "TOURNAMENT",
                        "ROUND",
                        "PLAYER_1",
                        "PLAYER_2",
                        "RANK_CHANGE",
                        "WIN_PCT_DELTA",
                        "MODEL_WIN_PROB_1",
                    ],
                    limit=20,
                ),
                "",
            ]
        )

    Path(args.output).mkdir(parents=True, exist_ok=True)
    filepath = os.path.join(args.output, "tennis_data.md")
    with open(filepath, "w") as handle:
        handle.write("\n".join(md_lines))

    print(f"\nSaved consolidated markdown to {filepath}")
    return results


def main():
    parser = argparse.ArgumentParser(
        description="Tennis Data Bot - Extract schedule, rankings, stats, and injury signals",
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
    except Exception as exc:
        print(f"Error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
