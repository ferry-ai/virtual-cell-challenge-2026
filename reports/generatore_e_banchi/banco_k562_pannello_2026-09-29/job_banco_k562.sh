# R-REV azione 4 (Claude f2abd9a6): K562 panel bench, trial-01 generator (g0:, stage 45's path), 3 generator seeds.
# Protocol and rule: reports/generatore_e_banchi/banco_k562_pannello_2026-09-29/RISULTATI.md (18:10, 29/09).
# Inputs: build_arms.py's <arm>.npz and manifest.json in $IN (copied by hand to Drive, manifest last).
# It must run ALONE on the 12 GB runtime (docs/LAVORO.md section 3: two benches together can end in rc=137).
# Queue by hand, refusing to overwrite (queue_trial.sh only wraps generate_trial.sh).
export CODE_DIR=/content/code_$(date +%s)_$$
mkdir -p "$CODE_DIR" && cp -r /content/drive/MyDrive/vcc2026/code/. "$CODE_DIR/"
source "$CODE_DIR/notebooks/colab_jobs/common.sh"
wait_for "$K562SC/report.json"
IN="$DRIVE/data/processed/banco_k562_pannello_2026-09-29"
wait_for "$IN/manifest.json"
OUT="$DRIVE/runs/banco_k562_pannello_2026-09-29/k001"
[ -e "$OUT/bench.json" ] && { echo "refusing: $OUT already holds a bench"; exit 2; }
EFFECTS=()
ARMS=()
for name in t22 t23 t22s gate excl exclrs t22h t22d t22r9; do
  [ -f "$IN/$name.npz" ] || { echo "missing $IN/$name.npz"; exit 2; }
  EFFECTS+=(--effects "$name=$IN/$name.npz")
  ARMS+=("g0:${name}_a1.0")
done
if [ -f "$IN/rb.npz" ]; then          # built only when R-B is more than 10% from 3.152
  EFFECTS+=(--effects "rb=$IN/rb.npz")
  ARMS+=("g0:rb_a1.0")
fi
ARMS+=("g0d:t22_a1.0")                # G1: C1's effects with the per-gene dispersion
sha256sum "$IN"/*.npz
python scripts/73_bench_k562_panel.py --k562 "$K562SC" --out "$OUT" \
  --control-cells 8000 --min-cells 40 --seed 2026 --gen-seeds 1 2 3 \
  "${EFFECTS[@]}" --arms "${ARMS[@]}"
echo "job end $(date -u +%FT%TZ)"
