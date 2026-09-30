#!/usr/bin/env bash
# R-LAB j07_replogle_ess_rpe1_r3. Built by reports/sorgenti/corpus_cellulare_2026-09-30/colab_job.py; code snapshot of commit 58a64aab91006c5ad1ddec3c8244d48145f45b9e. Do not edit by hand.
set -euo pipefail
export PYTHONUNBUFFERED=1 PYTHONHASHSEED=0 PYTHONIOENCODING=utf-8
DRIVE=/content/drive/MyDrive/vcc2026
SETUP="$DRIVE/runs/rlab_setup_2026-09-30_r4"
WORK=/content/work/rlab_j07_replogle_ess_rpe1_r3
OUT="$DRIVE/data/processed/corpus_cellulare_2026-09-30/j07_replogle_ess_rpe1_r3"
REC="$SETUP/receipts/j07_replogle_ess_rpe1_r3"
PY=/usr/bin/python3
echo "job j07_replogle_ess_rpe1_r3 start $(date -u +%FT%TZ) host=$(hostname) cpus=$(nproc)"
free -g | head -2; df -h /content | tail -1
test -x "$PY"; test ! -e "$WORK"; test ! -e "$REC"
test ! -e "$OUT"
bootstrap_ready() {
  sha256sum -c --quiet - <<'SUMS' || return 1
1df1ca1f82ff3e4b7a65f829dc742da4218a32adb7180721d95b65328b88e744  /content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-09-30_r4/preflight.py
594c59d7fb849f9e35243afa0e3cbfd37df97565ea7242a89233e1645cb749ac  /content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-09-30_r4/j07_replogle_ess_rpe1_r3_manifest.json
67fb11c4ba100c1f4890ddb60af85083f216d8a3fa58de8a6dc89ef09d723803  /content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-09-30_r4/code_snapshot.tar.gz
bf3970f9635e8874e953eed6a95dacdfc649e6b72413f5fcb2572ce7b526cccb  /content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-09-30_r4/j07_replogle_ess_rpe1_r3_spec.json
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
export RLAB_SNAPSHOT_SHA256=67fb11c4ba100c1f4890ddb60af85083f216d8a3fa58de8a6dc89ef09d723803 RLAB_COMMIT=58a64aab91006c5ad1ddec3c8244d48145f45b9e
"$PY" -c "import anndata" 2>/dev/null || "$PY" -m pip install -q anndata
command -v kaggle >/dev/null || "$PY" -m pip install -q kaggle
"$PY" "$C/validate_runtime.py" --out "$REC/environment_manifest_colab.json" --data-root "$DRIVE/data"
copy "$DRIVE/data/raw/controls/gene_names.csv" "$WORK/in/"
"$PY" "$SETUP/preflight.py" validate --manifest "$SETUP/j07_replogle_ess_rpe1_r3_manifest.json" --site runtime --receipt "$REC/preflight_runtime.json" --attempts 3 --interval-seconds 20
"$PY" "$C/rlab_job.py" --spec "$SETUP/j07_replogle_ess_rpe1_r3_spec.json" --stage "$WORK/stage" --out "$OUT" --runtime-manifest "$REC/environment_manifest_colab.json" --set IN="$WORK/in" AXIS="$WORK/in/gene_names.csv" WORK="$WORK" DRIVE="$DRIVE"
"$PY" "$C/publish_kaggle.py" --job-dir "$OUT" --unit k562_essential --owner davidmaisterx --slug rlab-k562-essential --config-dir "$DRIVE/runs/rlab_secrets_davidmaisterx" --stage "$WORK/publish_rlab-k562-essential" --receipt "$REC/publish_rlab-k562-essential.json"
"$PY" "$C/publish_kaggle.py" --job-dir "$OUT" --unit rpe1 --owner davidmaisterx --slug rlab-rpe1 --config-dir "$DRIVE/runs/rlab_secrets_davidmaisterx" --stage "$WORK/publish_rlab-rpe1" --receipt "$REC/publish_rlab-rpe1.json"
rm -rf "$WORK"
echo "job j07_replogle_ess_rpe1_r3 end $(date -u +%FT%TZ)"
