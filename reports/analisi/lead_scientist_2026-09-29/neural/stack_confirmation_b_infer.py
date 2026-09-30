"""Confirmation profile export: same Stack inference, no final cells or scoring.

Prepared for selected B only; no final B protocol exists by this build.
Derived from frozen A confirmation. Each input retains its own measured
model vocabulary. Output shared support, calls, cache,
baseline and paired-control correction are unchanged. This adapter records the
two float64 profiles instead of sampling final cells; CPU scoring samples them.
"""
from __future__ import annotations
import argparse
import importlib.metadata
import json
from pathlib import Path
import pickle

import numpy as np
import pandas as pd
import scipy.sparse as sp
import stack_pilot as pilot
from stack_confirmation_pack import EXPECTED
from stack_ab_selection_guard import validate_embedded
from stack_pilot import (CONTROL, SEED, CHECKPOINT_SHA, GENELIST_SHA, sha, write_json,
    GeneListUnpickler, align_shared, pick, call_model, memory_shapes,
    predicted_profile, corrected_profile)

FROZEN_PILOT_SHA = "b259371df3d0d515003597c4d9ce5755c25840f0d36fc96d8ac390ffe1275508"
ORIGINAL_PROTOCOL_SHA = "2c2614532d49e35a60735858f150e6bd46f1cb9414ccc8b3914aaf12061245f2"
B_PROTOCOL_PATH = Path(__file__).with_name("PROTOCOLLO_STACK_CONFERMA_B.md")
INPUT_AXIS_POLICY = "own_measured_support"


def infer(args):
    import anndata as ad
    if sha(pilot.__file__) != FROZEN_PILOT_SHA:
        raise ValueError("Scientific helper differs from the frozen pilot")
    if args.out.exists():
        raise FileExistsError(args.out)
    bundle = json.loads((args.bundle / "bundle.json").read_text(encoding="utf-8"))
    if bundle["targets"] != EXPECTED:
        raise ValueError("Confirmation target set differs from the frozen registration")
    if bundle["adapter_sha256"] != FROZEN_PILOT_SHA:
        raise ValueError("B confirmation must preserve original A preparation")
    if (sha(__file__) != bundle["inference_adapter_sha256"]
            or bundle["protocol_sha256"] == ORIGINAL_PROTOCOL_SHA
            or sha(B_PROTOCOL_PATH) != bundle["protocol_sha256"]):
        raise ValueError("B confirmation adapter or separate final protocol differs")
    if bundle["ab_selector_sha256"] != sha(Path(__file__).with_name("select_stack_ab.py")):
        raise ValueError("AB selector differs from frozen selection")
    if validate_embedded(bundle) != "B":
        raise ValueError("Only prospectively selected B may run this exporter")
    for name, expected in bundle["files"].items():
        if sha(args.bundle / name) != expected:
            raise ValueError(f"Prepared input changed: {name}")
    if sha(args.checkpoint) != CHECKPOINT_SHA or sha(args.genelist) != GENELIST_SHA:
        raise ValueError("Checkpoint/genelist differ from pinned official Stack files")
    # Exact pinned trusted public file; no arbitrary downloadable pickle.
    with args.genelist.open("rb") as f:
        model_genes = [str(x) for x in GeneListUnpickler(f).load()]
    if len(set(model_genes)) != len(model_genes):
        raise ValueError("Duplicate Stack model genes")
    controls_full = ad.read_h5ad(args.bundle / "destination_controls.h5ad")
    if set(controls_full.obs.gene.astype(str)) != {CONTROL}:
        raise ValueError("Destination bundle is not control-only")
    source_control = ad.read_h5ad(args.bundle / "source_00.h5ad")
    if set(source_control.obs.gene.astype(str)) != {CONTROL}:
        raise ValueError("Source reference is not control-only")
    shared = set(model_genes) & set(source_control.var_names) & set(controls_full.var_names)
    if len(shared) < 500:
        raise ValueError("Fewer than 500 shared measured genes")
    def model_adata(obj, rows=None):
        selected = obj if rows is None else obj[rows]
        return ad.AnnData(align_shared(selected.X, selected.var_names, model_genes, set(selected.var_names)),
                         obs=selected.obs.copy(), var=pd.DataFrame(index=model_genes))
    ctrl = model_adata(controls_full, pick(np.arange(controls_full.n_obs), 512, "model:destination"))
    src_ctrl = model_adata(source_control)
    basal = np.asarray(controls_full.X.sum(axis=0), dtype=np.float64).ravel()
    libraries = np.asarray(controls_full.X.sum(axis=1), dtype=np.float64).ravel()
    if np.any(libraries <= 0):
        raise ValueError("Zero-library destination controls")
    args.out.mkdir(parents=True)
    with (args.out / "model_genes.pkl").open("xb") as f:
        pickle.dump(model_genes, f)
    genelist = args.out / "model_genes.pkl"
    import torch
    from stack.model_loading import load_model_from_checkpoint
    model = load_model_from_checkpoint(str(args.checkpoint), model_class="ICL_FinetunedModel",
                                       device=torch.device("cpu"))
    model.to(torch.device(args.device)).eval()
    write_json(args.out / "inference_manifest.json", {"status": "inference_started_before_results",
        "bundle_sha256": sha(args.bundle / "bundle.json"), "adapter_sha256": sha(__file__),
        "preparation_adapter_sha256": bundle["adapter_sha256"], "protocol_sha256": bundle["protocol_sha256"],
        "ab_selection_sha256": bundle["ab_selection_sha256"], "input_axis_policy": INPUT_AXIS_POLICY,
        "ab_protocol_sha256": bundle["ab_protocol_sha256"],
        "checkpoint_sha256": CHECKPOINT_SHA, "genelist_sha256": GENELIST_SHA,
        "shared_genes": len(shared), "model_genes": len(model_genes), "device": args.device,
        "memory_components": memory_shapes(model, args.batch_size), "batch_size": args.batch_size,
        "rng_note": "Same Stack seed for paired prompt and synthetic control; profiles exported before final draws",
        "versions": {p: importlib.metadata.version(p) for p in ["torch", "arc-stack", "numpy", "scipy", "anndata", "h5py"]}})
    profiles = {"transfer": [], "stack": []}
    diagnostics, cached_controls = [], {}
    with np.load(args.bundle / "transfer.npz", allow_pickle=False) as effect:
        if list(effect["targets"]) != bundle["targets"] or list(effect["genes"]) != list(controls_full.var_names):
            raise ValueError("Frozen transfer axis mismatch")
        for i, target in enumerate(bundle["targets"]):
            source = ad.read_h5ad(args.bundle / f"source_{i + 1:02d}.h5ad")
            if set(source.obs.gene.astype(str)) != {target} or list(source.var_names) != list(source_control.var_names):
                raise ValueError("Source prompt label/axis mismatch")
            source = model_adata(source)
            n = source.n_obs
            if n not in cached_controls:
                ref_rows = pick(np.arange(src_ctrl.n_obs), n, f"model:sourcecontrol:{n}")
                cached_controls[n] = call_model(model, src_ctrl[ref_rows], ctrl, genelist, args.batch_size)
            pred = call_model(model, source, ctrl, genelist, args.batch_size)
            baseline, _ = predicted_profile(basal, effect["lfc"][i] / np.log(2.), effect["observed"][i])
            corrected, info = corrected_profile(basal, baseline, model_genes, list(controls_full.var_names),
                                                 shared, pred, cached_controls[n])
            # Record exact model-derived profiles before any final-cell draws.
            profiles["transfer"].append(np.asarray(baseline, dtype=np.float64).copy())
            profiles["stack"].append(np.asarray(corrected, dtype=np.float64).copy())
            diagnostics.append(info | {"target": target, "source_cells": n})
            write_json(args.out / f"diagnostic_{i:02d}.json", diagnostics[-1])
            print(f"Finished {target}", flush=True)
    np.savez_compressed(args.out / "profiles.npz", targets=np.asarray(bundle["targets"], dtype=str),
        genes=np.asarray(controls_full.var_names, dtype=str),
        transfer=np.stack(profiles["transfer"]), stack=np.stack(profiles["stack"]),
        basal=basal.astype(np.float64), library_sizes=libraries.astype(np.float64),
        shared=np.array([g in shared for g in controls_full.var_names], dtype=bool))
    write_json(args.out / "finished.json", {"targets": bundle["targets"],
        "status": "profiles_exported_no_final_cells_no_scores", "diagnostics": diagnostics,
        "profile_sha256": sha(args.out / "profiles.npz"), "profile_dtype": "float64",
        "stack_seed": SEED, "final_poisson_seeds": [1, 2, 3], "protocol_sha256": bundle["protocol_sha256"],
        "claim": "One frozen Stack inference; exact profiles before final sampling; no pretraining holdout claim"})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("bundle", "checkpoint", "genelist", "out"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--batch-size", type=int, default=1)
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error("Batch size must be positive")
    infer(args)


if __name__ == "__main__":
    main()
