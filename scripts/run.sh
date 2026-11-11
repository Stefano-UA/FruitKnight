#!/usr/bin/env bash
# Idempotent setup (venv + dependencies + MediaPipe models) and launch of Fruit Knight.
# Usage: ./scripts/run.sh [--reinstall] [game arguments, e.g. --no-camera]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

REINSTALL=0
ARGS=()
for arg in "$@"; do
  if [[ "$arg" == "--reinstall" ]]; then REINSTALL=1; else ARGS+=("$arg"); fi
done

# Pick the first working Python 3 interpreter (python3 may be a stub on Windows).
PY=""
for candidate in python3 python py; do
  if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c "import sys; sys.exit(sys.version_info < (3, 10))" >/dev/null 2>&1; then
    PY="$candidate"
    break
  fi
done
if [[ -z "$PY" ]]; then
  echo "error: Python 3.10+ is required" >&2
  exit 1
fi

NEEDS_INSTALL=$REINSTALL
if [[ ! -d .venv ]]; then
  echo ">> Creating virtual environment (.venv)"
  "$PY" -m venv .venv
  NEEDS_INSTALL=1
fi

# shellcheck disable=SC1091
if [[ -f .venv/bin/activate ]]; then source .venv/bin/activate; else source .venv/Scripts/activate; fi

if [[ "$NEEDS_INSTALL" == "1" ]]; then
  echo ">> Installing dependencies from requirements.txt"
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt
fi

export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"

echo ">> Checking MediaPipe models (assets/models)"
python -m fruit_knight.vision.models

echo ">> Launching Fruit Knight"
exec python -m fruit_knight.main "${ARGS[@]+"${ARGS[@]}"}"
