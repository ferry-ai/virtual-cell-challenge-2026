#!/usr/bin/env bash
# R-LAB j07_replogle_ess_rpe1_r4. Built by reports/sorgenti/corpus_cellulare_2026-09-30/colab_job.py; code snapshot of commit 42f00ff2a8ce648eca4d967d5fb22c7f15cac204. Do not edit by hand.
set -euo pipefail
export PYTHONUNBUFFERED=1 PYTHONHASHSEED=0 PYTHONIOENCODING=utf-8
DRIVE=/content/drive/MyDrive/vcc2026
SETUP="$DRIVE/runs/rlab_setup_2026-09-30_r5"
WORK=/content/work/rlab_j07_replogle_ess_rpe1_r4
OUT="$DRIVE/data/processed/corpus_cellulare_2026-09-30/j07_replogle_ess_rpe1_r4"
REC="$SETUP/receipts/j07_replogle_ess_rpe1_r4"
PY=/usr/bin/python3
echo "job j07_replogle_ess_rpe1_r4 start $(date -u +%FT%TZ) host=$(hostname) cpus=$(nproc)"
free -g | head -2; df -h /content | tail -1
test -x "$PY"; test ! -e "$WORK"; test ! -e "$REC"
test ! -e "$OUT"
bootstrap_ready() {
  sha256sum -c --quiet - <<'SUMS' || return 1
1df1ca1f82ff3e4b7a65f829dc742da4218a32adb7180721d95b65328b88e744  /content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-09-30_r5/preflight.py
39eeb3d8950eb940928b8213177e04be8337b6cb9d256a2e3acd5b0f42224b2b  /content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-09-30_r5/j07_replogle_ess_rpe1_r4_manifest.json
415ba63f614aea090b5b08273b1e38063ff53daa60313934a52d34d9b794046e  /content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-09-30_r5/code_snapshot.tar.gz
7b0433499110b38594c8869f56c1d1e046d7f28b802173b992ba53562f6431af  /content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-09-30_r5/j07_replogle_ess_rpe1_r4_spec.json
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
export RLAB_SNAPSHOT_SHA256=415ba63f614aea090b5b08273b1e38063ff53daa60313934a52d34d9b794046e RLAB_COMMIT=42f00ff2a8ce648eca4d967d5fb22c7f15cac204
"$PY" -c "import anndata" 2>/dev/null || "$PY" -m pip install -q anndata
command -v kaggle >/dev/null || "$PY" -m pip install -q kaggle
"$PY" "$C/validate_runtime.py" --out "$REC/environment_manifest_colab.json" --data-root "$DRIVE/data"
copy "$DRIVE/data/raw/controls/gene_names.csv" "$WORK/in/"
"$PY" "$SETUP/preflight.py" validate --manifest "$SETUP/j07_replogle_ess_rpe1_r4_manifest.json" --site runtime --receipt "$REC/preflight_runtime.json" --attempts 3 --interval-seconds 20
"$PY" "$C/rlab_job.py" --spec "$SETUP/j07_replogle_ess_rpe1_r4_spec.json" --stage "$WORK/stage" --out "$OUT" --runtime-manifest "$REC/environment_manifest_colab.json" --set IN="$WORK/in" AXIS="$WORK/in/gene_names.csv" WORK="$WORK" DRIVE="$DRIVE"
"$PY" "$C/publish_kaggle.py" --job-dir "$OUT" --unit k562_essential --owner davidmaisterx --slug rlab-k562-essential --config-dir "$DRIVE/runs/rlab_secrets_davidmaisterx" --stage "$WORK/publish_rlab-k562-essential" --receipt "$REC/publish_rlab-k562-essential.json"
"$PY" "$C/publish_kaggle.py" --job-dir "$OUT" --unit rpe1 --owner davidmaisterx --slug rlab-rpe1 --config-dir "$DRIVE/runs/rlab_secrets_davidmaisterx" --stage "$WORK/publish_rlab-rpe1" --receipt "$REC/publish_rlab-rpe1.json"
rm -rf "$WORK"
echo "job j07_replogle_ess_rpe1_r4 end $(date -u +%FT%TZ)"
