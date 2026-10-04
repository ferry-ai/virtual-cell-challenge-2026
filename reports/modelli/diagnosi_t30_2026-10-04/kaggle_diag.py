"""The diagnostic lane B (diag_lanes.py) on a Kaggle CPU kernel, never on the laptop.

The launcher of the D-056 lanes (reports/modelli/ibrido_selettivo_2026-10-04/kaggle_hybrid.py) imported as it is, with
two changes made here and checked before anything is written:
- the code snapshot also carries diag_lanes.py of this folder;
- the kernel's `lanes` steps are replaced by one step, `diagB`, that runs diag_lanes.py with the same inputs as lane B
  (network outputs, splits, anchors manifest, cube, real cells, targets, weights) and --dose-share 0.65.
Arguments are those of kaggle_hybrid.py with `--mode lanes`. A push spends Kaggle CPU quota: it needs the owner's go.

    python kaggle_diag.py --config-dir <dir> --owner davideferrante11 --stage <new dir> --mode lanes \
        --held-group HepG2 --train-kernel rcell-d056-train-hepg2-r1 --prepass-kernel rcell-prepass-hepg2-r1 \
        --anchors-dir anchors_HepG2_all --real-kernel rcell-gen-hepg2-r3b \
        --weights <esito/selector_lolo_r1/weights_HepG2.json> --slug rcell-t30diag-hepg2-r1 \
        [--launch-log lancio_diag_r1.jsonl] [--dry-run]
"""
from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
HYBRID = HERE.parent / "ibrido_selettivo_2026-10-04"
sys.path.insert(0, str(HYBRID))
import kaggle_hybrid as KH  # noqa: E402

MINE = "reports/modelli/diagnosi_t30_2026-10-04/diag_lanes.py"
DOSE_SHARE = "0.65"
OLD_STEPS = '''    steps = {"laneA": ["hybrid_lanes.py", "laneA", *common, "--weights", weights, "--out", OUT / "laneA"],
             "laneB": ["hybrid_lanes.py", "laneB", *common, "--weights", weights, "--real", REAL / P["real_file"],
                       "--targets", REAL / P["targets_file"], "--out", OUT / "laneB"]}
'''
NEW_STEPS = f'''    steps = {{"diagB": [repo / "{MINE}", *common, "--weights", weights, "--real", REAL / P["real_file"],
                       "--targets", REAL / P["targets_file"], "--dose-share", "{DOSE_SHARE}", "--out", OUT / "diagB"]}}
'''


def snapshot() -> tuple[bytes, list]:
    """kaggle_hybrid.snapshot's file list plus diag_lanes.py, zipped the same way."""
    _, names = ORIGINAL_SNAPSHOT()
    names = [*names, MINE]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for n in names:
            info = zipfile.ZipInfo(n, date_time=(2026, 10, 4, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, (KH.REPO / n).read_bytes())
    return buf.getvalue(), names


if KH.KERNEL.count(OLD_STEPS) != 1:
    sys.exit("kaggle_hybrid.py changed: the lanes steps are not where this launcher expects them")
ORIGINAL_SNAPSHOT = KH.snapshot
KH.KERNEL = KH.KERNEL.replace(OLD_STEPS, NEW_STEPS)
KH.snapshot = snapshot

if __name__ == "__main__":
    if "--mode" in sys.argv and sys.argv[sys.argv.index("--mode") + 1] != "lanes":
        sys.exit("kaggle_diag.py only runs --mode lanes")
    KH.main()
