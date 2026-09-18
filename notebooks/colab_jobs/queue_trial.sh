#!/usr/bin/env bash
# Local helper (Git Bash): queue a generate-and-package job for one trial.
# Usage: bash notebooks/colab_jobs/queue_trial.sh <queue-name> <TRIAL> "<GEN_ARGS>" [<file that must exist first, Drive-relative>]
set -euo pipefail
name="$1"; trial="$2"; gen_args="$3"; after="${4:-}"
repo="$(cd "$(dirname "$0")/../.." && pwd)"
queue="${QUEUE_DIR:-G:/Il mio Drive/vcc2026/runs/queue}"
out="$queue/$name.sh"
[ -e "$out" ] && { echo "refusing: $out exists" >&2; exit 2; }
{
  echo "TRIAL=$trial"
  echo "GEN_ARGS=\"$gen_args\""
  if [ -n "$after" ]; then
    echo "AFTER=\"/content/drive/MyDrive/vcc2026/$after\""
  fi
  sed -n '3,$p' "$repo/notebooks/colab_jobs/generate_trial.sh" | sed 's|^wait_for "\$K562SC/report.json"$|wait_for "$K562SC/report.json"\n[ -n "${AFTER:-}" ] \&\& wait_for "$AFTER"|'
} > "$out.tmp"
bash -n "$out.tmp"
mv "$out.tmp" "$out"
echo "queued $out"
