"""Compare old and new stage-45 outputs on a synthetic streamed pilot."""
from __future__ import annotations
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import h5py
import numpy as np
import scipy.sparse as sp

REPO = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(REPO / "src"))
from vcc2026.genes import GeneAxis
from vcc2026.inference import BasalProfile
from vcc2026.sampling import sample_counts


def load_stage(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    rng = np.random.default_rng(765)
    genes = tuple(f"G{i}" for i in range(128))
    profile = rng.gamma(0.7, 10, len(genes))
    libraries = rng.integers(4000, 10000, 800)
    real = sample_counts(profile, libraries, rng, max_stored_per_cell=128,
                         max_counts_per_cell=1000000, overdispersion=0.6)
    control_path = args.out / "synthetic_controls.h5ad"
    with h5py.File(control_path, "w") as f:
        for key in ["data", "indices", "indptr"]:
            f.create_dataset(f"X/{key}", data=getattr(real, key))
    basal = BasalProfile("A", np.asarray(real.sum(axis=0)).ravel(),
                         np.asarray(real.sum(axis=1)).ravel().astype(int),
                         real.shape[0], real.getnnz(axis=1), str(control_path))
    predictions = {"A": {}}
    for target in ["G1", "G2"]:
        delta = rng.normal(0, 0.2, len(genes))
        mask = np.arange(len(genes)) < 96
        delta[genes.index(target)] = -2.74
        predictions["A"][target] = (delta, mask)
    axis = GeneAxis(genes)
    contract = SimpleNamespace(pert_col="target_gene", context_col="context",
                               max_stored_per_cell=128, max_counts_per_cell=1000000)
    before_path = Path(__file__).with_name("stage45_before_dispersion_scale.py")
    after_path = REPO / "scripts/45_generate_prediction.py"
    before = load_stage("pilot45_before", before_path)
    after = load_stage("pilot45_after", after_path)
    paths = {}
    for phase, module in [("before", before), ("after", after)]:
        fitted = module.fit_dispersions({"A": basal}, len(axis), 91)
        for mode, phi in [("poisson", {}), ("full", fitted)]:
            path = args.out / f"{phase}_{mode}.h5ad"
            module.generate(path, axis, contract, ["A"], ["G1", "G2"], {"A": basal},
                            predictions, phi, None, 400, np.random.default_rng(20260912))
            paths[f"{phase}_{mode}"] = path
    zero_phi = after.fit_dispersions({"A": basal}, len(axis), 91, scale=0)
    zero_path = args.out / "after_zero.h5ad"
    after.generate(zero_path, axis, contract, ["A"], ["G1", "G2"], {"A": basal},
                   predictions, zero_phi, None, 400, np.random.default_rng(20260912))
    comparisons = []
    for name, a, b in [("default Poisson unchanged", paths["before_poisson"], paths["after_poisson"]),
                       ("default fitted dispersion unchanged", paths["before_full"], paths["after_full"]),
                       ("zero dispersion equals Poisson", paths["after_poisson"], zero_path)]:
        arrays = {}
        with h5py.File(a, "r") as fa, h5py.File(b, "r") as fb:
            for key in ["X/data", "X/indices", "X/indptr"]:
                arrays[key] = bool(np.array_equal(fa[key][:], fb[key][:]))
        comparisons.append({"name": name, "arrays_bit_identical": arrays,
                            "files_bit_identical": a.read_bytes() == b.read_bytes()})
        if not all(arrays.values()):
            raise AssertionError(name)
    record = {"synthetic": True, "cells_per_arm": 800, "genes": len(axis),
              "stage_before_sha256": hashlib.sha256(before_path.read_bytes()).hexdigest(),
              "stage_after_sha256": hashlib.sha256(after_path.read_bytes()).hexdigest(),
              "comparisons": comparisons}
    (args.out / "result.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(json.dumps(record, indent=2))


if __name__ == "__main__":
    main()
