#!/usr/bin/env bash
# Idempotent setup (venv + dependencies) and Sphinx HTML build into docs/html (furo, dark mode).
# Usage: ./scripts/docs.sh [--reinstall]
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

REINSTALL=0
for arg in "$@"; do
  if [[ "$arg" == "--reinstall" ]]; then REINSTALL=1; fi
done

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
export SDL_VIDEODRIVER=dummy SDL_AUDIODRIVER=dummy PYGAME_HIDE_SUPPORT_PROMPT=1

echo ">> Generating API stubs (sphinx-apidoc)"
rm -rf docs/source/_apidoc
python -m sphinx.ext.apidoc -f -e -M -o docs/source/_apidoc src/fruit_knight

echo ">> Building HTML documentation (sphinx-build, warnings are errors)"
rm -rf docs/html
python -m sphinx -b html -W --keep-going -d docs/.doctrees docs/source docs/html
touch docs/html/.nojekyll

echo ">> Documentation ready: docs/html/index.html"
