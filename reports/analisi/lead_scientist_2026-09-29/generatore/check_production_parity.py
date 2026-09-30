"""Small synthetic before/after stage-45 pilot; save SHA256 and full H5AD equality."""
from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.util
import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np

from vcc2026.inference import BasalProfile


def load(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    here = Path(__file__).resolve().parent
    repo = here.parents[3]
    before_path = here / "production_before_depth.py"
    after_path = repo / "scripts/45_generate_prediction.py"
    before = load(before_path, "stage45_before_depth_parity")
    after = load(after_path, "stage45_after_depth_parity")
    rng = np.random.default_rng(20260929)
    genes = [f"G{i:03d}" for i in range(50)]
    axis = type("Axis", (), {"symbols": genes, "__len__": lambda self: len(self.symbols)})()
    ch = SimpleNamespace(pert_col="target_gene", context_col="context", max_stored_per_cell=50,
                         max_counts_per_cell=1000000)
    targets = ["T1", "T2", "T3"]
    basals, predictions = {}, {}
    for context in "AB":
        basal = rng.integers(1, 1000, len(genes)).astype(float)
        basal[-2:] = 0
        libs = rng.integers(500, 10000, 250)
        basals[context] = BasalProfile(context, basal, libs, libs.size, rng.integers(20, 50, libs.size))
        predictions[context] = {}
        for target in targets:
            effect = rng.normal(0, .5, len(genes))
            observed = rng.random(len(genes)) < .7
            effect[0], effect[1] = -10, 0
            observed[0:2] = True
            predictions[context][target] = (effect, observed)
    rows = []
    for name, gene_phi, over in [
        ("poisson", {}, None),
        ("scalar", {}, .25),
        ("gene_phi", {c: np.linspace(0, .5, 50) for c in "AB"}, None),
    ]:
        paths = []
        for label, stage in [("before", before), ("after", after)]:
            path = args.out / f"{name}_{label}.h5ad"
            with contextlib.redirect_stdout(io.StringIO()):
                stage.generate(path, axis, ch, list("AB"), targets, basals, predictions,
                               gene_phi, over, 37, np.random.default_rng(29))
            paths.append(path)
        a, b = paths
        row = {"arm": name, "before_sha256": digest(a), "after_sha256": digest(b),
               "byte_identical": a.read_bytes() == b.read_bytes(), "bytes": a.stat().st_size}
        rows.append(row)
        print(json.dumps(row), flush=True)
    result = {"claim_type": "synthetic stage45 output parity; no real-data scoring",
              "before_source_sha256": digest(before_path), "after_source_sha256": digest(after_path),
              "rows": rows, "all_byte_identical": all(r["byte_identical"] for r in rows)}
    with (args.out / "parity.json").open("x", encoding="utf8") as fh:
        json.dump(result, fh, indent=2)
    if not result["all_byte_identical"]:
        raise SystemExit("Default generation parity failed")


if __name__ == "__main__":
    main()
