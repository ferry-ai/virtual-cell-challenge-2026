"""Complete KOLF/CD4 acquisition adapters. Local development uses tiny fixtures only.

The corpus adapter remains unchanged. These generators use its contract tuple
(name, X, obs, var, uns), but stage CSC entries compactly and filter CD4 before
reading counts. Source identity/byte verification and publication belong to the job runner.
"""
from __future__ import annotations

import importlib.util
import json
import re
import shutil
import sys
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlsplit

import h5py
import numpy as np
import pandas as pd
import scipy.sparse as sp

HERE = Path(__file__).resolve().parent
CORPUS = HERE.parent.parent / "corpus_cellulare_2026-09-30"
sys.path.insert(0, str(CORPUS))
_spec = importlib.util.spec_from_file_location("_complete_ingestion_base", CORPUS / "adapters.py")
base = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(base)
MISSING = base.MISSING


def column(group, name, start=None, stop=None, required=False):
    """Slice modern/legacy categorical, nullable and plain AnnData columns as text."""
    if name is None or name not in group:
        if required:
            raise ValueError(f"missing required column {name}")
        return None
    node, sl = group[name], slice(start, stop)
    legacy = group.get("__categories")
    categorical = isinstance(node, h5py.Group) and "categories" in node
    if categorical or (legacy is not None and name in legacy):
        cats = base._h5_text((node["categories"] if categorical else legacy[name])[:])
        codes = (node["codes"] if categorical else node)[sl].astype(np.int64)
        if np.any((codes < -1) | (codes >= len(cats))):
            raise ValueError(f"invalid categorical code in {name}")
        out = np.full(len(codes), MISSING, dtype=object)
        out[codes >= 0] = cats[codes[codes >= 0]]
        return out
    if isinstance(node, h5py.Group):
        vals = base._h5_text(node["values"][sl])
        mask = node["mask"][sl] if "mask" in node else np.zeros(len(vals), bool)
        return np.where(mask, MISSING, vals)
    return base._h5_text(node[sl])


def index_name(group):
    value = group.attrs.get("_index", "_index")
    return value.decode() if isinstance(value, bytes) else str(value)


def bounds(n, cell_range=None, max_cells=None):
    lo, hi = (0, n) if cell_range is None else cell_range
    if not isinstance(lo, (int, np.integer)) or not isinstance(hi, (int, np.integer)):
        raise ValueError("cell_range endpoints must be integers")
    if not 0 <= lo <= hi <= n:
        raise ValueError(f"invalid cell_range {lo, hi} for {n} rows")
    if max_cells is not None:
        if not isinstance(max_cells, (int, np.integer)) or max_cells < 0:
            raise ValueError("max_cells must be a non-negative integer")
        hi = min(hi, lo + max_cells)
    return int(lo), int(hi)


def axis_frame(group, axis_csv, var_symbol_col=None, feature_id_col=None):
    symbols = column(group, var_symbol_col or index_name(group), required=True)
    ids = column(group, feature_id_col) if feature_id_col else None
    idx, kind = base._official(symbols, axis_csv)
    return pd.DataFrame({"feature_id": symbols if ids is None else ids, "symbol": symbols,
                         "feature_type": "Gene Expression", "measured": True,
                         "official_index": idx, "mapping": kind}, index=[f"f{i}" for i in range(len(symbols))])


def compact_dtype(max_index):
    if max_index <= np.iinfo(np.uint16).max:
        return np.dtype("uint16")
    if max_index <= np.iinfo(np.uint32).max:
        return np.dtype("uint32")
    return np.dtype("uint64")


def value_dtype(values):
    """Choose uint16 only after an exact check; float32 fallback must also be lossless."""
    if np.any(~np.isfinite(values)) or np.any(values < 0):
        raise ValueError("counts contain negative or non-finite values")
    if np.all(values <= 65535) and np.all(values == np.floor(values)):
        return np.dtype("uint16")
    with np.errstate(over="ignore", invalid="ignore"):
        converted = values.astype(np.float32)
    if not np.array_equal(converted.astype(values.dtype), values):
        raise ValueError("values cannot be stored losslessly as float32")
    return np.dtype("float32")


def plan_passes(n_cells, nnz, lo, hi, block, free_bytes, min_free_bytes, record_bytes,
                cells_per_pass=None, disk_fraction=0.75):
    """Estimate by average nnz/cell using measured free space and worst-case record size.

    Partial ranges may be denser than average: every write is also checked against
    actual free space. The estimate is not a claim of uniform density or a disk guarantee.
    """
    if block <= 0 or not 0 < disk_fraction <= 1 or min_free_bytes < 0:
        raise ValueError("invalid block, disk fraction or reserve")
    budget = max(0, int((free_bytes - min_free_bytes) * disk_fraction))
    if budget <= 0 and hi > lo:
        raise OSError("no disk budget remains after the measured free-space reserve")
    density = nnz / max(n_cells, 1)
    estimated = max(1, int(budget / max(density * record_bytes, 1)))
    chosen = min(max(hi - lo, 1), estimated)
    if cells_per_pass is not None:
        if not isinstance(cells_per_pass, (int, np.integer)) or cells_per_pass <= 0:
            raise ValueError("cells_per_pass must be a positive integer or None")
        chosen = min(chosen, int(cells_per_pass))
    if chosen >= block:
        chosen = max(block, chosen // block * block)
    if estimated >= hi - lo and (cells_per_pass is None or cells_per_pass >= hi - lo):
        chosen = max(1, hi - lo)
    return {"free_bytes_measured": int(free_bytes), "reserve_bytes": int(min_free_bytes),
            "disk_fraction": disk_fraction, "bucket_budget_bytes": budget,
            "nnz_per_cell_average": density, "worst_record_bytes": int(record_bytes),
            "cells_per_pass": chosen, "cell_range": [lo, hi],
            "density_assumption": "source mean; each write separately checks actual free bytes"}


def h5csc(path, study=None, context=None, chemistry=None, modality=None, axis_csv=None, work=None,
          block=20000, cells_per_pass=None, column_chunk=1_000_000, max_cells=None,
          min_free_bytes=3 << 30, layer="X", cell_range=None, disk_fraction=0.75, **labels):
    """Yield (start, stop, source_rows, CSR, read_receipt) for all requested CSC rows.

    Each pass scans the source once, in hard-bounded nnz chunks (including long columns).
    Two compact binary buckets at most per row block, one per encountered value dtype.
    A new work directory is required. Failed runs retain their buckets for diagnosis.
    """
    if work is None or block <= 0 or column_chunk <= 0:
        raise ValueError("work, positive block and positive column_chunk are required")
    work = Path(work)
    work.mkdir(parents=True, exist_ok=False)
    with base._h5_open(path) as f:
        node = f[layer] if layer in f else f["layers"][layer]
        enc = node.attrs.get("encoding-type", "")
        if isinstance(enc, bytes):
            enc = enc.decode()
        if enc != "csc_matrix":
            raise ValueError(f"{layer} is {enc}, expected CSC")
        n_all, n_genes = map(int, node.attrs["shape"])
        ptr = node["indptr"][:].astype(np.int64)
        nnz = len(node["data"])
        if (len(ptr) != n_genes + 1 or ptr[0] != 0 or ptr[-1] != nnz
                or np.any(np.diff(ptr) < 0) or len(node["indices"]) != nnz):
            raise ValueError("inconsistent CSC structure")
        lo_all, hi_all = bounds(n_all, cell_range, max_cells)
        rd, gd = compact_dtype(block - 1), compact_dtype(n_genes - 1)
        plan = plan_passes(n_all, nnz, lo_all, hi_all, block, shutil.disk_usage(work).free,
                           min_free_bytes, rd.itemsize + gd.itemsize + 4, cells_per_pass, disk_fraction)
        with (work / "plan.json").open("x", encoding="utf-8") as out:
            json.dump(plan, out, indent=2)
        for p, lo in enumerate(range(lo_all, hi_all, plan["cells_per_pass"])):
            hi = min(hi_all, lo + plan["cells_per_pass"])
            bucket_dir = work / f"pass_{p:05d}"
            bucket_dir.mkdir()
            parts, dtype_counts = defaultdict(dict), Counter()
            total, selected_nnz, bucket_bytes = 0.0, 0, 0
            for a in range(0, nnz, column_chunk):
                b = min(a + column_chunk, nnz)
                rows = node["indices"][a:b].astype(np.int64)
                if np.any((rows < 0) | (rows >= n_all)):
                    raise ValueError("CSC cell index out of bounds")
                select = (rows >= lo) & (rows < hi)
                if not select.any():
                    continue
                vals = node["data"][a:b][select]
                vd = value_dtype(vals)
                genes = np.searchsorted(ptr[1:], a + np.flatnonzero(select), side="right")
                local_rows = rows[select] - lo
                blocks = local_rows // block
                total += float(vals.sum(dtype=np.float64))
                selected_nnz += len(vals)
                dtype_counts[vd.name] += len(vals)
                dtype = np.dtype([("row", rd), ("gene", gd), ("value", vd)])
                for k in np.unique(blocks):
                    mask = blocks == k
                    record = np.empty(int(mask.sum()), dtype=dtype)
                    record["row"], record["gene"], record["value"] = local_rows[mask] % block, genes[mask], vals[mask]
                    if shutil.disk_usage(bucket_dir).free - record.nbytes < min_free_bytes:
                        raise OSError("bucket write would cross the free-space reserve; use a smaller cell_range")
                    target = bucket_dir / f"b{int(k):06d}_{vd.name}.bin"
                    with target.open("ab") as out:
                        record.tofile(out)
                    parts[int(k)][vd.name] = dtype
                    bucket_bytes += record.nbytes
            for k, start in enumerate(range(lo, hi, block)):
                stop = min(hi, start + block)
                arrays = []
                for name, dtype in parts[k].items():
                    target = bucket_dir / f"b{k:06d}_{name}.bin"
                    arrays.append(np.fromfile(target, dtype=dtype))
                    target.unlink()
                if arrays:
                    # Promote before CSR duplicate summation: uint16 accumulation can overflow.
                    v = np.concatenate([a["value"].astype(np.float64) for a in arrays])
                    r = np.concatenate([a["row"] for a in arrays])
                    g = np.concatenate([a["gene"] for a in arrays])
                    x = sp.csr_matrix((v, (r, g)), shape=(stop - start, n_genes))
                else:
                    x = sp.csr_matrix((stop - start, n_genes), dtype=np.float64)
                x.sum_duplicates()
                read = {"pass": p, "pass_range": f"{lo}:{hi}", "pass_sum_before": total,
                        "pass_selected_nnz": selected_nnz, "bucket_payload_bytes": bucket_bytes,
                        "bucket_row_dtype": rd.name, "bucket_gene_dtype": gd.name,
                        "bucket_values_by_dtype": dict(dtype_counts), "disk_plan": plan,
                        "source_nnz": nnz, "column_chunk": column_chunk, "source_rows": n_all,
                        "whole_file_request": lo_all == 0 and hi_all == n_all}
                yield start, stop, n_all, x, read
            bucket_dir.rmdir()
    (work / "plan.json").unlink()
    work.rmdir()


def h5csc_shards(path, study, context, chemistry, modality, axis_csv, work, block=20000,
                 target_col="perturbation", control_values=("control",), control_pattern=None,
                 unassigned_values=("nan", "<NA>", "", "None", "MISSING"), guides_col=None,
                 library_col=None, published_depth=None, context_col=None, condition_cols=(), donor_col=None,
                 var_symbol_col=None, feature_id_col=None, target_id_col=None, **kwargs):
    """Contract shards with metadata sliced per output block; no full obs allocation."""
    rx = re.compile(control_pattern) if control_pattern else None
    with base._h5_open(path) as f:
        og = f["obs"]
        var = axis_frame(f["var"], axis_csv, var_symbol_col, feature_id_col)
        for start, stop, n_all, x, read in h5csc(path, work=work, block=block, **kwargs):
            get = lambda name, required=False: column(og, name, start, stop, required)
            target = get(target_col, True)
            ctrl = np.isin(target, control_values)
            if rx:
                ctrl |= np.array([bool(rx.search(t)) for t in target])
            unknown = np.isin(target, unassigned_values) & ~ctrl
            lib, bcs, guides = get(library_col), get(index_name(og), True), get(guides_col)
            lib = np.full(stop - start, MISSING, object) if lib is None else lib
            depth = np.asarray(x.sum(axis=1)).ravel()
            published = get(published_depth)
            published = depth if published is None else pd.to_numeric(pd.Series(published), errors="coerce").to_numpy(float)
            native = np.where(np.isfinite(published) & (published >= depth - 0.5), published, depth)
            ctx, donor, tid = get(context_col), get(donor_col), get(target_id_col)
            condition_values = [(name, get(name)) for name in condition_cols]
            condition = ["|".join(f"{name}={v[i]}" for name, v in condition_values if v is not None)
                         for i in range(stop - start)] if condition_cols else MISSING
            obs = base._obs(stop - start, cell_key=[f"{study}|{l}|{b}" for l, b in zip(lib, bcs)],
                            study=study, library=lib, barcode=bcs, target=np.where(ctrl, "NTC", np.where(unknown, "UNASSIGNED", target)),
                            target_published=target, target_id=tid if tid is not None else MISSING,
                            guides=guides if guides is not None else MISSING, modality=modality,
                            control_kind=np.where(ctrl, "NTC", np.where(unknown, "UNASSIGNED", "none")),
                            context=ctx if ctx is not None else context, donor_or_clone=donor if donor is not None else MISSING,
                            batch=lib, chemistry=chemistry, condition=condition, depth_native=native,
                            depth_published=np.where(np.isfinite(published), published, depth), depth_on_file_axis=depth,
                            n_genes_detected=np.asarray((x > 0).sum(axis=1)).ravel(), source_row=np.arange(start, stop))
            obs.index = [f"c{i}" for i in range(start, stop)]
            yield f"shard_{start:09d}_{stop:09d}", x, obs, var, {
                "rows": {"range": f"{start}:{stop}", "of": n_all},
                "read": {"how": "CSC bounded nnz chunks to compact per-block buckets", "block": block, **read}}


def cd4_identity(path):
    name = Path(urlsplit(str(path)).path).name
    match = re.fullmatch(r"(D[1-4])_(Rest|Stim8hr|Stim48hr)\.assigned_guide\.h5ad", name)
    if not match:
        raise ValueError("CD4 source name must be D{1..4}_{Rest,Stim8hr,Stim48hr}.assigned_guide.h5ad")
    return name, match[1], match[2]


def cd4_eligibility(cols):
    """Exclusive reasons, with low quality first. Unexpected labels are counted explicitly."""
    quality = np.char.lower(cols["low_quality"].astype(str))
    group, typ, target = cols["guide_group"], cols["guide_type"], cols["perturbed_gene_id"]
    reason = np.full(len(group), "", object)
    reason[np.isin(quality, ["true", "1"])] = "low_quality"
    reason[~np.isin(quality, ["false", "0", "true", "1"])] = "unknown_quality"
    for name, mask in (("no_sgRNA", group == "no sgRNA"), ("multi_sgRNA", group == "multi sgRNA"),
                       ("unexpected_guide_group", group != "targeting single sgRNA"),
                       ("unexpected_guide_type", ~np.isin(typ, ["targeting", "non-targeting"]))):
        reason[(reason == "") & mask] = name
    ntc = typ == "non-targeting"
    valid_id = np.array([bool(re.fullmatch(r"ENSG\d+(?:\.\d+)?", t)) for t in target])
    reason[(reason == "") & ~ntc & ~valid_id] = "invalid_target_id"
    reason[(reason == "") & ntc & (target != "NTC")] = "inconsistent_control_target"
    return reason, ntc


def read_selected_rows(node, rows, n_genes, max_gap=8):
    """Read selected CSR rows in nearby spans, then discard only the intervening gap rows."""
    if len(rows) == 0:
        return sp.csr_matrix((0, n_genes))
    pieces = []
    cuts = np.r_[0, 1 + np.flatnonzero(np.diff(rows) > max_gap + 1), len(rows)]
    for a, b in zip(cuts[:-1], cuts[1:]):
        chosen = rows[a:b]
        start, stop = int(chosen[0]), int(chosen[-1] + 1)
        ptr = node["indptr"][start:stop + 1].astype(np.int64)
        if np.any(np.diff(ptr) < 0):
            raise ValueError("nonmonotonic CSR indptr")
        lo, hi = int(ptr[0]), int(ptr[-1])
        x = sp.csr_matrix((node["data"][lo:hi], node["indices"][lo:hi], ptr - lo), shape=(stop - start, n_genes))
        pieces.append(x[chosen - start])
    out = sp.vstack(pieces, format="csr").astype(np.float64)
    out.sum_duplicates()
    out.eliminate_zeros()
    return out


def h5rows_cd4(path, study, axis_csv, exclusions_path, block=20000, cell_range=None, max_cells=None,
               chemistry="10x Flex", context="CD4T", layer="X", max_gap=8):
    """Yield every eligible CD4 row, no sampling. Write exclusive counts only on exhaustion.

    Required source columns and categories are explicit. Controls must be single-guide,
    non-targeting and labelled NTC. Source obs values survive under cd4_<column>.
    The final JSON counts raw=eligible+excluded per file/lane and eligible=emitted.
    It is a selection receipt, not proof that the caller published/verified its shards.
    """
    if block <= 0 or max_gap < 0:
        raise ValueError("block must be positive and max_gap non-negative")
    exclusions_path = Path(exclusions_path)
    if exclusions_path.exists():
        raise FileExistsError(exclusions_path)
    filename, donor, condition = cd4_identity(path)
    totals, lanes, crosstab = Counter(), defaultdict(Counter), Counter()
    with base._h5_open(path) as f:
        node = f[layer] if layer in f else f["layers"][layer]
        enc = node.attrs.get("encoding-type", "")
        enc = enc.decode() if isinstance(enc, bytes) else str(enc)
        if enc != "csr_matrix":
            raise ValueError("CD4 requires a CSR count matrix")
        n_all, n_genes = map(int, node.attrs["shape"])
        if len(node["indptr"]) != n_all + 1:
            raise ValueError("CSR shape/indptr mismatch")
        lo_all, hi_all = bounds(n_all, cell_range, max_cells)
        og, vg = f["obs"], f["var"]
        var = axis_frame(vg, axis_csv, "gene_name", "gene_ids")
        if len(var) != n_genes:
            raise ValueError("var length differs from count matrix")
        symbols = defaultdict(set)
        for tid, sym in zip(var.feature_id, var.symbol):
            symbols[str(tid).split(".")[0]].add(str(sym))
        if any(len(v) > 1 for v in symbols.values()):
            raise ValueError("an Ensembl feature ID maps to several symbols")
        symbols = {tid: next(iter(v)) for tid, v in symbols.items()}
        required = ["low_quality", "guide_group", "guide_type", "perturbed_gene_id", "guide_id", "lane_id", index_name(og)]
        names = [name for name in og if name != "__categories"]
        for start in range(lo_all, hi_all, block):
            stop = min(hi_all, start + block)
            cols = {name: column(og, name, start, stop, name in required) for name in names}
            for name in required:
                if name not in cols:
                    raise ValueError(f"missing required CD4 obs column {name}")
            reason, control = cd4_eligibility(cols)
            for lane, why, ntc, group, typ in zip(cols["lane_id"], reason, control, cols["guide_group"], cols["guide_type"]):
                role = why or ("eligible_control" if ntc else "eligible_targeted")
                totals[role] += 1
                lanes[str(lane)][role] += 1
                crosstab[f"{group}|{typ}"] += 1
            take = np.flatnonzero(reason == "")
            if not len(take):
                continue
            rows = start + take
            x = read_selected_rows(node, rows, n_genes, max_gap)
            if np.any(~np.isfinite(x.data)) or np.any(x.data < 0) or np.any(x.data != np.floor(x.data)):
                raise ValueError("CD4 X is not finite non-negative integer counts")
            keep = {name: vals[take] for name, vals in cols.items()}
            ntc = control[take]
            target_id = np.array([str(t).split(".")[0] if not c else "NTC"
                                  for t, c in zip(keep["perturbed_gene_id"], ntc)], object)
            target_symbol = np.array(["NTC" if c else symbols.get(t, MISSING) for t, c in zip(target_id, ntc)], object)
            target = np.where(target_symbol == MISSING, target_id, target_symbol)
            totals["unmapped_target_symbol"] += int((target_symbol == MISSING).sum())
            depth = np.asarray(x.sum(axis=1)).ravel().astype(float)
            published = pd.to_numeric(pd.Series(keep.get("total_counts", depth)), errors="coerce").to_numpy(float)
            lib, barcode = keep["lane_id"], keep[index_name(og)]
            obs = base._obs(len(rows), cell_key=[f"{study}|{filename}|{l}|{b}" for l, b in zip(lib, barcode)],
                            study=study, library=lib, barcode=barcode, target=target, target_id=target_id,
                            target_symbol=target_symbol, target_published=keep["perturbed_gene_id"],
                            guides=keep["guide_id"], modality="CRISPRi", control_kind=np.where(ntc, "NTC", "none"),
                            context=f"{context} {donor} {condition}", donor_or_clone=donor, batch=lib,
                            chemistry=chemistry, condition=condition,
                            depth_native=np.where(np.isfinite(published) & (published >= depth - 0.5), published, depth),
                            depth_published=np.where(np.isfinite(published), published, depth), depth_on_file_axis=depth,
                            n_genes_detected=np.diff(x.indptr), source_row=rows, sample_pi=1.0,
                            **{f"cd4_{name}": vals for name, vals in keep.items()})
            obs.index = [f"c{i}" for i in rows]
            totals["emitted"] += len(rows)
            yield f"{donor}_{condition}_{start:09d}_{stop:09d}", x, obs, var, {
                "rows": {"source_range": f"{start}:{stop}", "of": n_all, "eligible": len(rows),
                         "original_rows_in_obs": "source_row"},
                "read": {"how": "eligible CSR rows in coalesced spans", "block": block, "max_gap": max_gap},
                "eligibility": {"sampling": "none; all eligible cells", "control_pi": 1.0, "targeted_pi": 1.0}}
    role_keys = set(totals) - {"emitted", "unmapped_target_symbol"}
    raw = sum(totals[k] for k in role_keys)
    eligible = totals["eligible_control"] + totals["eligible_targeted"]
    excluded = sum(totals[k] for k in role_keys - {"eligible_control", "eligible_targeted"})
    if raw != hi_all - lo_all or raw != eligible + excluded or eligible != totals["emitted"]:
        raise AssertionError("CD4 selection parity failed")
    report = {"status": "selection_complete", "source": str(path), "file": filename, "donor": donor,
              "condition": condition, "source_rows": n_all, "cell_range": [lo_all, hi_all],
              "whole_file": lo_all == 0 and hi_all == n_all, "raw": raw, "eligible": eligible,
              "excluded": excluded, "emitted": totals["emitted"], "by_reason": dict(totals),
              "by_lane": {k: dict(v) for k, v in sorted(lanes.items())}, "guide_group_type": dict(crosstab),
              "exclusion_precedence": ["low_quality/unknown_quality", "no_sgRNA", "multi_sgRNA",
                                       "unexpected_guide_group", "unexpected_guide_type", "invalid_target_id",
                                       "inconsistent_control_target"],
              "parity": {"raw_equals_eligible_plus_excluded": True, "eligible_equals_emitted": True},
              "scope": "selection receipt only; shard publication/checksums require the job runner"}
    exclusions_path.parent.mkdir(parents=True, exist_ok=True)
    with exclusions_path.open("x", encoding="utf-8") as out:
        json.dump(report, out, indent=2)


# The name is explicit at integration: this is the CD4-specific row adapter, not a
# replacement for the generic historical h5rows used by jobs already in flight.
h5rows = h5rows_cd4
