"""A549 knockout table on the cube keys, and the extended cube (ADDENDUM_A549.md).

One pass over the rlab-a549 shards: count sums per target and for NTC controls on the cube genes; raw ln fold change of
fractions, SE and z_shrink with the route C formulas; a new cube layout = hard links to the original tables + a549_ko.

    python tabella_a549.py --shards <rlab-a549 folder> --cube <cube layout> --out <extended cube layout>
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import time
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp

PHI, MIN_CTRL_FRAC, SHRINK_K, MIN_CELLS = 0.2, 1e-6, 4.0, 10


def z_shrink(eff, se, k):
    z2 = np.divide(eff * eff, se ** 2, out=np.zeros_like(eff), where=se > 0)
    return eff * z2 / (z2 + k)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--shards", type=Path, required=True)
    ap.add_argument("--cube", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise FileExistsError(a.out)
    import anndata as ad
    from vcc2026.genes import official_axis

    t0 = time.time()
    genes = pd.read_csv(a.cube / "genes.csv")["gene"].astype(str).tolist()
    axis = list(official_axis().symbols)
    apos = pd.Index(axis).get_indexer(genes)                       # cube gene -> official index
    if (apos < 0).any():
        raise SystemExit("cube genes off the official axis")
    col_of_official = np.full(len(axis), -1, np.int64)
    col_of_official[apos] = np.arange(len(genes))
    G = len(genes)
    # symbol -> cube key (unambiguous symbols only)
    sym = {}
    for d in sorted(p for p in a.cube.iterdir() if p.is_dir()):
        r = pd.read_csv(d / "rows.csv")
        for k, s in zip(r["target_key"].astype(str), r["target"].astype(str)):
            sym.setdefault(s, set()).add(k)
    key_of = {s: next(iter(ks)) for s, ks in sym.items() if len(ks) == 1}
    sums, n, measured = {}, {}, None
    shards = sorted(a.shards.glob("a549_ko__shard_*.h5ad"))
    for i, p in enumerate(shards):
        x = ad.read_h5ad(p)
        obs, var = x.obs, x.var
        oi = var["official_index"].to_numpy().astype(np.int64)
        ok = (oi >= 0) & var["measured"].to_numpy().astype(bool) & (var["mapping"].astype(str).to_numpy() == "unique")
        cols = np.flatnonzero(ok)
        cc = col_of_official[oi[cols]]
        keep = cc >= 0
        cols, cc = cols[keep], cc[keep]
        m = np.zeros(G, bool)
        m[cc] = True
        measured = m if measured is None else (measured & m)
        proj = sp.csr_matrix((np.ones(cols.size, np.float32), (np.arange(cols.size), cc)), shape=(cols.size, G))
        X = sp.csr_matrix(x.X)[:, cols].astype(np.float32) @ proj
        ck = obs["control_kind"].astype(str).to_numpy()
        tg = obs["target"].astype(str).to_numpy()
        lab = np.where(ck == "NTC", "__NTC__", np.array([key_of.get(t, "") for t in tg], dtype=object))
        use = (obs["modality"].astype(str).to_numpy() == "KO") & (lab != "")
        labs, inv = np.unique(lab[use], return_inverse=True)
        R = sp.csr_matrix((np.ones(inv.size, np.float32), (inv, np.arange(inv.size))), shape=(labs.size, inv.size))
        S = np.asarray((R @ X[np.flatnonzero(use)]).todense(), dtype=np.float64)
        cnt = np.bincount(inv, minlength=labs.size)
        for j, l in enumerate(labs):
            sums[l] = sums.get(l, 0) + S[j]
            n[l] = n.get(l, 0) + int(cnt[j])
        print(f"{time.strftime('%H:%M:%S')} shard {i + 1}/{len(shards)}: {len(obs)} cells, {int(use.sum())} used", flush=True)
    s0, n0 = sums.pop("__NTC__"), n.pop("__NTC__")
    ctrl_mu = np.where(measured, s0 / n0, 0.0)
    ctrl_frac = ctrl_mu / ctrl_mu.sum()
    usable = measured & (ctrl_frac >= MIN_CTRL_FRAC)
    n_c = max(float(n0), 1000.0)
    keys = sorted(k for k in sums if n[k] >= MIN_CELLS)
    raw = np.full((len(keys), G), np.nan, np.float32)
    se = np.full_like(raw, np.nan)
    shr = np.full_like(raw, np.nan)
    for i, k in enumerate(keys):
        tot = float(n[k])
        mu = np.where(measured, sums[k] / tot, 0.0)
        frac = mu / mu.sum()
        eff = np.log(np.maximum(frac, 1e-7)) - np.log(np.maximum(ctrl_frac, 1e-7))
        s = np.sqrt(1.0 / (tot * np.maximum(mu, 1e-3)) + PHI / tot + 1.0 / (n_c * np.maximum(ctrl_mu, 1e-3)) + PHI / n_c)
        raw[i, usable], se[i, usable] = eff[usable], s[usable]
        shr[i, usable] = z_shrink(eff[usable], s[usable], SHRINK_K)
    # extended cube: hard links to every original file, then the new table, manifest and basal
    a.out.mkdir(parents=True)
    for p in a.cube.rglob("*"):
        if p.is_file() and p.name not in ("manifest.json", "basal.npz"):
            q = a.out / p.relative_to(a.cube)
            q.parent.mkdir(parents=True, exist_ok=True)
            os.link(p, q)
    t = a.out / "a549_ko"
    t.mkdir()
    for name, arr in (("raw", raw), ("se", se), ("shrunk", shr)):
        np.save(t / f"{name}.npy", arr.astype(np.float16))
    symbol_of = {k: s for s, k in key_of.items()}
    pd.DataFrame({"target_key": keys, "target": [symbol_of.get(k, "") for k in keys],
                  "n_cells": [n[k] for k in keys], "duplicate_of_key": False}).to_csv(t / "rows.csv", index=False)
    man = json.loads((a.cube / "manifest.json").read_text(encoding="utf-8"))
    man["tables"]["a549_ko"] = {"rows": len(keys), "group": "A549", "line": "A549", "study": "a549_liu_hillsley2026",
                                "assay": "KO", "state": None, "donor": None, "duplicate_symbol_rows": 0}
    man["extension"] = {"added": "a549_ko", "by": "tabella_a549.py (ADDENDUM_A549.md)", "estimator": "route C formulas",
                        "control_cells": int(n0), "keys": len(keys)}
    (a.out / "manifest.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
    with np.load(a.cube / "basal.npz") as z:
        basal = {k: z[k] for k in z.files}
    cpm = np.where(measured, s0 / s0[measured].sum() * 1e6, np.nan)
    basal["a549_ko"] = np.log1p(cpm).astype(np.float32)
    np.savez(a.out / "basal.npz", **basal)
    rep = {"keys": len(keys), "control_cells": int(n0), "target_cells_median": float(np.median([n[k] for k in keys])),
           "usable_genes": int(usable.sum()), "seconds": round(time.time() - t0, 1)}
    (a.out / "a549_report.json").write_text(json.dumps(rep, indent=1))
    print(json.dumps(rep), flush=True)


if __name__ == "__main__":
    main()
