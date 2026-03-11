# NBA Data Bot

CLI tool for extracting NBA stats and injury data from multiple sources.

This repository now also includes a separate tennis template pathway for stream-B style markdown outputs. The NBA workflow remains unchanged in `main.py`.

## Data Sources

| Source | Command | Data Extracted |
|--------|---------|----------------|
| TeamRankings.com | `last5` | L5_WINS, L5_LOSSES, L5_RATING |
| NBA.com Advanced | `advanced` | W, L, NET_RATING, OFF_RATING, DEF_RATING, PACE |
| NBA.com Four Factors | `fourfactors` | EFG_PCT, TOV_PCT, OREB_PCT, FT_RATE |
| NBA.com Defense | `defense` | OPP_FG_PCT, OPP_FG3_PCT, OPP_PTS, etc. |
| NBA Injury Report | `injuries` | Player status (OUT/DOUBTFUL/QUESTIONABLE/PROBABLE) by team |

## Installation

```bash
cd nba_data_bot
conda create -n nba_bot python=3.11 -y
conda activate nba_bot
pip install -r requirements.txt
```

## Usage

```bash
# Fetch all data sources
python main.py all

# Fetch individual sources
python main.py last5
python main.py advanced
python main.py fourfactors
python main.py defense
python main.py injuries

# Options
python main.py all --format json    # Output as JSON instead of CSV
python main.py all --output ./data  # Custom output directory
```

Output files are saved to `./output/` by default with timestamps (e.g., `advanced_stats_20260116_143022.csv`).

## Tennis

The tennis pathway is scaffolded separately in `main_tennis.py` so it does not change NBA behavior. It currently generates spec-aligned markdown templates and a local run log for the tennis pipeline outputs described in `docs/TENNIS_Data_Bot_Spec.md`.

```bash
# Generate tennis markdown templates in ./data
python3 main_tennis.py markdown --output ./data

# Print the local tennis spec path
python3 main_tennis.py docs
```

Generated tennis files:

```text
data/tennis_data.md
data/tennis_players.md
data/tennis_matches_today.md
data/tennis_quality_report.md
outputs/tennis_run_YYYY-MM-DD_HHMMSS.txt
```

The committed markdown files are placeholders with source status tables and sample rows so downstream tooling can integrate against a stable shape before live tennis scrapers land.

## Live Data URL

A consolidated markdown file is available at:

```
https://raw.githubusercontent.com/0xashrk/nba_data_bot/main/data/nba_data.md
```

Use this URL with tools like Jina AI to fetch the latest NBA stats programmatically.

## Update & Push to GitHub

Run the update script to fetch fresh data and push to GitHub:

```bash
cd /path/to/nba_data_bot
./scripts/update_and_push.sh
```

This will:
1. Fetch all NBA data (stats + injuries)
2. Generate `data/nba_data.md`
3. Commit and push to GitHub (only if data changed)
4. Commits are authored as "NBA Bot" (won't count to your GitHub profile)

Tennis template outputs can be refreshed with:

```bash
./scripts/update_and_push_tennis.sh
```

This script:
1. Generates the tennis markdown templates in `data/`
2. Writes a local run log under `outputs/`
3. Commits and pushes only when the tennis markdown files changed
4. Commits are authored as "Tennis Bot"

## Project Structure

```text
nba_data_bot/
├── main.py
├── main_tennis.py
├── scraper/
│   ├── teamrankings.py
│   ├── nba_stats.py
│   └── injury_report.py
├── scripts/
│   ├── update_and_push.sh
│   └── update_and_push_tennis.sh
├── data/
│   ├── nba_data.md
│   ├── tennis_data.md
│   ├── tennis_players.md
│   ├── tennis_matches_today.md
│   └── tennis_quality_report.md
├── docs/
│   └── TENNIS_Data_Bot_Spec.md
├── output/
├── outputs/
└── requirements.txt
```

`main.py` remains the NBA CLI entry point. `main_tennis.py` generates the tennis template outputs and `scripts/update_and_push_tennis.sh` refreshes and pushes those markdown files.
