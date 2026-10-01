#!/usr/bin/env bash
# R-LAB j07_replogle_ess_rpe1_r8. Built by reports/sorgenti/corpus_cellulare_2026-09-30/colab_job.py; code snapshot of commit 5524806187fafdb5d78305ba20cd0d006f6c0ddb. Do not edit by hand.
set -euo pipefail
export PYTHONUNBUFFERED=1 PYTHONHASHSEED=0 PYTHONIOENCODING=utf-8
DRIVE=/content/drive/MyDrive/vcc2026
SETUP="$DRIVE/runs/rlab_setup_2026-10-01_r10"
WORK=/content/work/rlab_j07_replogle_ess_rpe1_r8
OUT="$DRIVE/data/processed/corpus_cellulare_2026-09-30/j07_replogle_ess_rpe1_r8"
REC="$SETUP/receipts/j07_replogle_ess_rpe1_r8"
PY=/usr/bin/python3
echo "job j07_replogle_ess_rpe1_r8 start $(date -u +%FT%TZ) host=$(hostname) cpus=$(nproc)"
free -g | head -2; df -h /content | tail -1
test -x "$PY"; test ! -e "$WORK"; test ! -e "$REC"
test ! -e "$OUT"
bootstrap_ready() {
  sha256sum -c --quiet - <<'SUMS' || return 1
1df1ca1f82ff3e4b7a65f829dc742da4218a32adb7180721d95b65328b88e744  /content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-10-01_r10/preflight.py
41db21493d484ef6230e6161c7fe7e7c9f45890d7f60c23e62d7725761cfa853  /content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-10-01_r10/j07_replogle_ess_rpe1_r8_manifest.json
b4a3c6f79b29edf7228c082e32309a8aa75ab550e5bd875fa7669ba2753c86f2  /content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-10-01_r10/code_snapshot.tar.gz
70e16730ef7b864a9083b43e4f9c2ab855c80099c90b58c3f49e75622ca0f0ad  /content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-10-01_r10/j07_replogle_ess_rpe1_r8_spec.json
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
export RLAB_SNAPSHOT_SHA256=b4a3c6f79b29edf7228c082e32309a8aa75ab550e5bd875fa7669ba2753c86f2 RLAB_COMMIT=5524806187fafdb5d78305ba20cd0d006f6c0ddb
"$PY" -c "import anndata" 2>/dev/null || "$PY" -m pip install -q anndata
command -v kaggle >/dev/null || "$PY" -m pip install -q kaggle
"$PY" "$C/validate_runtime.py" --out "$REC/environment_manifest_colab.json" --data-root "$DRIVE/data"
copy "$DRIVE/data/raw/controls/gene_names.csv" "$WORK/in/"
"$PY" "$SETUP/preflight.py" validate --manifest "$SETUP/j07_replogle_ess_rpe1_r8_manifest.json" --site runtime --receipt "$REC/preflight_runtime.json" --attempts 3 --interval-seconds 20
"$PY" "$C/rlab_job.py" --spec "$SETUP/j07_replogle_ess_rpe1_r8_spec.json" --stage "$WORK/stage" --out "$OUT" --runtime-manifest "$REC/environment_manifest_colab.json" --set IN="$WORK/in" AXIS="$WORK/in/gene_names.csv" WORK="$WORK" DRIVE="$DRIVE"
"$PY" "$C/publish_kaggle.py" --job-dir "$OUT" --unit k562_essential --owner davidmaisterx --slug rlab-k562-essential-r2 --config-dir "$DRIVE/runs/rlab_secrets_davidmaisterx" --stage "$WORK/publish_rlab-k562-essential-r2" --receipt "$REC/publish_rlab-k562-essential-r2.json"
"$PY" "$C/publish_kaggle.py" --job-dir "$OUT" --unit rpe1 --owner davidmaisterx --slug rlab-rpe1-r2 --config-dir "$DRIVE/runs/rlab_secrets_davidmaisterx" --stage "$WORK/publish_rlab-rpe1-r2" --receipt "$REC/publish_rlab-rpe1-r2.json"
rm -rf "$WORK"
echo "job j07_replogle_ess_rpe1_r8 end $(date -u +%FT%TZ)"
