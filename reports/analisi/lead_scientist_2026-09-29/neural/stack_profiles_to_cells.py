"""Stream registered Stack profiles to cells; packaging/submission are separate.

Sampling is the frozen pilot's target-specific IID Poisson path. No parameter
fitting, profile scaling, gene dispersion, or target-specific model selection.
"""
from __future__ import annotations
import argparse
import inspect
import json
from pathlib import Path
import time

import numpy as np
import stack_pilot as pilot
from vcc2026.submission import SubmissionWriter


def read_context(path, *, context, genes, targets):
    complete = json.loads((path / "complete.json").read_text(encoding="utf-8"))
    if (complete.get("status") != "profiles_only_no_cells_no_scores"
            or complete.get("context") != context
            or complete.get("baseline") != "t25_unscaled"
            or complete.get("model_seed") != pilot.SEED
            or complete.get("axis_sha256") != pilot.sha(path / "axis.npz")):
        raise ValueError("Incomplete or changed profile context")
    with np.load(path / "axis.npz", allow_pickle=False) as data:
        axis = {key: data[key].copy() for key in data.files}
    if list(axis["genes"].astype(str)) != list(genes) or list(axis["targets"].astype(str)) != list(targets):
        raise ValueError("Profile context differs from official axes")
    libs = np.asarray(axis["library_sizes"], dtype=np.float64)
    shared = axis["shared"]
    if (libs.ndim != 1 or not len(libs) or not np.isfinite(libs).all() or np.any(libs <= 0)
            or shared.dtype != bool or shared.shape != (len(genes),)):
        raise ValueError("Invalid profile libraries/shared mask")
    rows = complete["profiles"]
    if [row["target"] for row in rows] != list(targets):
        raise ValueError("Incomplete or reordered profiles")
    for row in rows:
        member = (path / row["file"]).resolve()
        if not member.is_relative_to(path.resolve()) or pilot.sha(member) != row["sha256"]:
            raise ValueError("Profile hash/path differs")
        with np.load(member, allow_pickle=False) as data:
            q0, q1 = data["transfer"], data["stack"]
            if (str(data["target"]) != row["target"] or q0.shape != (len(genes),)
                    or q1.shape != q0.shape or q0.dtype != np.float64 or q1.dtype != np.float64
                    or not np.isfinite(q0).all() or not np.isfinite(q1).all()
                    or min(q0.min(), q1.min()) < 0 or q0.sum() <= 0
                    or not np.isclose(q0.sum(), q1.sum(), rtol=1e-12, atol=0)
                    or not np.array_equal(q0[~shared], q1[~shared])
                    or (row["fallback"] and not np.array_equal(q0, q1))):
                raise ValueError("Profile breaks output support/mass contract")
    return libs, rows


def draw(profile, libraries, target):
    rng = pilot.rng_for(f"output:{target}")
    libs = rng.choice(libraries, pilot.N_OUTPUT, replace=True)
    return pilot.sample_counts(profile, libs, rng, max_stored_per_cell=12000,
                               max_counts_per_cell=1000000)


def generate(context_paths, genes, targets, out, *, arm="stack"):
    if out.exists() or arm not in {"stack", "transfer"}:
        raise ValueError("Output already exists or unknown arm")
    prepared = {ctx: read_context(path, context=ctx, genes=genes, targets=targets) for ctx, path in context_paths.items()}
    out.mkdir(parents=True)
    pending, final = out / "prediction.partial.h5ad", out / "prediction.h5ad"
    blocks = []
    started = time.monotonic()
    with SubmissionWriter(pending, genes) as writer:
        for context, path in context_paths.items():
            libraries, rows = prepared[context]
            for row in rows:
                with np.load(path / row["file"], allow_pickle=False) as data:
                    profile = data[arm].copy()
                block = draw(profile, libraries, row["target"])
                writer.add(block, target_gene=row["target"], context=context)
                blocks.append({"context": context, "target": row["target"], "nnz": block.nnz,
                               "max_counts": float(np.asarray(block.sum(axis=1)).max())})
                print(f"Generated {context} {len(blocks)} blocks", flush=True)
        cells, nnz = writer.n_obs, writer.nnz
    pending.rename(final)
    summary = {"status": "cells_generated_not_packaged_not_submitted", "arm": arm,
               "seed": pilot.SEED, "n_cells": cells, "n_genes": len(genes), "nnz": nnz,
               "cells_per_target": pilot.N_OUTPUT, "prediction_sha256": pilot.sha(final),
               "generator_sha256": pilot.sha(__file__), "seconds": time.monotonic() - started,
               "sampling": "frozen pilot target-specific IID Poisson; full official control libraries",
               "blocks": blocks}
    pilot.write_json(out / "generation.json", summary)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--context", action="append", required=True, help="A=/path/to/profiles/A, and B/C")
    parser.add_argument("--registration", type=Path, required=True)
    parser.add_argument("--registration-sha256", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    frozen_helpers = {pilot.__file__: "b259371df3d0d515003597c4d9ce5755c25840f0d36fc96d8ac390ffe1275508",
                      inspect.getfile(pilot.sample_counts): "deb4d5a5720e916614fe59df56c2d08dab9d388b397af4d3cf797076ccde795e",
                      inspect.getfile(SubmissionWriter): "bde21cb1454bf5558f7dc248c623b1d12a52f3b2adeb2aa9cb853d0711d3fc5b"}
    if any(pilot.sha(path) != expected for path, expected in frozen_helpers.items()):
        raise ValueError("Frozen pilot RNG/sampling helper changed")
    if pilot.sha(args.registration) != args.registration_sha256:
        raise ValueError("Registration changed")
    reg = json.loads(args.registration.read_text(encoding="utf-8"))
    paths = {}
    for item in args.context:
        context, path = item.split("=", 1)
        if context in paths:
            raise ValueError("Repeated context")
        paths[context] = Path(path)
    if (list(paths) != ["A", "B", "C"] or reg.get("contexts") != list(paths)
            or reg.get("generator_sha256") != pilot.sha(__file__) or reg.get("seed") != pilot.SEED
            or reg.get("cells_per_target") != 400 or reg.get("arm") != "stack"
            or reg.get("status") != "registered_before_generation"
            or len(reg.get("genes", [])) != 18533 or len(set(reg["genes"])) != 18533
            or len(reg.get("targets", [])) != 300 or len(set(reg["targets"])) != 300
            or not reg.get("prediction_rule") or not reg.get("confirmation_sha256")):
        raise ValueError("Concrete official prediction registration required")
    for context, path in paths.items():
        if (pilot.sha(path / "complete.json") != reg["profile_complete_sha256"][context]
                or pilot.sha(path.parent / "manifest.json") != reg["profile_manifest_sha256"][context]):
            raise ValueError("Registered profile provenance differs")
        manifest = json.loads((path.parent / "manifest.json").read_text())
        if manifest.get("confirmation_sha256") != reg["confirmation_sha256"]:
            raise ValueError("Profiles do not belong to the chosen confirmation")
    generate(paths, reg["genes"], reg["targets"], args.out)
    pilot.write_json(args.out / "registration_receipt.json", {"registration_sha256": args.registration_sha256,
                                                              "registration": reg})


if __name__ == "__main__":
    main()
