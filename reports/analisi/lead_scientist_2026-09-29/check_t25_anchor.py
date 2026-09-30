"""Lightweight read-only parity check on actual r9/t25 files; no model, cells or scorer."""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np
import pandas as pd

import t25_source_adapter as A
from vcc2026.multisource import AxisTable
from vcc2026.resources import peak_rss_bytes


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("cache", "reference", "coords", "out"):
        parser.add_argument("--" + option, type=Path, required=True)
    args = parser.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    original = json.loads((args.reference / "manifest.json").read_text())
    if A.digest(args.coords) != original["cis"]["coords_sha256"]:
        raise ValueError("Coordinates differ from the actual t25 provenance")
    coords = pd.read_csv(args.coords, sep="\t").drop_duplicates("symbol").set_index("symbol")
    report = {"started_utc": datetime.now(timezone.utc).isoformat(), "claim": "neutral adapter parity, not biological performance",
              "adapter_sha256": A.digest(Path(A.__file__)), "inputs": {}, "contexts": {}}
    tables = {}
    for name in (*A.SOURCES, *A.CD4):
        path = args.cache / f"{name}.npz"
        with np.load(path, allow_pickle=False) as z:
            x = z["shrunk"]
            tables[name] = AxisTable(name, z["targets"].astype(str).tolist(), x, x, np.empty((0, 0)), z["n_cells"], json.loads(str(z["meta"])))
        report["inputs"][name] = {"sha256": A.digest(path), "shrunk_bytes": x.nbytes, "targets": len(tables[name].targets)}
    contributions = A.ProductionContributions(tables, gamma=original["gamma"], reliability_scale=original["reliability_scale"])
    for context, spec in original["recipe"]["contexts"].items():
        path = args.reference / f"effects_{context}.npz"
        if A.digest(path) != original["contexts"][context]["sha256"]:
            raise ValueError("Actual reference file differs from the t25 manifest")
        with np.load(path, allow_pickle=False) as z:
            reference = {k: z[k] for k in z.files}
        # Zero modifiers on an empty modeled-gene subset: the neutral operator acts on
        # all reference targets and validates the complete real source decomposition.
        factors = {"targets": reference["targets"], "genes": np.array([], dtype=str), "tokens": np.asarray(A.TOKENS),
                   "ratio": np.ones((6, len(reference["targets"]), 0)), "gate": np.ones((6, len(reference["targets"]), 0))}
        result, diagnostics = A.adapt(reference, factors, contributions, spec, coords)
        identical = {k: reference[k].tobytes() == result[k].tobytes() for k in reference}
        if not all(identical.values()):
            raise AssertionError(f"Neutral adapter changed real t25 arrays in {context}")
        report["contexts"][context] = {"reference_sha256": A.digest(path), "arrays_identical": identical,
                                         "targets": len(diagnostics), "changed_pairs": sum(d["changed_pairs"] for d in diagnostics),
                                         "max_reconstruction_abs": max(d["reconstruction_max_abs"] for d in diagnostics)}
        print(context, report["contexts"][context], flush=True)
        del result, reference
    report["finished_utc"] = datetime.now(timezone.utc).isoformat()
    report["peak_rss_bytes"] = peak_rss_bytes()
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
