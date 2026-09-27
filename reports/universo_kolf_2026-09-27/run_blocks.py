"""Run the gene blocks of kolf_sums.py one after another on this machine, keeping Windows awake.

Each block is resumable and validated by kolf_sums.run_block (a block already written is checked and
skipped), so this can be stopped and restarted, and blocks written elsewhere (Colab, Kaggle) against the
same groups.npz can be dropped into --out before the merge. Blocks are taken in the order given by --order
(default: 0..K-1), so two machines can work from opposite ends.

    scripts/py.cmd reports/universo_kolf_2026-09-27/run_blocks.py --groups <dir>/groups.npz --blocks 32 \
        --out <dir>/blocks
"""
from __future__ import annotations

import argparse
import ctypes
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "src"))
sys.path.insert(0, str(HERE))

import kolf_sums  # noqa: E402

URL = "https://ndownloader.figshare.com/files/64650261"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--groups", type=Path, required=True)
    ap.add_argument("--blocks", type=int, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--url", default=URL)
    ap.add_argument("--order", choices=["up", "down"], default="up")
    args = ap.parse_args()
    order = range(args.blocks) if args.order == "up" else range(args.blocks - 1, -1, -1)
    if sys.platform == "win32":
        ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)
    try:
        for block in order:
            t0 = time.time()
            done = kolf_sums.run_block(args.url, args.groups, block, args.blocks, args.out)
            print(f"block {block}/{args.blocks}: {'written' if done else 'already present'} in {time.time() - t0:.0f} s",
                  flush=True)
    finally:
        if sys.platform == "win32":
            ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)


if __name__ == "__main__":
    main()
