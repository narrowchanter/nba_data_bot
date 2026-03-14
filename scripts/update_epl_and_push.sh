#!/bin/bash
# EPL Data Bot - Local update script
# Generates EPL markdown outputs and pushes to GitHub.

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

"$PYTHON_BIN" epl_main.py markdown --output ./data

git add data/epl_data.md \
    data/epl_matches_today.md \
    data/epl_quality_report.md

if ! git diff --staged --quiet; then
    GIT_COMMITTER_NAME="EPL Bot" GIT_COMMITTER_EMAIL="epl-bot@automated.local" \
    git commit --author="EPL Bot <epl-bot@automated.local>" -m "Update EPL data [$(date -u '+%Y-%m-%d %H:%M') UTC]"
    git push
fi
