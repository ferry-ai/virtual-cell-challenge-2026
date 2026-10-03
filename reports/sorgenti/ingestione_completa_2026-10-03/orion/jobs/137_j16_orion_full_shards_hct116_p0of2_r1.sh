#!/usr/bin/env bash
# Full ingestion, Orion shards j16_orion_full_shards_hct116_p0of2_r1. Built by reports/sorgenti/ingestione_completa_2026-10-03/orion/build_orion_job.py; code snapshot of commit 0fa011530c2a4556d46fd27d3a93e7fbe4f8f909.
# Do not edit by hand.
set -euo pipefail
export PYTHONUNBUFFERED=1 PYTHONHASHSEED=0 PYTHONIOENCODING=utf-8
DRIVE=/content/drive/MyDrive/vcc2026
SETUP="$DRIVE/runs/orion_full_setup_2026-10-03_r1"
WORK=/content/work/j16_orion_full_shards_hct116_p0of2_r1
OUT="$DRIVE/data/processed/ingestione_completa_2026-10-03/j16_orion_full_shards_hct116_p0of2_r1"
REC="$SETUP/receipts/j16_orion_full_shards_hct116_p0of2_r1"
PY=/usr/bin/python3
echo "job j16_orion_full_shards_hct116_p0of2_r1 start $(date -u +%FT%TZ) host=$(hostname) cpus=$(nproc)"
free -g | head -2; df -h /content | tail -1; df -h /content/drive | tail -1
test -x "$PY"; test ! -e "$WORK"; test ! -e "$REC"; test ! -e "$OUT"
bootstrap_ready() {
  sha256sum -c --quiet - <<'SUMS' || return 1
4df47fab900ee65ac2527b6135a8118c395ea73a52157fa1f44b0e7cca83da01  /content/drive/MyDrive/vcc2026/runs/orion_full_setup_2026-10-03_r1/code_snapshot.tar.gz
1df1ca1f82ff3e4b7a65f829dc742da4218a32adb7180721d95b65328b88e744  /content/drive/MyDrive/vcc2026/runs/orion_full_setup_2026-10-03_r1/preflight.py
51d028d37bd0c219f9ec25b6a834565b17b0d5c97e0e3ca957d305ef4015a21c  /content/drive/MyDrive/vcc2026/data/processed/ingestione_completa_2026-10-03/j16_orion_full_meta_hct116_r1/sample/HCT116.parquet
94af7192f27e07ca206d626605361cb655bf346bf55dd1318d8f81f728d9a0a5  /content/drive/MyDrive/vcc2026/data/processed/ingestione_completa_2026-10-03/j16_orion_full_meta_hct116_r1/sample/HCT116.parquet.sha256
265804567e9a9e11b769c9699661e443e4ad696429de920e57bfe5ced5bec8b7  /content/drive/MyDrive/vcc2026/data/processed/ingestione_completa_2026-10-03/j16_orion_full_meta_hct116_r1/sample/HCT116.json
c4b9f647be5c04c1febb635ad0edb81ed45f7e93832f3445e4439868e561780c  /content/drive/MyDrive/vcc2026/runs/orion_full_setup_2026-10-03_r1/j16_orion_full_shards_hct116_p0of2_r1_manifest.json
SUMS
}
for attempt in $(seq 1 45); do
  if bootstrap_ready; then break; fi
  echo "waiting for the setup files by hash, attempt $attempt/45"; sleep 20
done
bootstrap_ready
copy() { for i in 1 2 3 4 5; do cp "$1" "$2" && return 0; echo "copy of $1 failed, attempt $i"; sleep 30; done; return 1; }
mkdir -p "$WORK/code" "$WORK/in" "$REC"
tar -xzf "$SETUP/code_snapshot.tar.gz" -C "$WORK/code"
C="$WORK/code/reports/sorgenti/ingestione_completa_2026-10-03/orion"
"$PY" -c "import anndata" 2>/dev/null || "$PY" -m pip install -q anndata
"$PY" -c "import pyarrow" 2>/dev/null || "$PY" -m pip install -q pyarrow
"$PY" "$WORK/code/reports/sorgenti/corpus_cellulare_2026-09-30/validate_runtime.py" --out "$REC/environment_manifest_colab.json" --data-root "$DRIVE/data"
copy "$DRIVE/data/raw/controls/gene_names.csv" "$WORK/in/"
"$PY" "$SETUP/preflight.py" validate --manifest "$SETUP/j16_orion_full_shards_hct116_p0of2_r1_manifest.json" --site runtime --receipt "$REC/preflight_runtime.json" --attempts 3 --interval-seconds 20
mkdir -p "$OUT"
"$PY" "$C/orion_job.py" shards --spec "$C/specs/orion_full_v1.json" --line HCT116 --sample "$DRIVE/data/processed/ingestione_completa_2026-10-03/j16_orion_full_meta_hct116_r1/sample" --axis "$WORK/in/gene_names.csv" --stage "$WORK/stage" --out "$OUT/shards" --data-root "$DRIVE/data" --runtime-manifest "$REC/environment_manifest_colab.json" --part 0/2
rm -rf "$WORK"
echo "job j16_orion_full_shards_hct116_p0of2_r1 end $(date -u +%FT%TZ)"
