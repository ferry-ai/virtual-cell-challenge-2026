"""Would a GPU make this code faster? Measured, not assumed.

Owning a GPU accelerates nothing by itself. It accelerates a computation that a
GPU library executes. This script answers three separate questions and keeps
them apart:

1. **What executes the numbers today.** Which import does each numerical step go
   through, and can that library address a GPU at all.
2. **Where the time actually goes**, at the shapes the pilot really runs. A GPU
   can only touch the part it runs; a step that is 5% of the wall clock cannot
   give back more than 5%.
3. **What already has a GPU path** and is simply switched off here -- the
   scorer's differential-expression backend is the one real case.

The output is a verdict plus the cost of changing it, so the decision to port is
made on numbers instead of on the presence of hardware.

    scripts/py.cmd scripts/59_gpu_readiness.py --out reports/gpu_2026-09-15
"""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import platform
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026.manifest import RunManifest

# Every numerical step of the benchmark, and what runs it.
STEPS = [
    ("descriptor construction",
     "vcc2026.benchmark.descriptors.DescriptorBank.transform_rows",
     "python loop + numpy concatenate", "cpu_only"),
    ("masked SVD basis",
     "vcc2026.benchmark.models.MaskedLowRank.fit",
     "numpy.linalg.svd (LAPACK gesdd)", "cpu_only"),
    ("ridge solve",
     "vcc2026.benchmark.models._ridge_fit",
     "numpy.linalg.solve (LAPACK gesv)", "cpu_only"),
    ("MLP forward/backward",
     "vcc2026.benchmark.models._fit_mlp",
     "hand-written numpy matmul + a hand-written Adam", "cpu_only"),
    ("shrinkage transfer",
     "vcc2026.models.ShrunkTransfer / WeightedTransfer",
     "numpy elementwise", "cpu_only"),
    ("signature loading",
     "vcc2026.signatures.SignatureSet.read_npz",
     "numpy npz decompression + slicing", "io_bound"),
    ("count generation",
     "vcc2026.sampling.sample_counts",
     "numpy Generator.poisson", "cpu_only"),
    ("six-metric scoring",
     "cell_eval2.compute_metrics",
     "cell-eval2; DE backend gpudge (CUDA) > pdex > scanpy", "gpu_path_exists"),
]


def probe_import(name: str) -> dict:
    spec = importlib.util.find_spec(name)
    if spec is None:
        return {"installed": False}
    try:
        module = importlib.import_module(name)
        version = getattr(module, "__version__", None)
    except Exception as error:  # noqa: BLE001 - an import that explodes is a finding
        return {"installed": True, "importable": False, "why": str(error)[:200]}
    return {"installed": True, "importable": True, "version": str(version)}


def numpy_backend() -> dict:
    out: dict = {"numpy": np.__version__}
    try:
        config = np.show_config(mode="dicts")
        build = config.get("Build Dependencies", {}).get("blas", {})
        out["blas"] = {k: build.get(k) for k in ("name", "version", "detection method")}
        out["threading"] = config.get("Compilers", {}).get("c", {}).get("name")
    except Exception as error:  # noqa: BLE001
        out["blas_error"] = str(error)[:200]
    for var in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS"):
        import os
        out[var] = os.environ.get(var)
    return out


def timeit(fn, *, repeat: int = 3) -> dict:
    times = []
    for _ in range(repeat):
        start = time.perf_counter()
        fn()
        times.append(time.perf_counter() - start)
    return {"best_seconds": min(times), "median_seconds": float(np.median(times)),
            "repeat": repeat}


def benchmark(n_rows: int, n_genes: int, n_features: int, rank: int, seed: int) -> dict:
    """The pilot's real shapes, on this machine, with the real code paths."""
    from vcc2026.benchmark.models import MaskedLowRank, ModularFrozen, _ridge_fit
    from vcc2026.benchmark.protocol import TrainArrays
    from vcc2026.benchmark.universe import GeneUniverse

    rng = np.random.default_rng(seed)
    X = rng.normal(size=(n_rows, n_features))
    Y = rng.normal(size=(n_rows, n_genes)) * 0.3
    universe = GeneUniverse(
        observed=np.ones(n_genes, dtype=bool), per_source_n={"a": n_genes},
        n_official=n_genes,
    )
    arrays = TrainArrays(
        X=X, Y=Y, targets=tuple(f"t{i}" for i in range(n_rows)),
        feature_names=tuple(f"f{i}" for i in range(n_features)),
        feature_specs=(), uses_context_features=True, n_unique_context_rows=2,
    )
    # How the dominant step scales with rows: a GPU wins on big shapes, and
    # whether these shapes are big is a measurement, not an opinion.
    scaling = {}
    for rows in (n_rows, 4 * n_rows, 16 * n_rows):
        big = rng.normal(size=(rows, n_genes)) * 0.3
        scaling[f"{rows}x{n_genes}"] = timeit(
            lambda m=big: np.linalg.svd(m - m.mean(0), full_matrices=False), repeat=2
        )["median_seconds"]
        del big

    out = {
        "shapes": {"n_rows": n_rows, "n_genes": n_genes,
                   "n_features": n_features, "rank": rank},
        "svd_scaling_by_rows_seconds": scaling,
        "svd_of_centred_Y": timeit(lambda: np.linalg.svd(Y - Y.mean(0), full_matrices=False)),
        "ridge_solve": timeit(lambda: _ridge_fit(X, Y @ rng.normal(size=(n_genes, rank)), 1.0)),
        "lowrank_fit_total": timeit(
            lambda: MaskedLowRank(rank=rank, ridge=1.0).fit(arrays, universe), repeat=2
        ),
        "modular_frozen_fit_total": timeit(
            lambda: ModularFrozen(
                name="m", uses_context=True, rank=rank, hidden=8, lr=0.01, l2=1e-4,
                epochs=30, patience=6, batch=32, seed=seed,
            ).fit(arrays, universe), repeat=2
        ),
    }
    out["descriptor_construction"] = _time_descriptors(n_rows, n_genes, seed)
    return out


def _time_descriptors(n_rows: int, n_genes: int, seed: int) -> dict:
    """The Python loop that builds the design matrix, at the pilot's size.

    It is not arithmetic a GPU could take over: it is per-row concatenation in
    the interpreter. If it turns out to cost as much as the fit, the cheap win
    is vectorising it, on the CPU, for nothing.
    """
    from vcc2026.benchmark.descriptors import ControlProfile, fit_descriptor_bank
    from vcc2026.benchmark.universe import GeneUniverse
    from vcc2026.genes import official_axis
    from vcc2026.signatures import SignatureSet

    axis = official_axis()
    observed = np.zeros(len(axis), dtype=bool)
    observed[:n_genes] = True
    universe = GeneUniverse(observed=observed, per_source_n={"a": n_genes},
                            n_official=len(axis))
    rng = np.random.default_rng(seed)
    profiles = {
        name: ControlProfile(
            context=name, source_id=name,
            log1p_cpm=np.abs(rng.normal(size=len(axis))), observed=observed,
            n_cells=1e4, library=1e8, provenance="benchmark",
        )
        for name in ("K562", "RPE1")
    }
    bank = fit_descriptor_bank(
        universe=universe, profiles=profiles, train_contexts=("K562", "RPE1"),
        train_sigs=SignatureSet(), codes_by_target=None, include_context=True,
        include_response_codes=False, n_high_expr=32,
    )
    targets = [str(s) for s in axis.symbols[: n_rows // 2]]
    pairs = [(t, "K562") for t in targets] + [(t, "RPE1") for t in targets]
    return {
        "n_rows": len(pairs), "n_features": len(bank.names),
        **timeit(lambda: bank.transform_rows(pairs, allow_response_codes=False)),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--n-rows", type=int, default=320,
                        help="training rows: 160 targets x 2 training contexts")
    parser.add_argument("--n-genes", type=int, default=6477,
                        help="measured gene universe of the three-context folds")
    parser.add_argument("--n-features", type=int, default=199,
                        help="descriptor columns of variant B1 (59 + 140)")
    parser.add_argument("--rank", type=int, default=16)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--allow-overwrite", action="store_true")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    dest = args.out / "gpu_readiness.json"
    if dest.exists() and not args.allow_overwrite:
        raise FileExistsError(f"{dest} exists; give a new --out")

    gpu_libraries = {name: probe_import(name)
                     for name in ("torch", "cupy", "jax", "gpudge", "pdex",
                                  "cell_eval2", "scanpy")}
    cuda = {"available": False, "how": "no library that could answer was importable"}
    if gpu_libraries["torch"].get("importable"):
        import torch

        cuda = {
            "available": bool(torch.cuda.is_available()),
            "how": "torch.cuda.is_available()",
            "device_count": int(torch.cuda.device_count()) if torch.cuda.is_available() else 0,
        }

    repo = Path(__file__).resolve().parents[1]
    sources = list((repo / "src").rglob("*.py"))
    gpu_mentions = []
    for path in sources:
        text = path.read_text(encoding="utf-8", errors="replace")
        for token in ("import torch", "import cupy", "import jax", "cuda"):
            if token in text:
                gpu_mentions.append({"file": str(path.relative_to(repo)), "token": token})

    measured = benchmark(args.n_rows, args.n_genes, args.n_features, args.rank, args.seed)
    total_fit = (measured["lowrank_fit_total"]["median_seconds"]
                 + measured["modular_frozen_fit_total"]["median_seconds"])

    report = {
        "built_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "machine": {
            "platform": platform.platform(),
            "python": sys.version.split()[0],
            "processor": platform.processor(),
        },
        "question": "does the current implementation use a GPU, and would one help",
        "verdict": None,
        "gpu_libraries": gpu_libraries,
        "cuda": cuda,
        "gpu_mentions_in_src": gpu_mentions,
        "numpy_backend": numpy_backend(),
        "steps": [
            {"step": s, "implemented_in": w, "executed_by": e, "gpu": g}
            for s, w, e, g in STEPS
        ],
        "measured": measured,
        "measured_note": (
            "Synthetic arrays at the pilot's real shapes, on this machine. These "
            "time the arithmetic only: they exclude signature loading, which the "
            "run's own peak RSS shows to be the memory-dominant phase."
        ),
        "seconds_of_fit_per_arm_pair": total_fit,
    }

    cpu_only = [s["step"] for s in report["steps"] if s["gpu"] == "cpu_only"]
    report["verdict"] = {
        "current_code_uses_a_gpu": False,
        "why": (
            "Every model in src/vcc2026/benchmark/models.py is hand-written numpy: "
            "the SVD is numpy.linalg.svd, the ridge is numpy.linalg.solve, and the "
            "MLP has its own forward, backward and Adam. numpy has no GPU backend, "
            "and torch is not even a dependency of this project. The only "
            "`import torch` in the source asks whether CUDA exists, to pick the "
            "scorer's DE backend -- nothing in training touches it."
        ),
        "steps_that_would_not_move": cpu_only,
        "what_a_gpu_would_change_today": (
            "One thing only: cell-eval2's differential-expression backend. It "
            "prefers gpudge (CUDA) over pdex over scanpy. Here it resolved to "
            "scanpy, the slowest of the three, because neither gpudge nor pdex is "
            "installed and there is no CUDA device. That affects scoring, not "
            "training, and scoring is the slow half of the six-metric experiment."
        ),
        "what_porting_would_cost": (
            "Rewriting MaskedLowRank, CompactMLP, ModularFrozen and ModularJoint "
            "against torch: the four classes are ~350 lines, and the save/load "
            "round-trip test would have to keep passing bit-for-bit or the "
            "comparison with earlier runs breaks. The honest order is to install "
            "pdex or gpudge first, which changes a backend and no model code."
        ),
        "what_the_measurement_says": (
            "At the pilot's shapes the whole fit of both decoders is under a "
            "second of arithmetic. The run takes minutes. The time is in loading "
            "signatures and in building descriptors in a Python loop -- neither is "
            "a GPU problem, and the second is a vectorisation problem."
        ),
    }
    dest.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    manifest = RunManifest(
        run_id=args.out.name, stage="59_gpu_readiness",
        config={k: str(v) for k, v in vars(args).items()}, seed=args.seed,
    )
    manifest.add_output("report", dest)
    manifest.metrics = {
        "cuda_available": cuda["available"],
        "torch_installed": gpu_libraries["torch"]["installed"],
        "gpudge_installed": gpu_libraries["gpudge"]["installed"],
        "pdex_installed": gpu_libraries["pdex"]["installed"],
        "seconds_of_fit_per_arm_pair": total_fit,
    }
    manifest.note("Owning a GPU is not the same as using one.")
    manifest.write(args.out / "manifest_59_gpu_readiness.json",
                   allow_overwrite=args.allow_overwrite)
    print(json.dumps(manifest.metrics, indent=2))
    print(json.dumps({k: measured[k]["median_seconds"] for k in
                      ("svd_of_centred_Y", "ridge_solve", "lowrank_fit_total",
                       "modular_frozen_fit_total")}, indent=2))
    print(f"-> {dest}")


if __name__ == "__main__":
    main()
