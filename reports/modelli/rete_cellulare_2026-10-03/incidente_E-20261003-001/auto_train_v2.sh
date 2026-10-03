#!/bin/bash
# One instance only (lock file with the PID). For each line, in order: when its prepass kernel is COMPLETE and fewer
# than 2 training kernels of the pilot are RUNNING or QUEUED (the account's limit of batch GPU sessions), push its
# training kernel once. Exits when every line is pushed or failed. Appends one line per event to the log.
LOCK=/c/Users/ferra/AppData/Local/Temp/claude/C--Users-ferra-OneDrive-Desktop-vcc2026/b0e0cbfb-4534-40bf-8215-dcb766eb8657/scratchpad/auto_train2.lock
if [ -f $LOCK ] && kill -0 "$(cat $LOCK)" 2>/dev/null; then echo "another instance $(cat $LOCK) is running"; exit 0; fi
echo $$ > $LOCK
export KAGGLE_CONFIG_DIR='C:\Users\ferra\.kaggle-davideferrante11'
KG=/c/Users/ferra/vcc2026-data/.venv/Scripts/kaggle.exe
D=/c/Users/ferra/vcc2026-data/processed/rete_cellulare_2026-10-03
st() { timeout 90 "$KG" kernels status davideferrante11/$1 2>&1 | tail -1 | sed 's/.*KernelWorkerStatus\.//; s/"//g'; }
declare -A done_
while true; do
  left=0
  for g in "$@"; do
    [ -n "${done_[$g]}" ] && continue
    left=1
    s=$(st rcell-prepass-$g-r1)
    case "$s" in
      COMPLETE)
        busy=0
        for t in h1 hepg2 rpe1; do case "$(st rcell-train-$t-r1)" in RUNNING|QUEUED) busy=$((busy+1));; esac; done
        if [ $busy -lt 2 ]; then
          cd $D
          out=$(timeout 300 "$KG" kernels push -p kernel_train_${g}_r1 2>&1 | tail -1)
          echo "$out" > kernel_train_${g}_r1/push_auto2.txt
          echo "$(date +%H:%M:%S) $g: prepass COMPLETE, $busy trainings busy -> $out"
          case "$out" in *successfully*) done_[$g]=pushed;; esac
        fi ;;
      *ERROR*|*CANCEL*) echo "$(date +%H:%M:%S) $g: prepass $s, training not pushed"; done_[$g]=failed ;;
    esac
  done
  [ $left = 0 ] && { echo "$(date +%H:%M:%S) every line handled"; rm -f $LOCK; exit 0; }
  sleep 120
done
