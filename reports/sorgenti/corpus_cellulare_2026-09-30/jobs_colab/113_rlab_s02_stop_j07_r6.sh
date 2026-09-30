#!/usr/bin/env bash
# R-LAB s02_stop_j07_r6: stop the rlab_job.py process of job j07_replogle_ess_rpe1_r6 on this runtime, if it runs. Built by reports/sorgenti/corpus_cellulare_2026-09-30/colab_job.py.
# Reason: the h5rows adapter of snapshot r7 read the old anndata categoricals of the Replogle files as their codes: targets are numbers and no control is found; replaced by j07_replogle_ess_rpe1_r7 (snapshot r8, decoded categories), which reuses nothing
set -uo pipefail
PAT='rlab_job[.]py --spec [^ ]*/j07_replogle_ess_rpe1_r6_spec[.]json'
echo "job s02_stop_j07_r6 start $(date -u +%FT%TZ) host=$(hostname)"
ps -eo pid,etimes,rss,args | grep -E "$PAT" | grep -v grep || echo "no process of j07_replogle_ess_rpe1_r6 on this runtime"
if pkill -TERM -f "$PAT"; then echo "TERM sent"; sleep 30; pkill -KILL -f "$PAT" && echo "KILL sent"; fi
ps -eo pid,etimes,rss,args | grep -E "$PAT" | grep -v grep || echo "j07_replogle_ess_rpe1_r6: not running"
free -g | head -2
echo "job s02_stop_j07_r6 end $(date -u +%FT%TZ)"
