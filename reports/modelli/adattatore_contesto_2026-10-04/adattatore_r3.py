"""Context adapter r3 (PROTOCOLLO_R3.md): K562 copy + a learned correction centred over targets, varied lines,
group-balanced sampling, leave-one-group-out with an inner held-out group for early stopping.

Usage: python adattatore_r3.py --keys <chiavi dir> --extra <extra chiavi dir> --out <dir> [--folds h1 kolf rpe1 hepg2 jurkat]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

import numpy as np
import torch

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "denoiser_k562_2026-10-04"))
import adattatore as r1  # noqa: E402
from denoiser import discrimination  # noqa: E402

ORDER = ["h1", "kolf", "rpe1", "hepg2", "jurkat"]
SPLIT_SEED = 3


def load_all(keys: Path, extra: Path):
    src, lines = r1.load(keys)
    groups = {}
    for d in (keys, extra):
        for f in d.glob("*.npz"):
            z = np.load(f, allow_pickle=False)
            groups[str(z["key"])] = str(z["group"])
    _, more = r1.load(extra)
    lines += [ln for ln in more if ln.key != r1.SOURCE]
    return src, lines, groups


def fold_sets(lines, groups, test_group):
    inner = ORDER[(ORDER.index(test_group) + 1) % len(ORDER)]
    test = [ln for ln in lines if groups[ln.key] == test_group]
    inner_l = [ln for ln in lines if groups[ln.key] == inner]
    drop = {ln.key for ln in lines if test_group == "kolf" and ln.key.startswith("hipsci") and "|kolf_" in ln.key}
    train = [ln for ln in lines if groups[ln.key] not in (test_group, inner) and ln.key not in drop]
    return train, inner_l, test, inner, sorted(drop)


def centred(model, src, prs, m_idx, n_genes, dev):
    """Copy + model correction centred over the targets of each line; also returns the pre-centring common share."""
    copy = r1.k562_predict(src, prs, m_idx, n_genes)
    raw = r1.predict_adapter(model, src, prs, m_idx, dev)
    corr = raw - copy
    out_c, out_n, shares = copy.copy(), raw, {}
    for key in {ln.key for ln, _ in prs}:
        idx = [i for i, (ln, _) in enumerate(prs) if ln.key == key]
        c = corr[idx].astype(np.float64)
        mu = c.mean(0)
        tot = (c ** 2).sum()
        shares[key] = float(len(idx) * (mu ** 2).sum() / tot) if tot > 0 else 0.0
        out_c[idx] = copy[idx] + (c - mu).astype(np.float32)
    return out_c, out_n, shares


def train(src, train_lines, groups, tr, va_inner, m_idx, n_genes, dev, seed=0, max_steps=3000, patience=10):
    torch.manual_seed(seed)
    rng = np.random.default_rng(seed)
    model = r1.Adapter(m_idx, n_genes, src.basal).to(dev)
    opt = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    by_group: dict[str, dict[str, list]] = {}
    for p in tr:
        by_group.setdefault(groups[p[0].key], {}).setdefault(p[0].key, []).append(p)
    gkeys = sorted(by_group)
    best, best_state, best_step, bad, hist = -1e9, None, 0, 0, []
    for step in range(max_steps + 1):
        if step % 100 == 0:
            pred, _, _ = centred(model, src, va_inner, m_idx, n_genes, dev)
            vc = float(np.mean(r1.score(pred, va_inner)))
            hist.append({"step": step, "inner_val_cos": vc})
            if vc > best + 1e-5:
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
        ok = ~torch.isnan(y)
        y0, p0 = torch.where(ok, y, torch.zeros_like(y)), torch.where(ok, pred, torch.zeros_like(pred))
        rel = ((p0 - y0) ** 2).sum(1) / ((y0 ** 2).sum(1) + 1e-8)
        loss = (1 - r1.cos_masked(pred, y)).mean() + 0.1 * rel.mean()
        opt.zero_grad()
        loss.backward()
        opt.step()
    model.load_state_dict(best_state)
    return model, hist, best, best_step


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keys", type=Path, required=True)
    ap.add_argument("--extra", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--panel", type=Path, default=None, help="pert_counts.csv, for the descriptive panel subset")
    ap.add_argument("--folds", nargs="+", default=ORDER)
    a = ap.parse_args()
    out = a.out / "r3"
    out.mkdir(parents=True, exist_ok=False)
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    src, lines, groups = load_all(a.keys, a.extra)
    n_genes = src.d.shape[1]
    m_idx = np.where(~np.isnan(src.d).all(0))[0]
    split = r1.split_targets(src, lines, seed=SPLIT_SEED)
    panel = set()
    if a.panel:
        panel = {r[0] for r in list(csv.reader(a.panel.open(encoding="utf-8")))[1:]} - {"non-targeting"}
    rng = np.random.default_rng(0)
    folds, boot_means = {}, {}
    for g in a.folds:
        train_lines, inner_lines, test_lines, inner, dropped = fold_sets(lines, groups, g)
        tr = r1.pairs(src, train_lines, split["train"])
        va = r1.pairs(src, inner_lines, split["val"])
        te = r1.pairs(src, test_lines, split["test"])
        r1.log(f"fold {g}: train lines {len(train_lines)} (groups {sorted({groups[l.key] for l in train_lines})}), "
               f"inner {inner}, test lines {len(test_lines)}; pairs tr {len(tr)} inner-val {len(va)} test {len(te)}; "
               f"test targets {len({t for _, t in te})}")
        model, hist, best, best_step = train(src, train_lines, groups, tr, va, m_idx, n_genes, dev)
        torch.save(model.state_dict(), out / f"adapter3_{g}.pt")
        copy = r1.k562_predict(src, te, m_idx, n_genes)
        if best_step == 0:
            pred_c, pred_n, shares = copy, copy, {}
        else:
            pred_c, pred_n, shares = centred(model, src, te, m_idx, n_genes, dev)
        mean_basal = np.mean([ln.basal for ln in train_lines], 0).astype(np.float32)
        swap_lines = [r1.Line(ln.key, ln.targets, ln.d, mean_basal) for ln in test_lines]
        sw = {l.key: l for l in swap_lines}
        te_swap = [(sw[ln.key], t) for ln, t in te]
        pred_s = copy if best_step == 0 else centred(model, src, te_swap, m_idx, n_genes, dev)[0]
        preds = {"k562": copy, "adapter3": pred_c, "adapter3_nocenter": pred_n, "adapter3_swap": pred_s}
        pt = {k: r1.per_target(r1.score(v, te), te) for k, v in preds.items()}
        ts = sorted(pt["k562"])
        diffs = np.array([pt["adapter3"][t] - pt["k562"][t] for t in ts])
        boot_means[g] = diffs[rng.integers(0, len(diffs), (10000, len(diffs)))].mean(1)
        pan = [i for i, (_, t) in enumerate(te) if t in panel]
        folds[g] = {
            "inner_group": inner, "dropped_from_training": dropped, "best_step": best_step, "inner_best": best,
            "inner_copy": hist[0]["inner_val_cos"], "history": hist,
            "n_pairs": [len(tr), len(va), len(te)], "test_targets": len(ts),
            "test_cos": {k: float(np.mean(r1.score(v, te))) for k, v in preds.items()},
            "discrimination": {k: discrimination(v, te) for k, v in preds.items()},
            "common_share_test": shares,
            "diff": {f"{k}-k562": r1.boot(pt[k], pt["k562"]) for k in ("adapter3", "adapter3_nocenter", "adapter3_swap")},
            "diff_adapter3-swap": r1.boot(pt["adapter3"], pt["adapter3_swap"]),
            "panel_test_targets": len({te[i][1] for i in pan}),
            "panel_test_cos": ({k: float(np.mean(r1.score(v[pan], [te[i] for i in pan]))) for k, v in preds.items()}
                               if pan else None),
            "nan": any(bool(np.isnan(v).any()) for v in preds.values()),
        }
        r1.log(f"fold {g}: best step {best_step}; cos {json.dumps({k: round(v, 4) for k, v in folds[g]['test_cos'].items()})}; "
               f"diff {folds[g]['diff']['adapter3-k562']}")
        (out / "result.json").write_text(json.dumps({"folds": folds}, indent=2), encoding="utf-8")
    macro_draws = np.mean([boot_means[g] for g in folds], 0)
    macro = {
        "adapter3-k562": float(np.mean([folds[g]["diff"]["adapter3-k562"]["mean"] for g in folds])),
        "lo": float(np.quantile(macro_draws, 0.025)), "hi": float(np.quantile(macro_draws, 0.975)),
        "folds_positive": int(sum(folds[g]["diff"]["adapter3-k562"]["mean"] > 0 for g in folds)),
        "discrimination_adapter3-k562": float(np.mean([folds[g]["discrimination"]["adapter3"]
                                                       - folds[g]["discrimination"]["k562"] for g in folds])),
        "adapter3-swap": float(np.mean([folds[g]["diff_adapter3-swap"]["mean"] for g in folds])),
    }
    (out / "result.json").write_text(json.dumps({"folds": folds, "macro": macro}, indent=2), encoding="utf-8")
    r1.log("macro " + json.dumps(macro))


if __name__ == "__main__":
    main()
