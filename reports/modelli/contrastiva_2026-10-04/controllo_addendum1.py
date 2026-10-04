"""ADDENDUM_1.md check: contr against the copy in the t31 semantics (same lfc, k562_lfc), from the saved checkpoints.

Usage: python controllo_addendum1.py --keys <chiavi> --extra <extra> --runs <dir with contr_<fold>.pt and result.json>
       --out <json>
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "adattatore_contesto_2026-10-04"))
sys.path.insert(0, str(HERE.parent / "denoiser_k562_2026-10-04"))
import adattatore as r1  # noqa: E402
import adattatore_r3 as r3  # noqa: E402
import contrastiva as c  # noqa: E402
from denoiser import discrimination  # noqa: E402


def lfc_copy(keys: Path, prs, n_genes):
    """to_d(K562 lfc, basal of the test line): the t31 semantics in each line's d space."""
    z = np.load(keys / "replogle_k562_gwps__K562.npz", allow_pickle=False)
    eff = z["eff"].astype(np.float32)
    meas = np.asarray(z["measured"])
    row = {t: i for i, t in enumerate(map(str, z["targets"]))}
    out = np.zeros((len(prs), n_genes), np.float32)
    for i, (ln, t) in enumerate(prs):
        lfc = np.where(meas, np.nan_to_num(eff[row[t]]), 0.0)
        out[i] = r1.to_d(lfc[None, :], ln.basal)[0]
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keys", type=Path, required=True)
    ap.add_argument("--extra", type=Path, required=True)
    ap.add_argument("--runs", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    prev = json.loads((a.runs / "result.json").read_text(encoding="utf-8"))["folds"]
    src, lines, groups = r3.load_all(a.keys, a.extra)
    n_genes = src.d.shape[1]
    m_idx = np.where(~np.isnan(src.d).all(0))[0]
    split = r1.split_targets(src, lines, seed=c.SPLIT_SEED)
    rng = np.random.default_rng(0)
    folds, draws = {}, {}
    for g in r3.ORDER:
        _, _, test_lines, _, _ = r3.fold_sets(lines, groups, g)
        te = r1.pairs(src, test_lines, split["test"])
        copy_d = r1.k562_predict(src, te, m_idx, n_genes)
        copy_l = lfc_copy(a.keys, te, n_genes)
        step = prev[g]["best_step"]["contr"]
        if step == 0:
            contr = copy_d
        else:
            model = r1.Adapter(m_idx, n_genes, src.basal).to(dev)
            model.load_state_dict(torch.load(a.runs / f"contr_{g}.pt", map_location=dev))
            contr = r3.centred(model, src, te, m_idx, n_genes, dev)[0]
        preds = {"k562": copy_d, "k562_lfc": copy_l, "contr": contr}
        pt = {k: r1.per_target(r1.score(v, te), te) for k, v in preds.items()}
        ts = sorted(pt["k562"])
        diffs = np.array([pt["contr"][t] - pt["k562_lfc"][t] for t in ts])
        draws[g] = diffs[rng.integers(0, len(diffs), (10000, len(diffs)))].mean(1)
        folds[g] = {"best_step": step, "test_targets": len(ts),
                    "test_cos": {k: float(np.mean(r1.score(v, te))) for k, v in preds.items()},
                    "discrimination": {k: discrimination(v, te) for k, v in preds.items()},
                    "contr-k562_lfc": r1.boot(pt["contr"], pt["k562_lfc"]),
                    "k562_lfc-k562": r1.boot(pt["k562_lfc"], pt["k562"])}
        r1.log(f"{g}: cos {json.dumps({k: round(v, 4) for k, v in folds[g]['test_cos'].items()})} disc "
               f"{json.dumps({k: round(v, 3) for k, v in folds[g]['discrimination'].items()})}")
    md = np.mean([draws[g] for g in folds], 0)
    macro = {"contr-k562_lfc": float(np.mean([folds[g]["contr-k562_lfc"]["mean"] for g in folds])),
             "lo": float(np.quantile(md, 0.025)), "hi": float(np.quantile(md, 0.975)),
             "k562_lfc-k562": float(np.mean([folds[g]["k562_lfc-k562"]["mean"] for g in folds])),
             "discrimination_contr-k562_lfc": float(np.mean([folds[g]["discrimination"]["contr"]
                                                             - folds[g]["discrimination"]["k562_lfc"] for g in folds]))}
    a.out.write_text(json.dumps({"folds": folds, "macro": macro}, indent=2), encoding="utf-8")
    r1.log("macro " + json.dumps(macro))


if __name__ == "__main__":
    main()
