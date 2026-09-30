#!/usr/bin/env bash
set -euo pipefail
export DRIVE=/content/drive/MyDrive/vcc2026
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
SETUP="$DRIVE/runs/lead_stack_setup_2026-09-29_r1"
OUT="$DRIVE/runs/lead_stack_dependencies_2026-09-29_r3"
SCRATCH=/content/lead_stack_dependencies_r3
test ! -e "$OUT"
test ! -e "$SCRATCH"
mkdir -p "$OUT" "$SCRATCH/code"
echo "a2e407961e2aefacd634f17541440bfd1e7035a036658f63cb655a33a9926698  $SETUP/code_snapshot.tar.gz" | sha256sum -c -
tar -xzf "$SETUP/code_snapshot.tar.gz" -C "$SCRATCH/code"
# Host Python remains unchanged; no host ensurepip or virtualenv dependency.
python -m pip install --no-cache-dir --no-deps --ignore-installed \
  --target "$SCRATCH/bootstrap_site" uv==0.8.22 > "$OUT/bootstrap.log" 2>&1
UV="$SCRATCH/bootstrap_site/bin/uv"
test -x "$UV"
export UV_PYTHON_INSTALL_DIR="$SCRATCH/python"
export UV_PYTHON_BIN_DIR="$SCRATCH/python_bin"
export UV_CACHE_DIR="$SCRATCH/uv_cache"
export UV_NO_MODIFY_PATH=1
"$UV" python install 3.11.13 > "$OUT/python_install.log" 2>&1
MANAGED_PYTHON=$("$UV" python find --managed-python 3.11.13)
case "$MANAGED_PYTHON" in "$SCRATCH/python/"*) ;; *) exit 42 ;; esac
"$UV" venv --python "$MANAGED_PYTHON" --seed "$SCRATCH/venv" > "$OUT/venv.log" 2>&1
"$SCRATCH/venv/bin/python" - "$OUT/environment.json" "$MANAGED_PYTHON" <<'PY'
import hashlib, json, platform, sys
from pathlib import Path
assert sys.version_info[:3] == (3, 11, 13)
info = {"python": sys.version, "platform": platform.platform(),
        "executable": sys.executable, "managed_base": sys.argv[2],
        "managed_base_sha256": hashlib.sha256(Path(sys.argv[2]).read_bytes()).hexdigest(),
        "uv_version": "0.8.22", "meminfo": Path('/proc/meminfo').read_text(),
        "action": "managed Python dependency dry run; no model download or inference"}
with open(sys.argv[1], 'x', encoding='utf-8') as f:
    json.dump(info, f, indent=2)
print(json.dumps(info))
PY
"$SCRATCH/venv/bin/python" -m pip install --dry-run --ignore-installed --no-cache-dir \
  --report "$OUT/resolution.json" \
  -r "$SCRATCH/code/reports/analisi/lead_scientist_2026-09-29/neural/requirements_stack.txt" \
  > "$OUT/resolution.log" 2>&1
printf '%s\n' 'Managed Python dependency resolution completed; no model download.' > "$OUT/done.txt"
