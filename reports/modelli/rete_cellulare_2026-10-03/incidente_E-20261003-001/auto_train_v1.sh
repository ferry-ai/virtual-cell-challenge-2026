#!/bin/bash
# For each line: when its prepass kernel is COMPLETE, push its training kernel once; report ERROR/CANCEL; exit when
# every line is handled. One stdout line per event.
export KAGGLE_CONFIG_DIR='C:\Users\ferra\.kaggle-davideferrante11'
KG=/c/Users/ferra/vcc2026-data/.venv/Scripts/kaggle.exe
D=/c/Users/ferra/vcc2026-data/processed/rete_cellulare_2026-10-03
declare -A handled
lines="$*"
while true; do
  left=0
  for g in $lines; do
    [ -n "${handled[$g]}" ] && continue
    s=$(timeout 90 "$KG" kernels status davideferrante11/rcell-prepass-$g-r1 2>&1 | tail -1 | sed 's/.*KernelWorkerStatus\.//; s/"//g')
    case "$s" in
      COMPLETE)
        cd $D
        out=$(timeout 300 "$KG" kernels push -p kernel_train_${g}_r1 2>&1 | tail -1)
        echo "$(date +%H:%M:%S) prepass $g COMPLETE -> push train: $out"
        echo "$out" > kernel_train_${g}_r1/push.txt
        handled[$g]=1 ;;
      *ERROR*|*CANCEL*)
        echo "$(date +%H:%M:%S) prepass $g $s: training NOT pushed"
        handled[$g]=1 ;;
      *) left=1 ;;
    esac
  done
  [ $left = 0 ] && { echo "$(date +%H:%M:%S) all lines handled"; exit 0; }
  sleep 90
done
