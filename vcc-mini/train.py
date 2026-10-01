"""Train TransferNet on one fold and one seed; evaluate it against the references on the held-out line.

    python train.py --held HepG2 --fold 0 --seed 0 --out runs/hepg2_f0_s0

A fold holds out one cell-line group (all its experiments) and one fifth of the targets.
Selection (early stopping, reference amplitudes, the choice between the two transfer references)
uses only the inner-validation targets in the training lines. The held-out line is read once,
at the end.

Written to <out>/:
    results.json   configuration, counts, curve, summary metrics, paired bootstrap intervals
    per_target.npz per-target metrics of every method and regime, for aggregate.py

Methods compared on the same pairs:
    zero             no change
    train_mean       mean training effect, the same vector for every target
    oracle_mean      mean effect of the held-out line's evaluated targets (uses test labels:
                     the analogue of the scorer's 0 anchor, a reference and not a method)
    transfer_simple  mean over source groups of the source effects x amplitude fitted on validation
    transfer_gamma1  as above after subtracting each source line's mean training effect
                     (the team's gamma = 1 centring, computed on training targets only)
    replicate        K562 only: the other K562 experiment, same targets (a between-experiment
                     ceiling, lower than the scorer's within-experiment replicate)
    model            TransferNet
Neither transfer reference is the t22 recipe: no shrinkage, no reliability weights, no cis module.

Uncertainty (P1): for each regime, model minus each reference, per target; 2,000 paired bootstrap
resamples of the targets give a 95% interval of the mean difference. Seeds are combined in
aggregate.py.
"""
import argparse
import hashlib
import json
import time
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

from data import Fold, Mini
from model import TransferNet, loss_fn

ROOT = Path(__file__).resolve().parent
C_EVAL_SEED = 12345          # the C-regime subsample is the same for every training seed
N_BOOT = 2000


# --------------------------------------------------------------------------- metrics
def per_target(P: torch.Tensor, Y: torch.Tensor, gmask: torch.Tensor, pds_cols: torch.Tensor) -> dict:
    """Per-target vectors. pds_rank: cosine-distance rank of the own truth among the evaluated
    targets, with every evaluated target's gene removed (as the scorer removes panel genes);
    ties count half; 0 is perfect, 0.5 is chance."""
    m = gmask.float()
    mse = ((P - Y) ** 2 * m).sum(1) / m.sum(1)
    cos = (F.normalize(P * m, dim=1) * F.normalize(Y * m, dim=1)).sum(1)
    Pc, Yc = F.normalize(P[:, pds_cols], dim=1), F.normalize(Y[:, pds_cols], dim=1)
    D = 1 - Pc @ Yc.T
    d = D.diag()[:, None]
    rank = ((D < d).sum(1) + 0.5 * ((D == d).sum(1) - 1)) / max(D.shape[0] - 1, 1)
    k = min(100, Y.shape[1])
    top = (Y.abs() * m).topk(k, dim=1).indices
    ys, ps = Y.gather(1, top).sign(), P.gather(1, top).sign()
    return {"mse": mse, "cosine": cos, "pds_rank": rank.float(),
            "sign_top100": (ys == ps).float().mean(1), "down_top100": (ys < 0).float().mean(1)}


def summary(v: dict) -> dict:
    return {k: float(x.mean()) for k, x in v.items()} | {"n": int(len(v["mse"]))}


def paired_ci(model: np.ndarray, ref: np.ndarray, rng) -> dict:
    """Mean of (model - ref) per target, with a 95% paired bootstrap interval."""
    diff = model - ref
    idx = rng.integers(0, len(diff), size=(N_BOOT, len(diff)))
    boots = diff[idx].mean(1)
    return {"mean": float(diff.mean()), "lo": float(np.quantile(boots, 0.025)),
            "hi": float(np.quantile(boots, 0.975))}


# --------------------------------------------------------------------------- helpers
def run_batches(ds, pairs, allowed, load, fn, bs=32, **kw):
    outs = []
    for i in range(0, len(pairs), bs):
        outs.append(fn(ds.batch(pairs[i: i + bs], allowed, load, **kw)))
    return {k: torch.cat([o[k] for o in outs]) for k in outs[0]}


def transfer_refs(b: dict) -> dict:
    """Mean over the source groups present, raw and gamma = 1 centred."""
    m = b["mask"][:, :, None].float()
    n = m.sum(1).clamp(min=1)
    out = {"transfer_simple": (b["sd"] * m).sum(1) / n}
    if "sc" in b:
        out["transfer_gamma1"] = ((b["sd"] - b["sc"]) * m).sum(1) / n
    return out


def amplitude(T: torch.Tensor, Y: torch.Tensor) -> float:
    return float((T * Y).sum() / (T ** 2).sum().clamp(min=1e-12))


# --------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=str(ROOT / "mini"))
    ap.add_argument("--held", required=True)
    ap.add_argument("--fold", type=int, default=0)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", required=True)
    ap.add_argument("--epochs", type=int, default=40)
    ap.add_argument("--patience", type=int, default=5)
    ap.add_argument("--bs", type=int, default=16)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--d", type=int, default=64)
    ap.add_argument("--k-prog", type=int, default=32)
    ap.add_argument("--k-readout", type=int, default=64)
    ap.add_argument("--lam-cos", type=float, default=0.5)
    ap.add_argument("--gene-res", action="store_true", help="ablation: learned vector per gene")
    ap.add_argument("--max-c-eval", type=int, default=1000)
    ap.add_argument("--max-train-pairs", type=int, default=0,
                    help="smoke runs only: keep at most this many training pairs of each kind (0 = all)")
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)          # never overwrite a run
    torch.manual_seed(args.seed)
    rng = np.random.default_rng(args.seed)
    t0 = time.time()

    ds = Mini(Path(args.data), args.device)
    sp = ds.split(Fold(args.held, args.fold), seed=args.seed)
    tl = sp["train_lines"]
    load, _ = ds.readout_svd(tl, sp["train_t"], k=args.k_readout)

    # gamma = 1 centring: each training line's mean effect over *training* targets.
    line_mean = {li: torch.stack([ds.delta[li][i] for t, i in ds.row[li].items() if t in sp["train_t"]]).mean(0)
                 for li in tl}

    with_src = [p for p in sp["train"] if ds.sources(p[0], p[1], tl)]
    no_src = [p for p in sp["train"] if not ds.sources(p[0], p[1], tl)]
    val = [p for p in sp["val"] if ds.sources(p[0], p[1], tl)]
    if args.max_train_pairs:
        cut = lambda ps: [ps[i] for i in sorted(rng.choice(len(ps), min(len(ps), args.max_train_pairs), replace=False))] if ps else ps
        with_src, no_src, val = cut(with_src), cut(no_src), cut(val)

    model = TransferNet(load, d=args.d, k_prog=args.k_prog, gene_res=args.gene_res).to(args.device)
    n_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
    opt = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=1e-4)
    amp = dict(device_type="cuda", dtype=torch.bfloat16, enabled=args.device == "cuda")

    def val_loss():
        model.eval()
        tot, n = 0.0, 0
        with torch.no_grad(), torch.autocast(**amp):
            for i in range(0, len(val), 32):
                b = ds.batch(val[i: i + 32], tl, load)
                tot += float(loss_fn(model(**b).float(), b["y"], b["w"], b["gmask"], args.lam_cos)) * len(b["y"])
                n += len(b["y"])
        return tot / max(n, 1)

    curve, best, bad = [], float("inf"), 0
    ckpt = out / "best.pt"
    for ep in range(args.epochs):
        model.train()
        pick = rng.choice(len(no_src), size=min(len(with_src), len(no_src)), replace=False) if no_src else []
        epoch = with_src + [no_src[i] for i in pick]
        rng.shuffle(epoch)
        tr = 0.0
        for i in range(0, len(epoch), args.bs):
            b = ds.batch(epoch[i: i + args.bs], tl, load, train=True, rng=rng)
            with torch.autocast(**amp):
                loss = loss_fn(model(**b).float(), b["y"], b["w"], b["gmask"], args.lam_cos)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            tr += float(loss.detach()) * len(b["y"])
        vl = val_loss()
        curve.append(dict(epoch=ep, train=tr / len(epoch), val=vl, seconds=round(time.time() - t0)))
        print(curve[-1], flush=True)
        if vl < best - 1e-4:
            best, bad = vl, 0
            torch.save(model.state_dict(), ckpt)
        else:
            bad += 1
            if bad >= args.patience:
                break
    model.load_state_dict(torch.load(ckpt))
    model.eval()

    def refs_for(pairs, override=None, **kw):
        def f(b):
            with torch.no_grad(), torch.autocast(**amp):
                pred = model(**b).float()
            o = dict(model=pred, y=b["y"], g=b["gmask"], sd=b["sd"], mask=b["mask"])
            if "sc" in b:
                o["sc"] = b["sc"]
            return o
        centre = line_mean if override is None else None
        return run_batches(ds, pairs, tl, load, f, src_override=override, line_centre=centre, **kw)

    # Reference amplitudes and the choice between the two transfer references: validation only.
    rv = refs_for(val)
    Tv = transfer_refs(rv)
    Yv = rv["y"] * rv["g"]
    amps = {k: amplitude(T * rv["g"], Yv) for k, T in Tv.items()}
    val_mse = {k: float((((amps[k] * T - rv["y"]) ** 2) * rv["g"]).sum(1).div(rv["g"].sum(1)).mean())
               for k, T in Tv.items()}
    best_ref = min(val_mse, key=val_mse.get)

    train_mean = torch.stack([ds.delta[q][ds.row[q][t]] for t, q in sp["train"]]).mean(0)
    c_rng = np.random.default_rng(C_EVAL_SEED)
    s_rng = np.random.default_rng(C_EVAL_SEED + 1)
    boot_rng = np.random.default_rng(C_EVAL_SEED + 2)

    results, arrays = {}, {}
    for q in sp["held_lines"]:
        key = ds.keys[q]
        test = [(t, q) for t in ds.row[q] if t in sp["test_t"]]
        seen = sorted((t, q) for t in ds.row[q] if t in sp["train_t"] | sp["val_t"] and ds.sources(t, q, tl))
        if len(seen) > args.max_c_eval:
            seen = [seen[i] for i in sorted(c_rng.choice(len(seen), args.max_c_eval, replace=False))]
        ct = [p for p in test if ds.sources(p[0], p[1], tl)]
        regimes = {"CT": (ct, None, {}), "J": (test, "none", {}), "C": (seen, None, {})}
        if ds.s_max > 2:   # P3 sensitivity: at most as many sources as training ever showed
            regimes["CT_max2"] = (ct, None, {"max_src": ds.s_max - 1, "rng": s_rng})
        results[key] = {}
        for name, (pairs, override, kw) in regimes.items():
            if len(pairs) < 10:
                results[key][name] = {"skipped": f"{len(pairs)} pairs"}
                continue
            r = refs_for(pairs, override, **kw)
            Y, gm = r["y"], r["g"]
            cols = torch.ones(ds.G, dtype=torch.bool, device=ds.device)
            for t, _ in pairs:
                if t in ds.gidx:
                    cols[ds.gidx[t]] = False
            preds = {"zero": torch.zeros_like(Y), "train_mean": train_mean.expand_as(Y),
                     "oracle_mean": Y.mean(0, keepdim=True).expand_as(Y), "model": r["model"]}
            if override is None:
                for k, T in transfer_refs(r).items():
                    preds[k] = amps[k] * T
            pt = {k: per_target(v, Y, gm, cols) for k, v in preds.items()}
            if ds.group[key] == "K562":
                other = [s for s in sp["held_lines"] if s != q]
                both = [i for i, (t, _) in enumerate(pairs) if any(t in ds.row[s] for s in other)]
                if len(both) >= 10:
                    s = other[0]
                    idx = torch.tensor(both, device=ds.device)
                    R = torch.stack([ds.delta[s][ds.row[s][pairs[i][0]]] for i in both])
                    pt["replicate_same_targets"] = per_target(R, Y[idx], gm[idx], cols)
                    pt["model_same_targets"] = per_target(r["model"][idx], Y[idx], gm[idx], cols)
            res = {k: summary(v) for k, v in pt.items()}
            refs = [k for k in ("zero", "train_mean", "oracle_mean", "transfer_simple", "transfer_gamma1") if k in pt]
            res["model_minus_ref"] = {
                ref: {m: paired_ci(pt["model"][m].cpu().numpy(), pt[ref][m].cpu().numpy(), boot_rng)
                      for m in ("mse", "pds_rank", "cosine")} for ref in refs}
            results[key][name] = res
            for meth, v in pt.items():
                for m, x in v.items():
                    arrays[f"{key}|{name}|{meth}|{m}"] = x.cpu().numpy()
            arrays[f"{key}|{name}|targets"] = np.array([t for t, _ in pairs])

    record = dict(
        args=vars(args), seconds=round(time.time() - t0), basal_file=ds.basal_file,
        trainable_params=n_params,
        script_sha256={f: hashlib.sha256((ROOT / f).read_bytes()).hexdigest()
                       for f in ("train.py", "model.py", "data.py")},
        counts=dict(train_pairs=len(sp["train"]), with_sources=len(with_src), no_sources=len(no_src),
                    val_pairs_with_sources=len(val), test_targets=len(sp["test_t"])),
        reference_amplitudes=amps, reference_val_mse=val_mse, reference_selected_on_val=best_ref,
        curve=curve, results=results,
    )
    (out / "results.json").write_text(json.dumps(record, indent=1))
    np.savez_compressed(out / "per_target.npz", **arrays)
    for key, rr in results.items():
        for name, res in rr.items():
            if "skipped" in res:
                print(key, name, res)
                continue
            print(f"\n{key} {name}")
            for meth, mm in res.items():
                if meth == "model_minus_ref":
                    continue
                print(f"  {meth:24s} n={mm['n']:5d} mse={mm['mse']:.5f} cos={mm['cosine']:+.3f} "
                      f"pds_rank={mm['pds_rank']:.3f} sign={mm['sign_top100']:.3f}")
            ci = res["model_minus_ref"].get(best_ref)
            if ci:
                print(f"  model - {best_ref}: mse {ci['mse']['mean']:+.5f} [{ci['mse']['lo']:+.5f}, {ci['mse']['hi']:+.5f}]"
                      f"  pds_rank {ci['pds_rank']['mean']:+.3f} [{ci['pds_rank']['lo']:+.3f}, {ci['pds_rank']['hi']:+.3f}]")


if __name__ == "__main__":
    main()
