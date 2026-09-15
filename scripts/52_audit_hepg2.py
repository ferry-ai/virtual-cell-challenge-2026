"""Audit an acquired single-cell perturbation object before anything uses it.

Written for the Nadig HepG2 mirror, general enough for the RPE1 one. Reads
structure, `obs` and `var` in full (they are small) and samples `X` in blocks.
**It never materialises the dense matrix**: the HepG2 object is ~5.6 GB dense
and the machine has under 8 GB.

The report keeps three things apart, because this repository has been burned by
their collapse:

* `declared`  -- what the file says about itself: names, dtypes, shapes, labels.
* `verified`  -- what this script established by reading values.
* `uncertain` -- what neither the file nor this script settles.

In particular: a file named "raw", a dtype of int, or integral values are each
**declared** evidence of counts. What is verified here is the arithmetic --
non-negative, integral, and consistent with a library-size column when one
exists. Guide counts are not an RNA matrix, and a matrix that fails these checks
does not unlock single-cell evaluation.

    scripts/py.cmd scripts/52_audit_hepg2.py \
        --h5ad C:/Users/ferra/vcc2026-data/raw/nadig_hepg2/NadigOConner2024_hepg2.h5ad \
        --out reports/hepg2_2026-09-14 --source-id nadig_hepg2
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

import h5py
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from vcc2026 import config
from vcc2026.genes import official_axis
from vcc2026.manifest import RunManifest
from vcc2026.pseudobulk import _read_categorical

# Labels that have meant "no gene was targeted" in the perturbation literature.
# Matching is case-insensitive and exact against a level, never a substring:
# "non-targeting" must not swallow a gene called "NT5C2".
NTC_CANDIDATES = (
    "non-targeting", "non_targeting", "nontargeting", "control", "ctrl",
    "ntc", "nt", "safe-harbour", "safe_harbor", "scrambled", "none",
)
# Columns that have carried the perturbed gene. Order is preference order.
PERT_CANDIDATES = (
    "perturbation", "gene", "target_gene", "gene_target", "target",
    "perturbation_name", "guide_target", "knockdown",
)
BATCH_CANDIDATES = ("batch", "donor", "lane", "channel", "sample", "condition",
                    "replicate", "library", "experiment", "timepoint")
GUIDE_CANDIDATES = ("guide_id", "guide", "sgrna", "sgRNA", "protospacer", "grna")


def sha256_and_md5(path: Path, *, block: int = 1 << 22) -> dict:
    """Both digests in one pass. md5 is what Zenodo publishes; sha256 is ours."""
    md5, sha = hashlib.md5(), hashlib.sha256()
    with path.open("rb") as fh:
        while chunk := fh.read(block):
            md5.update(chunk)
            sha.update(chunk)
    return {"md5": md5.hexdigest(), "sha256": sha.hexdigest()}


def matrix_spec(node) -> dict:
    """Shape, dtype and storage of X or a layer, without reading the values."""
    if isinstance(node, h5py.Dataset):
        return {
            "storage": "dense",
            "shape": [int(v) for v in node.shape],
            "dtype": str(node.dtype),
            "chunks": None if node.chunks is None else [int(v) for v in node.chunks],
            "compression": node.compression,
            "nbytes_dense_estimate": int(np.prod(node.shape) * node.dtype.itemsize),
        }
    enc = node.attrs.get("encoding-type", "")
    enc = enc.decode() if isinstance(enc, bytes) else str(enc)
    shape = node.attrs.get("shape")
    return {
        "storage": enc or "group",
        "shape": [int(v) for v in shape] if shape is not None else None,
        "dtype": str(node["data"].dtype) if "data" in node else None,
        "nnz": int(node["data"].shape[0]) if "data" in node else None,
        "indptr_len": int(node["indptr"].shape[0]) if "indptr" in node else None,
        "compression": node["data"].compression if "data" in node else None,
        "nbytes_dense_estimate": (
            int(np.prod(shape) * node["data"].dtype.itemsize)
            if shape is not None and "data" in node else None
        ),
    }


def read_frame(group: h5py.Group) -> tuple[pd.DataFrame, list[dict]]:
    """Read an h5ad dataframe group into pandas, describing each column."""
    columns, described = {}, []
    keys = [k for k in group.keys() if k not in ("__categories",)]
    for key in keys:
        if key.startswith("_index"):
            continue
        try:
            values = _read_categorical(group, key)
        except Exception as error:  # noqa: BLE001 - an unreadable column is a finding
            described.append({"name": key, "readable": False, "why": str(error)[:200]})
            continue
        values = np.asarray(values)
        if values.ndim != 1:
            described.append({"name": key, "readable": False,
                              "why": f"ndim={values.ndim}"})
            continue
        columns[key] = values
        uniq = pd.unique(values)
        described.append({
            "name": key,
            "readable": True,
            "dtype": str(values.dtype),
            "n_unique": int(len(uniq)),
            "example_levels": [str(v) for v in uniq[:8]],
            "n_missing": int(pd.isna(values).sum()) if values.dtype.kind == "f"
            else int((values == "").sum()) if values.dtype.kind in "OSU" else 0,
        })
    return pd.DataFrame(columns), described


def pick_column(frame: pd.DataFrame, candidates) -> list[str]:
    lower = {c.lower(): c for c in frame.columns}
    return [lower[c] for c in candidates if c in lower]


def find_ntc_levels(values: np.ndarray) -> dict:
    levels = {str(v) for v in pd.unique(values)}
    hits = sorted(lv for lv in levels if lv.strip().lower() in NTC_CANDIDATES)
    return {
        "levels_matched": hits,
        "n_cells_matched": int(np.isin(values.astype(str), hits).sum()) if hits else 0,
    }


def sample_blocks(node, n_rows: int, *, n_blocks: int, block: int, seed: int):
    """Yield (start, dense block) for a few random row ranges, dense or CSR."""
    rng = np.random.default_rng(seed)
    starts = sorted(int(s) for s in rng.choice(
        max(1, n_rows - block), size=min(n_blocks, max(1, n_rows // block)),
        replace=False))
    for start in starts:
        stop = min(start + block, n_rows)
        if isinstance(node, h5py.Dataset):
            yield start, np.asarray(node[start:stop, :])
        else:
            indptr = node["indptr"]
            lo, hi = int(indptr[start]), int(indptr[stop])
            data = np.asarray(node["data"][lo:hi])
            indices = np.asarray(node["indices"][lo:hi])
            ptr = np.asarray(indptr[start:stop + 1]) - lo
            n_cols = int(node.attrs["shape"][1])
            out = np.zeros((stop - start, n_cols), dtype=data.dtype)
            for i in range(stop - start):
                out[i, indices[ptr[i]:ptr[i + 1]]] = data[ptr[i]:ptr[i + 1]]
            yield start, out


def check_counts(node, n_rows: int, *, n_blocks: int, block: int, seed: int) -> dict:
    """Are the sampled values non-negative integers, and what are their sizes?"""
    seen = 0
    mins, maxs, libs, frac_zero = [], [], [], []
    integral = True
    negative = False
    for _, chunk in sample_blocks(node, n_rows, n_blocks=n_blocks, block=block,
                                  seed=seed):
        values = chunk.astype(np.float64, copy=False)
        seen += values.shape[0]
        mins.append(float(values.min()))
        maxs.append(float(values.max()))
        libs.extend(values.sum(axis=1).tolist())
        frac_zero.append(float(np.mean(values == 0.0)))
        if np.any(values < 0):
            negative = True
        if not np.all(np.equal(np.mod(values, 1.0), 0.0)):
            integral = False
    libs = np.asarray(libs, dtype=np.float64)
    return {
        "n_cells_sampled": int(seen),
        "min": float(min(mins)) if mins else None,
        "max": float(max(maxs)) if maxs else None,
        "any_negative": bool(negative),
        "all_integral": bool(integral),
        "fraction_zero_mean": float(np.mean(frac_zero)) if frac_zero else None,
        "library_size": {
            "min": float(libs.min()) if libs.size else None,
            "median": float(np.median(libs)) if libs.size else None,
            "max": float(libs.max()) if libs.size else None,
            "n_zero_library_cells": int((libs == 0).sum()),
        },
    }


def panel_targets() -> set[str]:
    csv = config.paths().raw / "controls" / "pert_counts.csv"
    if not csv.exists():
        return set()
    return set(pd.read_csv(csv).target_gene.astype(str))


def local_source_targets(signature_dir: Path) -> dict[str, set[str]]:
    out: dict[str, set[str]] = {}
    for rows in sorted(signature_dir.glob("*.rows.json")):
        payload = json.loads(rows.read_text(encoding="utf-8"))
        out[rows.name.replace(".rows.json", "")] = {
            str(r["target"]) for r in payload
        }
    return out


def local_source_observed(signature_dir: Path) -> dict[str, np.ndarray]:
    out: dict[str, np.ndarray] = {}
    for npz in sorted(signature_dir.glob("*.npz")):
        with np.load(npz) as handle:
            observed = np.asarray(handle["observed"])
        out[npz.stem] = observed.reshape(-1) if observed.ndim == 1 else observed[0]
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--h5ad", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--source-id", default="nadig_hepg2")
    parser.add_argument("--url", default="")
    parser.add_argument("--expect-md5", default="")
    parser.add_argument("--signatures", type=Path, default=None,
                        help="e001 signature directory, for the overlap join")
    parser.add_argument("--blocks", type=int, default=12)
    parser.add_argument("--block-rows", type=int, default=256)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--skip-digest", action="store_true")
    parser.add_argument("--allow-overwrite", action="store_true")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    dest = args.out / f"{args.source_id}_audit.json"
    if dest.exists() and not args.allow_overwrite:
        raise FileExistsError(f"{dest} exists; give a new --out (never overwrite)")

    axis = official_axis()
    axis_symbols = set(axis.symbols) if hasattr(axis, "symbols") else set(axis)
    report: dict = {
        "source_id": args.source_id,
        "path": str(args.h5ad),
        "url": args.url,
        "declared": {},
        "verified": {},
        "uncertain": [],
    }

    stat = args.h5ad.stat()
    report["declared"]["bytes_on_disk"] = int(stat.st_size)
    if not args.skip_digest:
        digests = sha256_and_md5(args.h5ad)
        report["verified"]["digests"] = digests
        if args.expect_md5:
            report["verified"]["md5_matches_publisher"] = (
                digests["md5"] == args.expect_md5.replace("md5:", "")
            )

    with h5py.File(args.h5ad, "r") as handle:
        report["declared"]["root_keys"] = sorted(handle.keys())
        report["declared"]["X"] = matrix_spec(handle["X"])
        report["declared"]["layers"] = {
            key: matrix_spec(handle["layers"][key])
            for key in (handle["layers"].keys() if "layers" in handle else [])
        }
        report["declared"]["has_raw"] = "raw" in handle
        if "raw" in handle and "X" in handle["raw"]:
            report["declared"]["raw_X"] = matrix_spec(handle["raw"]["X"])
        report["declared"]["obsm_keys"] = sorted(handle["obsm"].keys()) if "obsm" in handle else []
        report["declared"]["uns_keys"] = sorted(handle["uns"].keys()) if "uns" in handle else []

        obs, obs_described = read_frame(handle["obs"])
        var, var_described = read_frame(handle["var"])
        report["declared"]["obs_columns"] = obs_described
        report["declared"]["var_columns"] = var_described

        n_rows = int(report["declared"]["X"]["shape"][0])
        n_cols = int(report["declared"]["X"]["shape"][1])

        # ---- genes -------------------------------------------------------
        symbol_col = next(
            (c for c in ("gene_symbol", "symbol", "gene_name", "gene_symbols", "index",
                         "_index", "gene_ids", "ensembl_id")
             if c in var.columns), None)
        if symbol_col is None:
            raw_index = handle["var"]["_index"].asstr()[:] if "_index" in handle["var"] else None
            symbols = np.asarray(raw_index, dtype=str) if raw_index is not None else np.array([])
            symbol_source = "var/_index"
        else:
            symbols = np.asarray(var[symbol_col], dtype=str)
            symbol_source = f"var/{symbol_col}"
        duplicates = {k: int(v) for k, v in Counter(symbols.tolist()).items() if v > 1}
        on_axis = np.isin(symbols, list(axis_symbols))
        report["verified"]["genes"] = {
            "n_features": int(n_cols),
            "symbol_source": symbol_source,
            "n_unique_symbols": int(len(set(symbols.tolist()))),
            "n_duplicate_symbols": len(duplicates),
            "duplicate_examples": dict(list(duplicates.items())[:10]),
            "n_on_official_axis": int(on_axis.sum()),
            "n_official_axis": len(axis_symbols),
        }

        # ---- perturbation labels ----------------------------------------
        pert_cols = pick_column(obs, PERT_CANDIDATES)
        report["verified"]["perturbation_column_candidates"] = pert_cols
        if not pert_cols:
            report["uncertain"].append(
                "No obs column matched the known perturbation-label names; the "
                "targets could not be read and nothing downstream may assume them."
            )
            pert_col = None
            labels = np.array([], dtype=str)
        else:
            pert_col = pert_cols[0]
            labels = np.asarray(obs[pert_col], dtype=str)
        report["verified"]["perturbation_column_used"] = pert_col

        ntc = find_ntc_levels(labels) if labels.size else {"levels_matched": [],
                                                           "n_cells_matched": 0}
        report["verified"]["ntc"] = ntc
        is_ntc = np.isin(labels, ntc["levels_matched"]) if labels.size else np.zeros(0, bool)

        per_target = Counter(labels[~is_ntc].tolist()) if labels.size else Counter()
        cells = np.array(sorted(per_target.values()), dtype=np.int64)
        report["verified"]["targets"] = {
            "n_targeting_levels": len(per_target),
            "n_cells_targeting": int((~is_ntc).sum()) if labels.size else 0,
            "n_cells_ntc": int(is_ntc.sum()) if labels.size else 0,
            "cells_per_target": {
                "min": int(cells.min()) if cells.size else None,
                "median": float(np.median(cells)) if cells.size else None,
                "max": int(cells.max()) if cells.size else None,
            },
            "n_targets_ge_10_cells": int((cells >= 10).sum()),
            "n_targets_ge_30_cells": int((cells >= 30).sum()),
            "n_targets_ge_50_cells": int((cells >= 50).sum()),
        }

        # ---- batch / donor / guide --------------------------------------
        batch_cols = pick_column(obs, BATCH_CANDIDATES)
        guide_cols = pick_column(obs, GUIDE_CANDIDATES)
        report["verified"]["batch_like_columns"] = {
            col: int(obs[col].nunique()) for col in batch_cols
        }
        report["verified"]["guide_like_columns"] = {
            col: int(obs[col].nunique()) for col in guide_cols
        }
        if batch_cols and labels.size:
            first = batch_cols[0]
            table = pd.crosstab(labels, np.asarray(obs[first], dtype=str))
            report["verified"]["ntc_available_per_batch"] = {
                str(level): int(table.loc[table.index.isin(ntc["levels_matched"]),
                                          level].sum())
                for level in table.columns
            }
            report["verified"]["batch_column_used_for_pairing"] = first
        else:
            report["verified"]["batch_column_used_for_pairing"] = None

        # ---- values ------------------------------------------------------
        report["verified"]["counts_sampled"] = check_counts(
            handle["X"], n_rows, n_blocks=args.blocks, block=args.block_rows,
            seed=args.seed,
        )
        lib_col = next((c for c in ("ncounts", "n_counts", "total_counts", "nCount_RNA")
                        if c in obs.columns), None)
        if lib_col is not None:
            declared_lib = np.asarray(obs[lib_col], dtype=np.float64)
            report["verified"]["declared_library_column"] = {
                "name": lib_col,
                "median": float(np.median(declared_lib)),
                "min": float(declared_lib.min()),
                "max": float(declared_lib.max()),
            }

    # ---- overlaps with what we already have ------------------------------
    sig_dir = args.signatures or (config.paths().data_root / "artifacts" / "e001" / "signatures")
    overlaps: dict = {"signature_dir": str(sig_dir)}
    observed_here = set(np.asarray(symbols)[on_axis].tolist()) if symbols.size else set()
    if sig_dir.exists():
        targets_by_source = local_source_targets(sig_dir)
        observed_by_source = local_source_observed(sig_dir)
        here = set(per_target.keys())
        for sid, other in sorted(targets_by_source.items()):
            overlaps[f"targets_shared_with_{sid}"] = len(here & other)
        axis_list = np.asarray(list(axis.symbols) if hasattr(axis, "symbols") else list(axis))
        for sid, mask in sorted(observed_by_source.items()):
            other_genes = set(axis_list[mask].tolist())
            overlaps[f"axis_genes_shared_with_{sid}"] = len(observed_here & other_genes)
        if targets_by_source:
            common = set.intersection(*targets_by_source.values()) if len(targets_by_source) > 1 \
                else next(iter(targets_by_source.values()))
            overlaps["targets_shared_with_all_local_sources"] = len(here & common)
        if observed_by_source:
            masks = list(observed_by_source.values())
            all_mask = np.logical_and.reduce(masks)
            overlaps["axis_genes_shared_with_all_local_sources"] = len(
                observed_here & set(axis_list[all_mask].tolist())
            )
    panel = panel_targets()
    overlaps["panel_targets_total"] = len(panel)
    overlaps["panel_targets_observed_here"] = len(panel & set(per_target.keys()))
    report["verified"]["overlaps"] = overlaps

    # ---- what stays open --------------------------------------------------
    counts = report["verified"]["counts_sampled"]
    usable = bool(counts["all_integral"] and not counts["any_negative"]
                  and report["verified"]["ntc"]["n_cells_matched"] > 0)
    report["verified"]["counts_look_like_raw_rna_counts"] = usable
    report["uncertain"].extend([
        "Integrality and non-negativity were checked on sampled blocks, not on "
        f"all {report['declared']['X']['shape'][0]} cells.",
        "Whether the object is the same processing as the GEO original is not "
        "established here: a mirror is a copy of an experiment, not an "
        "independent one, and its obs schema may be harmonised.",
        "Panel coverage of 0/300 would mean this bundle tests transfer between "
        "contexts, not coverage of the VCC targets.",
    ])
    if report["verified"]["batch_column_used_for_pairing"] is None:
        report["uncertain"].append(
            "No batch-like column was recognised: NTCs can only be pooled across "
            "the whole object, and a batch effect cannot be separated from the "
            "perturbation effect."
        )

    dest.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")

    manifest = RunManifest(
        run_id=args.out.name, stage="52_audit_hepg2",
        config={k: str(v) for k, v in vars(args).items()},
    )
    manifest.add_input("h5ad", args.h5ad)
    manifest.add_output("audit", dest)
    manifest.metrics = {
        "n_cells": report["declared"]["X"]["shape"][0],
        "n_features": report["declared"]["X"]["shape"][1],
        "n_targeting_levels": report["verified"]["targets"]["n_targeting_levels"],
        "n_cells_ntc": report["verified"]["targets"]["n_cells_ntc"],
        "counts_look_like_raw_rna_counts": usable,
        "panel_targets_observed_here": overlaps["panel_targets_observed_here"],
    }
    manifest.note("Sampled blocks, never the dense matrix.")
    manifest.note("A file named raw is a declaration; the arithmetic is the check.")
    manifest.write(args.out / f"manifest_52_audit_{args.source_id}.json",
                   allow_overwrite=args.allow_overwrite)
    print(json.dumps(manifest.metrics, indent=2))
    print(f"-> {dest}")


if __name__ == "__main__":
    main()
