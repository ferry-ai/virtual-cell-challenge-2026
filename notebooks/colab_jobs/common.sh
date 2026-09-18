# Sourced by every Colab job, from the job's PRIVATE copy of the code ($CODE_DIR).
# The dispatcher re-copies /content/vcc whenever it starts a job; on 2026-09-17 that
# deleted the working directory of the jobs already running (FileNotFoundError from
# os.getcwd), so a job never runs from /content/vcc.
set -euo pipefail
export DRIVE=/content/drive/MyDrive/vcc2026
export VCC2026_DATA_ROOT=$DRIVE/data
export PYTHONPATH=$CODE_DIR/src
export PYTHONIOENCODING=utf-8
export PYTHONUNBUFFERED=1
cd "$CODE_DIR"
echo "job start $(date -u +%FT%TZ) host=$(hostname) cpus=$(nproc) code=$CODE_DIR $(cat SYNC_STAMP.txt 2>/dev/null)"
free -g | head -2
df -h /content | tail -1

# Block until a file exists (a job that needs another job's output queues behind it).
wait_for() {
  local f="$1"
  while [ ! -f "$f" ]; do
    echo "$(date -u +%T) waiting for $f"
    sleep 120
  done
}
export K562SC=$DRIVE/data/processed/k562_gwps_sc/x002
export COORDS=$DRIVE/data/external/annotation/gene_coordinates_gencode_v50.tsv
