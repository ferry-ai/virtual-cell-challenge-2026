"""Production effects for A/B/C of the arm chosen by banco_t3.py's rule (README.md in this folder).

Inputs: T3's production effects (td 38's file, sha256 b8c61f6d..., the same for A, B, C) and ta 40's effects
(centred bridge network, processed/effects_rete_centrata_2026-10-12). Per context and target, on the genes both cover:
  ens_w : w * T3 / |T3| + (1 - w) * ta40 / |ta40|, then rescaled to T3's norm on those genes;
genes T3 covers and ta 40 does not keep T3's value scaled by the same factor; the own gene keeps T3's value. The
result has T3's per-target norm and T3's `observed` mask, so only the direction changes against td 38.

    python esporta_ens.py --t3 <T3_production.npz> --ta40 <effects folder> --out <new folder> --w 0.5
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import numpy as np

T3_SHA = "b8c61f6da684f6c28107199469ac42ef030a4644176371b9723ae6e3f863f6a6"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--t3", type=Path, required=True)
    ap.add_argument("--ta40", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--w", type=float, required=True)
    a = ap.parse_args()
    if sha(a.t3) != T3_SHA:
        raise SystemExit("T3 file is not td 38's (sha256 mismatch)")
    if a.out.exists():
        raise SystemExit(f"{a.out} exists: never overwrite")
    a.out.mkdir(parents=True)
    z3 = np.load(a.t3, allow_pickle=False)
    targets, genes = [str(t) for t in z3["targets"]], np.asarray(z3["genes"], str)
    T = np.where(z3["observed"], z3["lfc"], 0).astype(np.float64)
    gpos = {g: i for i, g in enumerate(genes)}
    own = np.array([gpos.get(t, -1) for t in targets])
    rec = {"t3": str(a.t3), "t3_sha256": T3_SHA, "ta40": str(a.ta40), "w": a.w, "contexts": {}}
    for ctx in "ABC":
        z4 = np.load(a.ta40 / f"effects_{ctx}.npz", allow_pickle=False)
        if [str(t) for t in z4["targets"]] != targets or list(np.asarray(z4["genes"], str)) != list(genes):
            raise SystemExit(f"{ctx}: axes differ between T3 and ta 40")
        E = np.where(z4["observed"], z4["lfc"], 0).astype(np.float64)
        both = z3["observed"] & z4["observed"]
        T0, E0 = np.where(both, T, 0), np.where(both, E, 0)
        for i, o in enumerate(own):
            if o >= 0:
                T0[i, o] = E0[i, o] = 0.0
        nT, nE = np.linalg.norm(T0, axis=1), np.linalg.norm(E0, axis=1)
        M = a.w * T0 * np.divide(1, nT, out=np.zeros_like(nT), where=nT > 0)[:, None] \
            + (1 - a.w) * E0 * np.divide(1, nE, out=np.zeros_like(nE), where=nE > 0)[:, None]
        nM = np.linalg.norm(M, axis=1)
        M = M * np.divide(nT, nM, out=np.zeros_like(nM), where=nM > 0)[:, None]
        new = np.where(both, M, T)                     # genes only T3 covers keep T3's value
        for i, o in enumerate(own):
            if o >= 0:
                new[i, o] = T[i, o]
        new = np.where(z3["observed"], new, 0).astype(np.float32)
        path = a.out / f"effects_{ctx}.npz"
        np.savez_compressed(path, targets=np.array(targets, dtype=str), genes=genes, lfc=new, observed=z3["observed"])
        cos = lambda A, B: (A * B).sum(1) / np.maximum(np.linalg.norm(A, axis=1) * np.linalg.norm(B, axis=1), 1e-12)
        rec["contexts"][ctx] = {"file": path.name, "sha256": sha(path), "ta40_sha256": sha(a.ta40 / f"effects_{ctx}.npz"),
                                "genes_both_median": float(np.median(both.sum(1))),
                                "cos_new_t3_median": float(np.median(cos(np.where(both, new, 0), T0))),
                                "cos_new_ta40_median": float(np.median(cos(np.where(both, new, 0), E0))),
                                "cos_t3_ta40_median": float(np.median(cos(T0, E0))),
                                "norm_new_over_t3_median": float(np.median(np.linalg.norm(new, axis=1)
                                                                           / np.maximum(np.linalg.norm(T, axis=1), 1e-12)))}
        print(ctx, json.dumps({k: v for k, v in rec["contexts"][ctx].items() if "sha" not in k}), flush=True)
    (a.out / "ens.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
