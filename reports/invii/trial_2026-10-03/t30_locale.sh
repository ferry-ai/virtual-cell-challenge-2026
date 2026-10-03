#!/usr/bin/env bash
# t30, local chain after the kernel rete-sorgenti-r1-train (INVIO_T30.md): verified download of consegna/, export of
# the A/B/C effects, stage 45 with the t22 settings, stage 48. Stops at the first failure; never uploads.
set -euo pipefail
D=/c/Users/39346/vcc2026-data
DW='C:\Users\39346\vcc2026-data'
REPO=/c/Users/39346/virtual-cell-challenge-2026
HERE=$REPO/reports/invii/trial_2026-10-03
OUTK=$D/kaggle/rete_sorgenti_r1_train_output
PY=$D/.venv/Scripts/python.exe
export VCC2026_DATA_ROOT="$DW" PYTHONIOENCODING=utf-8

step=${1:-all}
if [[ $step == all || $step == download ]]; then
  [[ -e $OUTK ]] && { echo "$OUTK exists: refusing to overwrite"; exit 1; }
  $D/.venv/Scripts/kaggle.exe kernels output alfredo2003bit/rete-sorgenti-r1-train -p "$OUTK" \
    --file-pattern '(consegna/.*|kernel_done\.json|steps\.json|env\.json|.*\.log)'
  "$PY" - "$OUTK/consegna" <<'EOF'
import hashlib, json, sys
from pathlib import Path
d = Path(sys.argv[1]); m = json.loads((d / "manifest.json").read_text())
bad = [n for n, v in m.items() if hashlib.sha256((d / n).read_bytes()).hexdigest() != v["sha256"]]
print(f"{len(m)} files, {sum(v['bytes'] for v in m.values())/1e6:.0f} MB, mismatches: {bad}")
sys.exit(1 if bad else 0)
EOF
fi
if [[ $step == all || $step == export ]]; then
  cd $REPO/reports/modelli/rete_sorgenti_2026-10-03
  "$PY" esporta_abc.py --keys "$OUTK/consegna/chiavi" --run "$OUTK/consegna/rete" --controls $D/raw/controls \
    --targets-csv $D/raw/controls/pert_counts.csv --axis $D/raw/controls/gene_names.csv \
    --out $D/processed/effects_t30_2026-10-03
fi
if [[ $step == all || $step == generate ]]; then
  cd $REPO
  E="$DW\\processed\\effects_t30_2026-10-03"
  cmd //c "scripts\\py.cmd scripts\\45_generate_prediction.py --run-id t30gen --trial trial-ext-profile --effects A=$E\\effects_A.npz --effects B=$E\\effects_B.npz --effects C=$E\\effects_C.npz" 2>&1 | tee $HERE/t30_stage45.log
  cmd //c "scripts\\py.cmd scripts\\48_package_prediction.py --run-id t30pack --prediction $DW\\artifacts\\t30gen\\prediction.h5ad" 2>&1 | tee $HERE/t30_stage48.log
fi
