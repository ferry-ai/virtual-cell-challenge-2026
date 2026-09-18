# Generate, package and verify one trial on Colab. Queue a copy with TRIAL and GEN_ARGS set
# on the first lines (e.g. TRIAL=t02; GEN_ARGS="--a-transfer 1.5 --a-cis 1 --a-cis-measured 1").
export CODE_DIR=/content/code_$(date +%s)_$$
mkdir -p "$CODE_DIR" && cp -r /content/drive/MyDrive/vcc2026/code/. "$CODE_DIR/"
source "$CODE_DIR/notebooks/colab_jobs/common.sh"
: "${TRIAL:?set TRIAL, e.g. t02}"
: "${GEN_ARGS:?set GEN_ARGS, the amplitudes chosen from the benches}"
wait_for "$K562SC/report.json"
WORK=/content/work/$TRIAL
mkdir -p "$WORK"
python scripts/76_generate_sc_prediction.py --run-id "$TRIAL" --k562 "$K562SC" --coords "$COORDS" \
  --out "$WORK/gen" $GEN_ARGS
python -m pip install -q vcc-cli==0.2.0
python scripts/48_package_prediction.py --run-id "${TRIAL}pack" --prediction "$WORK/gen/prediction.h5ad" \
  --out "$WORK/pack" --reserve-gib 4
DEST="$DRIVE/runs/trials_2026-09-17/$TRIAL"
mkdir -p "$DEST"
cp "$WORK/gen/generation.json" "$WORK/pack/"*.json "$DEST/"
cp "$WORK/pack/prediction.vcc" "$DEST/prediction.vcc"
sha256sum "$DEST/prediction.vcc" | tee "$DEST/prediction.vcc.sha256"
echo "job end $(date -u +%FT%TZ)"
