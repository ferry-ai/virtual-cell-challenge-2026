#!/usr/bin/env bash
# R-LAB h1_vcc2025_r1: VCC 2025 H1 release to its frozen home on Drive, after J02. Built by reports/sorgenti/corpus_cellulare_2026-09-30/build_jobs.py at commit 5f8d03bc18ce2aaba6d10c8d6925e32423bda78e.
# The test split is the reserve: this job downloads, verifies and copies it, and never opens it.
set -euo pipefail
export PYTHONUNBUFFERED=1 PYTHONIOENCODING=utf-8
DRIVE=/content/drive/MyDrive/vcc2026
SETUP="/content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-09-30_r2"
WORK=/content/work/rlab_h1_vcc2025_r1
OUT="/content/drive/MyDrive/vcc2026/data/raw/vcc2025_h1_2026-09-30"
REC="$SETUP/receipts/h1_vcc2025_r1"
PY=/usr/bin/python3
echo "job h1_vcc2025_r1 start $(date -u +%FT%TZ) host=$(hostname) cpus=$(nproc)"
test -x "$PY"; test ! -e "$OUT"; test ! -e "$WORK"; test ! -e "$REC"
while [ ! -f "/content/drive/MyDrive/vcc2026/runs/queue/088_rlab_j02_hipsci_r1.sh.done" ]; do echo "$(date -u +%T) waiting for J02 to end: /content/drive/MyDrive/vcc2026/runs/queue/088_rlab_j02_hipsci_r1.sh.done"; sleep 120; done
free -g | head -2; df -h /content | tail -1; df -h /content/drive 2>/dev/null | tail -1 || true
bootstrap_ready() {
  sha256sum -c --quiet - <<'SUMS' || return 1
1df1ca1f82ff3e4b7a65f829dc742da4218a32adb7180721d95b65328b88e744  /content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-09-30_r2/preflight.py
7015e7c1a6c1443865b2b1040d0888eb9f80f8c7f3f6d6452ca670d8c78a0105  /content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-09-30_r2/h1_vcc2025_r1_manifest.json
0e637776e2ea610f181f4a90ddf9cc4a02aa22c9164c0319f6d407fbcfd9f757  /content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-09-30_r2/code_snapshot.tar.gz
8e4ea89a2503957fb469888e9f44d44236f3e2db6d06787cf7e56d64901b0c69  /content/drive/MyDrive/vcc2026/runs/rlab_setup_2026-09-30_r2/h1_vcc2025_r1_fetch.json
SUMS
}
for attempt in $(seq 1 45); do
  if bootstrap_ready; then break; fi
  echo "waiting for the setup files by hash, attempt $attempt/45"; sleep 20
done
bootstrap_ready
mkdir -p "$WORK/code" "$REC"
tar -xzf "$SETUP/code_snapshot.tar.gz" -C "$WORK/code"
C="$WORK/code/reports/sorgenti/corpus_cellulare_2026-09-30"
"$PY" "$C/validate_runtime.py" --out "$REC/environment_manifest_colab.json" --data-root "$DRIVE/data"
"$PY" "$SETUP/preflight.py" validate --manifest "$SETUP/h1_vcc2025_r1_manifest.json" --site runtime --receipt "$REC/preflight_runtime.json" --attempts 3 --interval-seconds 20
"$PY" -c "import shutil, sys; f = shutil.disk_usage('$DRIVE').free; print('drive free', f, 'needed', 36509809537); sys.exit(0 if f >= 36509809537 else 1)"
"$PY" "$C/fetch.py" --list "$SETUP/h1_vcc2025_r1_fetch.json" --receipt "$REC/fetch.json"
"$PY" "$C/publish.py" --receipt "$REC/fetch.json" --from "$WORK/dl" --out "$OUT" --min-free-bytes 2147483648 --roles '{"test/": "RISERVA: non aprire; si legge una volta sola, a modello e regola congelati (scelta del proprietario, 30/09)", "train/": "training", "validation/": "training", "gene_names.csv": "asse dei geni del rilascio"}' --note "VCC 2025 H1 (H1 hESC, CRISPRi, 10x Flex), Arc bucket objects of 16/12/2025; roles chosen by the owner on 30/09"
rm -rf "$WORK"
echo "job h1_vcc2025_r1 end $(date -u +%FT%TZ)"
