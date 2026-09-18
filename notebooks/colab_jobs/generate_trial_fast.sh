# Generate, package and verify one trial. Two costs of jobs 011/012 are removed:
#  * the stage-71 statistics (1.48 GB) are copied to local disk once and read from there;
#    read straight from the Drive mount, by two jobs at the same time, they produced no
#    output in 50 minutes;
#  * the cis bins come from the stage-77 neighbour pairs (--cis-pairs), so the source
#    effects of ~9,600 non-panel targets are never computed.
# Set TRIAL, GEN_ARGS and optionally AFTER before sourcing/prepending this body.
: "${TRIAL:?set TRIAL, e.g. t02}"
: "${GEN_ARGS:?set GEN_ARGS, the amplitudes chosen from the benches}"
export CODE_DIR=/content/code_$(date +%s)_$$
mkdir -p "$CODE_DIR" && cp -r /content/drive/MyDrive/vcc2026/code/. "$CODE_DIR/"
source "$CODE_DIR/notebooks/colab_jobs/common.sh"
[ -n "${AFTER:-}" ] && wait_for "$AFTER"
LOCAL=/content/work/k562sc
mkdir -p "$LOCAL"
if [ ! -f "$LOCAL/READY" ]; then
  echo "$(date -u +%T) copying stage-71 statistics to local disk"
  for f in groups.csv var.csv report.json group_stats.npz; do cp "$K562SC/$f" "$LOCAL/$f.part" && mv "$LOCAL/$f.part" "$LOCAL/$f"; done
  touch "$LOCAL/READY"
fi
echo "$(date -u +%T) local copy ready"; ls -la "$LOCAL"
WORK=/content/work/$TRIAL
mkdir -p "$WORK"
python -u scripts/76_generate_sc_prediction.py --run-id "$TRIAL" --k562 "$LOCAL" --coords "$COORDS" \
  --cis-pairs "$DRIVE/data/external/annotation/k562_neighbour_pairs.csv" \
  --out "$WORK/gen" $GEN_ARGS || { echo "GENERATION FAILED rc=$?"; exit 1; }
echo "$(date -u +%T) generation done, packaging"
python -m pip install -q vcc-cli==0.2.0
python -u scripts/48_package_prediction.py --run-id "${TRIAL}pack" --prediction "$WORK/gen/prediction.h5ad" \
  --out "$WORK/pack" --reserve-gib 4 || { echo "PACKAGING FAILED rc=$?"; exit 1; }
DEST="$DRIVE/runs/trials_2026-09-17/$TRIAL"
mkdir -p "$DEST"
cp "$WORK/gen/generation.json" "$WORK/pack/"*.json "$DEST/"
cp "$WORK/pack/prediction.vcc" "$DEST/prediction.vcc"
sha256sum "$DEST/prediction.vcc" | tee "$DEST/prediction.vcc.sha256"
echo "job end $(date -u +%FT%TZ)"
