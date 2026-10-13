"""Low-rank denoising (--mode lowrank) or deflation (--mode deflate, the arm `deflate_r` of deflate_banco.py) of
production effects on A/B/C (README.md in this folder). deflate: centre over the panel, then remove the top-r SVD
components shared by the panel's targets.

Per context, the 300 x G matrix of predicted effects (predictions only) is projected on its top-r right singular
vectors, then each target is rescaled to its own original norm over the genes it covers, so only the DIRECTION
changes. The target's own gene keeps its original value (it is excluded from every scored member; it stays for the
generator's realism). Genes outside `observed` stay 0.

    python esporta_lowrank.py --ref <effects folder> --out <new folder> --rank 20 [--mode lowrank|deflate]
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--rank", type=int, required=True)
    ap.add_argument("--mode", choices=("lowrank", "deflate"), default="lowrank")
    a = ap.parse_args()
    if a.out.exists():
        raise SystemExit(f"{a.out} exists: never overwrite")
    a.out.mkdir(parents=True)
    rec = {"ref": str(a.ref), "rank": a.rank, "mode": a.mode, "contexts": {}}
    for ctx in "ABC":
        src = a.ref / f"effects_{ctx}.npz"
        z = np.load(src, allow_pickle=False)
        targets, genes, lfc, obs = [str(t) for t in z["targets"]], np.asarray(z["genes"], str), z["lfc"], z["observed"]
        L = np.where(obs, lfc, 0).astype(np.float64)
        gpos = {g: i for i, g in enumerate(genes)}
        own = np.array([gpos.get(t, -1) for t in targets])
        Lx = L.copy()
        for i, o in enumerate(own):              # the own gene does not shape the programmes
            if o >= 0:
                Lx[i, o] = 0.0
        if a.mode == "deflate":
            Lx = Lx - Lx.mean(0, keepdims=True)
        U, s, Vt = np.linalg.svd(Lx, full_matrices=False)
        P = (U[:, :a.rank] * s[:a.rank]) @ Vt[:a.rank]
        if a.mode == "deflate":
            P = Lx - P
        P = np.where(obs, P, 0.0)
        L0 = L.copy()
        for i, o in enumerate(own):
            if o >= 0:
                L0[i, o] = 0.0
        n0 = np.sqrt((L0 ** 2).sum(1))
        n1 = np.sqrt((P ** 2).sum(1))
        P = P * np.divide(n0, n1, out=np.zeros_like(n1), where=n1 > 0)[:, None]
        cos = (P * L0).sum(1) / np.maximum(n0 * np.sqrt((P ** 2).sum(1)), 1e-12)
        for i, o in enumerate(own):
            if o >= 0:
                P[i, o] = L[i, o]
        new = P.astype(lfc.dtype)
        path = a.out / f"effects_{ctx}.npz"
        np.savez_compressed(path, targets=np.array(targets, dtype=str), genes=genes, lfc=new, observed=obs)
        energy = s ** 2 / (s ** 2).sum()
        rec["contexts"][ctx] = {
            "file": path.name, "sha256": sha(path), "source_sha256": sha(src), "targets": len(targets),
            "energy_top_r": float(energy[:a.rank].sum()), "cos_new_vs_ref_median": float(np.median(cos[n0 > 0])),
            "cos_new_vs_ref_q10_q90": np.quantile(cos[n0 > 0], [0.1, 0.9]).tolist(),
            "genes_abs_ge_0.2x1.5_median_before_after": [float(np.median((np.abs(lfc * 1.5) >= 0.2).sum(1))),
                                                         float(np.median((np.abs(new * 1.5) >= 0.2).sum(1)))]}
        print(ctx, json.dumps({k: v for k, v in rec["contexts"][ctx].items() if "sha" not in k}), flush=True)
    (a.out / "lowrank.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
