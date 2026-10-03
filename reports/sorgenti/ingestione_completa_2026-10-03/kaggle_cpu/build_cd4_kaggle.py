"""CD4 parts as Kaggle CPU kernels: build_kolf_kaggle.py with the CD4 job in the place of the KOLF one.

The kernel is the KOLF kernel (snapshot checked file by file, runtime manifest, the job, complete.json) and runs
cd4/cd4_job.py for one file and one range of its rows. A part of 2 of the largest file is about 10 GB of shards at
the 2.5 bytes per value assumed in DIMENSIONAMENTO.md, under Kaggle's 20 GB.

    python build_cd4_kaggle.py code --config-dir <dir> --owner davideferrante11 --stage <new dir> --axis <gene_names.csv>
    python build_cd4_kaggle.py kernel --config-dir <dir> --owner davideferrante11 --stage <new dir> \
        --code-stage <staged folder of the code dataset> --file D1_Rest --part 0/2 --readahead 8 \
        --slug vcc-cd4-d1-rest-p0of2-r1 [--max-cells N]
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_kolf_kaggle as bk  # noqa: E402

PATHS = bk.SNAPSHOT_PATHS + [f"{bk.REPORT}/cd4/cd4_job.py", f"{bk.REPORT}/cd4/specs/cd4_v1.json"]
OLD = 'K / "kolf_job.py", "--spec", K / "specs/kolf_pan_v1.json"'
NEW = 'K.parent / "cd4/cd4_job.py", "--spec", K.parent / "cd4/specs/cd4_v1.json", "--file", P["file"]'
if bk.KERNEL.count(OLD) != 1:
    sys.exit("the KOLF kernel does not call its job where this builder expects it")
KERNEL = bk.KERNEL.replace(OLD, NEW)

if __name__ == "__main__":
    bk.main(PATHS, KERNEL, "vcc-ingest-code-cd4-r1", "cd4_marson2025", ("file",))
