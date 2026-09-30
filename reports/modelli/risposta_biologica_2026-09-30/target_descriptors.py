"""Transferable biological descriptors for every gene of the official axis: the TargetEncoder's input (R-LAB P4).

A target never perturbed anywhere can only be predicted from what is known about the gene itself. Each block below is
built from a public annotation, reduced to a few dimensions, and written with the source files' hashes:
- GO: gene x GO term membership from the GOA human annotations (experimental and electronic evidence alike; NOT and
  obsolete terms dropped), propagated to ancestors through is_a and part_of, TF-IDF weighted, truncated SVD;
- STRING: the physical interaction network (combined score >= 700) as a symmetric normalised adjacency, truncated SVD
  (spectral coordinates), plus log degree;
- HGNC: gene groups (multi-hot, SVD) and locus type (one-hot);
- GENCODE: chromosome (one-hot), relative position, log gene length, log number of genes within 20 kb and 1 Mb;
- DepMap 24Q4: the gene's expression profile across the cell lines (log TPM), centred per line, truncated SVD. It
  describes the gene in many lines; it is not an outcome of any perturbation.
Genes missing from a source get zeros and a missing flag for that block, never an invented value.

No perturbation outcome enters a descriptor (D-044): the files are annotations, a protein network and basal expression.

    python target_descriptors.py --data-root C:/Users/ferra/vcc2026-data --out <new dir>
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for b in iter(lambda: fh.read(8 << 20), b""):
            h.update(b)
    return h.hexdigest()


def opener(path: Path):
    with open(path, "rb") as fh:
        gz = fh.read(2) == b"\x1f\x8b"
    return gzip.open(path, "rt", encoding="utf-8", errors="replace") if gz else open(path, encoding="utf-8", errors="replace")


def svd_block(mat, k, seed=0):
    """Truncated SVD of a sparse or dense matrix (rows = genes); returns U*S scaled to unit variance per column."""
    from scipy.sparse.linalg import svds
    import scipy.sparse as sp
    k = min(k, min(mat.shape) - 1)
    if k <= 0:
        return np.zeros((mat.shape[0], 0), np.float32)
    rng = np.random.default_rng(seed)
    v0 = rng.standard_normal(min(mat.shape))
    u, s, _ = svds(sp.csr_matrix(mat, dtype=np.float64), k=k, v0=v0)
    order = np.argsort(-s)
    emb = u[:, order] * s[order]
    sd = emb.std(0)
    return (emb / np.where(sd > 0, sd, 1)).astype(np.float32)


def go_block(gaf: Path, obo: Path, genes: dict, k: int):
    import scipy.sparse as sp
    parents = defaultdict(set)
    obsolete, cur = set(), None
    with opener(obo) as fh:
        for line in fh:
            line = line.strip()
            if line == "[Term]":
                cur = None
            elif line.startswith("id: GO:"):
                cur = line[4:]
            elif cur and line.startswith("is_obsolete: true"):
                obsolete.add(cur)
            elif cur and line.startswith("is_a: GO:"):
                parents[cur].add(line[6:16])
            elif cur and line.startswith("relationship: part_of GO:"):
                parents[cur].add(line.split()[2])
    memo = {}

    def ancestors(t):
        if t in memo:
            return memo[t]
        out = {t}
        for p in parents.get(t, ()):
            out |= ancestors(p)
        memo[t] = out
        return out

    sys.setrecursionlimit(100000)
    ann = defaultdict(set)
    with opener(gaf) as fh:
        for line in fh:
            if line.startswith("!"):
                continue
            f = line.rstrip("\n").split("\t")
            if len(f) < 5 or "NOT" in f[3] or f[4] in obsolete:
                continue
            if f[2] in genes:
                ann[genes[f[2]]].update(ancestors(f[4]))
    terms = sorted({t for s in ann.values() for t in s})
    tix = {t: i for i, t in enumerate(terms)}
    rows, cols = [], []
    for g, ts in ann.items():
        rows += [g] * len(ts)
        cols += [tix[t] for t in ts]
    m = sp.csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(len(genes), len(terms)))
    df = np.asarray((m > 0).sum(0)).ravel()
    keep = (df >= 5) & (df <= 0.2 * max(1, len(ann)))
    m = m[:, np.flatnonzero(keep)]
    idf = np.log(len(genes) / (1 + df[keep]))
    m = m.multiply(idf[None, :]).tocsr()
    norms = np.sqrt(np.asarray(m.multiply(m).sum(1)).ravel())
    m = sp.diags(1 / np.where(norms > 0, norms, 1)) @ m
    have = np.zeros(len(genes), bool)
    have[list(ann)] = True
    return svd_block(m, k), have, {"terms_kept": int(keep.sum()), "genes_annotated": int(have.sum())}


def string_block(links: Path, info: Path, genes: dict, k: int, min_score: int = 700):
    import scipy.sparse as sp
    pid = {}
    with opener(info) as fh:
        next(fh)
        for line in fh:
            f = line.split("\t")
            if len(f) > 1 and f[1] in genes:
                pid[f[0]] = genes[f[1]]
    rows, cols = [], []
    with opener(links) as fh:
        next(fh)
        for line in fh:
            a, b, s = line.split()
            if int(s) >= min_score and a in pid and b in pid:
                rows.append(pid[a]); cols.append(pid[b])
    n = len(genes)
    adj = sp.csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(n, n))
    adj = ((adj + adj.T) > 0).astype(np.float64)
    deg = np.asarray(adj.sum(1)).ravel()
    dinv = sp.diags(1 / np.sqrt(np.where(deg > 0, deg, 1)))
    norm = dinv @ adj @ dinv
    emb = svd_block(norm, k)
    return np.hstack([emb, np.log1p(deg)[:, None].astype(np.float32)]), deg > 0, {"edges": int(adj.nnz // 2)}


def hgnc_block(path: Path, genes: dict, k: int):
    import scipy.sparse as sp
    with opener(path) as fh:
        header = next(fh).rstrip("\n").split("\t")
        ix = {h: i for i, h in enumerate(header)}
        groups, locus = defaultdict(set), {}
        for line in fh:
            f = line.rstrip("\n").split("\t")
            sym = f[ix["symbol"]]
            if sym not in genes:
                continue
            g = genes[sym]
            locus[g] = f[ix["locus_type"]]
            for grp in f[ix["gene_group_id"]].split("|") if f[ix["gene_group_id"]] else []:
                groups[g].add(grp.strip('"'))
    names = sorted({x for s in groups.values() for x in s})
    gix = {x: i for i, x in enumerate(names)}
    rows = [g for g, s in groups.items() for _ in s]
    cols = [gix[x] for g, s in groups.items() for x in s]
    m = sp.csr_matrix((np.ones(len(rows)), (rows, cols)), shape=(len(genes), len(names)))
    emb = svd_block(m, k) if len(names) > k else np.zeros((len(genes), 0), np.float32)
    types = sorted(set(locus.values()))
    onehot = np.zeros((len(genes), len(types)), np.float32)
    for g, t in locus.items():
        onehot[g, types.index(t)] = 1
    have = np.zeros(len(genes), bool)
    have[list(locus)] = True
    return np.hstack([emb, onehot]), have, {"groups": len(names), "locus_types": types}


def coord_block(path: Path, genes: dict):
    import pandas as pd
    t = pd.read_csv(path, sep="\t")
    sym_col = next((c for c in ("gene_name", "symbol") if c in t.columns), t.columns[0])
    t = t[t[sym_col].astype(str).isin(genes)]
    chroms = [f"chr{c}" for c in list(range(1, 23)) + ["X", "Y", "M"]]
    out = np.zeros((len(genes), len(chroms) + 4), np.float32)
    have = np.zeros(len(genes), bool)
    t = t.drop_duplicates(sym_col)
    tss = pd.to_numeric(t["tss"], errors="coerce") if "tss" in t.columns else pd.to_numeric(t["start"], errors="coerce")
    start = pd.to_numeric(t.get("start", tss), errors="coerce")
    end = pd.to_numeric(t.get("end", tss), errors="coerce")
    chrom = t["chrom"].astype(str)
    by = defaultdict(list)
    for s, c, p in zip(t[sym_col], chrom, tss):
        if np.isfinite(p):
            by[c].append(p)
    by = {c: np.sort(v) for c, v in by.items()}
    maxpos = {c: v.max() for c, v in by.items()}
    for s, c, p, a, b in zip(t[sym_col], chrom, tss, start, end):
        g = genes[s]
        if c in chroms:
            out[g, chroms.index(c)] = 1
        if np.isfinite(p) and c in by:
            pos = by[c]
            out[g, len(chroms)] = p / maxpos[c]
            out[g, len(chroms) + 1] = np.log1p(abs(b - a)) if np.isfinite(a) and np.isfinite(b) else 0
            out[g, len(chroms) + 2] = np.log1p(np.searchsorted(pos, p + 2e4) - np.searchsorted(pos, p - 2e4) - 1)
            out[g, len(chroms) + 3] = np.log1p(np.searchsorted(pos, p + 1e6) - np.searchsorted(pos, p - 1e6) - 1)
            have[g] = True
    return out, have, {"genes_with_coordinates": int(have.sum())}


def depmap_block(path: Path, genes: dict, k: int):
    import pandas as pd
    header = pd.read_csv(path, nrows=0).columns.tolist()
    sym = [re.sub(r"\s*\(.*\)$", "", c) for c in header]
    cols = [(i, genes[s]) for i, s in enumerate(sym) if s in genes]
    use = [i for i, _ in cols]
    rows = []
    for chunk in pd.read_csv(path, usecols=use, chunksize=100, dtype=np.float32):
        rows.append(chunk.to_numpy(dtype=np.float32))
    x = np.vstack(rows)                                # lines x genes (log TPM)
    x = x - x.mean(1, keepdims=True)
    mat = np.zeros((len(genes), x.shape[0]), np.float32)
    for (i, g), j in zip(cols, range(len(cols))):
        mat[g] = x[:, j]
    have = np.zeros(len(genes), bool)
    have[[g for _, g in cols]] = True
    return svd_block(mat, k), have, {"lines": int(x.shape[0]), "genes_in_file": len(cols)}


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data-root", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--k-go", type=int, default=128)
    p.add_argument("--k-string", type=int, default=64)
    p.add_argument("--k-hgnc", type=int, default=16)
    p.add_argument("--k-depmap", type=int, default=32)
    a = p.parse_args()
    if a.out.exists():
        sys.exit(f"refusing: {a.out} exists")
    d = a.data_root
    axis_path = d / "raw/controls/gene_names.csv"
    axis = [l.strip().split(",")[0] for l in open(axis_path, encoding="utf-8") if l.strip()]
    if axis[0].lower() in ("gene", "gene_name", "genes", "x"):
        axis = axis[1:]
    genes = {g: i for i, g in enumerate(axis)}
    enc = d / "interim/encoder_inputs_2026-09-14"
    files = {"axis": axis_path, "goa": enc / "goa_human_gaf", "obo": enc / "go_basic_obo",
             "string_links": enc / "string_physical_links", "string_info": enc / "string_protein_info",
             "hgnc": enc / "hgnc_complete_set", "coords": d / "external/annotation/gene_coordinates_gencode_v50.tsv",
             "depmap_expression": d / "external/depmap_24q4/OmicsExpressionProteinCodingGenesTPMLogp1.csv"}
    blocks, info = [], {}
    for name, fn in (("go", lambda: go_block(files["goa"], files["obo"], genes, a.k_go)),
                     ("string", lambda: string_block(files["string_links"], files["string_info"], genes, a.k_string)),
                     ("hgnc", lambda: hgnc_block(files["hgnc"], genes, a.k_hgnc)),
                     ("coords", lambda: coord_block(files["coords"], genes)),
                     ("depmap", lambda: depmap_block(files["depmap_expression"], genes, a.k_depmap))):
        emb, have, meta = fn()
        blocks.append((name, emb, have))
        info[name] = {**meta, "dims": int(emb.shape[1]), "genes_covered": int(have.sum())}
        print(name, info[name], flush=True)
    mats, flags, layout, pos = [], [], [], 0
    for name, emb, have in blocks:
        mats.append(emb * have[:, None])
        flags.append(have[:, None].astype(np.float32))
        layout.append({"block": name, "start": pos, "stop": pos + emb.shape[1]})
        pos += emb.shape[1]
    X = np.hstack(mats + flags).astype(np.float32)
    for k, (name, _, _) in enumerate(blocks):
        layout.append({"block": f"{name}_present", "start": pos + k, "stop": pos + k + 1})
    a.out.mkdir(parents=True)
    np.save(a.out / "descriptors.npy", X)
    (a.out / "genes.txt").write_text("\n".join(axis) + "\n", encoding="utf-8")
    manifest = {"what": "biological descriptors of every official-axis gene, rows in genes.txt order",
                "shape": list(X.shape), "layout": layout, "blocks": info,
                "sources": {k: {"path": str(v), "bytes": v.stat().st_size, "sha256": sha(v)} for k, v in files.items()},
                "sha256_descriptors": sha(a.out / "descriptors.npy"),
                "leakage": "annotations, a protein network, genomic coordinates and basal expression only: no perturbation outcome"}
    (a.out / "manifest.json").write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print("written", X.shape)


if __name__ == "__main__":
    main()
