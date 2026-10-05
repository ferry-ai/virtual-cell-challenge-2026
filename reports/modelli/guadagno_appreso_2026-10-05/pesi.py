"""Source-weight network (PROTOCOLLO_PESI.md): per target, softmax weights over source groups from control similarity
and consensus; init = the all transfer; cosine loss in the scorer geometry; leave-one-line-out on the cube.

    python pesi.py --cube <layout> --code <cube code> --out <dir>
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import guadagno as G  # noqa: E402

NG, STEPS = 6000, 300


def corr(a, b):
    ok = np.isfinite(a) & np.isfinite(b)
    return float(np.corrcoef(a[ok], b[ok])[0, 1])


def parts_and_features(C, groups, keys, commons, basal_x):
    """P (S, K, G) group means, F (S, K, 6) features, avail (S, K)."""
    cube = C.cube
    P, SD, CE = [], [], []
    for g in groups:
        m, s, c = G.group_stats(C, g, "all", keys, commons)
        P.append(m); SD.append(s); CE.append(c)
    P, SD, CE = np.stack(P), np.stack(SD), np.stack(CE)
    fin = np.isfinite(P)
    avail = fin.any(2)
    P0 = np.where(fin, P, 0).astype(np.float32)
    tot = P0.sum(0, keepdims=True)
    cnt = fin.sum(0, keepdims=True)
    others = np.divide(tot - P0, cnt - fin, out=np.zeros_like(P0), where=(cnt - fin) > 0)
    num = (P0 * others).sum(2)
    den = np.sqrt((P0 ** 2).sum(2) * (others ** 2).sum(2))
    cons = np.divide(num, den, out=np.zeros_like(num), where=den > 0)
    sim = np.array([corr(basal_x, G.basal_of(cube, cube.tables_of(g))) for g in groups], np.float32)
    msd = np.where(fin, SD, 0).sum(2) / np.maximum(fin.sum(2), 1)
    F = np.stack([np.broadcast_to(sim[:, None], avail.shape), np.log1p(CE), np.log(msd + 1e-4),
                  np.log(np.sqrt((P0 ** 2).sum(2)) + 1e-3), cons, fin.mean(2)], -1).astype(np.float32)
    return P, F, avail


class Net:
    def __init__(self, torch, dev, seed=0):
        torch.manual_seed(seed)
        nn = torch.nn
        self.t, self.dev = torch, dev
        self.m = nn.Sequential(nn.Linear(6, 16), nn.ReLU(), nn.Linear(16, 16), nn.ReLU(), nn.Linear(16, 1)).to(dev)
        with torch.no_grad():
            self.m[-1].weight.zero_(); self.m[-1].bias.zero_()

    def combine(self, P, F, avail, fin):
        t = self.t
        s = self.m(F).squeeze(-1)                                   # (S, K)
        s = s.masked_fill(~avail, -1e9)
        w = t.softmax(s, 0) * avail                                 # (S, K)
        num = (w[..., None] * P * fin).sum(0)
        den = (w[..., None] * fin).sum(0)
        return t.where(den > 0, num / den.clamp_min(1e-12), t.zeros_like(num)), w


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cube", type=Path, required=True)
    ap.add_argument("--code", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    if a.out.exists():
        raise FileExistsError(a.out)
    a.out.mkdir(parents=True)
    sys.path.insert(0, str(a.code))
    import arms
    import torch
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    C = G.Cubes(arms, a.cube)
    cube = C.cube
    rngb = np.random.default_rng(0)
    rec = {"lines": {}}
    for L in G.HELD:
        t0 = time.time()
        ctx = G.Context(C, L)
        rng = np.random.default_rng(0)
        train = []
        for h in cube.groups:
            if h == L:
                continue
            keys = sorted({k for t in cube.tables_of(h) for k in cube.keys_of(t)}, key=lambda k: G.hkey(k, "fit"))
            if len(keys) < G.MIN_TRAIN_KEYS:
                continue
            keys = keys[:G.MAX_TRAIN_KEYS]
            srcs = [g for g in C.groups("all", {L, h})]
            bl = G.basal_of(cube, cube.tables_of(h))
            P, F, av = parts_and_features(C, srcs, keys, ctx.commons, bl)
            y, _, _ = G.truth(C, h, keys)
            cols = rng.choice(len(cube.genes), NG, replace=False)
            x = 0.05 * np.expm1(np.nan_to_num(bl[cols]))
            d = (x / (1 + x)).astype(np.float32)
            own = G.own_gene_cols(cube, keys)
            ym = np.isfinite(y[:, cols]) & np.isfinite(bl[cols])[None]
            for i, o in enumerate(own):
                ym[i, cols == o] = False
            Pc = P[:, :, cols]
            train.append(dict(P=torch.tensor(np.nan_to_num(Pc), device=dev), fin=torch.tensor(np.isfinite(Pc), device=dev),
                              F=torch.tensor(F, device=dev), av=torch.tensor(av, device=dev),
                              y=torch.tensor(np.where(ym, np.nan_to_num(y[:, cols]), 0), device=dev),
                              ym=torch.tensor(ym, device=dev), d=torch.tensor(d, device=dev)))
        allF = torch.cat([b["F"][b["av"]] for b in train])
        mu, sd = allF.mean(0), allF.std(0) + 1e-6
        net = Net(torch, dev)
        opt = torch.optim.Adam(net.m.parameters(), lr=3e-3, weight_decay=1e-4)

        def loss_of(b):
            T, _ = net.combine(b["P"], (b["F"] - mu) / sd, b["av"], b["fin"])
            p = T * b["d"] * b["ym"]
            q = b["y"] * b["d"]
            c = (p * q).sum(1) / (p.norm(dim=1) * q.norm(dim=1) + 1e-12)
            ok = (p.norm(dim=1) > 0) & (q.norm(dim=1) > 0)
            return -c[ok].mean()
        with torch.no_grad():
            l0 = float(sum(loss_of(b) for b in train) / len(train))
        for step in range(STEPS):
            loss = sum(loss_of(b) for b in train) / len(train)
            opt.zero_grad(); loss.backward(); opt.step()
        lf = float(loss)
        # apply to L
        keys = G.eval_keys(C, L)
        st = G.transfer(C, "all", keys, ctx.commons, {L})
        keys = [k for k, s in zip(keys, st["n"].max(1) > 0) if s][:G.MAX_EVAL]
        Tall = G.transfer(C, "all", keys, ctx.commons, {L})["T"]
        bl = G.basal_of(cube, cube.tables_of(L))
        srcs = C.groups("all", {L})
        P, F, av = parts_and_features(C, srcs, keys, ctx.commons, bl)
        Pt, fin = torch.tensor(np.nan_to_num(P), device=dev), torch.tensor(np.isfinite(P), device=dev)
        Ft, avt = (torch.tensor(F, device=dev) - mu) / sd, torch.tensor(av, device=dev)
        with torch.no_grad():
            T0 = Net(torch, dev).combine(Pt, Ft, avt, fin)[0].cpu().numpy()
            Tw, w = net.combine(Pt, Ft, avt, fin)
            Tw, w = Tw.cpu().numpy(), w.cpu().numpy()
        parity = bool(np.allclose(T0, np.nan_to_num(Tall), atol=1e-5))
        if not parity:
            raise SystemExit(f"{L}: init parity with all failed")
        y, ysd, _ = G.truth(C, L, keys)
        x = 0.05 * np.expm1(np.nan_to_num(bl))
        mask = np.isfinite(bl)[None] & np.isfinite(y)
        for i, o in enumerate(G.own_gene_cols(cube, keys)):
            if o >= 0:
                mask[i, o] = False
        ref = np.sqrt((np.where(mask, np.nan_to_num(Tall), 0) ** 2).sum(1))
        m0 = G.measures(np.nan_to_num(Tall), y, ysd ** 2, x, mask, ref)
        m1 = G.measures(Tw, y, ysd ** 2, x, mask, ref)
        wmean = {g: float(w[i][av[i]].mean()) for i, g in enumerate(srcs) if av[i].any()}
        line = {"targets": len(keys), "init_parity": parity, "train_loss_init": l0, "train_loss_final": lf,
                "cos_all": float(np.nanmean(m0["cos"])), "cos_pesi": float(np.nanmean(m1["cos"])),
                "pds_all": float(np.mean(m0["pds"])), "pds_pesi": float(np.mean(m1["pds"])),
                "diff_cos": G.boot_diff(m1["cos"], m0["cos"], rngb), "diff_pds": G.boot_diff(m1["pds"], m0["pds"], rngb),
                "mean_weight_by_group": wmean, "seconds": round(time.time() - t0, 1)}
        rec["lines"][L] = line
        print(L, json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in line.items()
                             if k not in ("diff_cos", "diff_pds", "mean_weight_by_group")}),
              "| dcos", {k: round(v, 4) for k, v in line["diff_cos"].items() if k != "n"},
              "| dpds", {k: round(v, 4) for k, v in line["diff_pds"].items() if k != "n"},
              "| w", {g: round(v, 3) for g, v in wmean.items()}, flush=True)
        (a.out / "result.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    Ls = rec["lines"].values()
    mean = float(np.mean([d["diff_cos"]["mean"] for d in Ls]))
    pos = sum(d["diff_cos"]["lo90"] > 0 for d in Ls)
    pds_ok = all(d["diff_pds"]["mean"] >= -0.005 for d in Ls)
    rec["rule"] = {"mean_cos_diff": mean, "lines_lo90_positive": int(pos), "pds_ok_all": bool(pds_ok),
                   "passed": bool(mean >= 0.005 and pos >= 3 and pds_ok)}
    (a.out / "result.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    print("rule:", json.dumps(rec["rule"]), flush=True)


if __name__ == "__main__":
    main()
