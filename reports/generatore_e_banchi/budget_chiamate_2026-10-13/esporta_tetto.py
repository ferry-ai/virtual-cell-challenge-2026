"""Cap on production effect magnitudes (README.md in this folder): the arm `cap_c` of tetto_banco.py on A/B/C.

Every (target, gene) value is clipped so that the emitted magnitude |lfc x scale| (stage-45 --effects-scale) is at most
`cap`; the target's own gene keeps its value (it is excluded from every scored member). Signs, `observed`, targets and
the gene axis are unchanged; a value below the cap is untouched, so the genes called stay the same.

    python esporta_tetto.py --ref <effects folder> --out <new folder> --cap 1.0 [--scale 1.5]
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
    ap.add_argument("--cap", type=float, required=True)
    ap.add_argument("--scale", type=float, default=1.5)
    a = ap.parse_args()
    if a.out.exists():
        raise SystemExit(f"{a.out} exists: never overwrite")
    a.out.mkdir(parents=True)
    lim = a.cap / a.scale
    rec = {"ref": str(a.ref), "cap_emitted": a.cap, "scale": a.scale, "cap_file_units": lim, "contexts": {}}
    for ctx in "ABC":
        src = a.ref / f"effects_{ctx}.npz"
        z = np.load(src, allow_pickle=False)
        targets, genes, lfc, obs = [str(t) for t in z["targets"]], np.asarray(z["genes"], str), z["lfc"], z["observed"]
        gpos = {g: i for i, g in enumerate(genes)}
        new = np.clip(lfc, -lim, lim).astype(lfc.dtype)
        own = np.array([gpos.get(t, -1) for t in targets])
        for i, o in enumerate(own):
            if o >= 0:
                new[i, o] = lfc[i, o]
        path = a.out / f"effects_{ctx}.npz"
        np.savez_compressed(path, targets=np.array(targets, dtype=str), genes=genes, lfc=new, observed=obs)
        changed = (new != lfc).sum(1)
        cos = (new.astype(float) * lfc).sum(1) / np.maximum(
            np.linalg.norm(new.astype(float), axis=1) * np.linalg.norm(lfc.astype(float), axis=1), 1e-12)
        rec["contexts"][ctx] = {"file": path.name, "sha256": sha(path), "source_sha256": sha(src), "targets": len(targets),
                                "own_gene_found": int((own >= 0).sum()),
                                "capped_genes_per_target_median_q90": [float(np.median(changed)),
                                                                       float(np.quantile(changed, 0.9))],
                                "cos_capped_vs_ref_median": float(np.median(cos)),
                                "norm_ratio_median": float(np.median(np.linalg.norm(new, axis=1)
                                                                     / np.maximum(np.linalg.norm(lfc, axis=1), 1e-12)))}
        print(ctx, json.dumps({k: v for k, v in rec["contexts"][ctx].items() if "sha" not in k}), flush=True)
    (a.out / "tetto.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
