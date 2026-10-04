"""Local step of the t35 bench (PROTOCOLLO.md): for each held-out line L in h1, kolf, hepg2, jurkat, train the
`rete_anti` exactly as its bench fold (reports/modelli/rete_l1_2026-10-04/rete_l1_r2.py: groups other than L and its
inner group, early stop on the inner group, seed 0), then write, for every key of L, the network's magnitude |m| for
each covered target and each gene with key CPM >= 5. The sign is applied on Kaggle from the arm's own effect.

Usage: python obiettivi_linee.py --keys <chiavi> --extra <extra chiavi> --controls <raw/controls> --out <dir>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1] / "modelli" / "rete_l1_2026-10-04"))
import rete_l1 as r1  # noqa: E402
import rete_l1_r2 as r2  # noqa: E402

LINES = ["h1", "kolf", "hepg2", "jurkat"]


def sha256(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keys", type=Path, required=True)
    ap.add_argument("--extra", type=Path, required=True)
    ap.add_argument("--controls", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise SystemExit(f"{a.out} exists: never overwrite")
    a.out.mkdir(parents=True)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    src, data = r1.build(a)
    order = [g for g in r1.ORDER if g in data]
    lines = r1.load_lines(a.keys, a.extra)
    meta = {"lines": {}}
    for L in LINES:
        inner = order[(order.index(L) + 1) % len(order)]
        tr = {h: data[h] for h in order if h not in (L, inner)}
        net, step, vbest = r2.train(tr, data[inner], dev, seed=0)
        torch.save(net.state_dict(), a.out / f"rete_anti_{L}.pt")
        meta["lines"][L] = {"inner": inner, "best_step": step, "inner_nmae": vbest, "keys": {}}
        for ln in (x for x in lines if x["group"] == L):
            z = np.load(ln["path"], allow_pickle=False)
            cpm = r1.cpm_of(z["basal"])
            gidx = np.where(cpm >= r1.MIN_CPM)[0]
            targets = [t for t in map(str, z["targets"]) if t in src.row]
            mag = np.zeros((len(targets), len(gidx)), np.float16)
            with torch.no_grad():
                for i, t in enumerate(targets):
                    f = r1.features(src, t, cpm, gidx)
                    mag[i] = net(torch.as_tensor(f, device=dev)).abs().cpu().numpy().astype(np.float16)
            name = "obiettivi_" + ln["key"].replace("|", "__").replace(" ", "_").replace(".", "") + ".npz"
            np.savez_compressed(a.out / name, key=np.array(ln["key"]), group=np.array(L),
                                targets=np.array(targets, dtype=str), gene_idx=gidx.astype(np.int32), mag=mag)
            meta["lines"][L]["keys"][ln["key"]] = {"file": name, "sha256": sha256(a.out / name),
                                                    "targets": len(targets), "genes": int(len(gidx)),
                                                    "mag_median": float(np.median(mag[mag > 0])) if (mag > 0).any() else 0.0}
            r1.log(f"{L} {ln['key']}: {len(targets)} targets, {len(gidx)} genes")
        r1.log(f"{L}: inner {inner}, step {step}, inner nMAE {vbest:.4f}")
    (a.out / "obiettivi.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
