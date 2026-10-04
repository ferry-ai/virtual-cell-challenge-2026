"""Contrastive effect network (PROTOCOLLO.md): the r3 residual adapter trained with a PDS-like InfoNCE loss.

Arms k562, contr, cosloss (r3 objective and early stopping on the same split), contr_swap. Split seed 4.
Usage: python contrastiva.py --keys <chiavi> --extra <extra chiavi> --panel <pert_counts.csv> --out <dir>
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "adattatore_contesto_2026-10-04"))
sys.path.insert(0, str(HERE.parent / "denoiser_k562_2026-10-04"))
import adattatore as r1  # noqa: E402
import adattatore_r3 as r3  # noqa: E402
from denoiser import discrimination  # noqa: E402

SPLIT_SEED = 4
TAU, W_COS, DISC_SLACK = 0.1, 0.5, 0.005


def info_nce(pred: torch.Tensor, y: torch.Tensor) -> torch.Tensor:
    ok = ~torch.isnan(y)
    y0 = torch.where(ok, y, torch.zeros_like(y))
    yn = y0 / (y0.norm(dim=1, keepdim=True) + 1e-8)
    pn = pred / (pred.norm(dim=1, keepdim=True) + 1e-8)
    logits = (pn @ yn.T) / TAU
    target = torch.arange(len(pred), device=pred.device)
    return F.cross_entropy(logits, target) + W_COS * (1 - r1.cos_masked(pred, y)).mean()


def train_contr(src, groups, tr, va_inner, m_idx, n_genes, dev, seed=0, max_steps=3000, patience=10):
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    model = r1.Adapter(m_idx, n_genes, src.basal).to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    by_group: dict[str, dict[str, list]] = {}
    for p in tr:
        by_group.setdefault(groups[p[0].key], {}).setdefault(p[0].key, []).append(p)
    gkeys = sorted(by_group)
    hist, best, best_state, best_step, bad, disc0 = [], -1e9, None, 0, 0, None
    for step in range(max_steps + 1):
        if step % 100 == 0:
            pred, _, _ = r3.centred(model, src, va_inner, m_idx, n_genes, dev)
            vc, vd = float(np.mean(r1.score(pred, va_inner))), discrimination(pred, va_inner)
            if disc0 is None:
                disc0 = vd
            hist.append({"step": step, "inner_val_cos": vc, "inner_val_disc": vd})
            admissible = vd >= disc0 - DISC_SLACK
            if admissible and vc > best + 1e-5:
                best, bad, best_step = vc, 0, step
                best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
            else:
                bad += 1
                if bad >= patience:
                    break
            model.train()
        lines_g = by_group[gkeys[rng.integers(len(gkeys))]]
        cand = lines_g[list(lines_g)[rng.integers(len(lines_g))]]
        prs = [cand[i] for i in rng.choice(len(cand), size=min(64, len(cand)), replace=False)]
        x, y = r1.batch(src, prs, m_idx, dev)
        out = model(x, torch.as_tensor(prs[0][0].basal, device=dev))
        copy = torch.zeros_like(out)
        copy[:, model.m_idx] = x
        corr = out - copy
        pred = copy + corr - corr.mean(0, keepdim=True)
        loss = info_nce(pred, y)
        opt.zero_grad()
        loss.backward()
        opt.step()
    model.load_state_dict(best_state)
    return model, hist, best, best_step


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keys", type=Path, required=True)
    ap.add_argument("--extra", type=Path, required=True)
    ap.add_argument("--panel", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    out = a.out / "contrastiva"
    out.mkdir(parents=True, exist_ok=False)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    src, lines, groups = r3.load_all(a.keys, a.extra)
    n_genes = src.d.shape[1]
    m_idx = np.where(~np.isnan(src.d).all(0))[0]
    split = r1.split_targets(src, lines, seed=SPLIT_SEED)
    panel = {r[0] for r in list(csv.reader(a.panel.open(encoding="utf-8")))[1:]} - {"non-targeting"}
    rng = np.random.default_rng(0)
    folds, draws = {}, {}
    for g in r3.ORDER:
        train_lines, inner_lines, test_lines, inner, dropped = r3.fold_sets(lines, groups, g)
        tr = r1.pairs(src, train_lines, split["train"])
        va = r1.pairs(src, inner_lines, split["val"])
        te = r1.pairs(src, test_lines, split["test"])
        r1.log(f"fold {g}: pairs tr {len(tr)} inner-val {len(va)} ({inner}) test {len(te)}; "
               f"test targets {len({t for _, t in te})}")
        copy = r1.k562_predict(src, te, m_idx, n_genes)
        mc, hc, bc, sc = train_contr(src, groups, tr, va, m_idx, n_genes, dev)
        mr, hr, br, sr = r3.train(src, train_lines, groups, tr, va, m_idx, n_genes, dev)
        torch.save(mc.state_dict(), out / f"contr_{g}.pt")
        torch.save(mr.state_dict(), out / f"cosloss_{g}.pt")
        preds, shares = {"k562": copy}, {}
        for name, model, step in (("contr", mc, sc), ("cosloss", mr, sr)):
            if step == 0:
                preds[name] = copy
            else:
                preds[name], _, shares[name] = r3.centred(model, src, te, m_idx, n_genes, dev)
        mean_basal = np.mean([ln.basal for ln in train_lines], 0).astype(np.float32)
        sw = {ln.key: r1.Line(ln.key, ln.targets, ln.d, mean_basal) for ln in test_lines}
        te_swap = [(sw[ln.key], t) for ln, t in te]
        preds["contr_swap"] = copy if sc == 0 else r3.centred(mc, src, te_swap, m_idx, n_genes, dev)[0]
        pt = {k: r1.per_target(r1.score(v, te), te) for k, v in preds.items()}
        ts = sorted(pt["k562"])
        diffs = np.array([pt["contr"][t] - pt["k562"][t] for t in ts])
        draws[g] = diffs[rng.integers(0, len(diffs), (10000, len(diffs)))].mean(1)
        pan = [i for i, (_, t) in enumerate(te) if t in panel]
        folds[g] = {
            "inner_group": inner, "dropped_from_training": dropped, "best_step": {"contr": sc, "cosloss": sr},
            "history": {"contr": hc, "cosloss": hr}, "n_pairs": [len(tr), len(va), len(te)], "test_targets": len(ts),
            "test_cos": {k: float(np.mean(r1.score(v, te))) for k, v in preds.items()},
            "discrimination": {k: discrimination(v, te) for k, v in preds.items()},
            "common_share_test": shares,
            "diff": {f"{k}-k562": r1.boot(pt[k], pt["k562"]) for k in ("contr", "cosloss", "contr_swap")},
            "diff_contr-cosloss": r1.boot(pt["contr"], pt["cosloss"]),
            "panel_test_targets": len({te[i][1] for i in pan}),
            "panel_test_cos": ({k: float(np.mean(r1.score(v[pan], [te[i] for i in pan]))) for k, v in preds.items()}
                               if pan else None),
            "nan": any(bool(np.isnan(v).any()) for v in preds.values()),
        }
        r1.log(f"fold {g}: steps contr {sc} cosloss {sr}; cos "
               f"{json.dumps({k: round(v, 4) for k, v in folds[g]['test_cos'].items()})}; disc "
               f"{json.dumps({k: round(v, 3) for k, v in folds[g]['discrimination'].items()})}")
        (out / "result.json").write_text(json.dumps({"folds": folds}, indent=2), encoding="utf-8")
    md = np.mean([draws[g] for g in folds], 0)
    macro = {
        "contr-k562": float(np.mean([folds[g]["diff"]["contr-k562"]["mean"] for g in folds])),
        "lo": float(np.quantile(md, 0.025)), "hi": float(np.quantile(md, 0.975)),
        "folds_positive": int(sum(folds[g]["diff"]["contr-k562"]["mean"] > 0 for g in folds)),
        "discrimination_contr-k562": float(np.mean([folds[g]["discrimination"]["contr"]
                                                    - folds[g]["discrimination"]["k562"] for g in folds])),
        "contr-cosloss": float(np.mean([folds[g]["diff_contr-cosloss"]["mean"] for g in folds])),
        "folds_back_to_copy": int(sum(folds[g]["best_step"]["contr"] == 0 for g in folds)),
    }
    (out / "result.json").write_text(json.dumps({"folds": folds, "macro": macro}, indent=2), encoding="utf-8")
    r1.log("macro " + json.dumps(macro))


if __name__ == "__main__":
    main()
