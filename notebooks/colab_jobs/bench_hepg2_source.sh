# Stage-75 HepG2 bench with the transfer source swapped, on a FIXED panel.
# The queue file sets: SRC_NAME, SRC_FILE (basename under $DRIVE/data/external),
# SRC_MD5, OUT_NAME, RUN_DIR and optionally AFTER (a Drive path to wait on).
# Two benches do not fit in 12 GB together -- chain the second with AFTER.
export CODE_DIR=/content/code_$(date +%s)_$$
mkdir -p "$CODE_DIR" && cp -r /content/drive/MyDrive/vcc2026/code/. "$CODE_DIR/"
source "$CODE_DIR/notebooks/colab_jobs/common.sh"
RUN="$DRIVE/runs/$RUN_DIR"
if [ -n "${AFTER:-}" ]; then wait_for "$AFTER"; fi
wait_for "$RUN/panel/shared_targets.txt"
wait_for "$DRIVE/data/external/$SRC_FILE"
mkdir -p /content/work/hepg2
[ -f /content/work/hepg2/hepg2.h5ad ] || cp "$DRIVE/data/raw/nadig_hepg2/NadigOConner2024_hepg2.h5ad" /content/work/hepg2/hepg2.h5ad
[ -f "/content/work/$SRC_FILE" ] || cp "$DRIVE/data/external/$SRC_FILE" "/content/work/$SRC_FILE"
# The Drive copy is fresh: refuse to bench a half-uploaded source.
echo "$SRC_MD5  /content/work/$SRC_FILE" | md5sum -c -
python scripts/75_bench_hepg2_transfer.py --hepg2 /content/work/hepg2/hepg2.h5ad   --k562-bulk "/content/work/$SRC_FILE" --coords "$COORDS"   --targets-file "$RUN/panel/shared_targets.txt"   --out "$RUN/$OUT_NAME" --n-targets 300 --min-cells 50 --seed 2026   --arms null_new transfer_a0.5 transfer_a1.0 transfer_a2.0 rawtransfer_a0.5          "transfer_a2.0+cismeas_a1.0+cis_a1.0" ${EXTRA_ARGS:-}
echo "job end $(date -u +%FT%TZ)"
