"""Adapters from three published schemas to contract shards (R-LAB P2, jobs J01-J03).

Each adapter yields (shard_name, x, obs, var, uns) one block of cells at a time; `rlab_job.py`
writes, validates, hashes and publishes every block as it comes, so a lost runtime keeps the
shards already published. Every cell of the source is kept: calls, flags and missing metadata
become columns, never a reason to drop a row. The one exception is declared: in a 10x channel
matrix the barcodes below --min-umi are empty droplets, summarised as an ambient profile per
channel, and the raw matrix they come from stays on Drive untouched.

- h5ad: a published AnnData with counts in X, dense or CSR (J01, HepG2).
- hipsci: genes x cells CSV.gz with a cell metadata TSV (J02). One pass over the file per range of
  cells (`cells_per_pass`): each gene row is parsed with numpy and the non-zeros of the range go to
  an on-disk bucket per block of cells; each bucket is then assembled into one CSR shard. A range
  bounds the disk the buckets take, at the price of reading the file once per range.
- mtx10x: one 10x channel as MatrixMarket files for transcriptome, guides and hash labels (J03).

`max_cells` limits any adapter to the first cells, for local smoke tests only.
"""
from __future__ import annotations

import gzip
import re
from pathlib import Path

import numpy as np

MISSING = "MISSING"
GUIDE = re.compile(r"^([^_]+)_([ACGT]+)$")


def _official(symbols, axis_csv):
    if not axis_csv:
        return np.full(len(symbols), -1), np.array(["none"] * len(symbols))
    axis = [l.strip().split(",")[0] for l in open(axis_csv, encoding="utf-8") if l.strip()]
    if axis and axis[0].lower() in ("gene", "gene_name", "genes", "x"):
        axis = axis[1:]
    where = {}
    for i, g in enumerate(axis):
        where.setdefault(g, []).append(i)
    idx = np.array([where[s][0] if len(where.get(s, [])) == 1 else -1 for s in symbols])
    kind = np.array(["unique" if len(where.get(s, [])) == 1 else ("ambiguous" if s in where else "none")
                     for s in symbols])
    return idx, kind


def _obs(n, **cols):
    import pandas as pd
    base = {k: MISSING for k in ("guide_confidence", "donor_or_clone", "batch", "condition")}
    base.update(cols)
    frame = pd.DataFrame({k: (v if np.ndim(v) else [v] * n) for k, v in base.items()})
    for c in frame.columns:
        if frame[c].dtype.kind not in "iufb":
            frame[c] = frame[c].astype(str).astype(object)
    return frame


# ------------------------------------------------------------------------------------------ h5ad

def h5ad(path, study, context, chemistry, modality, axis_csv, block=20000, max_cells=None,
         target_col="gene", guides_col="guide_id", library_col="batch", published_depth="UMI_count",
         control_label="non-targeting"):
    import anndata as ad
    import pandas as pd
    import scipy.sparse as sp
    a = ad.read_h5ad(path, backed="r")
    n = a.n_obs if max_cells is None else min(a.n_obs, max_cells)
    symbols = list(a.var_names)
    idx, kind = _official(symbols, axis_csv)
    var = pd.DataFrame({"feature_id": a.var["gene_id"].astype(str).to_numpy() if "gene_id" in a.var else symbols,
                        "symbol": symbols, "feature_type": "Gene Expression", "measured": True,
                        "official_index": idx, "mapping": kind}, index=symbols)
    for k, start in enumerate(range(0, n, block)):
        stop = min(n, start + block)
        part = a[start:stop]
        x = part.X[:]
        x = sp.csr_matrix(np.asarray(x) if not sp.issparse(x) else x)
        o = part.obs
        target = o[target_col].astype(str).to_numpy()
        ntc = target == control_label
        on_axis = np.asarray(x.sum(axis=1)).ravel().astype(float)
        depth = o[published_depth].to_numpy(dtype=float) if published_depth in o else on_axis
        library = o[library_col].astype(str).to_numpy() if library_col in o else np.array([MISSING] * len(o))
        obs = _obs(len(o), cell_key=[f"{study}|{lib}|{bc}" for lib, bc in zip(library, part.obs_names)],
                   study=study, library=library, barcode=list(part.obs_names),
                   target=np.where(ntc, "NTC", target),
                   guides=o[guides_col].astype(str).to_numpy() if guides_col in o else MISSING,
                   modality=modality, control_kind=np.where(ntc, "NTC", "none"), context=context,
                   batch=library, chemistry=chemistry, depth_native=depth, depth_published=depth,
                   depth_on_file_axis=on_axis, n_genes_detected=np.diff(x.indptr))
        obs.index = [f"c{start + i}" for i in range(len(o))]
        yield f"shard_{k:05d}", x, obs, var, {"rows": {"range": f"{start}:{stop}", "of": int(a.n_obs)},
                                               "read": {"how": "anndata backed, row blocks", "block": block}}
    a.file.close()


# ------------------------------------------------------------------------------------------ h5rows

def _h5_open(path):
    """An h5py File on a local path, or on a URL read by HTTP byte ranges (inspect_remote.RangeFile)."""
    import io
    import h5py
    if str(path).startswith(("http://", "https://")):
        from inspect_remote import RangeFile
        return h5py.File(io.BufferedReader(RangeFile(str(path), block=8 << 20), buffer_size=8 << 20), "r")
    return h5py.File(path, "r")


def _h5_text(values):
    return np.asarray([v.decode() if isinstance(v, bytes) else str(v) for v in values], dtype=object)


def _h5_column(group, name):
    """An anndata dataframe column as text (categorical, string or numeric), or None when absent."""
    import h5py
    if name is None or name not in group:
        return None
    node = group[name]
    if isinstance(node, h5py.Group) and "categories" in node:
        cats = _h5_text(node["categories"][:])
        codes = node["codes"][:].astype(np.int64)
        return np.where(codes >= 0, cats[np.clip(codes, 0, None)], MISSING).astype(object)
    if isinstance(node, h5py.Group):                       # nullable string / int arrays
        values = node["values"][:]
        mask = node["mask"][:] if "mask" in node else np.zeros(values.shape, bool)
        return np.where(mask, MISSING, _h5_text(values)).astype(object)
    return _h5_text(node[:])


def h5rows(path, study, context, chemistry, modality, axis_csv, block=20000, max_cells=None,
           target_col="perturbation", control_values=("control",), control_pattern=None,
           unassigned_values=("nan", "<NA>", "", "None", "MISSING"), guides_col=None, library_col=None,
           published_depth=None, context_col=None, condition_cols=(), donor_col=None, var_symbol_col=None,
           feature_id_col=None, layer="X", row_range=None):
    """Row-major h5ad (CSR or dense X, or a CSR/dense layer), local or remote, read with h5py alone.

    Column names come from the source's plan (the remote inventory); nothing is guessed at run time. Controls are
    the target values in `control_values`, or matching `control_pattern` (a regex); unassigned cells keep target
    UNASSIGNED and control_kind UNASSIGNED; every other label is kept as published in `target` (a later, declared
    mapping turns guide-level labels into gene symbols). `row_range` = (start, stop) reads a part of the file, so a
    very large source is split across jobs. A CSC matrix is refused here: it needs the transposing adapter.
    """
    import h5py
    import pandas as pd
    import scipy.sparse as sp
    rx = re.compile(control_pattern) if control_pattern else None
    f = _h5_open(path)
    try:
        node = f[layer] if layer in f else f["layers"][layer]
        if isinstance(node, h5py.Dataset):
            dense, (n_all, n_genes) = True, node.shape
        else:
            enc = node.attrs.get("encoding-type", b"")
            enc = enc.decode() if isinstance(enc, bytes) else str(enc)
            if enc != "csr_matrix":
                raise ValueError(f"{layer} is {enc}: the row adapter reads CSR or dense only")
            dense, (n_all, n_genes) = False, tuple(int(v) for v in node.attrs["shape"])
        indptr = None if dense else node["indptr"][:].astype(np.int64)
        obs, varg = f["obs"], f["var"]
        vindex = varg.attrs.get("_index", "_index")
        vindex = vindex.decode() if isinstance(vindex, bytes) else str(vindex)
        symbols = list(_h5_column(varg, var_symbol_col) if var_symbol_col else _h5_column(varg, vindex))
        feature_ids = _h5_column(varg, feature_id_col) if feature_id_col else None
        idx, kind = _official(symbols, axis_csv)
        var = pd.DataFrame({"feature_id": list(feature_ids) if feature_ids is not None else symbols,
                            "symbol": symbols, "feature_type": "Gene Expression", "measured": True,
                            "official_index": idx, "mapping": kind}, index=[f"f{i}" for i in range(len(symbols))])
        oindex = obs.attrs.get("_index", "_index")
        oindex = oindex.decode() if isinstance(oindex, bytes) else str(oindex)
        barcodes = _h5_column(obs, oindex)
        target_all = _h5_column(obs, target_col)
        if target_all is None:
            raise ValueError(f"obs has no column {target_col}")
        cols = {"guides": _h5_column(obs, guides_col), "library": _h5_column(obs, library_col),
                "context": _h5_column(obs, context_col), "donor": _h5_column(obs, donor_col),
                "depth": _h5_column(obs, published_depth)}
        conds = [(c, _h5_column(obs, c)) for c in condition_cols]
        lo_all, hi_all = (0, n_all) if row_range is None else (int(row_range[0]), int(row_range[1]))
        hi_all = hi_all if max_cells is None else min(hi_all, lo_all + max_cells)
        for start in range(lo_all, hi_all, block):
            stop = min(hi_all, start + block)
            if dense:
                x = sp.csr_matrix(np.asarray(node[start:stop]))
            else:
                a, b = int(indptr[start]), int(indptr[stop])
                x = sp.csr_matrix((node["data"][a:b], node["indices"][a:b], indptr[start:stop + 1] - a),
                                  shape=(stop - start, n_genes))
            rows = slice(start, stop)
            target = target_all[rows].astype(str)
            is_ctrl = np.isin(target, list(control_values))
            if rx is not None:
                is_ctrl |= np.array([bool(rx.search(t)) for t in target])
            unassigned = np.isin(target, list(unassigned_values)) & ~is_ctrl
            library = cols["library"][rows] if cols["library"] is not None else np.array([MISSING] * (stop - start))
            on_axis = np.asarray(x.sum(axis=1)).ravel().astype(float)
            depth = on_axis
            if cols["depth"] is not None:
                published = pd.to_numeric(pd.Series(cols["depth"][rows]), errors="coerce").to_numpy(dtype=float)
                depth = np.where(np.isfinite(published) & (published >= on_axis - 0.5), published, on_axis)
            condition = MISSING
            if conds:
                condition = np.array(["|".join(f"{c}={v[i]}" for c, v in conds if v is not None)
                                      for i in range(start, stop)], dtype=object)
            ctx = cols["context"][rows] if cols["context"] is not None else context
            bcs = barcodes[rows] if barcodes is not None else np.array([f"row{i}" for i in range(start, stop)])
            obs_block = _obs(stop - start,
                             cell_key=[f"{study}|{lib}|{bc}" for lib, bc in zip(library, bcs)],
                             study=study, library=library, barcode=list(bcs),
                             target=np.where(is_ctrl, "NTC", np.where(unassigned, "UNASSIGNED", target)),
                             target_published=target,
                             guides=cols["guides"][rows] if cols["guides"] is not None else MISSING,
                             modality=modality,
                             control_kind=np.where(is_ctrl, "NTC", np.where(unassigned, "UNASSIGNED", "none")),
                             context=ctx, donor_or_clone=cols["donor"][rows] if cols["donor"] is not None else MISSING,
                             batch=library, chemistry=chemistry, condition=condition, depth_native=depth,
                             depth_published=depth, depth_on_file_axis=on_axis, n_genes_detected=np.diff(x.indptr))
            obs_block.index = [f"c{i}" for i in range(start, stop)]
            yield f"shard_{start // block:05d}", x, obs_block, var, {
                "rows": {"range": f"{start}:{stop}", "of": int(n_all)},
                "read": {"how": f"h5py row blocks of {layer} ({'dense' if dense else 'CSR'}), "
                                f"{'HTTP byte ranges' if str(path).startswith('http') else 'local file'}",
                         "block": block},
                "notes": "target keeps controls as NTC and unassigned cells as UNASSIGNED; target_published is the "
                         "label as published; depth_native is the published total when it is at least the file's "
                         "row sum, otherwise the row sum"}
    finally:
        f.close()


# ---------------------------------------------------------------------------------------- hipsci

def _hipsci_ids(meta, cells):
    """The id rule of reports/sorgenti/universo_hipsci_2026-09-27/hipsci_sums.py, reused as it is."""
    prefixes = {v[:3] for v in meta.Cell_ID}
    if len(prefixes) != 1 or not prefixes <= {"MP-", "PC-"}:
        raise ValueError(f"unexpected metadata prefixes: {prefixes}")
    meta.index = meta.Cell_ID.str.slice(3)
    rule = "metadata prefix stripped"
    if not set(meta.index) & set(cells):
        stripped = meta.index.str.replace(r"^(P\d+)-D\d+_", r"\1_", regex=True)
        if stripped.is_unique and set(stripped) & set(cells):
            meta.index = stripped
            rule = "metadata prefix and day stripped (P<n>-D<d>_ -> P<n>_)"
    return meta, rule


def _hipsci_pass(counts, n, lo, hi, block, bucket_dir, flush_nnz, min_free_bytes, sliced):
    """One pass over the CSV.gz for the cells [lo, hi): their non-zeros go to on-disk buckets."""
    import shutil
    n_blocks = (hi - lo + block - 1) // block
    buffers = {b: [] for b in range(n_blocks)}
    chunks = {b: 0 for b in range(n_blocks)}
    state = {"buffered": 0}
    labels, total = [], 0

    def flush():
        if shutil.disk_usage(bucket_dir).free < min_free_bytes:
            raise OSError(f"less than {min_free_bytes} bytes free beside the buckets: stopping before the disk fills")
        for b, parts in buffers.items():
            if parts:
                c, g, v = (np.concatenate(p) for p in zip(*parts))
                v = v.astype(np.uint16) if v.max() < 65536 else v  # counts are read back exactly either way
                for arr, name in ((c, "c"), (g, "g"), (v, "v")):
                    np.save(bucket_dir / f"b{b:05d}_{chunks[b]:05d}_{name}.npy", arr)
                chunks[b] += 1
                parts.clear()
        state["buffered"] = 0

    with gzip.open(counts, "rt") as fh:
        fh.readline()
        for gene, line in enumerate(fh):
            if gene > 65535:
                raise ValueError("more than 65,536 feature rows: the bucket's uint16 gene index would overflow")
            label, rest = line.rstrip("\n").split(",", 1)
            if sliced:
                values = np.array(rest.split(",", n)[:n], dtype=np.int64)
            else:
                values = np.fromstring(rest, sep=",", dtype=np.int64)
                if values.size != n:
                    raise ValueError(f"row {gene} has {values.size} values, expected {n}")
            labels.append(label.strip('"'))
            values = values[lo:hi]
            nz = np.flatnonzero(values)
            if nz.size:
                total += int(values[nz].sum())
                bounds = np.searchsorted(nz, np.arange(1, n_blocks) * block)
                for b, sel in enumerate(np.split(nz, bounds)):
                    if sel.size:
                        buffers[b].append(((sel - b * block).astype(np.uint16),
                                           np.full(sel.size, gene, np.uint16), values[sel].astype(np.int32)))
                        state["buffered"] += sel.size
            if state["buffered"] >= flush_nnz:
                flush()
    flush()
    return labels, chunks, total


def hipsci(counts, metadata, study, axis_csv, work, block=20000, max_cells=None, flush_nnz=40_000_000,
           cells_per_pass=600_000, min_free_bytes=3 << 30):
    """Cells [lo, hi) of one pass are bucketed on disk, so the buckets never exceed one pass."""
    import pandas as pd
    if cells_per_pass % block:
        raise ValueError("cells_per_pass must be a multiple of block")
    work = Path(work)
    work.mkdir(parents=True, exist_ok=False)
    with gzip.open(counts, "rt") as fh:
        header = fh.readline().rstrip("\n").split(",")
    all_cells = [c.strip('"') for c in header[1:]]
    n = len(all_cells) if max_cells is None else min(len(all_cells), max_cells)
    cells = all_cells[:n]
    meta = pd.read_csv(metadata, sep="\t", dtype=str, keep_default_na=False)
    meta, rule = _hipsci_ids(meta, cells)
    aligned = meta.reindex(cells)
    var, first_labels = None, None
    for p, lo in enumerate(range(0, n, cells_per_pass)):
        hi = min(n, lo + cells_per_pass)
        bucket_dir = work / f"pass_{p:02d}"
        bucket_dir.mkdir()
        labels, chunks, total_pass = _hipsci_pass(counts, len(all_cells) if max_cells is None else n, lo, hi,
                                                  block, bucket_dir, flush_nnz, min_free_bytes,
                                                  sliced=max_cells is not None)
        if first_labels is None:
            first_labels = labels
            parts = [l.split(":") for l in labels]
            symbols = [q[1] if len(q) > 1 else q[0] for q in parts]
            idx, kind = _official(symbols, axis_csv)
            var = pd.DataFrame({"feature_id": [q[0] for q in parts], "symbol": symbols,
                                "feature_type": [q[2] if len(q) > 2 else MISSING for q in parts], "measured": True,
                                "official_index": idx, "mapping": kind},
                               index=[f"f{i}" for i in range(len(labels))])
        elif labels != first_labels:
            raise ValueError(f"pass {p} read a different feature axis than pass 0")
        yield from _hipsci_blocks(p, lo, hi, block, bucket_dir, chunks, total_pass, len(labels), var, aligned,
                                  cells, all_cells, study, rule)
        bucket_dir.rmdir()


def _hipsci_blocks(p, lo, hi, block, bucket_dir, chunks, total_pass, n_features, var, aligned, cells, all_cells,
                   study, rule):
    import scipy.sparse as sp
    for b in range((hi - lo + block - 1) // block):
        start, stop = lo + b * block, min(hi, lo + (b + 1) * block)
        rows = stop - start
        cs, gs, vs = [], [], []
        for k in range(chunks[b]):
            for name, lst in (("c", cs), ("g", gs), ("v", vs)):
                f = bucket_dir / f"b{b:05d}_{k:05d}_{name}.npy"
                lst.append(np.load(f))
                f.unlink()
        c = np.concatenate(cs) if cs else np.zeros(0, np.uint16)
        g = np.concatenate(gs) if gs else np.zeros(0, np.uint16)
        v = np.concatenate([a.astype(np.int32) for a in vs]) if vs else np.zeros(0, np.int32)
        x = sp.csr_matrix((v, (c.astype(np.int64), g.astype(np.int64))), shape=(rows, n_features))
        x.sum_duplicates()
        m = aligned.iloc[start:stop]
        call = m.Guide_Call.fillna(MISSING).astype(str).to_numpy()
        matched = m.Cell_ID.notna().to_numpy()
        target, control = [], []
        for value, ok in zip(call, matched):
            hit = GUIDE.fullmatch(value) if ok else None
            if not ok:
                target.append("NO_METADATA"); control.append("none")
            elif hit and hit[1] == "NonTarget":
                target.append("NTC"); control.append("NTC")
            elif hit:
                target.append(hit[1]); control.append("none")
            else:
                target.append("UNASSIGNED"); control.append("UNASSIGNED" if value == "unassigned" else "none")
        batch = m.Batch.fillna(MISSING).astype(str).to_numpy()
        day = [re.search(r"Day\d+", s).group(0).lower() if re.search(r"Day\d+", s) else MISSING for s in batch]
        depth = np.asarray(x.sum(axis=1)).ravel().astype(float)
        line = m.Cell_Line.fillna(MISSING).astype(str).to_numpy()
        obs = _obs(rows, cell_key=[f"{study}|{bt}|{cid}" for bt, cid in zip(batch, cells[start:stop])],
                   study=study, library=batch, barcode=cells[start:stop], target=np.array(target), guides=call,
                   modality="CRISPRi", control_kind=np.array(control), context=line, donor_or_clone=line,
                   batch=batch, chemistry=MISSING, condition=np.array(day), depth_native=depth,
                   depth_published=depth, depth_on_file_axis=depth, n_genes_detected=np.diff(x.indptr))
        obs.index = [f"c{start + i}" for i in range(rows)]
        yield f"shard_{start // block:05d}", x, obs, var, {
            "rows": {"range": f"{start}:{stop}", "of": len(all_cells)},
            "read": {"how": "passes over the CSV.gz, each for a range of cells, non-zeros bucketed per block",
                     "block": block, "id_rule": rule, "pass": p, "pass_range": f"{lo}:{hi}",
                     "pass_sum_before": total_pass},
            "notes": "depth_native is the file sum: the published counts carry every feature row of the file"}


# ---------------------------------------------------------------------------------------- mtx10x

def _read_mtx(path):
    import pandas as pd
    import scipy.sparse as sp
    with gzip.open(path, "rt") as fh:
        skip, line = 0, fh.readline()
        while line.startswith("%"):
            skip += 1
            line = fh.readline()
        rows, cols, _ = (int(v) for v in line.split())
    frame = pd.read_csv(path, sep=" ", header=None, skiprows=skip + 1, names=["r", "c", "v"],
                        dtype={"r": np.int32, "c": np.int32, "v": np.float64})
    return sp.csc_matrix((frame.v.to_numpy(), (frame.r.to_numpy() - 1, frame.c.to_numpy() - 1)), shape=(rows, cols))


def mtx10x(prefix, study, context, axis_csv, panel_csv=None, min_umi=100, block=20000, max_cells=None):
    import pandas as pd
    import scipy.sparse as sp
    import hashlib
    channel = Path(prefix).name
    # guides and hash labels are indexed by the same barcode list as the transcriptome (checked on 30/09
    # for channels 1 and 16: the decompressed lists are identical); refuse a channel where they are not
    lists = {k: hashlib.sha256(gzip.open(f"{prefix}_{k}_barcode.tsv.gz").read()).hexdigest()
             for k in ("transcriptome", "guides", "labels")}
    if len(set(lists.values())) != 1:
        raise ValueError(f"{channel}: barcode lists differ between modalities {lists}")
    feats = pd.read_csv(f"{prefix}_transcriptome_features.tsv.gz", sep="\t", header=None, dtype=str)
    bcs = pd.read_csv(f"{prefix}_transcriptome_barcode.tsv.gz", sep="\t", header=None, dtype=str)[0].to_numpy()
    tx = _read_mtx(f"{prefix}_transcriptome_matrix.mtx.gz")            # genes x barcodes
    matrix_total = float(tx.sum())
    umi = np.asarray(tx.sum(axis=0)).ravel()
    keep = np.flatnonzero(umi >= min_umi)
    if max_cells is not None:
        keep = keep[:max_cells]
    ambient_cols = np.flatnonzero((umi > 0) & (umi < min_umi))
    ambient = np.asarray(tx[:, ambient_cols].sum(axis=1)).ravel()
    guides = _read_mtx(f"{prefix}_guides_matrix.mtx.gz")
    gnames = pd.read_csv(f"{prefix}_guides_features.tsv.gz", sep="\t", header=None, dtype=str)[0].to_numpy()
    labels = _read_mtx(f"{prefix}_labels_matrix.mtx.gz")
    lnames = pd.read_csv(f"{prefix}_labels_features.tsv.gz", sep="\t", header=None, dtype=str)[0].to_numpy()
    symbols = feats[1].to_numpy()
    panel = set(pd.read_csv(panel_csv, skiprows=1).symbol) if panel_csv else set()
    idx, kind = _official(list(symbols), axis_csv)
    var = pd.DataFrame({"feature_id": feats[0].to_numpy(), "symbol": symbols,
                        "feature_type": feats[2].to_numpy() if feats.shape[1] > 2 else "Gene Expression",
                        "measured": True, "in_targeted_panel": [s in panel for s in symbols],
                        "official_index": idx, "mapping": kind}, index=[f"f{i}" for i in range(len(symbols))])
    txr, gr, lr = tx.T.tocsr(), guides.T.tocsr(), labels.T.tocsr()
    for k, start in enumerate(range(0, keep.size, block)):
        cols = keep[start:start + block]
        x = txr[cols]
        gsub, lsub = gr[cols], lr[cols]
        gtop = np.asarray(gsub.argmax(axis=1)).ravel()
        gmax = np.asarray(gsub.max(axis=1).todense()).ravel()
        gsum = np.asarray(gsub.sum(axis=1)).ravel()
        ltop = np.asarray(lsub.argmax(axis=1)).ravel()
        lsum = np.asarray(lsub.sum(axis=1)).ravel()
        lmax = np.asarray(lsub.max(axis=1).todense()).ravel()
        hash_top = np.where(lsum > 0, lnames[ltop], MISSING)
        # hash oligo names are <condition><n>_1 (table S6: untreated or activated)
        condition = np.array([re.sub(r"\d*_\d+$", "", h) if h != MISSING else MISSING for h in hash_top])
        depth = np.asarray(x.sum(axis=1)).ravel().astype(float)
        obs = _obs(len(cols), cell_key=[f"{study}|{channel}|{bc}" for bc in bcs[cols]], study=study,
                   library=channel, barcode=list(bcs[cols]), target="UNASSIGNED", guides=MISSING,
                   modality="CRISPRi", control_kind="UNASSIGNED", context=context, batch=channel,
                   chemistry="10x, targeted primer panel", condition=condition,
                   depth_native=depth, depth_published=depth, depth_on_file_axis=depth,
                   n_genes_detected=np.diff(x.indptr), guide_umi_total=gsum,
                   guide_top=np.where(gsum > 0, gnames[gtop], MISSING), guide_top_umi=gmax,
                   guides_detected=np.diff(gsub.indptr), hash_top=hash_top, hash_top_umi=lmax,
                   hash_umi_total=lsum, hashes_detected=np.diff(lsub.indptr))
        obs.index = [f"{channel}_{i}" for i in range(start, start + len(cols))]
        uns = {"rows": {"barcodes_kept": int(keep.size), "of_barcodes": int(bcs.size),
                        "block": f"{start}:{start + len(cols)}"},
               "read": {"how": "whole channel MTX in memory", "min_umi": min_umi},
               "parity_source": {"matrix_total": matrix_total, "ambient_umi": float(ambient.sum())},
               "guide_features": np.asarray(gnames, dtype=str), "hash_features": np.asarray(lnames, dtype=str),
               "_obsm": {"guide_umi": sp.csr_matrix(gsub).astype(np.int32),
                         "hash_umi": sp.csr_matrix(lsub).astype(np.int32)},
               "notes": "the source publishes no guide calls: guides is MISSING, target UNASSIGNED, and the raw "
                        "guide and hash UMI matrices are in obsm (columns named in uns guide_features and "
                        "hash_features); calls are a derived view, tested before supervision. condition is the "
                        "top hash oligo with its number stripped"}
        if k == 0:
            uns["ambient"] = {"barcodes": int(ambient_cols.size), "umi": float(ambient.sum()),
                              "profile_nonzero_features": int((ambient > 0).sum())}
            uns["ambient_profile"] = ambient
        yield f"{channel}_shard_{k:05d}", sp.csr_matrix(x), obs, var, uns
