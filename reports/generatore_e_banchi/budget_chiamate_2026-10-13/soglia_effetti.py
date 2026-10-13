"""Hard threshold on production effects (README.md in this folder): keep |lfc x scale| >= tau, zero the rest.

The target's own gene is always kept (the knockdown itself). `observed` is left as it is, so a zeroed gene is emitted
as "no effect" by stage 45, exactly like an unperturbed gene. Nothing else changes: same targets, gene axis, values.

    python soglia_effetti.py --ref <effects folder> --out <new folder> --tau 0.5 [--scale 1.5]
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
    ap.add_argument("--tau", type=float, required=True)
    ap.add_argument("--scale", type=float, default=1.5, help="stage-45 --effects-scale the threshold refers to")
    a = ap.parse_args()
    if a.out.exists():
        raise SystemExit(f"{a.out} exists: never overwrite")
    a.out.mkdir(parents=True)
    rec = {"ref": str(a.ref), "tau": a.tau, "scale": a.scale, "contexts": {}}
    for ctx in "ABC":
        src = a.ref / f"effects_{ctx}.npz"
        z = np.load(src, allow_pickle=False)
        targets, genes, lfc, obs = [str(t) for t in z["targets"]], np.asarray(z["genes"], str), z["lfc"], z["observed"]
        gpos = {g: i for i, g in enumerate(genes)}
        keep = np.abs(lfc * a.scale) >= a.tau
        own = np.array([gpos.get(t, -1) for t in targets])
        for i, o in enumerate(own):
            if o >= 0:
                keep[i, o] = True
        new = np.where(keep, lfc, 0.0).astype(lfc.dtype)
        path = a.out / f"effects_{ctx}.npz"
        np.savez_compressed(path, targets=np.array(targets, dtype=str), genes=genes, lfc=new, observed=obs)
        nz_before = (lfc != 0).sum(1)
        nz_after = (new != 0).sum(1)
        e_before = (lfc.astype(float) ** 2).sum(1)
        e_after = (new.astype(float) ** 2).sum(1)
        rec["contexts"][ctx] = {
            "file": path.name, "sha256": sha(path), "source_sha256": sha(src), "targets": len(targets),
            "own_gene_found": int((own >= 0).sum()),
            "nonzero_genes_median_before_after": [float(np.median(nz_before)), float(np.median(nz_after))],
            "nonzero_genes_q10_q90_after": np.quantile(nz_after, [0.1, 0.9]).tolist(),
            "energy_kept_median": float(np.median(np.divide(e_after, e_before, out=np.ones_like(e_after),
                                                            where=e_before > 0))),
            "frac_up_kept": float((new > 0).sum() / max((new != 0).sum(), 1))}
        print(ctx, json.dumps({k: v for k, v in rec["contexts"][ctx].items() if "sha" not in k}), flush=True)
    (a.out / "soglia.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
