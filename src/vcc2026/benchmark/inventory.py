"""Machine-readable inventory of what is actually on disk.

A registry row is a claim. This module opens the files that exist, reads the
cheap metadata (obs, var, sizes) and writes a matrix of context × target ×
cells, with gene support and matrix kind. Candidates that were never acquired
stay candidates. An unmeasured gene is not an unchanged gene.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import h5py
import numpy as np

from vcc2026 import config
from vcc2026.genes import official_axis
from vcc2026.pseudobulk import NTC_SYMBOL, PseudobulkFile, _read_categorical, parse_gene_transcript
from vcc2026.registry import load_registry

__all__ = ["build_inventory", "classify_matrix"]

_DONOR_KEYS = ("donor", "donor_id", "Donor", "donor_number")
_BATCH_KEYS = ("batch", "batch_id", "Batch", "gem_group", "channel")


def classify_matrix(source) -> str:
    """One of: pseudobulk_mean, single_cell_counts, metadata_only, not_acquired, sample_only."""
    schema = (source.count_schema or "").lower()
    status = (source.ingestion_status or "").lower()
    path = source.local_path
    root = config.paths().data_root
    full = (root / path) if path else None
    exists = bool(full and (full.exists() or (full.is_dir() and any(full.iterdir()))))

    if "metadata only" in status or (schema.startswith("locally only") and not exists):
        return "metadata_only"
    if not exists:
        return "not_acquired"
    if "64-cell" in status or "pilot" in status:
        return "sample_only"
    if "per-cell mean" in schema or "per cell mean" in schema:
        return "pseudobulk_mean"
    if "integer counts" in schema or "csr" in schema:
        return "single_cell_counts"
    if path and str(path).endswith(".h5ad") and exists:
        return "h5ad_unclassified"
    if path and full and full.is_dir():
        return "directory"
    return "not_acquired"


def _obs_keys(path: Path) -> list[str]:
    with h5py.File(path, "r") as f:
        if "obs" not in f:
            return []
        obs = f["obs"]
        keys = [k for k in obs.keys() if k != "__categories"]
        return sorted(keys)


def _var_symbols(path: Path) -> np.ndarray:
    with h5py.File(path, "r") as f:
        if "var" not in f:
            return np.array([], dtype=str)
        var = f["var"]
        for key in ("gene_name", "gene_symbols", "symbol", "index"):
            if key in var:
                try:
                    return np.asarray(_read_categorical(var, key), dtype=str)
                except Exception:
                    continue
        # Some files store the index as _index.
        if "_index" in var:
            node = var["_index"]
            if hasattr(node, "asstr"):
                return np.asarray(node.asstr()[:], dtype=str)
            return np.asarray(node[:], dtype=str)
        return np.array([], dtype=str)


def _align_count(symbols, axis) -> dict:
    pos = axis.position()
    on = sum(1 for s in symbols if s in pos)
    return {
        "n_source_symbols": int(len(symbols)),
        "n_unique_source_symbols": int(len(set(map(str, symbols)))),
        "n_on_official_axis": int(on),
        "n_official": len(axis),
        "n_official_unmeasured": int(len(axis) - on),
        "note": (
            "Official-axis genes absent from this source are unmeasured, "
            "not unchanged."
        ),
    }


def _describe_pseudobulk(source, path: Path, axis) -> dict:
    pf = PseudobulkFile(path=path, source_id=source.id, context=source.cell_context or source.id)
    describe = pf.describe()
    census = pf.target_census()
    symbols = _var_symbols(path)
    ncf_ok = True
    try:
        with h5py.File(path, "r") as f:
            ncf = f["obs/num_cells_filtered"][:].astype(np.float64)
            labels = _read_categorical(f["obs"], "gene_transcript")
            symbol, _, _ = parse_gene_transcript(labels)
            is_ntc = symbol == NTC_SYMBOL
            cells_pert = {}
            cells_ntc = float(np.nansum(ncf[is_ntc]))
            for s, n in zip(symbol, ncf):
                if s == "" or s == NTC_SYMBOL or not np.isfinite(n) or n <= 0:
                    continue
                cells_pert[str(s)] = cells_pert.get(str(s), 0.0) + float(n)
    except Exception as exc:
        ncf_ok = False
        cells_pert, cells_ntc = {}, None
        describe["cell_count_error"] = f"{type(exc).__name__}: {exc}"

    return {
        "describe": describe,
        "n_perturbed_targets": len(census),
        "n_perturbed_rows": int(sum(census.values())),
        "median_rows_per_target": (
            float(np.median(list(census.values()))) if census else None
        ),
        "n_control_cells_effective": cells_ntc if ncf_ok else None,
        "median_cells_per_target": (
            float(np.median(list(cells_pert.values()))) if cells_pert else None
        ),
        "gene_axis": _align_count(symbols, axis),
        "obs_keys": _obs_keys(path),
        "donor_columns_present": [k for k in _obs_keys(path) if k in _DONOR_KEYS],
        "batch_columns_present": [k for k in _obs_keys(path) if k in _BATCH_KEYS],
        "targets": sorted(census),
    }


def _describe_h5ad_generic(path: Path, axis) -> dict:
    with h5py.File(path, "r") as f:
        shape = tuple(int(x) for x in f["X"].shape) if "X" in f else None
        n_obs = int(f["X"].shape[0]) if shape else None
        n_var = int(f["X"].shape[1]) if shape else None
        obs_keys = _obs_keys(path)
    symbols = _var_symbols(path)
    return {
        "shape": shape,
        "n_obs": n_obs,
        "n_var": n_var,
        "obs_keys": obs_keys,
        "gene_axis": _align_count(symbols, axis) if len(symbols) else None,
        "donor_columns_present": [k for k in obs_keys if k in _DONOR_KEYS],
        "batch_columns_present": [k for k in obs_keys if k in _BATCH_KEYS],
    }


def _file_stat(path: Path | None) -> dict:
    if path is None:
        return {"exists": False}
    if path.is_dir():
        files = [p for p in path.rglob("*") if p.is_file()]
        return {
            "exists": True,
            "is_dir": True,
            "path": str(path),
            "n_files": len(files),
            "bytes": int(sum(p.stat().st_size for p in files)),
        }
    if not path.exists():
        return {"exists": False, "path": str(path)}
    st = path.stat()
    return {
        "exists": True,
        "is_dir": False,
        "path": str(path),
        "bytes": int(st.st_size),
        "mtime_utc": datetime.fromtimestamp(st.st_mtime, tz=timezone.utc).isoformat(),
    }


def _overlap_table(per_source_targets: dict[str, set[str]], per_source_genes: dict[str, set[str]]) -> dict:
    ids = sorted(set(per_source_targets) | set(per_source_genes))
    targets = {}
    genes = {}
    for a in ids:
        for b in ids:
            ta, tb = per_source_targets.get(a, set()), per_source_targets.get(b, set())
            ga, gb = per_source_genes.get(a, set()), per_source_genes.get(b, set())
            targets[f"{a}∩{b}"] = len(ta & tb)
            genes[f"{a}∩{b}"] = len(ga & gb)
    return {"n_shared_targets": targets, "n_shared_genes_on_axis": genes}


def _executable_experiments(rows: list[dict], overlaps: dict) -> list[dict]:
    perturbed = [
        r for r in rows
        if r["matrix_kind"] == "pseudobulk_mean" and r["file"]["exists"]
        and r["n_perturbed_targets"]
    ]
    contexts = sorted({r["context"] for r in perturbed})
    single_cell_perturbed = [
        r for r in rows
        if r["matrix_kind"] == "single_cell_counts"
        and r.get("modality") not in {None, "observational"}
        and r["file"]["exists"]
        and r["ingestion_status"] not in {"not_started", "blocked", "metadata only"}
    ]
    # Official controls are observational.
    ntc_only = [
        r for r in rows
        if r["id"] == "vcc_controls" and r["file"]["exists"]
    ]

    experiments = []
    if len(contexts) >= 2:
        experiments.append({
            "id": "pseudobulk_mean_response_transfer",
            "status": "executable",
            "contexts": contexts,
            "n_perturbed_contexts": len(contexts),
            "metric_space": "pseudobulk log2FC proxy",
            "limitation": (
                f"Only {len(contexts)} perturbed context(s) are local. A test "
                "that holds one out leaves a single training context and is "
                "not a general demonstration of learning context dependence."
            ),
            "shared_targets_key_pairs": {
                k: v for k, v in overlaps["n_shared_targets"].items()
                if "∩" in k and k.split("∩")[0] != k.split("∩")[1]
            },
        })
    else:
        experiments.append({
            "id": "pseudobulk_mean_response_transfer",
            "status": "blocked",
            "reason": "fewer than two local perturbed contexts",
        })

    experiments.append({
        "id": "new_context_seen_target",
        "status": "executable" if len(contexts) >= 2 else "blocked",
        "requires": "shared targets between a train context and a held-out context",
        "limitation": "with two contexts this is 1-vs-1 transfer",
    })
    experiments.append({
        "id": "new_context_unseen_target",
        "status": "executable" if len(contexts) >= 2 else "blocked",
        "requires": (
            "the same shared-target pool, with a seed-controlled subset "
            "excluded from all training responses"
        ),
    })
    experiments.append({
        "id": "generator_x_predictor_six_vcc_metrics",
        "status": "blocked",
        "reason": "no local real perturbed single-cell counts with paired NTCs",
        "n_local_perturbed_single_cell_sources": len(single_cell_perturbed),
        "ntc_contexts_available": [r["id"] for r in ntc_only],
        "do_not": (
            "Do not replace the real reference with synthetic cells. "
            "Do not interpret a generator improvement as evidence about "
            "the predictor or about modularity."
        ),
    })
    return experiments


def build_inventory(*, include_target_lists: bool = True) -> dict:
    """Scan the registry against the disk. Does not download anything."""
    registry = load_registry()
    root = config.paths().data_root
    axis = official_axis()
    rows = []
    per_targets: dict[str, set[str]] = {}
    per_genes: dict[str, set[str]] = {}

    for source in registry:
        rel = source.local_path
        path = (root / rel) if rel else None
        kind = classify_matrix(source)
        file_info = _file_stat(path)
        row = {
            "id": source.id,
            "title": source.title,
            "context": source.cell_context,
            "cell_state": source.cell_state,
            "modality": source.modality,
            "assay": source.assay,
            "verification": source.verification.label,
            "ingestion_status": source.ingestion_status,
            "enabled": source.enabled,
            "role": source.role,
            "limits": list(source.limits),
            "matrix_kind": kind,
            "count_schema": source.count_schema,
            "ntc_rule": source.ntc_rule,
            "guide_ids": source.guide_ids,
            "coverage_registry": source.coverage.as_dict(),
            "bytes_declared": source.bytes_total,
            "file": file_info,
            "n_perturbed_targets": None,
            "donor_columns_present": [],
            "batch_columns_present": [],
        }
        if kind == "pseudobulk_mean" and file_info.get("exists") and path and path.is_file():
            extra = _describe_pseudobulk(source, path, axis)
            targets = extra.pop("targets")
            row.update(extra)
            per_targets[source.id] = set(targets)
            # Genes on the official axis this source measures.
            symbols = _var_symbols(path)
            pos = axis.position()
            per_genes[source.id] = {s for s in map(str, symbols) if s in pos}
            if not include_target_lists:
                row["n_perturbed_targets"] = len(targets)
            else:
                row["perturbed_targets"] = targets
        elif file_info.get("exists") and path and path.suffix == ".h5ad":
            try:
                row["h5ad"] = _describe_h5ad_generic(path, axis)
            except Exception as exc:
                row["h5ad_error"] = f"{type(exc).__name__}: {exc}"
        elif file_info.get("exists") and path and path.is_dir():
            names = sorted(p.name for p in path.iterdir())
            row["directory_entries"] = names[:50]
        # The CD4 64-cell ingestion test lives in the repo, not under data_root.
        if source.id == "cd4_marson":
            repo_pilot = (
                Path(__file__).resolve().parents[3]
                / "reports" / "candidate_verification" / "pilot" / "cd4_D1_Rest_64.h5ad"
            )
            if repo_pilot.exists():
                row["sample_only_path"] = str(repo_pilot)
                row["sample_only_bytes"] = int(repo_pilot.stat().st_size)
                row["sample_only_note"] = (
                    "64-cell ingestion test, not a training matrix. "
                    "Not enough to identify a modular advantage."
                )
        rows.append(row)

    overlaps = _overlap_table(per_targets, per_genes)
    experiments = _executable_experiments(rows, overlaps)

    # Panel overlap with the 300 competition targets, where we have a list.
    panel_path = config.paths().raw / "controls" / "pert_counts.csv"
    panel = []
    if panel_path.exists():
        import pandas as pd

        panel = sorted(pd.read_csv(panel_path).target_gene.astype(str).unique())
    panel_overlap = {}
    for sid, tset in per_targets.items():
        panel_overlap[sid] = {
            "n_panel": len(panel),
            "n_source_targets": len(tset),
            "n_panel_in_source": len(tset & set(panel)),
            "note": (
                "Panel overlap is not the same as a usable effect estimate. "
                "RPE1 essential is a transfer benchmark, not panel supervision."
            ),
        }

    return {
        "built_utc": datetime.now(timezone.utc).isoformat(),
        "data_root": str(root),
        "registry_version": registry.version,
        "n_official_genes": len(axis),
        "n_panel_targets": len(panel),
        "sources": rows,
        "overlaps": overlaps,
        "panel_overlap": panel_overlap,
        "executable_experiments": experiments,
        "unmeasured_vs_unchanged": (
            "A gene absent from a source's var is unmeasured. Treating it as "
            "log2FC = 0 invents evidence in the direction of no effect (D-009)."
        ),
        # A perturbed context is one whose file is on disk and whose cells were
        # perturbed -- not one whose file happens to be pseudobulk. The two were
        # the same thing while every perturbed source was a Replogle-style
        # pseudobulk, and stopped being the same when a single-cell perturbation
        # source arrived: HepG2 was on disk, enabled, and absent from this list.
        "perturbed_contexts_local": sorted(
            {r["context"] for r in rows
             if r["matrix_kind"] in ("pseudobulk_mean", "single_cell_counts")
             and r["file"]["exists"]
             and (r.get("cell_state") or "") != "unperturbed"}
        ),
        "perturbed_contexts_local_rule": (
            "on disk, perturbed cells, any matrix kind; the unperturbed official "
            "controls are excluded by cell_state"
        ),
    }


def write_inventory(path: Path, inventory: dict) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(inventory, indent=2, default=str), encoding="utf-8")
    tmp.replace(path)
    return path
