export CODE_DIR=/content/code_$(date +%s)_$$
mkdir -p "$CODE_DIR" && cp -r /content/drive/MyDrive/vcc2026/code/. "$CODE_DIR/"
source "$CODE_DIR/notebooks/colab_jobs/common.sh"
wait_for "$K562SC/report.json"
# One bench at a time: two of them together do not fit in 12 GB.
wait_for "$DRIVE/runs/bench_k562_2026-09-17/b002/bench.json"
mkdir -p /content/work/hepg2
[ -f /content/work/hepg2/hepg2.h5ad ] || cp "$DRIVE/data/raw/nadig_hepg2/NadigOConner2024_hepg2.h5ad" /content/work/hepg2/hepg2.h5ad
python scripts/75_bench_hepg2_transfer.py --hepg2 /content/work/hepg2/hepg2.h5ad --k562 "$K562SC"   --coords "$COORDS" --out "$DRIVE/runs/bench_hepg2_2026-09-17/h002" --n-targets 300 --min-cells 50   --arms null_new "g0:rawtransfer_a0.2" transfer_a0.5 transfer_a1.0 transfer_a2.0 rawtransfer_a0.25 rawtransfer_a0.5          "cismeas_a1.0+cis_a1.0" "transfer_a1.0+cismeas_a1.0+cis_a1.0" "rawtransfer_a0.25+cismeas_a1.0+cis_a1.0"          "transfer_a2.0+cismeas_a1.0+cis_a1.0" "transfer_a1.0+cismeas_a1.0+cis_a1.0+shared_a1.0" ${EXTRA_ARGS:-}
echo "job end $(date -u +%FT%TZ)"
