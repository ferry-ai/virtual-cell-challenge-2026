"""Plan and pack selected x002 K562 prompts, official controls and frozen t25.

Data preparation only: no model, model weights, inference, scoring or upload.
The fixed minimum/cap are 64/128 source cells; every other target falls back.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from pathlib import Path
import shutil

import h5py
import numpy as np
import scipy.sparse as sp

import stack_pilot as pilot

CONTEXTS = ("A", "B", "C")


def vector(group, name):
    node = group[name]
    if isinstance(node, h5py.Group):
        if "categories" in node:
            codes = node["codes"][:]
            if np.any(codes < 0):
                raise ValueError(f"Missing source metadata: {name}")
            return node["categories"].asstr()[:][codes]
        if "values" in node:
            if "mask" in node and node["mask"][:].any():
                raise ValueError(f"Missing source metadata: {name}")
            node = node["values"]
        else:
            raise ValueError(f"Unsupported metadata: {name}")
    return node.asstr()[:] if node.dtype.kind in "OSU" else node[:]


def digest_json(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def column_csv(path, column):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return [r[column] for r in csv.DictReader(f)]


def pick(values, n, label):
    values = np.sort(np.asarray(values, dtype=np.int64))
    if len(np.unique(values)) != len(values):
        raise ValueError("Repeated source cell ID")
    words = np.frombuffer(hashlib.sha256(f"StackProduction:20260929:{label}".encode()).digest()[:16], dtype="<u4")
    return np.sort(np.random.default_rng(words).choice(values, min(n, len(values)), replace=False))


def shard_metadata(path):
    genes = pilot.genes_of(path)
    with h5py.File(path, "r") as f:
        if f["X"].attrs.get("encoding-type") not in {"csr_matrix", b"csr_matrix"}:
            raise ValueError("Production source must be CSR")
        labels = vector(f["obs"], "gene").astype(str)
        source_rows = vector(f["obs"], "source_row").astype(np.int64)
        pointers = f["X/indptr"][:]
    fingerprint = {"bytes": path.stat().st_size, "metadata_sha256": digest_json({
        "gene": labels.tolist(), "source_row": source_rows.tolist(), "genes": genes.tolist()}),
        "n_obs": len(labels), "n_vars": len(genes), "nnz": int(pointers[-1])}
    return labels, source_rows, genes, np.diff(pointers), fingerprint


def plan(args):
    if args.out.exists():
        raise FileExistsError(args.out)
    targets = column_csv(args.controls / "pert_counts.csv", "target_gene")
    axis = column_csv(args.controls / "gene_names.csv", "gene_name")
    if len(set(targets)) != len(targets) or len(set(axis)) != len(axis):
        raise ValueError("Official target/gene axis must be unique")
    labels, ids, parts, locals_, nnz, fingerprints = [], [], [], [], [], {}
    source_genes = None
    for part in sorted(args.source.glob("cells_part*.h5ad")):
        lab, rows, genes, counts, fingerprint = shard_metadata(part)
        if source_genes is not None and list(genes) != list(source_genes):
            raise ValueError("Source shard gene axes differ")
        source_genes = genes
        labels.extend(lab); ids.extend(rows); parts.extend([part.name] * len(rows))
        locals_.extend(range(len(rows))); nnz.extend(counts)
        fingerprints[part.name] = fingerprint
    if source_genes is None:
        raise ValueError("No cells_part*.h5ad source shards found")
    labels, ids, parts, locals_, nnz = map(np.asarray, [labels, ids, parts, locals_, nnz])
    if len(set(ids.tolist())) != len(ids):
        raise ValueError("Source cell IDs repeat across shards")
    available = {t: int(np.sum(labels == t)) for t in targets}
    admitted = sorted(t for t in targets if available[t] >= 64)
    registration = json.loads(args.registration.read_text(encoding="utf-8"))
    if admitted != registration["production_targets_subset_ge64"] or sorted(set(targets) - set(admitted)) != registration["production_fallback_targets"]:
        raise ValueError("Source eligibility differs from pre-score target registration")
    if available != registration["counts_per_panel_target"]:
        raise ValueError("Source target counts differ from pre-score metadata")
    if np.sum(labels == pilot.CONTROL) < 512:
        raise ValueError("At least 512 source NTC required")
    selected = {}
    total_nnz = 0
    for target in [pilot.CONTROL, *admitted]:
        chosen = pick(ids[labels == target], 512 if target == pilot.CONTROL else 128, target)
        use = np.isin(ids, chosen)
        total_nnz += int(nnz[use].sum())
        selected[target] = {"source_rows": chosen.tolist(),
            "by_part": {part: locals_[use & (parts == part)].astype(int).tolist() for part in sorted(set(parts[use]))}}
    unique_genes, first = pilot.unique_first(source_genes)
    measured = set(unique_genes)
    source_mask = [g in measured for g in axis]
    controls, fallback = {}, {}
    for context in CONTEXTS:
        path = args.controls / f"context_{context}.h5ad"
        if list(pilot.genes_of(path)) != axis:
            raise ValueError(f"Official control axis differs: {context}")
        with h5py.File(path, "r") as f:
            for name in ("gene", "target_gene"):
                if name in f["obs"] and set(vector(f["obs"], name).astype(str)) != {pilot.CONTROL}:
                    raise ValueError("Control file contains a non-control label")
            x = f["X"]
            n = int(x.shape[0] if isinstance(x, h5py.Dataset) else x.attrs["shape"][0])
        if n < 512:
            raise ValueError("At least 512 destination controls required")
        controls[context] = {"file": path.name, "sha256": pilot.sha(path), "bytes": path.stat().st_size,
                             "cells": n, "model_rows": pick(np.arange(n), 512, f"destination:{context}").tolist()}
        path = args.effects / f"effects_{context}.npz"
        with np.load(path, allow_pickle=False) as z:
            if not {"targets", "genes", "lfc", "observed"}.issubset(z.files):
                raise ValueError("t25 effects require an explicit observed mask")
            if set(z["targets"].astype(str)) != set(targets) or list(z["genes"].astype(str)) != axis:
                raise ValueError("t25 effects target/gene axes differ")
            if len(z["targets"]) != len(targets) or z["lfc"].shape != (len(targets), len(axis)) or z["observed"].shape != z["lfc"].shape:
                raise ValueError("t25 effect dimensions or target uniqueness differ")
            if not np.isfinite(z["lfc"]).all() or z["observed"].dtype.kind != "b":
                raise ValueError("t25 requires finite effects and boolean observed mask")
        fallback[context] = {"file": path.name, "sha256": pilot.sha(path), "bytes": path.stat().st_size}
    result = {"status": "planned_no_model_no_scores", "seed_rule": "SHA256 StackProduction:20260929:<label>, first16bytes little-endianuint32",
        "target_order": "lexical admitted; official panel order retained separately", "targets": admitted,
        "official_targets": targets, "fallback_targets": sorted(set(targets) - set(admitted)),
        "source_counts": available, "source_cells": selected, "source_shards": fingerprints,
        "source_axis_raw": source_genes.tolist(), "source_axis_unique": unique_genes.tolist(), "source_keep_columns": first.tolist(),
        "official_axis": axis, "source_observed_on_official": source_mask,
        "control_files": controls, "fallback_files": fallback,
        "source_report_sha256": pilot.sha(args.source / "report.json"),
        "registration_sha256": pilot.sha(args.registration),
        "fallback_manifest_sha256": pilot.sha(args.effects / "manifest.json"),
        "packer_sha256": pilot.sha(__file__), "helper_adapter_sha256": pilot.sha(pilot.__file__),
        "selected_source_nnz_before_duplicate_drop": total_nnz,
        "selected_source_csr_bytes_approx": total_nnz * 8 + (sum(len(v["source_rows"]) for v in selected.values()) + 1) * 8,
        "baseline": "t25 unchanged on every unsupported target; no zero-imputed missing effect",
        "inference_authorized_by_preparation": False}
    args.out.parent.mkdir(parents=True, exist_ok=True)
    pilot.write_json(args.out, result)
    print(json.dumps({"targets": len(admitted), "fallback": len(result["fallback_targets"]),
                      "source_nnz": total_nnz, "plan": str(args.out)}))


def copy_verified(source, destination, expected):
    if destination.exists():
        raise FileExistsError(destination)
    shutil.copyfile(source, destination)
    if pilot.sha(destination) != expected:
        raise ValueError(f"Copied file differs: {destination.name}")


def prepare(args):
    if args.out.exists():
        raise FileExistsError(args.out)
    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    if plan["packer_sha256"] != pilot.sha(__file__) or plan["helper_adapter_sha256"] != pilot.sha(pilot.__file__):
        raise ValueError("Code changed after plan")
    if plan["registration_sha256"] != pilot.sha(args.registration):
        raise ValueError("Target registration changed after plan")
    if plan["source_report_sha256"] != pilot.sha(args.source / "report.json"):
        raise ValueError("Source lineage report changed")
    if plan["fallback_manifest_sha256"] != pilot.sha(args.effects / "manifest.json"):
        raise ValueError("t25 recipe manifest changed")
    args.out.mkdir(parents=True)
    all_targets = [pilot.CONTROL, *plan["targets"]]
    chunks = {t: [] for t in all_targets}
    chunk_ids = {t: [] for t in all_targets}
    first = np.asarray(plan["source_keep_columns"])
    for part, old in plan["source_shards"].items():
        path = args.source / part
        labels, ids, genes, nnz, actual = shard_metadata(path)
        if actual != old:
            raise ValueError(f"Source metadata changed: {part}")
        local_rows = sorted({r for t in all_targets for r in plan["source_cells"][t]["by_part"].get(part, [])})
        if not local_rows:
            continue
        block = pilot.read_rows(path, local_rows)[:, first]
        positions = {row: i for i, row in enumerate(local_rows)}
        for target in all_targets:
            take = plan["source_cells"][target]["by_part"].get(part, [])
            if not take:
                continue
            if not np.all(labels[take] == target):
                raise ValueError("Selected source label changed")
            chunks[target].append(block[[positions[row] for row in take]])
            chunk_ids[target].extend(ids[take].tolist())
        del block
    source_files = {}
    for i, target in enumerate(all_targets):
        block = sp.vstack(chunks.pop(target), format="csr")
        written_ids = np.asarray(chunk_ids.pop(target))
        order = np.argsort(written_ids)
        if written_ids[order].tolist() != plan["source_cells"][target]["source_rows"]:
            raise ValueError("Packed source cell IDs differ from plan")
        block = block[order]
        if block.shape[0] != len(plan["source_cells"][target]["source_rows"]):
            raise ValueError("Packed source cell count mismatch")
        name = f"source_{i:03d}.h5ad"
        pilot.write_counts(args.out / name, block, plan["source_axis_unique"], target)
        source_files[target] = name
    for context, control in plan["control_files"].items():
        raw = args.controls / control["file"]
        copy_verified(raw, args.out / f"full_controls_{context}.h5ad", control["sha256"])
        pilot.write_counts(args.out / f"model_controls_{context}.h5ad",
            pilot.read_rows(raw, control["model_rows"]), plan["official_axis"], pilot.CONTROL)
        effect = plan["fallback_files"][context]
        copy_verified(args.effects / effect["file"], args.out / f"fallback_t25_{context}.npz", effect["sha256"])
    copy_verified(args.effects / "manifest.json", args.out / "fallback_t25_manifest.json", plan["fallback_manifest_sha256"])
    np.savez_compressed(args.out / "gene_support.npz", official_genes=plan["official_axis"],
                        source_genes=plan["source_axis_unique"], source_observed_on_official=plan["source_observed_on_official"])
    result = {"status": "prepared_no_model_no_scores", "plan_sha256": pilot.sha(args.plan),
        "targets": plan["targets"], "fallback_targets": plan["fallback_targets"],
        "official_targets": plan["official_targets"], "source_files": source_files,
        "controls": plan["control_files"], "source_row_ids": {t: plan["source_cells"][t]["source_rows"] for t in all_targets},
        "source_lineage": {"report_sha256": plan["source_report_sha256"], "shards": plan["source_shards"]},
        "source_counts_claim": "Selected raw counts, no pseudobulk reconstruction or count normalization",
        "files": {p.name: pilot.sha(p) for p in sorted(args.out.iterdir())}, "inference_authorized": False}
    pilot.write_json(args.out / "bundle.json", result)
    print(json.dumps({"bundle": str(args.out), "source_targets": len(plan["targets"]), "fallback": len(plan["fallback_targets"])}))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("phase", choices=["plan", "prepare"])
    for name in ["source", "controls", "effects", "registration", "out"]:
        p.add_argument("--" + name, type=Path, required=True)
    p.add_argument("--plan", type=Path)
    args = p.parse_args()
    if args.phase == "prepare" and args.plan is None:
        p.error("prepare requires --plan")
    {"plan": plan, "prepare": prepare}[args.phase](args)


if __name__ == "__main__":
    main()
