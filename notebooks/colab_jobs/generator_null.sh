export CODE_DIR=/content/code_$(date +%s)_$$
mkdir -p "$CODE_DIR" && cp -r /content/drive/MyDrive/vcc2026/code/. "$CODE_DIR/"
source "$CODE_DIR/notebooks/colab_jobs/common.sh"
# After the benches: on 2026-09-17 the first attempt ran out of memory next to the extraction.
wait_for "$DRIVE/runs/bench_hepg2_2026-09-17/h002/bench.json"
python scripts/72_generator_null.py \
  --out "$DRIVE/runs/generator_null_2026-09-17/n003" \
  --controls-dir "$DRIVE/data/raw/controls" \
  --contexts A B C --arms real g0 kde --n-pseudo 20 --cells 400 ${EXTRA_ARGS:-}
echo "job end $(date -u +%FT%TZ)"
