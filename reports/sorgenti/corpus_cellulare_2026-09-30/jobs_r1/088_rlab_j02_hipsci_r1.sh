#!/usr/bin/env bash
# R-LAB j02_hipsci_r1: HIPSCI three screens from Figshare to contract shards. Built by reports/sorgenti/corpus_cellulare_2026-09-30/build_jobs.py at commit 190094b67262a3508558f21f4503463b82f46694; do not edit by hand.
set -euo pipefail
export PYTHONUNBUFFERED=1 PYTHONHASHSEED=0 PYTHONIOENCODING=utf-8
DRIVE=/content/drive/MyDrive/vcc2026
SETUP="/content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-09-30_r1"
WORK=/content/work/rlab_j02_hipsci_r1
OUT="/content/drive/MyDrive/vcc2026/data/processed/corpus_cellulare_2026-09-30/j02_hipsci_r1"
REC="$SETUP/receipts/j02_hipsci_r1"
PY=/usr/bin/python3
echo "job j02_hipsci_r1 start $(date -u +%FT%TZ) host=$(hostname) cpus=$(nproc)"
free -g | head -2; df -h /content | tail -1; df -h /content/drive 2>/dev/null | tail -1 || true
test -x "$PY"; test ! -e "$OUT"; test ! -e "$WORK"; test ! -e "$REC"
bootstrap_ready() {
  sha256sum -c --quiet - <<'SUMS' || return 1
1df1ca1f82ff3e4b7a65f829dc742da4218a32adb7180721d95b65328b88e744  /content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-09-30_r1/preflight.py
a3ef994a5fdfd190b7b8e51786afcb4580d1b77339243b1eecada93f7fb0aaf1  /content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-09-30_r1/j02_hipsci_r1_manifest.json
e80d74c331559792489092109904295fe380097dd5b53202504bed332fdaa39d  /content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-09-30_r1/code_snapshot.tar.gz
0d420f8d7b0599eef0549ba6b913bbf0146bf72976d96eb4f3729a165b8a6836  /content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-09-30_r1/j02_hipsci_r1_spec.json
fea51a6eafb2dc357d0e7f9e0510420ec6c7262107d69e34e3a376a0c23c9d11  /content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-09-30_r1/j02_hipsci_r1_fetch.json
SUMS
}
for attempt in $(seq 1 45); do
  if bootstrap_ready; then break; fi
  echo "waiting for the setup files by hash, attempt $attempt/45"; sleep 20
done
bootstrap_ready
copy() {  # a read from the Drive mount can fail (E-20260929-007): retry, the preflight hashes the copy
  for i in 1 2 3 4 5; do cp "$1" "$2" && return 0; echo "copy of $1 failed, attempt $i"; sleep 30; done; return 1
}
mkdir -p "$WORK/code" "$WORK/in" "$REC"
tar -xzf "$SETUP/code_snapshot.tar.gz" -C "$WORK/code"
C="$WORK/code/reports/sorgenti/corpus_cellulare_2026-09-30"
export RLAB_SNAPSHOT_SHA256=e80d74c331559792489092109904295fe380097dd5b53202504bed332fdaa39d RLAB_COMMIT=190094b67262a3508558f21f4503463b82f46694
"$PY" "$C/validate_runtime.py" --out "$REC/environment_manifest_colab.json" --data-root "$DRIVE/data"
"$PY" "$C/fetch.py" --list "$SETUP/j02_hipsci_r1_fetch.json" --receipt "$REC/fetch.json"
copy "$DRIVE/data/raw/controls/gene_names.csv" "$WORK/in/"
"$PY" "$SETUP/preflight.py" validate --manifest "$SETUP/j02_hipsci_r1_manifest.json" --site runtime --receipt "$REC/preflight_runtime.json" --attempts 3 --interval-seconds 20
"$PY" "$C/rlab_job.py" --spec "$SETUP/j02_hipsci_r1_spec.json" --stage "$WORK/stage" --out "$OUT" --runtime-manifest "$REC/environment_manifest_colab.json" --set IN="$WORK/in" AXIS="$WORK/in/gene_names.csv" WORK="$WORK"
rm -rf "$WORK"
echo "job j02_hipsci_r1 end $(date -u +%FT%TZ)"
