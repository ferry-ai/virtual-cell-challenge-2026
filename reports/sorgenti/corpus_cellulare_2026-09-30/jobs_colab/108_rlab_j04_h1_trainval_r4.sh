#!/usr/bin/env bash
# R-LAB j04_h1_trainval_r4. Built by reports/sorgenti/corpus_cellulare_2026-09-30/colab_job.py; code snapshot of commit 33f2cf5595c926b33d1d6a279677a54634996784. Do not edit by hand.
set -euo pipefail
export PYTHONUNBUFFERED=1 PYTHONHASHSEED=0 PYTHONIOENCODING=utf-8
DRIVE=/content/drive/MyDrive/vcc2026
SETUP="$DRIVE/runs/rlab_setup_2026-09-30_r6"
WORK=/content/work/rlab_j04_h1_trainval_r4
OUT="$DRIVE/data/processed/corpus_cellulare_2026-09-30/j04_h1_trainval_r4"
REC="$SETUP/receipts/j04_h1_trainval_r4"
PY=/usr/bin/python3
echo "job j04_h1_trainval_r4 start $(date -u +%FT%TZ) host=$(hostname) cpus=$(nproc)"
free -g | head -2; df -h /content | tail -1
test -x "$PY"; test ! -e "$WORK"; test ! -e "$REC"
test ! -e "$OUT"
bootstrap_ready() {
  sha256sum -c --quiet - <<'SUMS' || return 1
1df1ca1f82ff3e4b7a65f829dc742da4218a32adb7180721d95b65328b88e744  /content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-09-30_r6/preflight.py
6ad0a755713d56d09a09ed390e9417d5e38117dde065dd39236baf34d2783575  /content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-09-30_r6/j04_h1_trainval_r4_manifest.json
2d76f233acdccb0b44d355f41597569e1e479b289512e028d4ef98c60d31ae54  /content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-09-30_r6/code_snapshot.tar.gz
80b47409790592411b3acf01cedcb94896c117c2ff76c47d01bc115bd7aa33b9  /content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-09-30_r6/j04_h1_trainval_r4_spec.json
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
export RLAB_SNAPSHOT_SHA256=2d76f233acdccb0b44d355f41597569e1e479b289512e028d4ef98c60d31ae54 RLAB_COMMIT=33f2cf5595c926b33d1d6a279677a54634996784
"$PY" -c "import anndata" 2>/dev/null || "$PY" -m pip install -q anndata
command -v kaggle >/dev/null || "$PY" -m pip install -q kaggle
"$PY" "$C/validate_runtime.py" --out "$REC/environment_manifest_colab.json" --data-root "$DRIVE/data"
copy "$DRIVE/data/raw/controls/gene_names.csv" "$WORK/in/"
"$PY" "$SETUP/preflight.py" validate --manifest "$SETUP/j04_h1_trainval_r4_manifest.json" --site runtime --receipt "$REC/preflight_runtime.json" --attempts 3 --interval-seconds 20
"$PY" "$C/rlab_job.py" --spec "$SETUP/j04_h1_trainval_r4_spec.json" --stage "$WORK/stage" --out "$OUT" --runtime-manifest "$REC/environment_manifest_colab.json" --reuse "$DRIVE/data/processed/corpus_cellulare_2026-09-30/j04_h1_trainval_r3" --set IN="$WORK/in" AXIS="$WORK/in/gene_names.csv" WORK="$WORK" DRIVE="$DRIVE"
"$PY" "$C/publish_kaggle.py" --job-dir "$OUT" --unit ALL --owner davidmaisterx --slug rlab-h1-vcc2025-trainval --config-dir "$DRIVE/runs/rlab_secrets_davidmaisterx" --stage "$WORK/publish_rlab-h1-vcc2025-trainval" --receipt "$REC/publish_rlab-h1-vcc2025-trainval.json"
rm -rf "$WORK"
echo "job j04_h1_trainval_r4 end $(date -u +%FT%TZ)"
