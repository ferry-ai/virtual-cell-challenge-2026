"""Production effects of the bridge network for contexts A, B, C (stage-45 external_effects layout).

The ensemble of the bench (EMENDAMENTO_R3/R4: seeds 2-11) is refitted on every cube group (no line held out) and
predicts the 300 panel targets with the official controls' basal of each context (cube basal `competition_<ctx>`).
Each target's prediction is rescaled to the norm of its `all` transfer T over the cube genes, times the t25 amplitude
1.576, exactly as the bench compares them: against the `all` export only the direction changes. Targets and gene axis
come from the `all` export (esporta_all.py); a target without sources stays all 0, observed False.

    python esporta_rete.py --cube <layout> --code <cube code> --cache <rete cache> --ref <effects_all folder> --out <new>
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rete_ponte as rp  # noqa: E402
from rete_ponte import gd  # noqa: E402

SEEDS = (2, 3, 4, 5, 6, 7, 8, 9, 10, 11)


@torch.no_grad()
def predict_context(fold: rp.Fold, model, keys: list[str], basal_ctx: np.ndarray) -> np.ndarray:
    srcg = list(range(len(fold.groups)))
    bt = torch.tensor(basal_ctx, device=fold.dev)
    outs = []
    for b0 in range(0, len(keys), rp.BATCH):
        ii = torch.tensor([fold.kpos[k] for k in keys[b0:b0 + rp.BATCH]], device=fold.dev)
        src = fold.S[torch.tensor(srcg, device=fold.dev)[:, None], ii[None, :]].float()
        out, _, _ = model(src, fold.basal[srcg], bt, True)
        outs.append(out.cpu().numpy())
    return np.concatenate(outs).astype(np.float32)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cube", type=Path, required=True)
    ap.add_argument("--code", type=Path, required=True)
    ap.add_argument("--cache", type=Path, required=True)
    ap.add_argument("--ref", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise SystemExit(f"{a.out} exists: never overwrite")
    a.out.mkdir(parents=True)
    logf = open(a.out / "run.log", "w", encoding="utf-8")

    def log(s):
        line = f"{time.strftime('%H:%M:%S')} {s}"
        print(line, flush=True)
        logf.write(line + "\n"); logf.flush()

    sys.path.insert(0, str(a.code))
    import arms
    C = gd.Cubes(arms, a.cube)
    cube = C.cube
    meta = rp.build_cache(C, a.cache, log)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    commons = gd.table_means(cube, set())
    by_symbol = {}
    for k, s in cube.symbol.items():
        by_symbol.setdefault(s, set()).add(k)
    fold = rp.Fold(C, a.cache, meta, None, dev, log)
    models = []
    for s in SEEDS:
        m, hist = fold.fit(seed=s)
        models.append(m)
        log(f"  seed {s}: {len(hist)} epochs, best val {min(h['val'] for h in hist):.5f}")
    rec = {"cube_manifest_sha256": gd.sha(a.cube / "manifest.json"), "groups": meta["groups"], "seeds": list(SEEDS),
           "amplitude": gd.AMP, "ref": str(a.ref), "contexts": {}}
    for ctx in "ABC":
        ref = np.load(a.ref / f"effects_{ctx}.npz", allow_pickle=False)
        targets, genes = [str(t) for t in ref["targets"]], np.asarray(ref["genes"], str)
        keys = [next(iter(by_symbol[t])) if len(by_symbol.get(t, ())) == 1 else None for t in targets]
        have = [i for i, k in enumerate(keys) if k is not None]
        hk = [keys[i] for i in have]
        st = gd.transfer(C, "all", hk, commons, set())
        T = st["T"]
        basal_ctx = cube.basal[f"competition_{ctx}"]
        P = np.mean([predict_context(fold, m, hk, basal_ctx) for m in models], 0)
        fin = np.isfinite(T)
        nT = np.sqrt((np.where(fin, T, 0) ** 2).sum(1))
        nP = np.sqrt((P ** 2).sum(1))
        Pn = P * np.divide(nT * gd.AMP, nP, out=np.zeros_like(nP), where=nP > 0)[:, None]
        gpos = pd.Index(genes).get_indexer(cube.genes)
        if (gpos < 0).any():
            raise SystemExit("cube genes missing from the reference axis")
        lfc = np.zeros((len(targets), len(genes)), np.float32)
        obs = np.zeros((len(targets), len(genes)), bool)
        for j, i in enumerate(have):
            if nT[j] > 0:
                lfc[i, gpos] = Pn[j]
                obs[i, gpos] = True
        # the all export of the same targets, for the record: same norms, cosine between the two directions
        Ta = np.where(fin, T, 0)
        cos = (Ta * P).sum(1) / np.maximum(nT * nP, 1e-12)
        path = a.out / f"effects_{ctx}.npz"
        np.savez_compressed(path, targets=np.array(targets, dtype=str), genes=genes, lfc=lfc, observed=obs)
        rec["contexts"][ctx] = {"file": path.name, "sha256": gd.sha(path), "targets": len(targets),
                                "mapped_to_cube": len(have), "covered": int(obs.any(1).sum()),
                                "cos_rete_vs_all_median": float(np.median(cos[nT > 0])),
                                "cos_rete_vs_all_q10_q90": np.quantile(cos[nT > 0], [0.1, 0.9]).tolist(),
                                "lfc_abs_mean_covered": float(np.abs(lfc[obs]).mean())}
        log(f"{ctx} " + json.dumps({k: v for k, v in rec["contexts"][ctx].items() if k != "sha256"}))
    (a.out / "export.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
