"""Read pilot QC receipts and probe whole-context exclusion on tiny synthetic shards.

Read-only against the existing prepass and data. Writes a new JSON receipt only;
synthetic h5ad inputs and prepass states live in a temporary directory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "reports/modelli/ibrido_selettivo_2026-10-04"
sys.path.insert(0, str(SOURCE))
from fixtures import GENES, write_shard  # noqa: E402


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pilot_receipt(folder):
    qc_path = folder / "qc.json"
    q = json.loads(qc_path.read_text(encoding="utf-8"))
    files = [qc_path, folder / "prepass_done.json", folder / "splits.json"]
    done = json.loads(files[1].read_text(encoding="utf-8"))
    split = json.loads(files[2].read_text(encoding="utf-8"))
    return {
        "inputs": [{"path": str(p), "bytes": p.stat().st_size, "sha256": digest(p)} for p in files],
        "done": done,
        "min_controls": q["min_controls_per_key"],
        "keys_with_control_counts": len(q["controls_per_key"]),
        "controls_related_rejections": {k: v for k, v in q["rejected"].items() if "controls_in_key" in k},
        "all_rejections": q["rejected"],
        "perturbed_rejection_rate": q["overall_perturbed_rejection_rate"],
        "phenotype_readmitted": sum(q["phenotype_guard"]["readmitted_by_key"].values()),
        "mask_intersection_losses": {k: v for k, v in q["masks"]["by_key"].items()
                                     if v["genes_in_some_shard_only"]},
        "input_genes": q["input_genes"],
        "training_cells_by_unit": split["loss_weights"]["training_cells_by_unit"],
        "admitted_cells_by_class": split["admitted_cells_by_class"],
    }


def boundary_probe(work, n_controls):
    case = work / f"controls_{n_controls}"
    shards = case / "shards"
    shards.mkdir(parents=True)
    axis = case / "axis.csv"
    axis.write_text("gene_name\n" + "\n".join(GENES) + "\n", encoding="utf-8")
    # Same high-quality profile for every cell: the number of controls is the only
    # changing variable. One independent held-out context satisfies the API.
    for context, nctrl in (("KEPT", n_controls), ("HELD", 40)):
        n = nctrl + 20
        x = np.full((n, len(GENES)), 100, dtype=np.int32)
        x[:, -4:] = 1
        write_shard(shards / f"{context}.h5ad", x, f"study_{context}", context, f"library_{context}",
                    ["NTC"] * nctrl + ["G1"] * 20, [f"{context}_{i}" for i in range(n)],
                    f"synthetic://{context}")
    out = case / "prepass"
    args = [sys.executable, str(SOURCE / "train_cellnet.py"), "prepass", "--shards", str(shards),
            "--axis", str(axis), "--holdout-context", "HELD", "--holdout-target-frac", "0",
            "--out", str(out), "--workers", "1", "--input-genes", "8", "--pool-size", "64"]
    run = subprocess.run(args, capture_output=True, text=True, check=False)
    if run.returncode:
        raise RuntimeError(f"prepass failed ({run.returncode}): {run.stdout}\n{run.stderr}")
    q = json.loads((out / "qc.json").read_text())
    d = json.loads((out / "prepass_done.json").read_text())
    result = {"controls_in_kept_context": n_controls, "perturbed_in_kept_context": 20,
              "admitted_training_cells": d["admitted_training_cells"], "rejected": q["rejected"],
              "exit_code": run.returncode}
    expected = 0 if n_controls < 30 else n_controls + 20
    assert result["admitted_training_cells"] == expected, result
    if n_controls < 30:
        assert q["rejected"]["study_KEPT|KEPT|too_few_controls_in_key"] == n_controls + 20
    else:
        assert not q["rejected"]
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    args = parser.parse_args()
    if args.out.exists():
        raise SystemExit(f"refusing to overwrite {args.out}")
    source_hashes = {name: digest(SOURCE / name) for name in
                     ("train_cellnet.py", "cell_data.py", "cellnet.py", "fixtures.py")}
    receipts = {}
    for fold in ("h1", "hepg2", "rpe1"):
        folder = args.data_root / f"processed/rete_cellulare_2026-10-03/out_prepass_{fold}_r1/prepass"
        receipts[fold] = pilot_receipt(folder)
    with tempfile.TemporaryDirectory(prefix="vcc_prepass_audit_") as tmp:
        probes = [boundary_probe(Path(tmp), n) for n in (29, 30)]
    assert all(digest(SOURCE / n) == h for n, h in source_hashes.items())
    report = {"created_utc": datetime.now(timezone.utc).isoformat(),
              "claim": "pilot receipt recount and synthetic threshold probe; no new training or official score",
              "script_sha256": digest(__file__), "source_hashes": source_hashes,
              "pilot": receipts, "boundary_probe": probes,
              "limits": ["Pilot receipts are dated 3 October, not a coverage receipt for the expanded corpus.",
                         "No full raw-data scan, no state rehash, no proof of clinical or biological QC validity.",
                         "The threshold probe reproduces a policy, not the cause of the t30 result."]}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("x", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")
    print(json.dumps({"out": str(args.out), "boundary_probe": probes,
                      "pilot_rejection_rates": {k: v["perturbed_rejection_rate"] for k, v in receipts.items()}}))


if __name__ == "__main__":
    main()
