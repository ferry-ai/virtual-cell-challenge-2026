"""Why did t29 score so low? Diagnostics of a stage-100 effects file (targets, genes, lfc in ln units, observed),
optionally against a reference effects file (t22), on the official controls of each context.

Every number is a property of the effects that stage 45 turns into cells; nothing here is a VCC score. The
hypotheses are in the README next to this file, written before the numbers.

Per context:
- detectable genes per target: |log2 shift| >= 4 / sqrt(400 mu), on genes at >= 5 CPM in the context's controls
  (mu = mean counts per control cell), the yardstick of the t22 registration;
- shared component: the share of the total sum of squares of the target effects that the mean over targets carries
  (1 = every target gets the same profile, so nothing tells them apart);
- the target gene's own shift (a CRISPRi knockdown should push its own gene down);
- against the reference: per-target cosine with the same target on the reference's detectable genes, and the share
  of targets whose nearest reference profile is their own (a PDS-like discrimination with the reference as truth).

    python diagnose_effects.py --effects <dir with effects_{A,B,C}.npz> [--reference <dir>] \
        --controls A=<h5ad> B=<h5ad> C=<h5ad> --out <json>
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import h5py
import numpy as np

LN2 = np.log(2.0)


def h5_index(group):
    """The index column of an AnnData dataframe group, as strings."""
    name = group.attrs.get("_index", "_index")
    col = group[name]
    if isinstance(col, h5py.Group):
        if "categories" in col:               # categorical
            cats = col["categories"][:].astype(str)
            return cats[col["codes"][:]]
        return col["values"][:].astype(str)   # nullable string array (the official control files)
    return col[:].astype(str)


def control_means(path):
    """Mean counts per control cell and per gene, and the median library, from a CSR h5ad, streamed by rows."""
    with h5py.File(path, "r") as f:
        g = f["X"]
        n, G = (int(v) for v in g.attrs["shape"])
        genes = h5_index(f["var"])
        indptr = g["indptr"][:]
        tot = np.zeros(G, np.float64)
        libs = np.zeros(n, np.float64)
        step = 2048
        for a in range(0, n, step):
            b = min(n, a + step)
            lo, hi = int(indptr[a]), int(indptr[b])
            idx, val = g["indices"][lo:hi], g["data"][lo:hi].astype(np.float64)
            np.add.at(tot, idx, val)
            rows = np.repeat(np.arange(a, b), np.diff(indptr[a:b + 1]))
            np.add.at(libs, rows, val)
    return dict(zip(genes, tot / n)), float(np.median(libs))


def load(path):
    z = np.load(path, allow_pickle=False)
    return ([str(t) for t in z["targets"]], [str(g) for g in z["genes"]], z["lfc"].astype(np.float64),
            z["observed"].astype(bool))


def cos(a, b):
    na, nb = np.linalg.norm(a), np.linalg.norm(b)
    return float(a @ b / (na * nb)) if na > 0 and nb > 0 else float("nan")


def summarise(x):
    x = np.asarray(x, np.float64)
    x = x[np.isfinite(x)]
    if x.size == 0:
        return None
    return {"median": float(np.median(x)), "p10": float(np.quantile(x, 0.1)), "p90": float(np.quantile(x, 0.9)),
            "mean": float(x.mean())}


def one(effects, mu, lib, ref=None):
    targets, genes, lfc, obs = effects
    l2 = np.where(obs, lfc / LN2, 0.0)
    m = np.array([mu.get(g, 0.0) for g in genes])
    cpm = m / max(lib, 1.0) * 1e6
    expressed = cpm >= 5
    thr = np.where(m > 0, 4.0 / np.sqrt(400.0 * np.maximum(m, 1e-12)), np.inf)
    det = (np.abs(l2) >= thr[None, :]) & expressed[None, :]
    mean = l2.mean(0)
    ss_tot = float((l2 ** 2).sum())
    shared = float(len(targets) * (mean ** 2).sum() / ss_tot) if ss_tot > 0 else float("nan")
    gpos = {g: i for i, g in enumerate(genes)}
    own = [l2[k, gpos[t]] for k, t in enumerate(targets) if t in gpos and obs[k, gpos[t]]]
    resid = l2 - mean
    rn = resid / np.maximum(np.linalg.norm(resid, axis=1, keepdims=True), 1e-12)
    cc = rn @ rn.T
    off = cc[~np.eye(len(targets), dtype=bool)]
    out = {
        "targets": len(targets), "genes": len(genes), "genes_observed": int(obs[0].sum()),
        "genes_expressed_5cpm": int(expressed.sum()), "control_median_library": lib,
        "abs_log2_mean_observed": float(np.abs(l2[obs]).mean()),
        "abs_log2_mean_expressed": float(np.abs(l2[:, expressed]).mean()),
        "detectable_genes_per_target": summarise(det.sum(1)),
        "shared_component_share_of_sum_of_squares": shared,
        "detectable_genes_of_the_mean_profile": int(((np.abs(mean) >= thr) & expressed).sum()),
        "own_gene_log2_shift": summarise(own), "own_gene_down_share": float(np.mean(np.array(own) < 0)) if own else None,
        "pairwise_cosine_after_removing_the_mean": summarise(off),
    }
    if ref is not None:
        rt, rg, rl, ro = ref
        rpos = {g: i for i, g in enumerate(rg)}
        tpos = {t: i for i, t in enumerate(rt)}
        common_t = [t for t in targets if t in tpos]
        cols = [g for g in genes if g in rpos]
        a_idx = np.array([gpos[g] for g in cols])
        b_idx = np.array([rpos[g] for g in cols])
        A = l2[[targets.index(t) for t in common_t]][:, a_idx]
        R = np.where(ro, rl / LN2, 0.0)[[tpos[t] for t in common_t]][:, b_idx]
        mc = np.array([mu.get(g, 0.0) for g in cols])
        thr_c = np.where(mc > 0, 4.0 / np.sqrt(400.0 * np.maximum(mc, 1e-12)), np.inf)
        rdet = (np.abs(R) >= thr_c[None, :]) & ((mc / max(lib, 1.0) * 1e6) >= 5)[None, :]
        same = [cos(A[k, rdet[k]], R[k, rdet[k]]) for k in range(len(common_t)) if rdet[k].sum() >= 5]
        An = A / np.maximum(np.linalg.norm(A, axis=1, keepdims=True), 1e-12)
        Rn = R / np.maximum(np.linalg.norm(R, axis=1, keepdims=True), 1e-12)
        sim = An @ Rn.T
        own_rank = np.array([(sim[k] > sim[k, k]).sum() for k in range(len(common_t))])
        out["against_reference"] = {
            "targets_in_common": len(common_t), "genes_in_common": len(cols),
            "cosine_same_target_on_reference_detectable_genes": summarise(same),
            "cosine_of_the_mean_profiles": cos(A.mean(0), R.mean(0)),
            "own_target_is_nearest_share": float(np.mean(own_rank == 0)),
            "own_target_rank_normalised_mean": float(np.mean(own_rank / max(len(common_t) - 1, 1))),
            "reference_detectable_genes_per_target": summarise(rdet.sum(1)),
        }
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--effects", required=True, type=Path)
    ap.add_argument("--reference", type=Path)
    ap.add_argument("--controls", nargs="+", required=True, metavar="CTX=H5AD")
    ap.add_argument("--out", required=True, type=Path)
    a = ap.parse_args()
    if a.out.exists():
        raise SystemExit(f"refusing: {a.out} exists")
    res = {"effects": str(a.effects), "reference": str(a.reference) if a.reference else None, "contexts": {}}
    for spec in a.controls:
        ctx, path = spec.split("=", 1)
        mu, lib = control_means(path)
        eff = load(a.effects / f"effects_{ctx}.npz")
        ref = load(a.reference / f"effects_{ctx}.npz") if a.reference else None
        res["contexts"][ctx] = one(eff, mu, lib, ref)
        if ref is not None:
            res["contexts"][ctx]["reference_alone"] = {k: v for k, v in one(ref, mu, lib).items()
                                                      if k != "against_reference"}
        print(ctx, json.dumps(res["contexts"][ctx], indent=1), flush=True)
    a.out.write_text(json.dumps(res, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
