#!/usr/bin/env bash
# R-LAB j04_h1_trainval_r1. Built by reports/sorgenti/corpus_cellulare_2026-09-30/colab_job.py; code snapshot of commit cac5a604db2c8f008baf4ccb3f8d257119c821d8. Do not edit by hand.
set -euo pipefail
export PYTHONUNBUFFERED=1 PYTHONHASHSEED=0 PYTHONIOENCODING=utf-8
DRIVE=/content/drive/MyDrive/vcc2026
SETUP="$DRIVE/runs/rlab_setup_2026-09-30_r3"
WORK=/content/work/rlab_j04_h1_trainval_r1
OUT="$DRIVE/data/processed/corpus_cellulare_2026-09-30/j04_h1_trainval_r1"
REC="$SETUP/receipts/j04_h1_trainval_r1"
PY=/usr/bin/python3
echo "job j04_h1_trainval_r1 start $(date -u +%FT%TZ) host=$(hostname) cpus=$(nproc)"
free -g | head -2; df -h /content | tail -1
test -x "$PY"; test ! -e "$WORK"; test ! -e "$REC"
test ! -e "$OUT"
bootstrap_ready() {
  sha256sum -c --quiet - <<'SUMS' || return 1
1df1ca1f82ff3e4b7a65f829dc742da4218a32adb7180721d95b65328b88e744  /content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-09-30_r3/preflight.py
3b0b11dc7168314161c602c7f5a42b85ade567865b1a5eb1bcfe080be886c249  /content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-09-30_r3/j04_h1_trainval_r1_manifest.json
439a69a6e4b2e61ade9847147e9a51d9486c022716464d6182baffd67c2405f9  /content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-09-30_r3/code_snapshot.tar.gz
cf696ead41dc8387da0de1e75180942713f16b8d91a2ea067abdd48eee95040d  /content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-09-30_r3/j04_h1_trainval_r1_spec.json
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
C="$WORK/code/reports/sorgenti/corpus_cellulare_2026-09-30"
export RLAB_SNAPSHOT_SHA256=439a69a6e4b2e61ade9847147e9a51d9486c022716464d6182baffd67c2405f9 RLAB_COMMIT=cac5a604db2c8f008baf4ccb3f8d257119c821d8
"$PY" -c "import anndata" 2>/dev/null || "$PY" -m pip install -q anndata
command -v kaggle >/dev/null || "$PY" -m pip install -q kaggle
"$PY" "$C/validate_runtime.py" --out "$REC/environment_manifest_colab.json" --data-root "$DRIVE/data"
copy "$DRIVE/data/raw/controls/gene_names.csv" "$WORK/in/"
"$PY" "$SETUP/preflight.py" validate --manifest "$SETUP/j04_h1_trainval_r1_manifest.json" --site runtime --receipt "$REC/preflight_runtime.json" --attempts 3 --interval-seconds 20
"$PY" "$C/rlab_job.py" --spec "$SETUP/j04_h1_trainval_r1_spec.json" --stage "$WORK/stage" --out "$OUT" --runtime-manifest "$REC/environment_manifest_colab.json" --set IN="$WORK/in" AXIS="$WORK/in/gene_names.csv" WORK="$WORK" DRIVE="$DRIVE"
"$PY" "$C/publish_kaggle.py" --job-dir "$OUT" --unit ALL --owner davideferrante11 --slug rlab-h1-vcc2025-trainval --config-dir "$DRIVE/runs/rlab_secrets" --stage "$WORK/publish_rlab-h1-vcc2025-trainval" --receipt "$REC/publish_rlab-h1-vcc2025-trainval.json"
rm -rf "$WORK"
echo "job j04_h1_trainval_r1 end $(date -u +%FT%TZ)"
