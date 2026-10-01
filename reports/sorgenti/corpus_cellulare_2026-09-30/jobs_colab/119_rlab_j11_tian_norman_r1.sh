#!/usr/bin/env bash
# R-LAB j11_tian_norman_r1. Built by reports/sorgenti/corpus_cellulare_2026-09-30/colab_job.py; code snapshot of commit b61631e1fb7d708f27a6afc11029a7a03faaa0ab. Do not edit by hand.
set -euo pipefail
export PYTHONUNBUFFERED=1 PYTHONHASHSEED=0 PYTHONIOENCODING=utf-8
DRIVE=/content/drive/MyDrive/vcc2026
SETUP="$DRIVE/runs/rlab_setup_2026-10-01_r9"
WORK=/content/work/rlab_j11_tian_norman_r1
OUT="$DRIVE/data/processed/corpus_cellulare_2026-09-30/j11_tian_norman_r1"
REC="$SETUP/receipts/j11_tian_norman_r1"
PY=/usr/bin/python3
echo "job j11_tian_norman_r1 start $(date -u +%FT%TZ) host=$(hostname) cpus=$(nproc)"
free -g | head -2; df -h /content | tail -1
test -x "$PY"; test ! -e "$WORK"; test ! -e "$REC"
test ! -e "$OUT"
bootstrap_ready() {
  sha256sum -c --quiet - <<'SUMS' || return 1
1df1ca1f82ff3e4b7a65f829dc742da4218a32adb7180721d95b65328b88e744  /content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-10-01_r9/preflight.py
5377212674c92613792a4ee5fb60fecebca28170b9c0510ea6212eec826b3df4  /content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-10-01_r9/j11_tian_norman_r1_manifest.json
07b61271204b909f77adabd76ab5f7a026f36169735ce404fcd1b80a127dc521  /content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-10-01_r9/code_snapshot.tar.gz
7a0e4290e9cbd64d4bea732afbdd513181903d4dfd97dc6e29af2e93f8479d11  /content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-10-01_r9/j11_tian_norman_r1_spec.json
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
export RLAB_SNAPSHOT_SHA256=07b61271204b909f77adabd76ab5f7a026f36169735ce404fcd1b80a127dc521 RLAB_COMMIT=b61631e1fb7d708f27a6afc11029a7a03faaa0ab
"$PY" -c "import anndata" 2>/dev/null || "$PY" -m pip install -q anndata
command -v kaggle >/dev/null || "$PY" -m pip install -q kaggle
"$PY" "$C/validate_runtime.py" --out "$REC/environment_manifest_colab.json" --data-root "$DRIVE/data"
copy "$DRIVE/data/raw/controls/gene_names.csv" "$WORK/in/"
"$PY" "$SETUP/preflight.py" validate --manifest "$SETUP/j11_tian_norman_r1_manifest.json" --site runtime --receipt "$REC/preflight_runtime.json" --attempts 3 --interval-seconds 20
"$PY" "$C/rlab_job.py" --spec "$SETUP/j11_tian_norman_r1_spec.json" --stage "$WORK/stage" --out "$OUT" --runtime-manifest "$REC/environment_manifest_colab.json" --set IN="$WORK/in" AXIS="$WORK/in/gene_names.csv" WORK="$WORK" DRIVE="$DRIVE"
"$PY" "$C/publish_kaggle.py" --job-dir "$OUT" --unit ALL --owner davidmaisterx --slug rlab-tian-norman --config-dir "$DRIVE/runs/rlab_secrets_davidmaisterx" --stage "$WORK/publish_rlab-tian-norman" --receipt "$REC/publish_rlab-tian-norman.json"
rm -rf "$WORK"
echo "job j11_tian_norman_r1 end $(date -u +%FT%TZ)"
