#!/usr/bin/env bash
# R-LAB c01: free the Colab disk from the temporary downloads of the failed job 090 (H1 archive). They are public files
# whose crc32c and sha256 are recorded in runs/rlab_setup_2026-09-30_r2/receipts/h1_vcc2025_r2/fetch.json; the archive
# on Drive will be made again on a runtime with free disk. Only this runtime scratch folder is removed.
set -euo pipefail
echo "c01 start $(date -u +%FT%TZ)"; df -h /content | tail -1
D=/content/work/rlab_h1_vcc2025_r2
if [ -d "$D" ]; then du -sh "$D"; rm -rf "$D"; echo "removed $D"; else echo "absent: $D"; fi
df -h /content | tail -1; echo "c01 end $(date -u +%FT%TZ)"
