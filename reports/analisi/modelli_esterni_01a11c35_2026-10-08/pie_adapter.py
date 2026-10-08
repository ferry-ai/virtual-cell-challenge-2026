"""Strict PIE parquet boundary; no network, model loading, scoring or calibration.

Native PIE columns remain distinct. Export requires an independently reviewed
normalization bridge and complete exposure ledger. Missing support falls back
to the supplied final-scale baseline, without applying gain, centering or cis.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def unique(values, name):
    values = list(values)
    if not values or any(not isinstance(x, str) or not x for x in values):
        raise ValueError(f"{name}: nonempty string identifiers required")
    if len(values) != len(set(values)):
        raise ValueError(f"{name}: duplicate identifiers")
    return values


def read_pie(path):
    """Read upstream format v1, preserving dataset-local axes and all three heads."""
    import pyarrow.parquet as pq
    table = pq.read_table(path)
    metadata = (table.schema.metadata or {}).get(b"pie")
    if metadata is None:
        raise ValueError("missing PIE schema metadata")
    metadata = json.loads(metadata)
    if metadata.get("format_version") != 1:
        raise ValueError("unsupported PIE parquet version")
    axes = {name: unique(genes, f"genes[{name}]")
            for name, genes in metadata["genes"].items()}
    required = {"dataset", "context", "perturbation", "p_de", "lfc_pred", "delta_p_pred"}
    if not required <= set(table.column_names):
        raise ValueError("missing PIE prediction columns")
    rows, seen = [], set()
    for row in table.to_pylist():
        key = tuple(row[k] for k in ("dataset", "context", "perturbation"))
        if any(not isinstance(x, str) or not x for x in key) or key in seen:
            raise ValueError("invalid or duplicate prediction key")
        seen.add(key)
        if key[0] not in axes:
            raise ValueError("dataset missing from gene metadata")
        n = len(axes[key[0]])
        for name in ("p_de", "lfc_pred", "delta_p_pred"):
            value = np.asarray(row[name], dtype=np.float64)
            if value.shape != (n,) or not np.isfinite(value).all():
                raise ValueError(f"{name}: wrong shape or nonfinite values")
            if name == "p_de" and np.any((value < 0) | (value > 1)):
                raise ValueError("p_de outside [0, 1]")
            row[name] = value
        rows.append(row)
    if not rows:
        raise ValueError("empty predictions")
    return axes, rows


def check_exposure(ledger, requests, regime):
    """Audit all label use, including validation/model selection, not just training.

Canonical context groups and target components must be reconciled by VALIDAZIONE.
Knowledge-only exposure is reported separately; this function cannot establish
the truth or completeness of an upstream provenance declaration.
"""
    if regime not in {"C", "J", "production"}:
        raise ValueError("regime must be C, J or production")
    if ledger.get("status") != "reviewed" or not ledger.get("review_id"):
        raise ValueError("exposure review required")
    if ledger.get("complete_label_inventory") is not True:
        raise ValueError("incomplete pretrained exposure inventory")
    for field in ("label_context_groups", "label_target_components", "knowledge_sources"):
        if not isinstance(ledger.get(field), list):
            raise ValueError(f"missing exposure field: {field}")
    contexts = set(ledger["label_context_groups"])
    targets = set(ledger["label_target_components"])
    for row in requests:
        if not row.get("context_group") or not row.get("target_components"):
            raise ValueError("canonical context and target components required")
        if row.get("protected", False):
            raise ValueError("protected evaluation rows are forbidden")
        if regime in {"C", "J"} and row["context_group"] in contexts:
            raise ValueError("held-out context exposed to checkpoint or derivatives")
        components = set(row["target_components"])
        if regime == "J" and components & targets:
            raise ValueError("J target exposed to checkpoint or derivatives")
        if regime == "C" and not components <= targets:
            raise ValueError("C target not evidenced as seen")


def validate_contract(contract, requests):
    if contract.get("schema_version") != 1:
        raise ValueError("unsupported contract")
    for key in ("release_sha256", "protocol_sha256", "checkpoint_sha256",
                "predictions_sha256", "baseline_sha256"):
        value = contract.get(key, "")
        if len(value) != 64 or any(x not in "0123456789abcdef" for x in value):
            raise ValueError(f"pinned {key} required")
    revision = contract.get("code_revision", "")
    if len(revision) != 40 or any(x not in "0123456789abcdef" for x in revision):
        raise ValueError("immutable code revision required")
    if not contract.get("assets") or not contract.get("license_review"):
        raise ValueError("asset and license provenance required")
    for asset in contract["assets"]:
        if not asset.get("revision") or not asset.get("sha256") or not asset.get("role"):
            raise ValueError("incomplete asset provenance")
    bridge = contract.get("normalization_bridge", {})
    if bridge.get("status") != "verified" or not bridge.get("evidence_sha256"):
        raise ValueError("normalization equivalence is not established by log conversion")
    if bridge.get("source_quantity") != "log2_fold_change" or bridge.get("destination_quantity") != "ln_fold_change":
        raise ValueError("only a reviewed LFC bridge is supported")
    for key in ("source_normalization", "destination_normalization", "pseudocount_policy",
                "denominator_gene_axis_sha256", "review_id"):
        if not bridge.get(key):
            raise ValueError(f"bridge missing {key}")
    if contract.get("baseline_stage") != "final_effect_before_emitter":
        raise ValueError("baseline must already include its final gain/centering/cis")
    if contract.get("postprocess") != {"gain": 1.0, "center": False, "cis": False}:
        raise ValueError("duplicate gain, centering or cis correction forbidden")
    check_exposure(contract["exposure"], requests, contract["regime"])


def adapt(axes, rows, requests, genes, baseline, baseline_mask, contract):
    """Return final-scale effects, support mask and untouched native diagnostics.

    Axes: requests x response genes. Absent external genes/rows use baseline.
    A supported external zero is a valid replacement, not a missing value.
    """
    genes = unique(genes, "output genes")
    keys = [(r["dataset"], r["context"], r["perturbation"]) for r in requests]
    if not keys or len(keys) != len(set(keys)):
        raise ValueError("empty or duplicate requested rows")
    validate_contract(contract, requests)
    baseline = np.asarray(baseline)
    baseline_mask = np.asarray(baseline_mask)
    shape = (len(requests), len(genes))
    if baseline.dtype not in (np.dtype("float32"), np.dtype("float64")):
        raise ValueError("baseline must be floating point")
    if baseline.shape != shape or baseline_mask.shape != shape or baseline_mask.dtype != bool:
        raise ValueError("baseline axes or mask mismatch")
    if not np.isfinite(baseline[baseline_mask]).all():
        raise ValueError("nonfinite observed baseline")
    for dataset, axis in axes.items():
        unique(axis, f"genes[{dataset}]")
    lookup = {}
    for row in rows:
        key = (row["dataset"], row["context"], row["perturbation"])
        if key in lookup:
            raise ValueError("duplicate external row")
        lookup[key] = row
    result = baseline.copy()
    mask = baseline_mask.copy()
    external = np.zeros(shape, dtype=bool)
    native = {name: np.full(shape, np.nan) for name in ("p_de", "lfc_pred", "delta_p_pred")}
    out_index = {g: j for j, g in enumerate(genes)}
    for i, key in enumerate(keys):
        row = lookup.get(key)
        if row is None:
            continue
        axis = axes[key[0]]
        for name in native:
            values = np.asarray(row[name], dtype=np.float64)
            if values.shape != (len(axis),) or not np.isfinite(values).all():
                raise ValueError(f"invalid {name}")
            if name == "p_de" and np.any((values < 0) | (values > 1)):
                raise ValueError("invalid probability")
        for j, gene in enumerate(axis):
            k = out_index.get(gene)
            if k is None:
                continue
            for name in native:
                native[name][i, k] = row[name][j]
            result[i, k] = row["lfc_pred"][j] * np.log(2.0)
            external[i, k] = mask[i, k] = True
    return {"effects": result, "mask": mask, "external_mask": external, **native}


def export(predictions, baseline_path, contract_path, out):
    """Write a new immutable directory, checksummed and readable without pickle."""
    contract = json.loads(Path(contract_path).read_text(encoding="utf-8"))
    for path, field in ((predictions, "predictions_sha256"), (baseline_path, "baseline_sha256")):
        if sha256(path) != contract[field]:
            raise ValueError(f"{field}: actual input differs from frozen contract")
    axes, rows = read_pie(predictions)
    with np.load(baseline_path, allow_pickle=False) as base:
        genes = base["genes"].tolist()
        if genes != contract["genes"]:
            raise ValueError("baseline gene axis differs from contract")
        for name in ("dataset", "context", "perturbation"):
            if base[name].tolist() != [r[name] for r in contract["requests"]]:
                raise ValueError(f"baseline {name} ordering differs from requests")
        values = adapt(axes, rows, contract["requests"], genes,
                       base["effects"], base["mask"], contract)
    out = Path(out)
    out.mkdir(parents=True, exist_ok=False)
    payload = out / "effects.npz"
    np.savez_compressed(payload, **values, genes=np.asarray(genes),
                        **{name: np.asarray([r[name] for r in contract["requests"]])
                           for name in ("dataset", "context", "perturbation")})
    manifest = {"schema_version": 1, "quantity": "ln_fold_change", "contract": contract,
                "contract_sha256": sha256(contract_path), "adapter_sha256": sha256(__file__),
                "output_sha256": sha256(payload), "shape": list(values["effects"].shape),
                "external_cells": int(values["external_mask"].sum()),
                "fallback_cells": int((~values["external_mask"] & values["mask"]).sum()),
                "unobserved_cells": int((~values["mask"]).sum()),
                "scientific_benefit": "not_evaluated"}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for flag in ("predictions", "baseline", "contract", "out"):
        parser.add_argument(f"--{flag}", required=True, type=Path)
    args = parser.parse_args()
    print(json.dumps(export(args.predictions, args.baseline, args.contract, args.out), indent=2))
