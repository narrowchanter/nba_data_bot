# NBA Data Bot

CLI tool for extracting NBA stats and injury data from multiple sources.

This repository now also includes an EPL pipeline scaffold in `epl_main.py` for generating stable markdown outputs under `data/` without changing the NBA workflow in `main.py`.

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

## EPL

The EPL pathway is scaffolded separately in `epl_main.py` so downstream consumers can integrate against committed markdown outputs while live EPL ingestion is still landing.

```bash
# Generate all EPL markdown outputs in ./data
python3 epl_main.py markdown

# Generate individual EPL outputs
python3 epl_main.py data
python3 epl_main.py matches_today
python3 epl_main.py quality_report
```

Generated EPL files:

```text
data/epl_data.md
data/epl_matches_today.md
data/epl_quality_report.md
```

These files are template-backed placeholders with stable headings, status tables, and sample rows so pipeline automation and downstream readers can rely on the file shape before live data sources are wired in.

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

EPL markdown outputs can be refreshed with:

```bash
./scripts/update_epl_and_push.sh
```

This script:
1. Regenerates `data/epl_data.md`, `data/epl_matches_today.md`, and `data/epl_quality_report.md`
2. Commits and pushes only when those EPL markdown files changed
3. Commits are authored as "EPL Bot"

## Project Structure

```text
nba_data_bot/
├── main.py                    # NBA CLI entry point
├── epl_main.py                # EPL markdown scaffold CLI
├── scraper/
│   ├── teamrankings.py        # Last-5 form scraper
│   ├── nba_stats.py           # NBA.com stats API client
│   └── injury_report.py       # Injury report PDF parser
├── scripts/
│   ├── update_and_push.sh     # NBA update and push script
│   └── update_epl_and_push.sh # EPL update and push script
├── data/
│   ├── nba_data.md
│   ├── epl_data.md
│   ├── epl_matches_today.md
│   └── epl_quality_report.md
├── tests/
│   └── test_epl_main.py
├── output/                    # Generated CSV/JSON files
└── requirements.txt
```
