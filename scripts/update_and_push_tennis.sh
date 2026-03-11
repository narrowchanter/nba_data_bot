#!/bin/bash
# Tennis Data Bot - Local update script
# Generates template tennis outputs and pushes to GitHub.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

if [ -f .venv/bin/activate ]; then
    # shellcheck disable=SC1091
    source .venv/bin/activate
fi

PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    if command -v python >/dev/null 2>&1; then
        PYTHON_BIN="python"
    else
        echo "No Python interpreter found in PATH." >&2
        exit 1
    fi
fi

"$PYTHON_BIN" main_tennis.py markdown --output ./data --log-dir ./outputs

git add data/tennis_data.md \
    data/tennis_players.md \
    data/tennis_matches_today.md \
    data/tennis_quality_report.md

if ! git diff --staged --quiet; then
    GIT_COMMITTER_NAME="Tennis Bot" GIT_COMMITTER_EMAIL="tennis-bot@automated.local" \
    git commit --author="Tennis Bot <tennis-bot@automated.local>" -m "Update tennis data [$(date -u '+%Y-%m-%d %H:%M') UTC]"
    git push
fi
