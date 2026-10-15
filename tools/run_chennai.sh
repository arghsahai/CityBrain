#!/bin/sh
# Start from any working directory; all runtime data stays outside research results.
set -eu
cd "$(dirname "$0")/.."
CITYBRAIN_PYTHON="${CITYBRAIN_PYTHON:-venv/bin/python}"
if [ ! -x "$CITYBRAIN_PYTHON" ]; then
  echo 'Create a Python environment first: python3 -m venv venv' >&2
  exit 1
fi
if ! "$CITYBRAIN_PYTHON" -c 'import sumolib,traci,pyproj' 2>/dev/null; then
  echo "Install pilot dependencies: $CITYBRAIN_PYTHON -m pip install -r requirements-chennai.txt" >&2
  exit 1
fi
if ! command -v sumo >/dev/null 2>&1; then
  echo 'SUMO must be installed and available on PATH.' >&2
  exit 1
fi
if [ ! -f simulation/chennai/network/chennai.net.xml ]; then
  "$CITYBRAIN_PYTHON" -m citybrain.chennai.build
fi
exec "$CITYBRAIN_PYTHON" -m citybrain.chennai "$@"
