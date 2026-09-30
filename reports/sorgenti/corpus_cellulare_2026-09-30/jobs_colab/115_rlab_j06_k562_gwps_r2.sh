#!/usr/bin/env bash
# R-LAB j06_k562_gwps_r2. Built by reports/sorgenti/corpus_cellulare_2026-09-30/colab_job.py; code snapshot of commit 404cc385b82c05390010a5708332b040ec17669e. Do not edit by hand.
set -euo pipefail
export PYTHONUNBUFFERED=1 PYTHONHASHSEED=0 PYTHONIOENCODING=utf-8
DRIVE=/content/drive/MyDrive/vcc2026
SETUP="$DRIVE/runs/rlab_setup_2026-09-30_r8"
WORK=/content/work/rlab_j06_k562_gwps_r2
OUT="$DRIVE/data/processed/corpus_cellulare_2026-09-30/j06_k562_gwps_r2"
REC="$SETUP/receipts/j06_k562_gwps_r2"
PY=/usr/bin/python3
echo "job j06_k562_gwps_r2 start $(date -u +%FT%TZ) host=$(hostname) cpus=$(nproc)"
free -g | head -2; df -h /content | tail -1
test -x "$PY"; test ! -e "$WORK"; test ! -e "$REC"
test ! -e "$OUT"
bootstrap_ready() {
  sha256sum -c --quiet - <<'SUMS' || return 1
1df1ca1f82ff3e4b7a65f829dc742da4218a32adb7180721d95b65328b88e744  /content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-09-30_r8/preflight.py
fed8abd6700d5a8c73f9da87a8af92fa5bf7082082da67892d107b5a59973ce2  /content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-09-30_r8/j06_k562_gwps_r2_manifest.json
b754e3381bff1417accfeaf932f435b78f9cb9c2ad830ef56fb4380390d21f55  /content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-09-30_r8/code_snapshot.tar.gz
7db6bbe3484e00066c8a79eeddc570531f654562863ccb81542386f3a52e77d6  /content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-09-30_r8/j06_k562_gwps_r2_spec.json
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
export RLAB_SNAPSHOT_SHA256=b754e3381bff1417accfeaf932f435b78f9cb9c2ad830ef56fb4380390d21f55 RLAB_COMMIT=404cc385b82c05390010a5708332b040ec17669e
"$PY" -c "import anndata" 2>/dev/null || "$PY" -m pip install -q anndata
command -v kaggle >/dev/null || "$PY" -m pip install -q kaggle
"$PY" "$C/validate_runtime.py" --out "$REC/environment_manifest_colab.json" --data-root "$DRIVE/data"
copy "$DRIVE/data/raw/controls/gene_names.csv" "$WORK/in/"
"$PY" "$SETUP/preflight.py" validate --manifest "$SETUP/j06_k562_gwps_r2_manifest.json" --site runtime --receipt "$REC/preflight_runtime.json" --attempts 3 --interval-seconds 20
"$PY" "$C/rlab_job.py" --spec "$SETUP/j06_k562_gwps_r2_spec.json" --stage "$WORK/stage" --out "$OUT" --runtime-manifest "$REC/environment_manifest_colab.json" --set IN="$WORK/in" AXIS="$WORK/in/gene_names.csv" WORK="$WORK" DRIVE="$DRIVE"
"$PY" "$C/publish_kaggle.py" --job-dir "$OUT" --unit ALL --owner davidmaisterx --slug rlab-k562-gwps-r2 --config-dir "$DRIVE/runs/rlab_secrets_davidmaisterx" --stage "$WORK/publish_rlab-k562-gwps-r2" --receipt "$REC/publish_rlab-k562-gwps-r2.json"
rm -rf "$WORK"
echo "job j06_k562_gwps_r2 end $(date -u +%FT%TZ)"
