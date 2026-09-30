#!/usr/bin/env bash
# R-LAB j03_jurkat_r1: Jurkat GSE249595, 16 channels from GEO to contract shards. Built by reports/sorgenti/corpus_cellulare_2026-09-30/build_jobs.py at commit 190094b67262a3508558f21f4503463b82f46694; do not edit by hand.
set -euo pipefail
export PYTHONUNBUFFERED=1 PYTHONHASHSEED=0 PYTHONIOENCODING=utf-8
DRIVE=/content/drive/MyDrive/vcc2026
SETUP="/content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-09-30_r1"
WORK=/content/work/rlab_j03_jurkat_r1
OUT="/content/drive/MyDrive/vcc2026/data/processed/corpus_cellulare_2026-09-30/j03_jurkat_r1"
REC="$SETUP/receipts/j03_jurkat_r1"
PY=/usr/bin/python3
echo "job j03_jurkat_r1 start $(date -u +%FT%TZ) host=$(hostname) cpus=$(nproc)"
free -g | head -2; df -h /content | tail -1; df -h /content/drive 2>/dev/null | tail -1 || true
test -x "$PY"; test ! -e "$OUT"; test ! -e "$WORK"; test ! -e "$REC"
bootstrap_ready() {
  sha256sum -c --quiet - <<'SUMS' || return 1
1df1ca1f82ff3e4b7a65f829dc742da4218a32adb7180721d95b65328b88e744  /content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-09-30_r1/preflight.py
e2dda1eb1d2d6292c8b52723582beb5114cccec721863ca1954ec81c9a18811d  /content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-09-30_r1/j03_jurkat_r1_manifest.json
e80d74c331559792489092109904295fe380097dd5b53202504bed332fdaa39d  /content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-09-30_r1/code_snapshot.tar.gz
eb95f67cdd4f389918c1d3ce171a0aa4c89d8104d220cfd19d3544966fb33d76  /content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-09-30_r1/j03_jurkat_r1_spec.json
bed1183ad4aa3ea9d495c53d6ffde5a413af5a8264407be5b5cc2703b119c9dd  /content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-09-30_r1/j03_jurkat_r1_fetch.json
aeb30c08fa551fa2576c1de75f63166dcf41823323021eed5180cc6e49d2c4ce  /content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-09-30_r1/table_s2_panel.csv
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
"$PY" "$C/fetch.py" --list "$SETUP/j03_jurkat_r1_fetch.json" --receipt "$REC/fetch.json"
cp "$SETUP/table_s2_panel.csv" "$WORK/in/"
copy "$DRIVE/data/raw/controls/gene_names.csv" "$WORK/in/"
"$PY" "$SETUP/preflight.py" validate --manifest "$SETUP/j03_jurkat_r1_manifest.json" --site runtime --receipt "$REC/preflight_runtime.json" --attempts 3 --interval-seconds 20
"$PY" "$C/rlab_job.py" --spec "$SETUP/j03_jurkat_r1_spec.json" --stage "$WORK/stage" --out "$OUT" --runtime-manifest "$REC/environment_manifest_colab.json" --set IN="$WORK/in" AXIS="$WORK/in/gene_names.csv" WORK="$WORK"
rm -rf "$WORK"
echo "job j03_jurkat_r1 end $(date -u +%FT%TZ)"
