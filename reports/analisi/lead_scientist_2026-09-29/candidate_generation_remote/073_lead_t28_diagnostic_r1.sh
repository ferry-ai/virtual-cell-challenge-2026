#!/usr/bin/env bash
set -euo pipefail
SCRIPT=/content/drive/MyDrive/vcc2026/runs/lead_candidate_t28_diagnostic_setup_2026-09-29_r1/inspect_candidate_process.py
echo "bb3617fcbf95bd4ddd6709e9eef96931124f7978bf5286b69f660b5ac548bc16  $SCRIPT" | sha256sum -c -
python -u "$SCRIPT"
