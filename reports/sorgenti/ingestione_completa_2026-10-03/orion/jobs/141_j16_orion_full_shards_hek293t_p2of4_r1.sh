#!/usr/bin/env bash
# Full ingestion, Orion shards j16_orion_full_shards_hek293t_p2of4_r1. Built by reports/sorgenti/ingestione_completa_2026-10-03/orion/build_orion_job.py; code snapshot of commit 0fa011530c2a4556d46fd27d3a93e7fbe4f8f909.
# Do not edit by hand.
set -euo pipefail
export PYTHONUNBUFFERED=1 PYTHONHASHSEED=0 PYTHONIOENCODING=utf-8
DRIVE=/content/drive/MyDrive/vcc2026
SETUP="$DRIVE/runs/orion_full_setup_2026-10-03_r1"
WORK=/content/work/j16_orion_full_shards_hek293t_p2of4_r1
OUT="$DRIVE/data/processed/ingestione_completa_2026-10-03/j16_orion_full_shards_hek293t_p2of4_r1"
REC="$SETUP/receipts/j16_orion_full_shards_hek293t_p2of4_r1"
PY=/usr/bin/python3
echo "job j16_orion_full_shards_hek293t_p2of4_r1 start $(date -u +%FT%TZ) host=$(hostname) cpus=$(nproc)"
free -g | head -2; df -h /content | tail -1; df -h /content/drive | tail -1
test -x "$PY"; test ! -e "$WORK"; test ! -e "$REC"; test ! -e "$OUT"
bootstrap_ready() {
  sha256sum -c --quiet - <<'SUMS' || return 1
4df47fab900ee65ac2527b6135a8118c395ea73a52157fa1f44b0e7cca83da01  /content/drive/MyDrive/vcc2026/runs/orion_full_setup_2026-10-03_r1/code_snapshot.tar.gz
1df1ca1f82ff3e4b7a65f829dc742da4218a32adb7180721d95b65328b88e744  /content/drive/MyDrive/vcc2026/runs/orion_full_setup_2026-10-03_r1/preflight.py
26a8725a0954a522586e3b1e378fc41430a86fc92642ff83746a5d02a9b379e7  /content/drive/MyDrive/vcc2026/data/processed/ingestione_completa_2026-10-03/j16_orion_full_meta_hek293t_r1/sample/HEK293T.parquet
86a3478779951764b02c257ad20f676b672865eea80944e87514ff8eeca7b375  /content/drive/MyDrive/vcc2026/data/processed/ingestione_completa_2026-10-03/j16_orion_full_meta_hek293t_r1/sample/HEK293T.parquet.sha256
b9367f209d12aa2e7cc8fca7ce23ea1d9cdb442477703314817dd795c44b098b  /content/drive/MyDrive/vcc2026/data/processed/ingestione_completa_2026-10-03/j16_orion_full_meta_hek293t_r1/sample/HEK293T.json
51ac067e278e542b87dc3f2fe6da82feda7a1e9dcb3800ed640547fd33062ad4  /content/drive/MyDrive/vcc2026/runs/orion_full_setup_2026-10-03_r1/j16_orion_full_shards_hek293t_p2of4_r1_manifest.json
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
"$PY" "$SETUP/preflight.py" validate --manifest "$SETUP/j16_orion_full_shards_hek293t_p2of4_r1_manifest.json" --site runtime --receipt "$REC/preflight_runtime.json" --attempts 3 --interval-seconds 20
mkdir -p "$OUT"
"$PY" "$C/orion_job.py" shards --spec "$C/specs/orion_full_v1.json" --line HEK293T --sample "$DRIVE/data/processed/ingestione_completa_2026-10-03/j16_orion_full_meta_hek293t_r1/sample" --axis "$WORK/in/gene_names.csv" --stage "$WORK/stage" --out "$OUT/shards" --data-root "$DRIVE/data" --runtime-manifest "$REC/environment_manifest_colab.json" --part 2/4
rm -rf "$WORK"
echo "job j16_orion_full_shards_hek293t_p2of4_r1 end $(date -u +%FT%TZ)"
