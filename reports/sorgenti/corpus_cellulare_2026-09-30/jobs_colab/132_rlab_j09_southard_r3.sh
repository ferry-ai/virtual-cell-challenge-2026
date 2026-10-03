#!/usr/bin/env bash
# R-LAB j09_southard_r3. Built by reports/sorgenti/corpus_cellulare_2026-09-30/colab_job.py; code snapshot of commit 267a29688e2663276ac1b99abe0ed1632c619cd7. Do not edit by hand.
set -euo pipefail
export PYTHONUNBUFFERED=1 PYTHONHASHSEED=0 PYTHONIOENCODING=utf-8
DRIVE=/content/drive/MyDrive/vcc2026
SETUP="$DRIVE/runs/rlab_setup_2026-10-03_r11"
WORK=/content/work/rlab_j09_southard_r3
OUT="$DRIVE/data/processed/corpus_cellulare_2026-09-30/j09_southard_r3"
REC="$SETUP/receipts/j09_southard_r3"
PY=/usr/bin/python3
echo "job j09_southard_r3 start $(date -u +%FT%TZ) host=$(hostname) cpus=$(nproc)"
free -g | head -2; df -h /content | tail -1
test -x "$PY"; test ! -e "$WORK"; test ! -e "$REC"
test ! -e "$OUT"
bootstrap_ready() {
  sha256sum -c --quiet - <<'SUMS' || return 1
1df1ca1f82ff3e4b7a65f829dc742da4218a32adb7180721d95b65328b88e744  /content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-10-03_r11/preflight.py
61261e36ced52a76e5a942403c32e64220976305ba7068097186f8ac02f7d3e8  /content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-10-03_r11/j09_southard_r3_manifest.json
f17e45f2246bd7f455a3a13d088300624a720b0466d6db587812b9f2e8a7af2d  /content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-10-03_r11/code_snapshot.tar.gz
876da7781a001f4450c8684d89d1fa56783656fe781fcd01eeaf1c7be2f54000  /content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-10-03_r11/j09_southard_r3_spec.json
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
export RLAB_SNAPSHOT_SHA256=f17e45f2246bd7f455a3a13d088300624a720b0466d6db587812b9f2e8a7af2d RLAB_COMMIT=267a29688e2663276ac1b99abe0ed1632c619cd7
"$PY" -c "import anndata" 2>/dev/null || "$PY" -m pip install -q anndata
command -v kaggle >/dev/null || "$PY" -m pip install -q kaggle
"$PY" "$C/validate_runtime.py" --out "$REC/environment_manifest_colab.json" --data-root "$DRIVE/data"
copy "$DRIVE/data/raw/controls/gene_names.csv" "$WORK/in/"
"$PY" "$SETUP/preflight.py" validate --manifest "$SETUP/j09_southard_r3_manifest.json" --site runtime --receipt "$REC/preflight_runtime.json" --attempts 3 --interval-seconds 20
"$PY" "$C/rlab_job.py" --spec "$SETUP/j09_southard_r3_spec.json" --stage "$WORK/stage" --out "$OUT" --runtime-manifest "$REC/environment_manifest_colab.json" --set IN="$WORK/in" AXIS="$WORK/in/gene_names.csv" WORK="$WORK" DRIVE="$DRIVE"
"$PY" "$C/publish_kaggle.py" --job-dir "$OUT" --unit southard_rpe1 --owner davidmaisterx --slug rlab-southard-rpe1 --config-dir "$DRIVE/runs/rlab_secrets_davidmaisterx" --stage "$WORK/publish_rlab-southard-rpe1" --receipt "$REC/publish_rlab-southard-rpe1.json"
"$PY" "$C/publish_kaggle.py" --job-dir "$OUT" --unit southard_hs27 --owner davidmaisterx --slug rlab-southard-hs27 --config-dir "$DRIVE/runs/rlab_secrets_davidmaisterx" --stage "$WORK/publish_rlab-southard-hs27" --receipt "$REC/publish_rlab-southard-hs27.json"
rm -rf "$WORK"
echo "job j09_southard_r3 end $(date -u +%FT%TZ)"
