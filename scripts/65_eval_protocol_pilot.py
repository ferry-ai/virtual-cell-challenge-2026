"""Freeze-check the evaluation protocol on existing splits and HepG2 cells.

Does three jobs and keeps them apart:

1. Load the frozen YAML and refuse it if it is not frozen.
2. Audit every three-context split JSON already on disk (leakage algebra).
3. If the HepG2 mirror is present, build local replicate/baseline anchors
   in log2FC space on a small disjoint cell split. That is not a VCC score.

    scripts/py.cmd scripts/65_eval_protocol_pilot.py --out reports/eval_protocol_2026-09-15
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026 import config
from vcc2026.eval_protocol import (
    AnchorSplit,
    audit_split_directory,
    load_protocol,
    local_anchor_deltas,
    split_cells_for_anchors,
)
from vcc2026.manifest import RunManifest
from vcc2026.pseudobulk import _read_categorical

REPO = Path(__file__).resolve().parents[1]
SPLITS = REPO / "reports/benchmark_3ctx_2026-09-14/splits"
PROTOCOL = REPO / "configs/eval_protocol.yaml"


def anchors_on_hepg2(h5ad: Path, *, n_targets: int, min_cells: int, seed: int) -> dict:
    import h5py

    # Contiguous window: random row gathers on gzip-chunked dense X are too
    # slow and too RAM-heavy on this machine. The first `window` rows are a
    # convenience sample, not a random sample of the study.
    window = 2000
    with h5py.File(h5ad, "r") as handle:
        labels = np.asarray(_read_categorical(handle["obs"], "perturbation"), dtype=str)
        labels_w = labels[:window]
        splits = split_cells_for_anchors(
            labels_w, ntc_label="control", min_cells=min_cells, seed=seed,
        )
        splits = splits[:n_targets]
        rng = np.random.default_rng(seed)
        capped = []
        ntc_cap = max(2 * min_cells, 40)
        for split in splits:
            ntc_a = split.ntc_a
            ntc_b = split.ntc_b
            if ntc_a.size > ntc_cap:
                ntc_a = np.sort(rng.choice(ntc_a, ntc_cap, replace=False))
            if ntc_b.size > ntc_cap:
                ntc_b = np.sort(rng.choice(ntc_b, ntc_cap, replace=False))
            capped.append(AnchorSplit(split.target, split.group_a, split.group_b, ntc_a, ntc_b))
        splits = capped
        n_genes = int(handle["X"].shape[1])
        needed = set()
        for split in splits:
            needed.update(int(i) for i in split.group_a)
            needed.update(int(i) for i in split.group_b)
            needed.update(int(i) for i in split.ntc_a)
            needed.update(int(i) for i in split.ntc_b)
        index = sorted(needed)
        pos = {row: j for j, row in enumerate(index)}
        # One contiguous read of the window, then slice. Still a protocol
        # smoke: not a random sample of HepG2.
        window_x = np.asarray(handle["X"][:window, :], dtype=np.float32)
        block = window_x[np.array(index, dtype=np.int64)]

    remapped = []
    for split in splits:
        remapped.append(AnchorSplit(
            split.target,
            np.array([pos[int(i)] for i in split.group_a]),
            np.array([pos[int(i)] for i in split.group_b]),
            np.array([pos[int(i)] for i in split.ntc_a]),
            np.array([pos[int(i)] for i in split.ntc_b]),
        ))
    result = local_anchor_deltas(block, remapped, n_boot=100, seed=seed)
    result["h5ad"] = str(h5ad)
    result["n_cells_read"] = len(index)
    result["min_cells_per_half"] = min_cells
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, default=PROTOCOL)
    parser.add_argument("--splits", type=Path, default=SPLITS)
    parser.add_argument("--h5ad", type=Path, default=None)
    parser.add_argument("--n-targets", type=int, default=8)
    parser.add_argument("--min-cells", type=int, default=15)
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    dest = args.out / "eval_protocol_pilot.json"
    if dest.exists():
        raise FileExistsError(f"{dest} exists; give a new --out")

    proto = load_protocol(args.protocol)
    audit = audit_split_directory(args.splits, protocol=proto)

    h5ad = args.h5ad or (
        config.paths().data_root / "raw/nadig_hepg2/NadigOConner2024_hepg2.h5ad"
    )
    anchors = None
    anchors_error = None
    if h5ad.exists():
        try:
            anchors = anchors_on_hepg2(
                h5ad, n_targets=args.n_targets, min_cells=args.min_cells, seed=args.seed,
            )
        except Exception as exc:  # noqa: BLE001
            anchors_error = f"{type(exc).__name__}: {exc}"
    else:
        anchors_error = f"{h5ad} not on disk"

    report = {
        "protocol": proto.as_dict(),
        "split_audit": audit,
        "anchors": anchors,
        "anchors_error": anchors_error,
        "development_note": (
            "These HepG2 cells and the 2026/2027 splits are development. "
            "Confirmation seed 4242 has not been opened."
        ),
        "not_a_vcc_score": True,
        "claim": "measured",
    }
    dest.write_text(json.dumps(report, indent=2, default=str) + "\n", encoding="utf-8")
    (args.out / "split_audit.json").write_text(
        json.dumps(audit, indent=2) + "\n", encoding="utf-8"
    )
    manifest = RunManifest(
        run_id=args.out.name, stage="65_eval_protocol_pilot",
        config={k: str(v) for k, v in vars(args).items()}, seed=args.seed,
    )
    manifest.add_output("pilot", dest)
    manifest.note("Proxy log2FC anchors are not VCC scores.")
    manifest.write(args.out / "manifest_65_eval_protocol_pilot.json")
    print(f"wrote {dest}")
    print(f"splits {audit['n']} fail {audit['n_fail']} "
          f"development {audit['n_development']} confirmation {audit['n_confirmation']}")
    if anchors:
        print(f"anchors n_targets {anchors['n_targets']} "
              f"replicate mse/null {anchors['replicate']['pooled_mse_vs_null']}")
    else:
        print(f"anchors skipped: {anchors_error}")


if __name__ == "__main__":
    main()
