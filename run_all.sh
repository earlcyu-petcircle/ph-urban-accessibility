#!/usr/bin/env bash
# One command, from a clean clone to every number, table and map in the README.
#   ./run_all.sh            reuse files already in data/raw/ and data/work/
#   ./run_all.sh --refresh  download everything again (new OpenStreetMap snapshot)
#                           and re-read Overture
# Creates a local virtual environment in .venv/; installs nothing globally.
set -euo pipefail
cd "$(dirname "$0")"

PYTHON="${PYTHON:-python3.12}"
if [ ! -x .venv/bin/python ]; then
  "$PYTHON" -m venv .venv
  .venv/bin/pip install --quiet --upgrade pip
fi
.venv/bin/pip install --quiet -r requirements.txt

bash src/fetch_data.sh "$@"

for step in extract barangays population network score webmap mapfig; do
  echo "== src/$step.py"
  (cd src && ../.venv/bin/python "$step.py" "$@")
done
