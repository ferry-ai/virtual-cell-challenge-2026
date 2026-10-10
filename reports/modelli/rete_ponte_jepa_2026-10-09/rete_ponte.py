"""Bridge network (JEPA latent prediction + LeJEPA's SIGReg) on top of the `all` transfer: PROTOCOLLO.md in this folder.

Leave-one-line-out on Davide's cube r2 with the stage-1 bench of guadagno_appreso_2026-10-05 (same targets, same
measures, same bootstrap, imported unchanged). The network starts exactly at T_all (uniform attention, zero residual).

    python rete_ponte.py --cube <cube_r2_layout> --code <cube code> --cache <dir> --out <new dir> [--held H1,...]
    python rete_ponte.py --selftest
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "guadagno_appreso_2026-10-05"))
import guadagno as gd  # noqa: E402  (the stage-1 bench, imported unchanged)

F32 = np.float32
MIN_KEYS, MAX_KEYS_PER_GROUP, VAL_PCT = 50, 1500, 15
D_LAT, D_CTX, RANK = 256, 64, 64
TAU_NCE, W_NCE, W_JEPA, LAMBDA_SIG = 0.1, 0.5, 0.1, 0.05
BATCH, MAX_EPOCHS, PATIENCE, LR, WD = 128, 30, 4, 1e-3, 1e-2


# ---------------------------------------------------------------- SIGReg (LeJEPA, Balestriero & LeCun 2025)
def sigreg(z: torch.Tensor, n_dir: int = 256, t_max: float = 3.0, n_t: int = 17, generator=None) -> torch.Tensor:
    """Sketched isotropic Gaussian regularisation: Epps-Pulley statistic of random 1-D projections against N(0, 1).

    EP = N * integral |phi_emp(t) - exp(-t^2/2)|^2 exp(-t^2/2) dt over [-t_max, t_max] (trapezoid on [0, t_max], x2 by
    symmetry), averaged over `n_dir` unit directions drawn anew at every call."""
    n, d = z.shape
    a = torch.randn(d, n_dir, device=z.device, generator=generator)
    a = a / a.norm(dim=0, keepdim=True)
    p = z @ a                                                    # (N, n_dir)
    t = torch.linspace(0.0, t_max, n_t, device=z.device)
    phi = torch.exp(-0.5 * t ** 2)
    xt = p.unsqueeze(-1) * t                                     # (N, n_dir, n_t)
    err = (torch.cos(xt).mean(0) - phi) ** 2 + torch.sin(xt).mean(0) ** 2
    tw = torch.full((n_t,), t_max / (n_t - 1), device=z.device)
    tw[0] = tw[-1] = tw[0] / 2
    return (2.0 * (err * phi * tw).sum(-1) * n).mean()


# ---------------------------------------------------------------- cache of the cube (group means for every key)
def build_cache(C, cache: Path, log) -> dict:
    """S[g] = arms.group_mean of shrunk minus each table's mean (the transfer's sources); R[g] = raw truth group mean
    (guadagno.truth); cells of R; basal per group. Every group is cached; a fold never reads its own group for fitting."""
    cube = C.cube
    keys = sorted({k for t in cube.tables for k in cube.keys_of(t)})
    groups = list(cube.groups)
    G = len(cube.genes)
    meta = {"keys": keys, "groups": groups, "genes": G}
    if (cache / "meta.json").exists():
        return json.loads((cache / "meta.json").read_text())
    cache.mkdir(parents=True, exist_ok=True)
    commons = gd.table_means(cube, set())
    S = np.lib.format.open_memmap(cache / "S.npy", "w+", F32, (len(groups), len(keys), G))
    R = np.lib.format.open_memmap(cache / "R.npy", "w+", F32, (len(groups), len(keys), G))
    cells = np.zeros((len(groups), len(keys)), F32)
    basal = np.zeros((len(groups), G), F32)
    for i, g in enumerate(groups):
        t0 = time.time()
        S[i], _, _ = gd.group_stats(C, g, "all", keys, commons)
        R[i], _, c = gd.group_stats(C, g, "all", keys, {}, kind="raw", gamma=0.0)
        cells[i] = c
        basal[i] = gd.basal_of(cube, cube.tables_of(g))
        log(f"  cache {g}: {time.time() - t0:.0f} s")
    S.flush(); R.flush()
    np.save(cache / "cells.npy", cells)
    np.save(cache / "basal.npy", basal)
    (cache / "meta.json").write_text(json.dumps(meta))
    return meta


# ---------------------------------------------------------------- the network
class Ponte(nn.Module):
    def __init__(self, G: int, gsd: torch.Tensor, basal_mu: torch.Tensor):
        super().__init__()
        self.register_buffer("gsd", gsd)
        self.register_buffer("basal_mu", basal_mu)
        self.E = nn.Linear(G, D_LAT)                              # effect encoder (JEPA context/target encoder)
        self.B = nn.Sequential(nn.Linear(G, D_CTX), nn.GELU(), nn.Linear(D_CTX, D_CTX))
        self.att = nn.Sequential(nn.Linear(2 * D_CTX + D_LAT, 128), nn.GELU(), nn.Linear(128, 1))
        self.pred = nn.Sequential(nn.Linear(D_LAT + D_CTX, 256), nn.GELU(), nn.Linear(256, D_LAT))
        self.to_r = nn.Linear(D_LAT, RANK)
        self.U = nn.Parameter(torch.zeros(G, RANK))               # gene loadings of the residual: zero = T_all
        self.head = nn.Linear(D_LAT, D_LAT)                       # latent prediction head for the JEPA term
        for m in (self.att[-1], self.pred[-1]):
            nn.init.zeros_(m.weight); nn.init.zeros_(m.bias)

    def encode(self, e: torch.Tensor) -> torch.Tensor:
        return self.E(e / self.gsd)

    def ctx(self, b: torch.Tensor) -> torch.Tensor:
        return self.B(torch.nan_to_num(b - self.basal_mu))

    def forward(self, src: torch.Tensor, b_src: torch.Tensor, b_tgt: torch.Tensor, residual: bool = True):
        """src (S, B, G) group means of the sources (NaN where unmeasured); b_src (S, G); b_tgt (G,)."""
        ok = torch.isfinite(src)
        e = torch.nan_to_num(src)
        avail = ok.any(-1)                                        # (S, B)
        z = self.encode(e)                                        # (S, B, D)
        cs = self.ctx(b_src)                                      # (S, C)
        ct = self.ctx(b_tgt[None])[0]                             # (C,)
        S, Bn = avail.shape
        h = torch.cat([ct.expand(S, Bn, -1), cs[:, None].expand(-1, Bn, -1), z], -1)
        logit = self.att(h).squeeze(-1).masked_fill(~avail, -1e9)
        a = torch.softmax(logit, 0) * avail                       # (S, B)
        w = a[..., None] * ok
        den = w.sum(0)
        base = torch.where(den > 0, (w * e).sum(0) / den.clamp_min(1e-12), torch.zeros_like(den))
        zbar = (a[..., None] * z).sum(0) / a.sum(0).clamp_min(1e-12)[:, None]
        zhat = zbar + self.pred(torch.cat([zbar, ct.expand(Bn, -1)], -1))
        out = base + (self.to_r(zhat) @ self.U.T if residual else 0.0)
        return out, zhat, z[avail]


def losses(model, out, zhat, zsrc, y, ym, wgt, gen):
    dp = out * wgt * ym
    dt = torch.nan_to_num(y) * wgt * ym
    pn = F.normalize(dp, dim=1, eps=1e-8)
    tn = F.normalize(dt, dim=1, eps=1e-8)
    l_cos = (1 - (pn * tn).sum(1)).mean()
    sim = pn @ tn.T / TAU_NCE
    l_nce = F.cross_entropy(sim, torch.arange(len(sim), device=sim.device))
    with torch.no_grad():
        zt = model.encode(torch.nan_to_num(y))                   # stop-gradient target latent
    l_lat = F.mse_loss(F.normalize(model.head(zhat), dim=1), F.normalize(zt, dim=1)) * zt.shape[1]
    l_sig = sigreg(zsrc, generator=gen) if len(zsrc) > 8 else zsrc.new_zeros(())
    l_jepa = (1 - LAMBDA_SIG) * l_lat + LAMBDA_SIG * l_sig
    total = l_cos + W_NCE * l_nce + W_JEPA * l_jepa
    return total, {"cos": float(l_cos.detach()), "nce": float(l_nce.detach()), "lat": float(l_lat.detach()),
                   "sig": float(l_sig.detach())}


# ---------------------------------------------------------------- one fold
class Fold:
    def __init__(self, C, cache: Path, meta: dict, held: str, dev: str, log):
        cube = C.cube
        self.C, self.held, self.dev, self.log = C, held, dev, log
        self.groups = meta["groups"]
        self.keys = meta["keys"]
        self.kpos = {k: i for i, k in enumerate(self.keys)}
        S = np.load(cache / "S.npy", mmap_mode="r")
        R = np.load(cache / "R.npy", mmap_mode="r")
        self.cells = np.load(cache / "cells.npy")
        self.basal = torch.tensor(np.load(cache / "basal.npy"), device=dev)
        L = self.groups.index(held) if held is not None else -1     # None: production fit on every group
        self.L = L
        log(f"  loading cache to {dev} (fp16), fold {held}: group {L} never read for fitting")
        self.S = torch.empty(S.shape, dtype=torch.float16, device=dev)
        self.R = torch.empty(R.shape, dtype=torch.float16, device=dev)
        for g in range(S.shape[0]):
            self.S[g] = torch.from_numpy(np.asarray(S[g])).to(dev).half()
            self.R[g] = torch.from_numpy(np.asarray(R[g])).to(dev).half()
        own = gd.own_gene_cols(cube, self.keys)
        self.own = torch.tensor(own, device=dev)
        fit = [i for i in range(len(self.groups)) if i != L]
        ss = torch.zeros(self.S.shape[-1], device=dev)
        for g in fit:
            ss += (torch.nan_to_num(self.S[g].float(), nan=0.0) ** 2).mean(0) / len(fit)
        gsd = torch.sqrt(ss).clamp_min(1e-3)
        bmu = torch.nanmean(self.basal[fit], 0)
        self.gsd, self.bmu = gsd, bmu
        self.train, self.val = {}, {}
        for h in fit:
            g = self.groups[h]
            ks = sorted({k for t in cube.tables_of(g) for k in cube.keys_of(t)}, key=lambda k: gd.hkey(k, "fit"))
            idx = [self.kpos[k] for k in ks if self.cells[h, self.kpos[k]] >= gd.MIN_TRUTH_CELLS]
            if len(idx) < MIN_KEYS:
                log(f"  train group {g}: {len(idx)} keys, skipped")
                continue
            idx = idx[:MAX_KEYS_PER_GROUP]
            va = [i for i in idx if int(gd.hkey(self.keys[i], "val"), 16) % 100 < VAL_PCT]
            tr = [i for i in idx if i not in set(va)]
            self.train[h], self.val[h] = tr, va
            log(f"  train group {g}: {len(tr)} train, {len(va)} val keys")

    def sources(self, h: int) -> list[int]:
        return [g for g in range(len(self.groups)) if g not in (self.L, h)]

    def batch(self, model, h, idx, residual=True):
        srcg = self.sources(h)
        ii = torch.tensor(idx, device=self.dev)
        src = self.S[torch.tensor(srcg, device=self.dev)[:, None], ii[None, :]].float()
        out, zhat, zsrc = model(src, self.basal[srcg], self.basal[h], residual)
        y = self.R[h, ii].float()
        bh = self.basal[h]
        x = 0.05 * torch.expm1(torch.nan_to_num(bh))
        wgt = (x / (1 + x))[None]
        ym = torch.isfinite(y) & torch.isfinite(bh)[None]
        own = self.own[ii]
        ym[torch.arange(len(idx), device=self.dev)[own >= 0], own[own >= 0]] = False
        return out, zhat, zsrc, y, ym.float(), wgt

    def fit(self, seed: int = 0):
        torch.manual_seed(seed)
        gen = torch.Generator(device=self.dev).manual_seed(seed)
        rng = np.random.default_rng(seed)
        G = self.S.shape[-1]
        model = Ponte(G, self.gsd, self.bmu).to(self.dev)
        opt = torch.optim.AdamW(model.parameters(), lr=LR, weight_decay=WD)
        best, best_state, bad, hist = math.inf, None, 0, []
        for ep in range(MAX_EPOCHS):
            model.train()
            jobs = [(h, b) for h, tr in self.train.items()
                    for b in np.array_split(rng.permutation(tr), max(1, len(tr) // BATCH))]
            rng.shuffle(jobs)
            agg = {"cos": 0.0, "nce": 0.0, "lat": 0.0, "sig": 0.0}
            for h, b in jobs:
                out, zhat, zsrc, y, ym, wgt = self.batch(model, h, list(b))
                loss, d = losses(model, out, zhat, zsrc, y, ym, wgt, gen)
                opt.zero_grad(set_to_none=True)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                opt.step()
                for k in agg:
                    agg[k] += d[k] / len(jobs)
            model.eval()
            with torch.no_grad():
                vl, nv = 0.0, 0
                for h, va in self.val.items():
                    for b in np.array_split(np.array(va), max(1, len(va) // BATCH)):
                        out, zhat, zsrc, y, ym, wgt = self.batch(model, h, list(b))
                        _, d = losses(model, out, zhat, zsrc, y, ym, wgt, gen)
                        vl += (d["cos"] + W_NCE * d["nce"]) * len(b)
                        nv += len(b)
                vl /= max(nv, 1)
            hist.append({"epoch": ep, **{k: round(v, 5) for k, v in agg.items()}, "val": round(vl, 5)})
            self.log(f"    epoch {ep}: " + json.dumps(hist[-1]))
            if vl < best - 1e-4:
                best, bad = vl, 0
                best_state = {k: v.detach().clone() for k, v in model.state_dict().items()}
            else:
                bad += 1
                if bad >= PATIENCE:
                    break
        model.load_state_dict(best_state)
        model.eval()
        return model, hist

    @torch.no_grad()
    def predict(self, model, keys, residual=True) -> np.ndarray:
        srcg = [g for g in range(len(self.groups)) if g != self.L]
        outs = []
        for b0 in range(0, len(keys), BATCH):
            ii = torch.tensor([self.kpos[k] for k in keys[b0:b0 + BATCH]], device=self.dev)
            src = self.S[torch.tensor(srcg, device=self.dev)[:, None], ii[None, :]].float()
            out, _, _ = model(src, self.basal[srcg], self.basal[self.L], residual)
            outs.append(out.cpu().numpy())
        return np.concatenate(outs).astype(F32)


def tall_from_cache(cache: Path, groups: list, kpos: dict, held: str, keys) -> np.ndarray:
    """Equal-weight mean over source groups of their group means, read in float32 from the cache (parity check)."""
    S = np.load(cache / "S.npy", mmap_mode="r")
    ii = np.array([kpos[k] for k in keys])
    P = np.stack([np.asarray(S[g][ii]) for g, name in enumerate(groups) if name != held])
    ok = np.isfinite(P)
    n = ok.sum(0)
    return np.divide(np.where(ok, P, 0).sum(0), n, out=np.full(P.shape[1:], np.nan, F32), where=n > 0)


# ---------------------------------------------------------------- rule and main
def rule(record: dict, arm: str = "rete") -> dict:
    lines = record["lines"]
    diffs, above, pds, pds_low = [], 0, [], False
    for L, d in lines.items():
        c, p = d["diff"][f"{arm}-all"]["cos"], d["diff"][f"{arm}-all"]["pds"]
        diffs.append(c["mean"])
        above += int(c["lo90"] is not None and c["lo90"] > 0)
        pds.append(p["mean"])
        pds_low |= p["mean"] < -0.02
    ok = (len(lines) == 5 and float(np.mean(diffs)) >= 0.015 and above >= 3 and float(np.mean(pds)) >= 0
          and not pds_low)
    return {"arm": arm, "mean_cos_diff": float(np.mean(diffs)), "lines_lo90_above_0": above, "mean_pds_diff": float(np.mean(pds)),
            "any_line_pds_below_-0.02": bool(pds_low), "n_lines": len(lines), "passed": bool(ok)}


def selftest() -> None:
    g = torch.Generator().manual_seed(0)
    gauss = torch.randn(1024, 64, generator=g)
    print("sigreg gaussian", float(sigreg(gauss, generator=g)), "collapsed", float(sigreg(torch.ones(1024, 64), generator=g)),
          "scaled 0.1", float(sigreg(0.1 * gauss, generator=g)), "rank1", float(sigreg(gauss[:, :1].repeat(1, 64), generator=g)))
    G = 50
    m = Ponte(G, torch.ones(G), torch.zeros(G))
    src = torch.randn(4, 3, G)
    src[1, 0, :10] = float("nan")
    src[3, 2] = float("nan")
    out, _, _ = m(src, torch.randn(4, G), torch.randn(G))
    ok = torch.isfinite(src)
    T = torch.where(ok, src, torch.zeros_like(src)).sum(0) / ok.sum(0).clamp_min(1)
    print("parity at init (max abs diff vs equal-weight mean):", float((out - T).abs().max()))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cube", type=Path)
    ap.add_argument("--code", type=Path)
    ap.add_argument("--cache", type=Path)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--held", default=",".join(gd.HELD))
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--w-jepa", type=float, default=None, help="ABLAZIONE_JEPA: override W_JEPA")
    ap.add_argument("--lambda-sig", type=float, default=None, help="ABLAZIONE_JEPA: override LAMBDA_SIG")
    ap.add_argument("--seeds", default="", help="EMENDAMENTO_R3: comma-separated seeds; predictions are averaged")
    ap.add_argument("--rule-arm", default="rete", help="r1: rete; r2 (EMENDAMENTO_R2.md): rete_centrata")
    a = ap.parse_args()
    if a.selftest:
        selftest()
        return
    global W_JEPA, LAMBDA_SIG
    if a.w_jepa is not None:
        W_JEPA = a.w_jepa
    if a.lambda_sig is not None:
        LAMBDA_SIG = a.lambda_sig
    if a.out.exists():
        raise FileExistsError(a.out)
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
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    meta = build_cache(C, a.cache, log)
    record = {"cube_manifest_sha256": gd.sha(a.cube / "manifest.json"), "groups": meta["groups"], "device": dev,
              "constants": {"D_LAT": D_LAT, "RANK": RANK, "TAU_NCE": TAU_NCE, "W_NCE": W_NCE, "W_JEPA": W_JEPA,
                            "LAMBDA_SIG": LAMBDA_SIG, "BATCH": BATCH, "LR": LR, "WD": WD}, "lines": {}}
    rng_boot = np.random.default_rng(0)
    kpos = {k: i for i, k in enumerate(meta["keys"])}
    for held in a.held.split(","):
        t0 = time.time()
        log(f"== {held}")
        ctx = gd.Context(C, held)
        keys = gd.eval_keys(C, held)
        st = gd.transfer(C, "all", keys, ctx.commons, {held})
        keys = [k for k, s in zip(keys, st["n"].max(1) > 0) if s][:gd.MAX_EVAL]
        st = gd.transfer(C, "all", keys, ctx.commons, {held})
        mine = tall_from_cache(a.cache, meta["groups"], kpos, held, keys)
        if not np.allclose(np.nan_to_num(st["T"], nan=9), np.nan_to_num(mine, nan=9), atol=1e-4):
            raise SystemExit(f"{held}: T_all parity with guadagno.transfer failed")
        log(f"  {len(keys)} targets; T_all parity with guadagno.transfer ok")
        fold = Fold(C, a.cache, meta, held, dev, log)
        seeds = [int(s) for s in a.seeds.split(",")] if a.seeds else [a.seed]
        P = Pw = 0.0
        hist = []
        for s in seeds:
            model, h = fold.fit(seed=s)
            P = P + fold.predict(model, keys) / len(seeds)
            Pw = Pw + fold.predict(model, keys, residual=False) / len(seeds)
            hist.append({"seed": s, "history": h})
        res_part = P - Pw                                    # the residual U r, per target
        Pc = Pw + res_part - res_part.mean(0, keepdims=True)  # EMENDAMENTO_R2: centred over the panel's targets
        y, ysd, ycells = gd.truth(C, held, keys)
        bl = gd.basal_of(cube, cube.tables_of(held))
        x = 0.05 * np.expm1(np.nan_to_num(bl))
        own = gd.own_gene_cols(cube, keys)
        mask = np.isfinite(bl)[None, :] & np.isfinite(y)
        for i, o in enumerate(own):
            if o >= 0:
                mask[i, o] = False
        Tall = np.nan_to_num(st["T"])
        ref = np.sqrt((np.where(mask, Tall, 0) ** 2).sum(1))
        arms_pred = {"all": Tall, "rete": P, "rete_pesi": Pw, "rete_centrata": Pc}
        res = {n: gd.measures(p, y, ysd ** 2, x, mask, ref) for n, p in arms_pred.items()}
        line = {"targets": len(keys), "epochs": len(hist), "history": hist,
                "per_target": {f"{n}_{m}": [None if not np.isfinite(v) else float(v) for v in r[m]]
                               for n, r in res.items() for m in ("cos", "pds")},
                "arms": {n: {m: float(np.nanmean(v)) for m, v in r.items()} for n, r in res.items()}, "diff": {}}
        for p in ("rete", "rete_pesi", "rete_centrata"):
            line["diff"][f"{p}-all"] = {m: gd.boot_diff(res[p][m], res["all"][m], rng_boot) for m in ("cos", "pds", "mse")}
        record["lines"][held] = line
        log("  arms: " + json.dumps({n: {m: round(v, 4) for m, v in d.items()} for n, d in line["arms"].items()}))
        log(f"  {a.rule_arm}-all: " + json.dumps(line["diff"][f"{a.rule_arm}-all"]))
        log(f"  {time.time() - t0:.0f} s")
        torch.save({k: v.cpu() for k, v in model.state_dict().items()}, a.out / f"model_{held}.pt")
        (a.out / "result.json").write_text(json.dumps(record, indent=1), encoding="utf-8")
        del fold, model
        torch.cuda.empty_cache()
    record["seed"] = a.seeds or a.seed
    record["rule"] = rule(record, a.rule_arm)
    (a.out / "result.json").write_text(json.dumps(record, indent=1), encoding="utf-8")
    log("rule: " + json.dumps(record["rule"]))


if __name__ == "__main__":
    main()
