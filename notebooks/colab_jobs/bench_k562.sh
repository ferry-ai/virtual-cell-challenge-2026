export CODE_DIR=/content/code_$(date +%s)_$$
mkdir -p "$CODE_DIR" && cp -r /content/drive/MyDrive/vcc2026/code/. "$CODE_DIR/"
source "$CODE_DIR/notebooks/colab_jobs/common.sh"
wait_for "$K562SC/report.json"
python scripts/73_bench_k562_panel.py --k562 "$K562SC" --coords "$COORDS"   --out "$DRIVE/runs/bench_k562_2026-09-17/b002" --control-cells 8000   --arms null_g0 null_new oracle_a0.25 oracle_a0.5 oracle_a1.0 oracle_a2.0 shared_a1.0 cis_a1.0          oracle_a0.5+cis_a1.0 oracle_a1.0+shared_a1.0 ${EXTRA_ARGS:-}
echo "job end $(date -u +%FT%TZ)"
