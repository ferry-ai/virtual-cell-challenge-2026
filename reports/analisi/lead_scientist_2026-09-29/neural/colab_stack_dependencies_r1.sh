#!/usr/bin/env bash
set -euo pipefail
export DRIVE=/content/drive/MyDrive/vcc2026
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
SETUP="$DRIVE/runs/lead_stack_setup_2026-09-29_r1"
OUT="$DRIVE/runs/lead_stack_dependencies_2026-09-29_r1"
SCRATCH=/content/lead_stack_dependencies_r1
test ! -e "$OUT"
test ! -e "$SCRATCH"
mkdir -p "$OUT" "$SCRATCH/code"
echo "a2e407961e2aefacd634f17541440bfd1e7035a036658f63cb655a33a9926698  $SETUP/code_snapshot.tar.gz" | sha256sum -c -
tar -xzf "$SETUP/code_snapshot.tar.gz" -C "$SCRATCH/code"
python - "$OUT/environment.json" <<'PY'
import json, platform, sys
from pathlib import Path
info = {"python": sys.version, "platform": platform.platform(),
        "meminfo": Path('/proc/meminfo').read_text(),
        "action": "dependency resolution dry run; no model download or inference"}
with open(sys.argv[1], 'x', encoding='utf-8') as f:
    json.dump(info, f, indent=2)
print(json.dumps(info))
if not (3, 10) <= sys.version_info[:2] <= (3, 12):
    raise SystemExit("Pinned NumPy/Torch wheels require Python3.10-3.12; no implicit version change")
PY
python -m venv "$SCRATCH/venv"
"$SCRATCH/venv/bin/python" -m pip install --dry-run --ignore-installed --no-cache-dir \
  --report "$OUT/resolution.json" \
  -r "$SCRATCH/code/reports/analisi/lead_scientist_2026-09-29/neural/requirements_stack.txt" \
  > "$OUT/resolution.log" 2>&1
printf '%s\n' 'Dependency resolution completed; no runtime install or model download.' > "$OUT/done.txt"
