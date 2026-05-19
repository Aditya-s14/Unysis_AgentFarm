#!/usr/bin/env bash
# Regenerate requirements.txt lockfile from requirements.in (run after changing direct deps).
set -euo pipefail
cd "$(dirname "$0")/.."
python -m pip install pip-tools -q
python -m piptools compile requirements.in -o requirements.txt --resolver=backtracking --strip-extras
echo "Updated backend/requirements.txt"
