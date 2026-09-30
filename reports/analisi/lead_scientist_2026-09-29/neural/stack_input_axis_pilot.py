"""Optional Stack pilot. Plan -> prepare public prompts -> infer; never downloads.

Inference receives an isolated prepared bundle with destination CONTROLS only.
The original destination perturbation matrix is never opened during inference.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
from pathlib import Path
import pickle
import sys

import h5py
import numpy as np
import pandas as pd
import scipy.sparse as sp

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "src"))
from vcc2026.sc_stream import read_frame
from vcc2026.inference import predicted_profile
from vcc2026.sampling import sample_counts

CONTROL = "non-targeting"
SEED = 20260929
N_TARGETS = 12
N_OUTPUT = 400
PREPARATION_ADAPTER_SHA = "b259371df3d0d515003597c4d9ce5755c25840f0d36fc96d8ac390ffe1275508"
AB_PROTOCOL_SHA = "181d7a00b1f5957948e2daf9fcd1f66fae9adb35dbf78aab59a5b2c006133506"
INPUT_AXIS_POLICY = "own_measured_support"
MAX_SOURCE = 128
MIN_SOURCE = 64
STACK_COMMIT = "cacc2e4b09435c3e536d46237d10b50f222dd144"
STACK_REVISION = "b09f085dac03d170b078a5c72f550ae93686e544"
CHECKPOINT_SHA = "f93cf6f42f36c8a85dc570d92e801c1fc3e1f45d55741e6bb250d178a6b6ad36"
GENELIST_SHA = "d8761dfda955b9897d3251798b72361ddd0171ef707119eaf65381bed2d85dcc"


def sha(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(4 * 1024**2), b""):
            h.update(block)
    return h.hexdigest()


def write_json(path, obj):
    with Path(path).open("x", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")


def rng_for(label):
    words = np.frombuffer(hashlib.sha256(f"{SEED}:{label}".encode()).digest()[:16], dtype="<u4")
    return np.random.default_rng(words)


def select_targets(development, source_counts, n=N_TARGETS):
    eligible = [t for t in development if source_counts.get(t, 0) >= MIN_SOURCE]
    ranked = sorted(eligible, key=lambda t: hashlib.sha256(f"Stack:{SEED}:{t}".encode()).hexdigest())
    if len(ranked) < n:
        raise ValueError(f"Only {len(ranked)} eligible development targets; need {n}; no automatic substitution")
    return ranked[:n]


def plan(args):
    if args.out.exists():
        raise FileExistsError(args.out)
    dev = json.loads(args.development_manifest.read_text(encoding="utf-8"))
    groups = pd.read_csv(args.source_groups)
    # Original-cell counts, aggregated over all guides, not selected x002 counts.
    counts = groups.groupby("gene").n_cells_obs.sum().astype(int).to_dict()
    targets = select_targets(dev["development"], counts)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    write_json(args.out, {"status": "planned_no_expression_read_no_scores", "targets": targets,
                         "source_counts": {t: counts[t] for t in targets}, "seed": SEED,
                         "development_manifest_sha256": sha(args.development_manifest),
                         "source_groups_sha256": sha(args.source_groups), "n_output": N_OUTPUT,
                         "source_max_cells": MAX_SOURCE, "source_min_cells": MIN_SOURCE,
                         "protocol_sha256": sha(HERE / "PROTOCOLLO_STACK.md"),
                         "adapter_sha256": sha(__file__), "stack_commit": STACK_COMMIT,
                         "checkpoint_revision": STACK_REVISION})
    print(json.dumps({"plan": str(args.out), "targets": targets}))


def genes_of(path):
    with h5py.File(path, "r") as f:
        var = read_frame(f["var"])
    names = var["gene_name"].astype(str).to_numpy() if "gene_name" in var else var.index.astype(str).to_numpy()
    return names


def unique_first(names):
    """Match stage 73 and the frozen HepG2 bench: retain first measured symbol."""
    names = np.asarray(names).astype(str)
    _, first = np.unique(names, return_index=True)
    first = np.sort(first)
    return names[first], first


def rows_for_labels(path, wanted):
    """Only reads one label column: categorical codes avoid full obs allocation."""
    wanted = list(wanted)
    with h5py.File(path, "r") as f:
        node = f["obs/gene"]
        if isinstance(node, h5py.Group):
            cats = node["categories"].asstr()[:]
            codes = node["codes"][:]
            return {label: np.flatnonzero(np.isin(codes, np.flatnonzero(cats == label))) for label in wanted}
        if "__categories" in f["obs"] and "gene" in f["obs/__categories"]:
            cats = f["obs/__categories/gene"].asstr()[:]
            codes = node[:]
            return {label: np.flatnonzero(np.isin(codes, np.flatnonzero(cats == label))) for label in wanted}
        labels = node.asstr()[:]
        return {label: np.flatnonzero(labels == label) for label in wanted}


def read_rows(path, rows):
    """Bounded row reads; dense contiguous sources never scan the whole matrix."""
    rows = np.sort(np.asarray(rows, dtype=np.int64))
    if len(rows) == 0 or np.any(np.diff(rows) <= 0):
        raise ValueError("Rows must be nonempty, unique and increasing")
    blocks = []
    with h5py.File(path, "r") as f:
        x = f["X"]
        if isinstance(x, h5py.Dataset):
            # Read each selected dense row. h5py does not materialize intervening rows.
            for lo in range(0, len(rows), 32):
                block = np.stack([x[int(i), :] for i in rows[lo:lo + 32]]).astype(np.float32)
                blocks.append(sp.csr_matrix(block))
        else:
            if x.attrs.get("encoding-type", "") not in {"csr_matrix", b"csr_matrix"}:
                raise ValueError("Only dense or CSR H5AD input is supported")
            n_cols = int(x.attrs["shape"][1])
            for row in rows:
                lo, hi = map(int, x["indptr"][int(row):int(row) + 2])
                blocks.append(sp.csr_matrix((x["data"][lo:hi].astype(np.float32),
                                              x["indices"][lo:hi], [0, hi - lo]), shape=(1, n_cols)))
    result = sp.vstack(blocks, format="csr")
    validate_counts(result)
    return result


def validate_counts(x):
    data = x.data if sp.issparse(x) else np.asarray(x)
    if not np.isfinite(data).all() or np.any(data < 0) or np.any(data != np.floor(data)):
        raise ValueError("Expected finite nonnegative raw integer counts")


def pick(rows, count, label):
    rows = np.asarray(rows, dtype=np.int64)
    return np.sort(rng_for(label).choice(rows, min(len(rows), count), replace=False))


def write_counts(path, x, genes, label):
    import anndata as ad
    obs = pd.DataFrame({"gene": [label] * x.shape[0], "target_gene": [label] * x.shape[0]},
                       index=[f"{label}:{i}" for i in range(x.shape[0])])
    ad.AnnData(x, obs=obs, var=pd.DataFrame(index=genes)).write_h5ad(path, compression="gzip")


def prepare(args):
    if args.out.exists():
        raise FileExistsError(args.out)
    planned = json.loads(args.plan.read_text(encoding="utf-8"))
    if len(planned["targets"]) != N_TARGETS or planned["seed"] != SEED:
        raise ValueError("Unregistered plan")
    if planned["protocol_sha256"] != sha(HERE / "PROTOCOLLO_STACK.md"):
        raise ValueError("Protocol changed after plan")
    if planned["adapter_sha256"] != sha(__file__):
        raise ValueError("Adapter changed after plan; create a new plan before extraction")
    source_raw_genes, dest_raw_genes = genes_of(args.source), genes_of(args.destination)
    source_genes, source_cols = unique_first(source_raw_genes)
    dest_genes, dest_cols = unique_first(dest_raw_genes)
    source_rows = rows_for_labels(args.source, [CONTROL, *planned["targets"]])
    # No destination perturbation row selection or expression read is possible here.
    dest_rows = rows_for_labels(args.destination, [CONTROL])[CONTROL]
    if len(dest_rows) < 512 or len(source_rows[CONTROL]) < 512:
        raise ValueError("Need at least 512 controls in each context")
    if any(len(source_rows[t]) < MIN_SOURCE for t in planned["targets"]):
        raise ValueError("Original source label counts disagree with plan")
    with np.load(args.effects, allow_pickle=False) as a:
        if "observed" not in a:
            raise ValueError("Frozen transfer must include explicit observed masks (not lfc != 0)")
        ti = pd.Index(a["targets"].astype(str)).get_indexer(planned["targets"])
        gi = pd.Index(a["genes"].astype(str)).get_indexer(dest_genes)
        if np.any(ti < 0):
            raise ValueError("Frozen transfer lacks planned targets")
        effect = np.zeros((N_TARGETS, len(dest_genes)), dtype=np.float32)
        observed = np.zeros(effect.shape, dtype=bool)
        have = gi >= 0
        effect[:, have] = a["lfc"][ti][:, gi[have]]
        observed[:, have] = a["observed"][ti][:, gi[have]]
    if not np.isfinite(effect).all():
        raise ValueError("Non-finite frozen effects")
    args.out.mkdir(parents=True)
    selected = {t: pick(source_rows[t], MAX_SOURCE, f"source:{t}") for t in planned["targets"]}
    selected[CONTROL] = pick(source_rows[CONTROL], 512, "source:control")
    chosen_dest = pick(dest_rows, 2000, "destination:control")
    write_counts(args.out / "destination_controls.h5ad", read_rows(args.destination, chosen_dest)[:, dest_cols], dest_genes, CONTROL)
    for i, target in enumerate([CONTROL, *planned["targets"]]):
        write_counts(args.out / f"source_{i:02d}.h5ad", read_rows(args.source, selected[target])[:, source_cols], source_genes, target)
    np.savez_compressed(args.out / "transfer.npz", targets=planned["targets"], genes=dest_genes,
                        lfc=effect, observed=observed)
    manifest = planned | {"status": "prepared_no_model_no_scores", "source": str(args.source),
                          "destination": str(args.destination), "source_size": args.source.stat().st_size,
                          "destination_size": args.destination.stat().st_size,
                          "duplicate_gene_policy": "first column per symbol, matching stage73/frozen HepG2 bench",
                          "source_columns_dropped": int(len(source_raw_genes) - len(source_cols)),
                          "destination_columns_dropped": int(len(dest_raw_genes) - len(dest_cols)),
                          "source_selected_rows": {t: r.tolist() for t, r in selected.items()},
                          "destination_control_rows": chosen_dest.tolist(),
                          "effects_sha256": sha(args.effects), "plan_sha256": sha(args.plan),
                          "files": {p.name: sha(p) for p in sorted(args.out.iterdir())}}
    write_json(args.out / "bundle.json", manifest)
    print(json.dumps({"bundle": str(args.out), "targets": planned["targets"], "destination_truth_rows_read": 0}))


def align_shared(x, names, model_genes, shared):
    names = pd.Index(np.asarray(names).astype(str))
    if not names.is_unique or len(set(model_genes)) != len(model_genes):
        raise ValueError("Duplicate gene axis")
    pos = names.get_indexer(model_genes)
    use = np.array([g in shared for g in model_genes]) & (pos >= 0)
    columns = np.flatnonzero(use)
    source = sp.coo_matrix(x[:, pos[use]])
    result = sp.csr_matrix((source.data, (source.row, columns[source.col])), shape=(x.shape[0], len(model_genes)))
    return result


def corrected_profile(basal, baseline, model_genes, full_genes, shared, perturb, control):
    """Paired synthetic-control ratio; preserve frozen transfer outside shared axis."""
    p = np.asarray(perturb.sum(axis=0), dtype=np.float64).ravel()
    c = np.asarray(control.sum(axis=0), dtype=np.float64).ravel()
    if not np.isfinite(p).all() or not np.isfinite(c).all() or p.min() < 0 or c.min() < 0:
        raise ValueError("Invalid generated expression")
    model_pos = pd.Index(model_genes).get_indexer(full_genes)
    keep = np.array([g in shared for g in full_genes]) & (model_pos >= 0)
    slots = model_pos[keep]
    if not keep.any() or p[slots].sum() <= 0 or c[slots].sum() <= 0:
        raise ValueError("No generated mass on shared genes")
    # Normalize both generated populations on exactly the same shared support.
    pf, cf = p[slots] / p[slots].sum(), c[slots] / c[slots].sum()
    lfc = np.clip(np.log((pf + 1e-6) / (cf + 1e-6)), -6 * np.log(2), 6 * np.log(2))
    out = np.asarray(baseline, dtype=np.float64).copy()
    tilted = np.asarray(basal, dtype=np.float64)[keep] * np.exp(lfc)
    if tilted.sum() <= 0:
        raise ValueError("No destination basal mass on shared genes")
    out[keep] = tilted * (out[keep].sum() / tilted.sum())
    return out, {"shared_genes": int(keep.sum()), "shared_lfc_rms": float(np.sqrt(np.mean(lfc**2))),
                 "baseline_mass_preserved_outside_shared": bool(np.array_equal(out[~keep], baseline[~keep])),
                 "total_mass_relative_error": float(abs(out.sum() / np.sum(baseline) - 1))}


def call_model(model, source, controls, genelist, batch_size, seed=SEED):
    """Fresh copies are essential: upstream iterative generation mutates its input."""
    if set(controls.obs["gene"].astype(str)) != {CONTROL}:
        raise ValueError("Destination input contains perturbation truth")
    result = model.get_incontext_generation(base_adata_or_path=source.copy(),
        test_adata_or_path=controls.copy(), genelist_path=str(genelist), num_steps=5,
        prompt_ratio=.25, context_ratio=.4, context_ratio_min=.2, mask_rate=1.,
        mode="mdm", gene_name_col=None, batch_size=batch_size, show_progress=False,
        num_workers=0, random_seed=seed)
    result = result[0] if isinstance(result, tuple) else result
    result = sp.csr_matrix(result)
    if result.shape != controls.shape:
        raise ValueError(f"Stack output shape {result.shape} != declared axis {controls.shape}")
    validate_counts(result)
    return result


def memory_shapes(model, batch_size):
    b, c, g, h, d = batch_size, model.n_cells, model.n_genes, model.n_hidden, model.token_dim
    return {"batch": b, "cells_per_set": c, "genes": g, "hidden_genes": h, "token_dim": d,
            "parameters": sum(p.numel() for p in model.parameters()),
            "weights_float32_bytes": sum(p.numel() for p in model.parameters()) * 4,
            "one_dense_input_bytes": b * c * g * 4, "decoder_two_channels_bytes": b * c * g * 8,
            "latent_bytes": b * c * h * d * 4,
            "caveat": "Component sizes, not total/peak VRAM; attention, copies, allocator, checkpoint add memory"}


class GeneListUnpickler(pickle.Unpickler):
    """Only the two numpy scalar constructors present in the pinned gene file."""

    def find_class(self, module, name):
        if module == "numpy" and name == "dtype":
            return np.dtype
        if module in {"numpy.core.multiarray", "numpy._core.multiarray"} and name == "scalar":
            return np.core.multiarray.scalar
        raise pickle.UnpicklingError(f"Unexpected gene-list constructor: {module}.{name}")


def infer(args):
    import anndata as ad
    if args.out.exists():
        raise FileExistsError(args.out)
    bundle = json.loads((args.bundle / "bundle.json").read_text(encoding="utf-8"))
    if bundle.get("adapter_sha256") != PREPARATION_ADAPTER_SHA:
        raise ValueError("B requires the immutable preparation from pilot A")
    if sha(HERE / "PROTOCOLLO_STACK_AB.md") != AB_PROTOCOL_SHA:
        raise ValueError("Prospective AB protocol changed")
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
        "preparation_adapter_sha256": PREPARATION_ADAPTER_SHA,
        "ab_protocol_sha256": AB_PROTOCOL_SHA, "input_axis_policy": INPUT_AXIS_POLICY,
        "checkpoint_sha256": CHECKPOINT_SHA, "genelist_sha256": GENELIST_SHA,
        "shared_genes": len(shared), "model_genes": len(model_genes), "device": args.device,
        "memory_components": memory_shapes(model, args.batch_size), "batch_size": args.batch_size,
        "rng_note": "Same Stack seed for paired prompt and synthetic control; final target-specific IID draws",
        "versions": {p: importlib.metadata.version(p) for p in ["torch", "arc-stack", "numpy", "scipy", "anndata", "h5py"]}})
    generated, transferred, diagnostics, cached_controls = [], [], [], {}
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
            for profile, dest in [(baseline, transferred), (corrected, generated)]:
                rng = rng_for(f"output:{target}")
                libs = rng.choice(libraries, N_OUTPUT, replace=True)
                dest.append(sample_counts(profile, libs, rng, max_stored_per_cell=12000,
                                          max_counts_per_cell=1000000))
            diagnostics.append(info | {"target": target, "source_cells": n})
            write_json(args.out / f"diagnostic_{i:02d}.json", diagnostics[-1])
            print(f"Finished {target}", flush=True)
    for arm, blocks in [("transfer", transferred), ("stack", generated)]:
        x = sp.vstack(blocks, format="csr")
        obs = pd.DataFrame({"gene": np.repeat(bundle["targets"], N_OUTPUT),
                            "target_gene": np.repeat(bundle["targets"], N_OUTPUT)})
        ad.AnnData(x, obs=obs, var=controls_full.var.copy()).write_h5ad(args.out / f"prediction_{arm}.h5ad", compression="gzip")
    write_json(args.out / "finished.json", {"targets": bundle["targets"], "cells_per_target": N_OUTPUT,
        "diagnostics": diagnostics, "claim": "Generated only; no model score or clean-pretraining holdout claim"})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    s = p.add_subparsers(dest="phase", required=True)
    a = s.add_parser("plan")
    a.add_argument("--development-manifest", type=Path, required=True)
    a.add_argument("--source-groups", type=Path, required=True)
    a.add_argument("--out", type=Path, required=True)
    a = s.add_parser("prepare")
    for name in ["plan", "source", "destination", "effects", "out"]:
        a.add_argument("--" + name, type=Path, required=True)
    a = s.add_parser("infer")
    for name in ["bundle", "checkpoint", "genelist", "out"]:
        a.add_argument("--" + name, type=Path, required=True)
    a.add_argument("--device", default="cuda")
    a.add_argument("--batch-size", type=int, default=1)
    args = p.parse_args()
    if args.phase == "infer" and args.batch_size < 1:
        p.error("batch-size must be positive")
    {"plan": plan, "prepare": prepare, "infer": infer}[args.phase](args)


if __name__ == "__main__":
    main()
