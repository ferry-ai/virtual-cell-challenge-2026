#!/usr/bin/env bash
# R-LAB s01_stop_j07_r4: stop the rlab_job.py process of job j07_replogle_ess_rpe1_r4 on this runtime, if it runs. Built by reports/sorgenti/corpus_cellulare_2026-09-30/colab_job.py.
# Reason: its HTTP range reader (snapshot r5) keeps every block read in memory: jobs 100 and 105 were killed after about 5 GB of H1, and K562 essential is 10.7 GB dense; replaced by j07_replogle_ess_rpe1_r5 (snapshot r6, bounded cache), which reuses its verified shards
set -uo pipefail
PAT='rlab_job[.]py --spec [^ ]*/j07_replogle_ess_rpe1_r4_spec[.]json'
echo "job s01_stop_j07_r4 start $(date -u +%FT%TZ) host=$(hostname)"
ps -eo pid,etimes,rss,args | grep -E "$PAT" | grep -v grep || echo "no process of j07_replogle_ess_rpe1_r4 on this runtime"
if pkill -TERM -f "$PAT"; then echo "TERM sent"; sleep 30; pkill -KILL -f "$PAT" && echo "KILL sent"; fi
ps -eo pid,etimes,rss,args | grep -E "$PAT" | grep -v grep || echo "j07_replogle_ess_rpe1_r4: not running"
free -g | head -2
echo "job s01_stop_j07_r4 end $(date -u +%FT%TZ)"
