#!/usr/bin/env bash
set -euo pipefail
DRIVE=/content/drive/MyDrive/vcc2026
SETUP="$DRIVE/runs/lead_candidate_environment_setup_2026-09-29_r2"
OUT="$DRIVE/runs/lead_candidate_environment_2026-09-29_r2"
ENVROOT=/content/lead_candidate_environment_r2
test ! -e "$OUT"
test ! -e "$ENVROOT"
mkdir -p "$OUT"
echo "4beb0401dbecc780ae00797096239774b5222c8eb0d6b4bdb1e97fc273c1bc0a  $SETUP/bootstrap_candidate_env_r2.py" | sha256sum -c -
preserve() {
  rc=$?
  trap - EXIT
  if test -d "$ENVROOT"; then
    find "$ENVROOT" -maxdepth 1 -type f -exec cp -n -- {} "$OUT/" \;
  fi
  printf '%s\n' "$rc" > "$OUT/returncode.txt"
  exit "$rc"
}
trap preserve EXIT
python -u "$SETUP/bootstrap_candidate_env_r2.py" --phase create --out "$ENVROOT" \
  --expected-environment "$DRIVE/runs/lead_generator_2026-09-29_r3/development_environment.json" \
  --code-archive "$DRIVE/runs/lead_generator_setup_2026-09-29_r3/code_snapshot.tar.gz" \
  > "$OUT/bootstrap.log" 2>&1
test -f "$ENVROOT/ready.json"
echo "Prepared isolated stage45/48 environment; no generation or submission."
