export CODE_DIR=/content/code_$(date +%s)_$$
mkdir -p "$CODE_DIR" && cp -r /content/drive/MyDrive/vcc2026/code/. "$CODE_DIR/"
source "$CODE_DIR/notebooks/colab_jobs/common.sh"
python scripts/71_extract_k562_sc.py   --src "$DRIVE/data/raw/replogle/K562_gwps_raw_singlecell_01.h5ad"   --out "$K562SC" --work /content/work/k562_x002   --panel "$DRIVE/data/raw/controls/pert_counts.csv"   --ntc-cells 20000 --other-targets 400 --segment-rows 250000 ${EXTRA_ARGS:-}
echo "job end $(date -u +%FT%TZ)"
