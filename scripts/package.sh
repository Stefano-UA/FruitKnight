#!/usr/bin/env bash
# Build the clean submission archive (sources, assets, config, scripts, README and compiled docs).
# Usage: ./scripts/package.sh [output.zip]   (default: fruit_knight_submission.zip)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

OUTPUT="${1:-fruit_knight_submission.zip}"

# Docs first so that docs/html is guaranteed to be up to date (also prepares .venv).
"$ROOT/scripts/docs.sh"

# shellcheck disable=SC1091
if [[ -f .venv/bin/activate ]]; then source .venv/bin/activate; else source .venv/Scripts/activate; fi

echo ">> Creating $OUTPUT"
python - "$OUTPUT" <<'PYEOF'
import os
import sys
import zipfile
from pathlib import Path

root = Path.cwd()
output = Path(sys.argv[1])
if not output.is_absolute():
    output = root / output
output.unlink(missing_ok=True)

INCLUDE = ["src", "assets", "config", "scripts", "requirements.txt", "README.md", "docs/html"]
EXCLUDED_DIRS = {".venv", ".git", "__pycache__", ".pytest_cache", ".doctrees", "build", "dist", ".mypy_cache"}
EXCLUDED_SUFFIXES = {".pyc", ".pyo", ".part"}
top = output.stem  # every file lives under one folder named after the archive

def wanted(path: Path) -> bool:
    return not (set(path.parts) & EXCLUDED_DIRS) and path.suffix not in EXCLUDED_SUFFIXES

count = 0
with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as zf:
    for item in INCLUDE:
        base = root / item
        files = [base] if base.is_file() else sorted(p for p in base.rglob("*") if p.is_file())
        for path in files:
            rel = path.relative_to(root)
            if not wanted(rel):
                continue
            info = zipfile.ZipInfo.from_file(path, Path(top) / rel)
            info.compress_type = zipfile.ZIP_DEFLATED
            if rel.parts[0] == "scripts":
                info.external_attr = 0o755 << 16  # keep scripts executable after extraction
            zf.writestr(info, path.read_bytes())
            count += 1
print(f"{count} files written to {output}")
PYEOF
echo ">> Done: $OUTPUT"
