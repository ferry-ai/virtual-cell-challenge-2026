"""Export context-conditioned Stack/t25 profiles after a reviewed positive gate.

No cells, packaging, scoring, upload or submission. Each completed context has
an independent profile artifact. The historical pilot helper remains unchanged.
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
from vcc2026.inference import read_basal_profile

PILOT_SHA = "b259371df3d0d515003597c4d9ce5755c25840f0d36fc96d8ac390ffe1275508"
CONFIRM_PROTOCOL_SHA = "2c2614532d49e35a60735858f150e6bd46f1cb9414ccc8b3914aaf12061245f2"


def control_summary(matrix):
    """Exactly the frozen correction's reduction, stored once as one sparse row.

    Do not sum with a new dtype: preserve original sum semantics, then cast.
    The helper only consumes this column sum, never individual decoded cells.
    """
    return sp.csr_matrix(np.asarray(matrix.sum(axis=0), dtype=np.float64))


def inside(root, name):
    path = (root / name).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file():
        raise ValueError("Missing or escaping bundle member")
    return path


def check_gate(confirmation, decision, bundle_sha, adapter_sha):
    """A benchmark verdict alone never grants production or upload authority."""
    if (confirmation.get("status") != "complete"
            or confirmation.get("passes_confirmation") is not True
            or confirmation.get("protocol_sha256") != CONFIRM_PROTOCOL_SHA):
        raise ValueError("Frozen confirmation has not passed")
    delta = confirmation.get("delta_projection", float("nan"))
    seeds = confirmation.get("per_seed_delta", [])
    interval = confirmation.get("paired_target_bootstrap_ci95")
    pds = confirmation.get("mean_pds_raw_delta", float("nan"))
    if (len(seeds) != 3 or not isinstance(interval, list) or len(interval) != 2
            or not np.isfinite([delta, pds, *seeds, *interval]).all()
            or delta < .005 or min(seeds) <= 0 or not 0 < interval[0] <= interval[1]
            or pds < 0 or confirmation.get("bootstrap_complete_fraction") != 1.):
        raise ValueError("Confirmation numeric gate is inconsistent")
    if (decision.get("production_inference_authorized") is not True
            or decision.get("bundle_sha256") != bundle_sha
            or decision.get("adapter_sha256") != adapter_sha
            or decision.get("baseline") != "t25_unscaled"
            or decision.get("regime_extension_acknowledged") is not True
            or decision.get("contexts") != ["A", "B", "C"]):
        raise ValueError("Missing concrete reviewed production decision")


def context_profiles(model, bundle_root, bundle, context, model_genes, genelist, *, out,
                     batch_size=1, model_call=pilot.call_model):
    """Same frozen prompt/control correction on one prepared destination axis."""
    import anndata as ad
    full_path = bundle_root / f"full_controls_{context}.h5ad"
    genes = list(pilot.genes_of(full_path))
    basal_record = read_basal_profile(full_path, context=context)
    basal = np.asarray(basal_record.profile, dtype=np.float64)
    libraries = np.asarray(basal_record.library_sizes, dtype=np.float64)
    if basal.shape != (len(genes),) or np.any(libraries <= 0):
        raise ValueError("Invalid destination basal summary")
    controls_full = ad.read_h5ad(bundle_root / f"model_controls_{context}.h5ad")
    source_control = ad.read_h5ad(inside(bundle_root, bundle["source_files"][pilot.CONTROL]))
    if (controls_full.n_obs != 512 or source_control.n_obs != 512
            or list(controls_full.var_names) != genes
            or set(controls_full.obs.gene.astype(str)) != {pilot.CONTROL}
            or set(source_control.obs.gene.astype(str)) != {pilot.CONTROL}):
        raise ValueError("Invalid prepared model controls")
    shared = set(model_genes) & set(source_control.var_names) & set(genes)
    if len(shared) < 500:
        raise ValueError("Fewer than 500 measured shared genes")
    def aligned(obj):
        return ad.AnnData(pilot.align_shared(obj.X, obj.var_names, model_genes, shared),
                         obs=obj.obs.copy(), var=pd.DataFrame(index=model_genes))
    ctrl, src_ctrl = aligned(controls_full), aligned(source_control)
    out.mkdir()
    shared_mask = np.array([g in shared for g in genes], dtype=bool)
    targets = bundle["official_targets"]
    admitted, fallback = set(bundle["targets"]), set(bundle["fallback_targets"])
    if (len(set(targets)) != len(targets) or admitted & fallback
            or admitted | fallback != set(targets)):
        raise ValueError("Invalid frozen target partition")
    retained = []
    cache = {}
    with np.load(bundle_root / f"fallback_t25_{context}.npz", allow_pickle=False) as effects:
        if (list(effects["genes"].astype(str)) != genes
                or len(effects["targets"]) != len(targets)
                or set(effects["targets"].astype(str)) != set(targets)
                or effects["lfc"].shape != (len(targets), len(genes))
                or effects["observed"].shape != effects["lfc"].shape
                or effects["observed"].dtype != bool
                or not np.isfinite(effects["lfc"]).all()):
            raise ValueError("Fallback axes differ")
        index = {t: i for i, t in enumerate(effects["targets"].astype(str))}
        for j, target in enumerate(targets):
            i = index[target]
            # Preserve the helper's original dtype promotion in its pinned runtime.
            q0, _ = pilot.predicted_profile(basal, effects["lfc"][i] / np.log(2.), effects["observed"][i])
            q0 = np.asarray(q0, dtype=np.float64)
            if target in admitted:
                source = ad.read_h5ad(inside(bundle_root, bundle["source_files"][target]))
                if (set(source.obs.gene.astype(str)) != {target}
                        or list(source.var_names) != list(source_control.var_names)
                        or not 64 <= source.n_obs <= 128):
                    raise ValueError("Prepared source label/axis/cardinality differs")
                n = source.n_obs
                if n not in cache:
                    rows = pilot.pick(np.arange(src_ctrl.n_obs), n, f"model:sourcecontrol:{n}")
                    cache[n] = control_summary(model_call(model, src_ctrl[rows], ctrl, genelist, batch_size))
                pred = model_call(model, aligned(source), ctrl, genelist, batch_size)
                q, info = pilot.corrected_profile(basal, q0, model_genes, genes, shared, pred, cache[n])
                info |= {"source_cells": n, "fallback": False}
            else:
                q, info = q0.copy(), {"fallback": True, "source_cells": 0}
            q = np.asarray(q, dtype=np.float64)
            if (not np.isfinite(q).all() or np.any(q < 0)
                    or not np.array_equal(q[~shared_mask], q0[~shared_mask])
                    or not np.isclose(q.sum(), q0.sum(), rtol=1e-12, atol=0)):
                raise ValueError("Corrected profile violates frozen support/mass contract")
            if target in fallback and not np.array_equal(q, q0):
                raise ValueError("Unsupported target changed")
            name = f"profile_{j:03d}.npz"
            np.savez_compressed(out / name, transfer=q0, stack=q,
                                target=np.asarray(target, dtype=str))
            row = {"target": target, "file": name, "sha256": pilot.sha(out / name), **info}
            row["synthetic_control_cache_bytes"] = sum(x.data.nbytes + x.indices.nbytes + x.indptr.nbytes for x in cache.values())
            pilot.write_json(out / f"diagnostic_{j:03d}.json", row)
            retained.append(row)
            print(f"Completed profile {context} {j + 1}/{len(targets)}", flush=True)
    np.savez_compressed(out / "axis.npz", genes=np.asarray(genes, dtype=str),
                        targets=np.asarray(targets, dtype=str), shared=shared_mask,
                        basal=basal, library_sizes=libraries)
    pilot.write_json(out / "complete.json", {"status": "profiles_only_no_cells_no_scores",
        "context": context, "profiles": retained, "axis_sha256": pilot.sha(out / "axis.npz"),
        "model_calls": len(admitted) + len(cache), "shared_genes": len(shared),
        "baseline": "t25_unscaled", "model_seed": pilot.SEED,
        "claim": "Extension to official basals; public HepG2 confirmation is not evidence above t25 here"})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("bundle", "checkpoint", "genelist", "confirmation", "decision", "out"):
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--confirmation-sha256", required=True)
    p.add_argument("--decision-sha256", required=True)
    p.add_argument("--contexts", nargs="+", choices=["A", "B", "C"], default=["A", "B", "C"])
    p.add_argument("--device", default="cuda")
    args = p.parse_args()
    if args.out.exists() or len(set(args.contexts)) != len(args.contexts):
        raise ValueError("Output exists or contexts are duplicated")
    if pilot.sha(pilot.__file__) != PILOT_SHA:
        raise ValueError("Scientific helper differs")
    if (pilot.sha(args.confirmation) != args.confirmation_sha256
            or pilot.sha(args.decision) != args.decision_sha256):
        raise ValueError("Reviewed confirmation or decision changed")
    confirmation = json.loads(args.confirmation.read_text(encoding="utf-8"))
    decision = json.loads(args.decision.read_text(encoding="utf-8"))
    bundle_path = args.bundle / "bundle.json"
    check_gate(confirmation, decision, pilot.sha(bundle_path), pilot.sha(__file__))
    bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
    if bundle.get("status") != "prepared_no_model_no_scores":
        raise ValueError("Production bundle is not prepared")
    for name, digest in bundle["files"].items():
        if pilot.sha(inside(args.bundle, name)) != digest:
            raise ValueError("Changed prepared production input: " + name)
    if pilot.sha(args.checkpoint) != pilot.CHECKPOINT_SHA or pilot.sha(args.genelist) != pilot.GENELIST_SHA:
        raise ValueError("Public model/checkpoint changed")
    with args.genelist.open("rb") as f:
        model_genes = [str(g) for g in pilot.GeneListUnpickler(f).load()]
    if len(set(model_genes)) != len(model_genes):
        raise ValueError("Duplicated model genes")
    args.out.mkdir(parents=True)
    genelist = args.out / "model_genes.pkl"
    with genelist.open("xb") as f:
        pickle.dump(model_genes, f)
    import torch
    from stack.model_loading import load_model_from_checkpoint
    model = load_model_from_checkpoint(str(args.checkpoint), model_class="ICL_FinetunedModel", device=torch.device("cpu"))
    model.to(torch.device(args.device)).eval()
    pilot.write_json(args.out / "manifest.json", {"adapter_sha256": pilot.sha(__file__),
        "pilot_helper_sha256": PILOT_SHA, "bundle_sha256": pilot.sha(bundle_path),
        "checkpoint_sha256": pilot.CHECKPOINT_SHA, "genelist_sha256": pilot.GENELIST_SHA,
        "confirmation_sha256": args.confirmation_sha256, "decision_sha256": args.decision_sha256,
        "contexts": args.contexts, "device": args.device, "batch_size": 1,
        "versions": {p: importlib.metadata.version(p) for p in ("numpy", "torch", "anndata", "arc-stack")},
        "claim": "Unscaled t25 fallback; frozen Stack correction on measured shared support; no submission"})
    for context in args.contexts:
        context_profiles(model, args.bundle, bundle, context, model_genes, genelist,
                         out=args.out / context)


if __name__ == "__main__":
    main()
