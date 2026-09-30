"""Freeze separate Colab scorer with no model code beyond pure adapter helpers."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--out", required=True, type=Path)
    a = p.parse_args()
    if a.out.exists():
        raise FileExistsError(a.out)
    setup = json.loads((HERE / "stack_setup_r1/setup_manifest.json").read_text())
    previous = (HERE / "stack_setup_r1/code_snapshot.tar.gz").read_bytes()
    if sha(previous) != setup["code_archive_sha256"]:
        raise ValueError("Frozen preparation archive changed")
    files = {}
    with tarfile.open(fileobj=io.BytesIO(previous), mode="r:gz") as t:
        for entry in t.getmembers():
            if entry.isfile():
                files[entry.name] = t.extractfile(entry).read()
    added = [HERE / "score_stack_pilot.py", HERE / "test_stack_remote.py", HERE / "stack_remote_runner.py",
             REPO / "src/vcc2026/bench.py", REPO / "src/vcc2026/de_tools.py",
             REPO / "reports/gara/anchors_2026-09-17/anchors.json"]
    files.update({f.relative_to(REPO).as_posix(): f.read_bytes() for f in added})
    output, entries = io.BytesIO(), []
    with tarfile.open(fileobj=output, mode="w") as t:
        for name, content in sorted(files.items()):
            info = tarfile.TarInfo(name)
            info.size, info.mode, info.mtime = len(content), 0o644, 0
            t.addfile(info, io.BytesIO(content))
            entries.append({"path": name, "bytes": len(content), "sha256": sha(content)})
    payload = gzip.compress(output.getvalue(), mtime=0)
    script = r'''#!/usr/bin/env bash
set -euo pipefail
export DRIVE=/content/drive/MyDrive/vcc2026
export CODE_DIR=/content/lead_stack_score_code_r1
export PYTHONPATH="$CODE_DIR/src"
export PYTHONUNBUFFERED=1
export OMP_NUM_THREADS=2 OPENBLAS_NUM_THREADS=2 MKL_NUM_THREADS=2
SETUP="$DRIVE/runs/lead_stack_scoring_setup_2026-09-29_r1"
BUNDLE="$DRIVE/runs/lead_stack_2026-09-29_r2/bundle"
PREDICTION="${STACK_PREDICTION_DIR:-$DRIVE/runs/lead_stack_infer_2026-09-29_r1/prediction}"
OUT="$DRIVE/runs/lead_stack_score_2026-09-29_r1"
test -f "$PREDICTION/finished.json"
test ! -e "$OUT"
test ! -e "$CODE_DIR"
echo "__HASH__  $SETUP/scoring_snapshot.tar.gz" | sha256sum -c -
mkdir -p "$CODE_DIR"
tar -xzf "$SETUP/scoring_snapshot.tar.gz" -C "$CODE_DIR"
cd "$CODE_DIR"
REPORT=reports/analisi/lead_scientist_2026-09-29/neural
python -u "$REPORT/test_stack_remote.py"
python -u "$REPORT/score_stack_pilot.py" \
  --bundle "$BUNDLE" --prediction "$PREDICTION" \
  --truth "$DRIVE/data/raw/nadig_hepg2/NadigOConner2024_hepg2.h5ad" \
  --anchors reports/gara/anchors_2026-09-17/anchors.json --out "$OUT"
python -m pip freeze > "$OUT/scoring_pip_freeze.txt"
'''.replace("__HASH__", sha(payload))
    a.out.mkdir(parents=True)
    (a.out / "scoring_snapshot.tar.gz").write_bytes(payload)
    with (a.out / "colab_stack_score_r1.sh").open("x", encoding="utf-8", newline="\n") as f:
        f.write(script)
    record = {"status": "frozen_before_pilot_scores", "snapshot_sha256": sha(payload),
              "snapshot_bytes": len(payload), "script_sha256": sha(script.encode()), "code_files": entries,
              "scope": "separate scoring process; inference never sees truth", "drive_setup": "runs/lead_stack_scoring_setup_2026-09-29_r1"}
    with (a.out / "scoring_manifest.json").open("x", encoding="utf-8") as f:
        json.dump(record, f, indent=2)
    print(json.dumps({k: v for k, v in record.items() if k != "code_files"}, indent=2))


if __name__ == "__main__":
    main()
