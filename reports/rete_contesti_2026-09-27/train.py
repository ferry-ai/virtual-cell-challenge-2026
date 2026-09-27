"""Train and evaluate the multi-context network on one design; --selftest on synthetic data (CPU, nothing kept).

Needs torch 2.x, numpy and pandas; no project import (net.py and pool.py sit beside this file).

A design (docs/GENERALIZZAZIONE.md, regimes C/T/J):
* C (default): --hold-out names the truth contexts. With --hold-out-mode family (default) their whole families
  leave training and every input, as in the atlas and gated benches; `group` takes out only their groups (a CD4
  condition takes the other two), `context` only themselves. Test targets: --n-test drawn with --test-seed among
  the targets measured in every truth context and in >= --min-groups visible groups, outside the panel and the
  K562 essential screen, with a TSS when two truth contexts are compared (E2); or --test-targets FILE. Their rows
  in the visible contexts stay in training: a regime-C target is known elsewhere.
* J: as C, and the test targets -- with every target whose TSS lies within --cis-group-bp of one of them -- leave
  every context: no transferred profile; the network predicts from priors, partners and the context.
* T: --truth names visible contexts; the test targets and their cis neighbours leave every context.
Validation serves only early stopping: a whole visible family in C and J (--val-family auto: the median one by
rows; with fewer than three visible families, none), held-out targets in T (or with --val-family targets); then a
refit on every visible row for the best number of steps (--no-refit keeps the validated model). Test rows are read
once, after training, and only as truth.

Outputs in --out (a new folder): config.json, log.txt, history.csv, metrics.json (effect-space diagnostics, not
the registered proxy: that is score_pred.py), checkpoints/*.pt, and pred_<context>.npz per truth context with
targets, net, blind, swap, transfer (m, unscaled), partners (q, unscaled) on the full official axis (NaN where
nothing is predicted: genes fewer than two families estimate, the target's own gene, its cis window) and meta
(the calibrated amplitudes, the swap context).

    python train.py --selftest
    python train.py --data DATASET --out NEW --hold-out orion_hct116
    python train.py --data DATASET --out NEW --hold-out orion_hct116,orion_hek293t
    python train.py --data DATASET --out NEW --regime J --hold-out k562
    python train.py --data DATASET --out NEW --predict-contexts A,B,C --predict-targets targets.txt
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import torch

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import net  # noqa: E402
import pool as P  # noqa: E402

ARM_PAIRS = [("net", "blind"), ("net", "swap"), ("net", "transfer"), ("net", "partners"), ("blind", "transfer")]


@dataclass
class TrainConfig:
    lr: float = 1e-3
    weight_decay: float = 1e-4
    batch: int = 256
    eval_every: int = 250
    patience: int = 8
    platform_sd: float = 0.5
    m_drop: float = 0.2
    q_drop: float = 0.2
    depth_drop: float = 0.5
    lam_gate: float = 1e-3
    lam_amp: float = 1e-3
    lam_r: float = 1e-2
    grad_clip: float = 1.0
    seed: int = 0
    calib_rows: int = 4000


class Logger:
    """Prints and appends to a file; `quiet` keeps the lines in memory only (the self-test)."""

    def __init__(self, path: Path | None = None, quiet: bool = False):
        self.fh = open(path, "x", encoding="utf-8") if path is not None else None
        self.quiet, self.lines, self.t0 = quiet, [], time.time()

    def __call__(self, msg: str) -> None:
        line = f"[{time.time() - self.t0:8.1f}s] {msg}"
        self.lines.append(line)
        if not self.quiet:
            print(line, flush=True)
        if self.fh is not None:
            self.fh.write(line + "\n")
            self.fh.flush()

    def close(self) -> None:
        if self.fh is not None:
            self.fh.close()
            self.fh = None


def resolve_device(name: str) -> str:
    if name == "auto":
        return "cuda" if torch.cuda.is_available() else "cpu"
    return name


def set_seed(seed: int) -> None:
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def jsonable(x):
    if isinstance(x, dict):
        return {str(k): jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [jsonable(v) for v in x]
    if isinstance(x, np.ndarray):
        return jsonable(x.tolist())
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, (np.floating, float)):
        v = float(x)
        return v if math.isfinite(v) else None
    if isinstance(x, (np.bool_,)):
        return bool(x)
    if isinstance(x, Path):
        return str(x)
    return x


def read_list(path) -> list[str]:
    """Names from a text file, one per line, or the first column of a CSV with a header."""
    path = Path(path)
    if path.suffix.lower() == ".csv":
        return pd.read_csv(path, keep_default_na=False, na_values=[""]).iloc[:, 0].astype(str).str.strip().tolist()
    return [s.strip() for s in path.read_text(encoding="utf-8").splitlines() if s.strip()]


# ---------------------------------------------------------------- training

def net_config(args, pool: P.Pool, phase: P.Phase) -> net.NetConfig:
    return net.NetConfig(n_genes=pool.G, n_priors=phase.n_priors, n_targets=len(pool.target_names),
                         d_gene=args.d_gene, d_target=args.d_target, d_context=args.d_context, d_hidden=args.d_hidden,
                         k_gate=args.k_gate, k_inter=args.k_inter, dropout=args.dropout,
                         use_gate=not args.no_gate, use_inter=not args.no_inter,
                         use_global_context=not args.no_global_context, use_partners=not args.no_partners,
                         use_depth=args.use_depth, target_embedding=args.target_embedding)


def calibrate(phase: P.Phase, tcfg: TrainConfig, rng) -> dict:
    """Least-squares amplitude of the training labels on m, then of the residual on q, over a sample of training
    rows with the loss weights; and the mean total weight of a row (the loss normaliser)."""
    rows = phase.train_rows
    take = np.sort(rng.choice(rows, size=min(tcfg.calib_rows, rows.size), replace=False))
    s = dict(ym=0.0, mm=0.0, yq=0.0, mq=0.0, qq=0.0, w=0.0)
    for i in range(0, take.size, tcfg.batch):
        b = phase.batch(phase.spec_rows(take[i:i + tcfg.batch]), labels="train")
        w, y, m, q = b["w"], b["y"], b["m"], b["q"]
        s["ym"] += float((w * y * m).sum())
        s["mm"] += float((w * m * m).sum())
        s["yq"] += float((w * y * q).sum())
        s["mq"] += float((w * m * q).sum())
        s["qq"] += float((w * q * q).sum())
        s["w"] += float(w.sum())
    a = s["ym"] / s["mm"] if s["mm"] > 0 else 0.0
    aq = (s["yq"] - a * s["mq"]) / s["qq"] if s["qq"] > 0 else 0.0
    if s["w"] <= 0:
        raise ValueError("the calibration rows carry no usable label")
    return {"amplitude_ls": a, "amplitude_q_ls": aq, "amplitude": max(a, 1e-3), "amplitude_q": max(aq, 1e-4),
            "row_weight": s["w"] / take.size, "rows": int(take.size)}


def objective(out: dict, b: dict, tcfg: TrainConfig, wnorm: float):
    """Heteroscedastic weighted squared error (weights 1 / (k SE^2 + tau2) x gene weight; masked labels weigh 0),
    plus small penalties pulling the gates, the amplitude corrections and the correction path back to the
    plain transfer."""
    w, y = b["w"], b["y"]
    denom = wnorm * y.shape[0]
    data = (w * (out["yhat"] - y) ** 2).sum() / denom
    pen = (tcfg.lam_gate * (out["logit"] ** 2).mean() + tcfg.lam_amp * (out["ds"] ** 2).mean()
           + tcfg.lam_r * (w * out["r"] ** 2).sum() / denom)
    return data + pen, float(data.detach())


@torch.no_grad()
def validation_loss(phase: P.Phase, model, val: dict, batch: int) -> float:
    """Weighted mean squared error on the validation rows, their truth centred on their own mean response."""
    model.eval()
    feats = phase.features(0.0, None)
    num = den = 0.0
    spec = val["spec"]
    for i in range(0, len(spec), batch):
        b = phase.batch(spec.take(slice(i, i + batch)), labels="truth", centre=val["centre"], depth="ref")
        yhat = model(b, feats, phase.consts)["yhat"]
        num += float((b["w"] * (yhat - b["y"]) ** 2).sum())
        den += float(b["w"].sum())
    return num / max(den, 1e-12)


def fit(phase: P.Phase, ncfg: net.NetConfig, tcfg: TrainConfig, *, steps: int, val: dict | None = None, log=print):
    """Train from a fixed seed. With `val`, early stopping on its loss (best state restored); without, exactly
    `steps` steps. Returns (model, history, best_step, calibration)."""
    set_seed(tcfg.seed)
    rng = np.random.default_rng(tcfg.seed)
    gen = torch.Generator(device=phase.device)
    gen.manual_seed(tcfg.seed)
    model = net.PerturbNet(ncfg).to(phase.device)
    cal = calibrate(phase, tcfg, rng)
    model.set_amplitude(cal["amplitude"], cal["amplitude_q"])
    log(f"calibration: A {cal['amplitude_ls']:.4g} (used {cal['amplitude']:.4g}), A_q {cal['amplitude_q_ls']:.4g} "
        f"(used {cal['amplitude_q']:.4g}), mean row weight {cal['row_weight']:.4g} on {cal['rows']} rows; "
        f"parameters {net.count_parameters(model)['total']}")
    opt = torch.optim.AdamW(model.parameters(), lr=tcfg.lr, weight_decay=tcfg.weight_decay)
    rows = phase.train_rows
    order, pos = rng.permutation(rows), 0
    history, best, bad = [], {"loss": math.inf, "step": 0, "state": None}, 0
    run_sum, run_n, step = 0.0, 0, 0
    for step in range(1, steps + 1):
        if pos + tcfg.batch > order.size:
            order, pos = rng.permutation(rows), 0
        br = np.sort(order[pos:pos + tcfg.batch])
        pos += tcfg.batch
        model.train()
        b = phase.batch(phase.spec_rows(br), labels="train", drop_m=tcfg.m_drop, drop_q=tcfg.q_drop, depth="train",
                        depth_drop=tcfg.depth_drop, rng=rng)
        feats = phase.features(tcfg.platform_sd, gen)
        out = model(b, feats, phase.consts)
        loss, data = objective(out, b, tcfg, cal["row_weight"])
        if not math.isfinite(float(loss.detach())):
            raise FloatingPointError(f"non-finite loss at step {step}")
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), tcfg.grad_clip)
        opt.step()
        run_sum, run_n = run_sum + data, run_n + 1
        if step % tcfg.eval_every == 0 or step == steps:
            rec = {"step": step, "train_loss": run_sum / max(run_n, 1),
                   "amplitude": float(torch.exp(model.log_amp.detach())),
                   "amplitude_q": float(torch.exp(model.log_amp_q.detach()))}
            run_sum, run_n = 0.0, 0
            if val is not None:
                vl = validation_loss(phase, model, val, tcfg.batch)
                rec["val_loss"] = vl
                if vl < best["loss"]:
                    best = {"loss": vl, "step": step,
                            "state": {k: v.detach().to("cpu", copy=True) for k, v in model.state_dict().items()}}
                    bad = 0
                else:
                    bad += 1
            history.append(rec)
            log("step " + ", ".join(f"{k} {v:.5g}" if isinstance(v, float) else f"{k} {v}" for k, v in rec.items()))
            if val is not None and bad >= tcfg.patience:
                log(f"early stop at step {step}: no validation gain in {tcfg.patience} evaluations; best step {best['step']}")
                break
    if val is not None and best["state"] is not None:
        model.load_state_dict(best["state"])
        return model, history, best["step"], cal
    return model, history, step, cal


@torch.no_grad()
def predict(phase: P.Phase, model, spec: P.RowSpec, *, feat: str = "true", swap_basal: int | None = None,
            chunk: int = 256):
    """(prediction, m, q), each [rows, G] float32 with NaN where not predicted."""
    G = phase.pool.G
    if len(spec) == 0:
        empty = np.zeros((0, G), dtype=np.float32)
        return empty, empty.copy(), empty.copy()
    model.eval()
    feats = phase.features(0.0, None)
    preds, ms, qs = [], [], []
    for i in range(0, len(spec), chunk):
        b = phase.batch(spec.take(slice(i, i + chunk)), labels=None, feat=feat, swap_basal=swap_basal, depth="ref")
        y = model(b, feats, phase.consts)["yhat"]
        nan = torch.full_like(y, float("nan"))
        keep = phase.t_R.unsqueeze(0) & ~b["excl"]
        preds.append(torch.where(keep, y, nan).cpu().numpy())
        ms.append(torch.where(b["m_ok"], b["m"], nan).cpu().numpy())
        qs.append(torch.where(b["q_ok"], b["q"], nan).cpu().numpy())
    return np.concatenate(preds), np.concatenate(ms), np.concatenate(qs)


def predict_arms(phase: P.Phase, model, spec: P.RowSpec, swap_basal: int | None, cal: dict):
    """The arms of one set of rows: net, blind, swap, and the plain transfer and partner paths at the calibrated
    amplitudes. Returns (arms, m, q)."""
    pred, m, q = predict(phase, model, spec, feat="true")
    arms = {"net": pred, "blind": predict(phase, model, spec, feat="blind")[0]}
    if swap_basal is not None:
        arms["swap"] = predict(phase, model, spec, feat="swap", swap_basal=swap_basal)[0]
    arms["transfer"] = cal["amplitude"] * m
    arms["partners"] = cal["amplitude_q"] * q
    return arms, m, q


# ---------------------------------------------------------------- designs

def cis_group(pool: P.Pool, targets, bp: float) -> np.ndarray:
    """The targets, and every target whose TSS lies within `bp` of one of theirs on the same chromosome."""
    out = {int(t) for t in targets}
    if bp <= 0 or len(out) == 0:
        return np.array(sorted(out), dtype=np.int64)
    ok = np.isfinite(pool.tgt_tss)
    by = {}
    for c in np.unique(pool.tgt_chrom[ok]):
        idx = np.flatnonzero(ok & (pool.tgt_chrom == c))
        idx = idx[np.argsort(pool.tgt_tss[idx], kind="stable")]
        by[c] = (idx, pool.tgt_tss[idx])
    for t in targets:
        if not ok[t]:
            continue
        idx, pos = by[pool.tgt_chrom[t]]
        lo = np.searchsorted(pos, pool.tgt_tss[t] - bp, side="left")
        hi = np.searchsorted(pos, pool.tgt_tss[t] + bp, side="right")
        out.update(int(v) for v in idx[lo:hi])
    return np.array(sorted(out), dtype=np.int64)


def make_design(pool: P.Pool, args, log) -> dict:
    """Visible rows, test rows, validation and swap contexts of a design; see the module docstring."""
    names, cid = pool.context_names, pool.context_index
    n_ctx = len(names)
    mods = {m.strip() for m in args.modalities.split(",") if m.strip()}
    usable = np.array([pool.ctx_modality[c] in mods for c in range(n_ctx)])

    def ids(spec):
        out = []
        for n in [s.strip() for s in (spec or "").split(",") if s.strip()]:
            if n not in cid:
                raise SystemExit(f"unknown context {n!r}; the dataset has {names}")
            out.append(cid[n])
        return out

    regime = args.regime
    hold = ids(args.hold_out)
    truth = ids(args.truth) if regime == "T" else hold
    if regime in ("C", "J") and not hold and not args.predict_contexts:
        raise SystemExit("regimes C and J need --hold-out (or --predict-contexts alone)")
    if regime == "T" and (not truth or hold):
        raise SystemExit("regime T needs --truth and no --hold-out")
    for c in truth:
        if not usable[c]:
            raise SystemExit(f"{names[c]} has modality {pool.ctx_modality[c]!r}, not in --modalities {sorted(mods)}")
    hidden = set()
    for c in hold:
        if args.hold_out_mode == "family":
            hidden |= {i for i in range(n_ctx) if pool.ctx_family[i] == pool.ctx_family[c]}
        elif args.hold_out_mode == "group":
            hidden |= {i for i in range(n_ctx) if pool.ctx_group[i] == pool.ctx_group[c]}
        else:
            hidden.add(c)
    visible_ctx = [c for c in range(n_ctx) if usable[c] and c not in hidden]
    if not visible_ctx:
        raise SystemExit("no visible context left")
    if regime == "T" and any(c not in visible_ctx for c in truth):
        raise SystemExit("in regime T the truth contexts must be visible")
    measured = {c: set(pool.row_target[pool.ctx_rows[c]].tolist()) for c in range(n_ctx)}
    groups_vis: dict[int, set] = {}
    for c in visible_ctx:
        for t in measured[c]:
            groups_vis.setdefault(t, set()).add(pool.ctx_group[c])

    test = np.zeros(0, dtype=np.int64)
    if truth:
        cand = set.intersection(*(measured[c] for c in truth))
        if args.test_targets:
            listed = read_list(args.test_targets)
            known = [pool.target_index[t] for t in listed if t in pool.target_index]
            test = np.array(sorted(t for t in set(known) if t in cand), dtype=np.int64)
            log(f"test targets from {args.test_targets}: {len(listed)} listed, {len(known)} in the dataset, "
                f"{test.size} measured in every truth context")
        else:
            elig = [t for t in sorted(cand)
                    if (regime != "C" or len(groups_vis.get(t, ())) >= args.min_groups)
                    and (args.include_panel or not pool.tgt_panel[t])
                    and (args.include_essential or not pool.tgt_essential[t])
                    and (len(truth) < 2 or np.isfinite(pool.tgt_tss[t]))]
            if not elig:
                raise SystemExit("no eligible test target")
            rng = np.random.default_rng(args.test_seed)
            test = np.sort(rng.choice(np.array(elig, dtype=np.int64), size=min(args.n_test, len(elig)), replace=False))
            log(f"test targets: {test.size} drawn from {len(elig)} eligible (seed {args.test_seed})")
        if test.size == 0:
            raise SystemExit("no test target")
    hidden_targets = cis_group(pool, test, args.cis_group_bp) if regime in ("T", "J") else np.zeros(0, dtype=np.int64)
    vis_rows = np.concatenate([pool.ctx_rows[c] for c in visible_ctx])
    if hidden_targets.size:
        vis_rows = vis_rows[~np.isin(pool.row_target[vis_rows], hidden_targets)]
    test_rows = {}
    for c in truth:
        r = pool.ctx_rows[c]
        r = r[np.isin(pool.row_target[r], test)]
        test_rows[c] = r[np.argsort(pool.row_target[r], kind="stable")]
    all_test = np.concatenate(list(test_rows.values())) if test_rows else np.zeros(0, dtype=np.int64)
    if np.intersect1d(vis_rows, all_test).size:
        raise P.LeakageError("a test row is among the visible rows")

    val = {"kind": None}
    vrng = np.random.default_rng([args.test_seed, 1])
    fam_of_row = pool.ctx_family[pool.row_context[vis_rows]]
    if args.val_family == "targets" or (regime == "T" and args.val_family != "none"):
        cand_t = np.unique(pool.row_target[vis_rows])
        k = max(1, int(round(args.val_frac * cand_t.size)))
        vt = vrng.choice(cand_t, size=k, replace=False)
        vmask = np.isin(pool.row_target[vis_rows], vt)
        v_all = vis_rows[vmask]
        take = np.sort(vrng.choice(v_all, size=min(args.val_rows, v_all.size), replace=False))
        val = {"kind": "targets", "targets": int(k), "phase1_rows": vis_rows[~vmask], "val_rows": take}
    elif args.val_family != "none" and regime in ("C", "J"):
        fams = sorted(set(pool.ctx_family[c] for c in visible_ctx))
        vf = None
        if args.val_family == "auto":
            if len(fams) < 3:
                log(f"only {len(fams)} visible families: no validation family, exactly --steps steps")
            else:
                counts = sorted((int((fam_of_row == f).sum()), pool.family_names[f], f) for f in fams)
                vf = counts[len(counts) // 2][2]
        else:
            if args.val_family not in pool.family_names or pool.family_names.index(args.val_family) not in fams:
                raise SystemExit(f"--val-family {args.val_family!r} is not a visible family")
            vf = pool.family_names.index(args.val_family)
        if vf is not None:
            v_all = vis_rows[fam_of_row == vf]
            take = np.sort(vrng.choice(v_all, size=min(args.val_rows, v_all.size), replace=False))
            val = {"kind": "family", "family": pool.family_names[vf], "phase1_rows": vis_rows[fam_of_row != vf],
                   "val_rows": take}

    srng = np.random.default_rng([args.test_seed, 2])
    swap = {}
    for i, c in enumerate(truth):
        if len(truth) > 1:
            swap[c] = truth[(i + 1) % len(truth)]
        else:
            others = [v for v in visible_ctx if v != c]
            swap[c] = int(srng.choice(others)) if others else None
    design = {"regime": regime, "truth": truth, "hidden_contexts": sorted(hidden), "visible_contexts": visible_ctx,
              "test_targets": test, "hidden_targets": hidden_targets, "train_rows": vis_rows, "test_rows": test_rows,
              "val": val, "swap": swap}
    log(f"design {regime}: truth {[names[c] for c in truth]}, hidden {[names[c] for c in sorted(hidden)]}, "
        f"visible {[names[c] for c in visible_ctx]}; {vis_rows.size} visible rows; {test.size} test targets, "
        f"{hidden_targets.size} targets hidden everywhere; validation {val['kind']}"
        + (f" ({val.get('family')})" if val["kind"] == "family" else ""))
    return design


# ---------------------------------------------------------------- diagnostics

def boot(x, rng, n: int = 1000) -> dict:
    x = np.asarray(x, dtype=np.float64)
    x = x[np.isfinite(x)]
    if x.size == 0:
        return {"mean": None, "ci95": [None, None], "sd": None, "n": 0}
    means = np.array([x[rng.integers(0, x.size, x.size)].mean() for _ in range(n)])
    return {"mean": float(x.mean()), "ci95": [float(np.quantile(means, 0.025)), float(np.quantile(means, 0.975))],
            "sd": float(means.std()), "n": int(x.size)}


def discrimination(pred: np.ndarray, truth: np.ndarray) -> np.ndarray:
    """1 - rank of each target's own truth among all truths by cosine to its prediction (ties at half),
    divided by T - 1; rows are already weighted and zero where not scored."""
    T = pred.shape[0]
    if T < 2:
        return np.full(T, np.nan)
    a = pred / np.maximum(np.linalg.norm(pred, axis=1, keepdims=True), 1e-12)
    b = truth / np.maximum(np.linalg.norm(truth, axis=1, keepdims=True), 1e-12)
    c = a @ b.T
    d = np.diag(c)[:, None]
    rank = (c > d).sum(axis=1) + 0.5 * ((c == d).sum(axis=1) - 1)
    return 1.0 - rank / (T - 1)


def centred(x: np.ndarray) -> np.ndarray:
    """x minus its NaN-aware mean over targets, gene by gene."""
    with np.errstate(invalid="ignore"):
        cnt = np.isfinite(x).sum(axis=0)
        mean = np.divide(np.nansum(x, axis=0), cnt, out=np.zeros(x.shape[1]), where=cnt > 0)
    return x - mean[None, :]


def effect_diagnostics(truth, se, arms: dict, gw: np.ndarray, k: float, tau2: float, keep: np.ndarray,
                       disc_drop: np.ndarray, rng) -> dict:
    """Effect-space diagnostics of one truth context (not VCC scores, not the registered proxy).

    truth, se [T, G] raw; the truth is centred on its mean over the test targets (the context's own mean response
    is the scorer's zero). Per target and arm: weighted MSE (weights gene weight / (k SE^2 + tau2)); skill =
    1 - sum MSE / sum MSE of predicting 0; weighted cosine (gene weight x/(1+x)); discrimination among the test
    targets (every test target's own gene left out). Contrasts a - b: mean over targets of (MSE_b - MSE_a) / mean
    MSE_0 (so it equals skill_a - skill_b), cosine and discrimination differences, with bootstrap intervals, on
    all targets and on the strong stratum (top quartile of |raw / SE| >= 3 genes)."""
    yc = centred(truth)
    use = keep & np.isfinite(yc) & np.isfinite(se) & (se > 0)
    wt = np.where(use, gw[None, :] / (k * np.where(use, se, 1.0) ** 2 + tau2), 0.0)
    y0 = np.where(use, yc, 0.0)
    wsum = wt.sum(axis=1)
    okt = wsum > 0
    mse0 = np.where(okt, (wt * y0 ** 2).sum(axis=1) / np.maximum(wsum, 1e-12), np.nan)
    norm = float(np.nanmean(mse0)) if np.isfinite(mse0).any() else float("nan")
    cw = np.where(use, gw[None, :], 0.0)
    ydisc = y0 * cw
    ydisc[:, disc_drop] = 0.0
    per, summary = {}, {}
    for name, p in arms.items():
        p0 = np.where(use & np.isfinite(p), p, 0.0)
        mse = np.where(okt, (wt * (p0 - y0) ** 2).sum(axis=1) / np.maximum(wsum, 1e-12), np.nan)
        a, b = p0 * cw, y0 * cw
        cos = (a * b).sum(axis=1) / np.maximum(np.linalg.norm(a, axis=1) * np.linalg.norm(b, axis=1), 1e-12)
        pdisc = a.copy()
        pdisc[:, disc_drop] = 0.0
        per[name] = {"mse": mse, "cos": cos, "pds": discrimination(pdisc, ydisc)}
        summary[name] = {"skill": float(1.0 - np.nansum(mse) / np.nansum(mse0)) if np.nansum(mse0) > 0 else None,
                         "cos": float(np.nanmean(cos)), "pds": float(np.nanmean(per[name]["pds"]))}
    with np.errstate(divide="ignore", invalid="ignore"):
        z = np.where(use, np.abs(truth / np.where(use, se, 1.0)), 0.0)
    strength = (z >= 3).sum(axis=1)
    strong = strength >= np.quantile(strength, 0.75)
    contrasts = {}
    for a_, b_ in ARM_PAIRS:
        if a_ not in per or b_ not in per:
            continue
        stats = {}
        for stratum, sel in (("all", np.ones(len(strength), dtype=bool)), ("strong", strong)):
            stats[stratum] = {"skill": boot(((per[b_]["mse"] - per[a_]["mse"]) / norm)[sel], rng),
                              "cos": boot((per[a_]["cos"] - per[b_]["cos"])[sel], rng),
                              "pds": boot((per[a_]["pds"] - per[b_]["pds"])[sel], rng)}
        contrasts[f"{a_}-{b_}"] = stats
    return {"targets": int(truth.shape[0]), "targets_scored": int(okt.sum()), "strong_targets": int(strong.sum()),
            "strong_threshold": float(np.quantile(strength, 0.75)), "median_significant_genes": float(np.median(strength)),
            "arms": summary, "contrasts": contrasts}


def weighted_corr_rows(a: np.ndarray, b: np.ndarray, w: np.ndarray, min_genes: int = 20) -> np.ndarray:
    """Weighted Pearson correlation of a[i] and b[i] per row, over entries finite in both with w > 0."""
    ok = np.isfinite(a) & np.isfinite(b) & (w > 0)
    ww = np.where(ok, w, 0.0)
    sw = ww.sum(axis=1)
    a0, b0 = np.where(ok, a, 0.0), np.where(ok, b, 0.0)
    ma = (ww * a0).sum(axis=1) / np.maximum(sw, 1e-12)
    mb = (ww * b0).sum(axis=1) / np.maximum(sw, 1e-12)
    da, db = np.where(ok, a0 - ma[:, None], 0.0), np.where(ok, b0 - mb[:, None], 0.0)
    cov = (ww * da * db).sum(axis=1)
    va, vb = (ww * da * da).sum(axis=1), (ww * db * db).sum(axis=1)
    r = np.where((va > 0) & (vb > 0), cov / np.sqrt(np.maximum(va * vb, 1e-300)), 0.0)
    return np.where(ok.sum(axis=1) >= min_genes, r, np.nan)


def e2_diagnostics(y1, y2, arms1: dict, arms2: dict, w: np.ndarray, keep: np.ndarray, rng, n_perm: int = 200) -> dict:
    """Per target, the weighted correlation between the predicted difference of the two contexts and the observed
    one, both centred on their mean over the test targets (a difference common to every target, the two lines'
    templates, does not count), on the stored genes outside each target's own gene and cis window. A permutation
    pairs each target's predicted difference with another target's observed one. As gated_bench.py's E2."""
    obs = centred(np.where(keep, y1 - y2, np.nan))
    wt = np.where(keep, w[None, :], 0.0)
    out = {}
    for name in arms1:
        if name not in arms2:
            continue
        raw_diff = arms1[name] - arms2[name]
        fin = np.isfinite(raw_diff)
        zero = bool(np.all(np.abs(raw_diff[fin]) < 1e-7)) if fin.any() else True
        dp = centred(np.where(keep, raw_diff, np.nan))
        corr = weighted_corr_rows(dp, obs, wt)
        res = {"predicted_difference_is_zero": zero, **boot(corr, rng)}
        if not zero and np.isfinite(corr).any():
            perm = np.array([np.nanmean(weighted_corr_rows(dp, obs[rng.permutation(obs.shape[0])], wt))
                             for _ in range(n_perm)])
            res.update({"perm_mean": float(np.mean(perm)), "perm_q975": float(np.quantile(perm, 0.975)),
                        "perm_p": float(np.mean(perm >= np.nanmean(corr)))})
        out[name] = res
    return out


# ---------------------------------------------------------------- outputs

def full_axis(pool: P.Pool, x: np.ndarray) -> np.ndarray:
    out = np.full((x.shape[0], len(pool.axis)), np.nan, dtype=np.float32)
    out[:, pool.genes_axis] = x
    return out


def write_predictions(path: Path, pool: P.Pool, targets: list, arms: dict, m, q, meta: dict) -> None:
    payload = {"targets": np.array(targets, dtype=str), "axis_index": pool.genes_axis}
    for key in ("net", "blind", "swap"):
        if key in arms:
            payload[key] = full_axis(pool, arms[key])
    payload["transfer"] = full_axis(pool, m)
    payload["partners"] = full_axis(pool, q)
    payload["meta"] = np.array(json.dumps(jsonable(meta)))
    with open(path, "xb") as fh:
        np.savez_compressed(fh, **payload)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--selftest", action="store_true", help="synthetic checks on CPU; exit 1 on a failure")
    ap.add_argument("--data", type=Path, help="dataset folder written by data.py")
    ap.add_argument("--out", type=Path, help="new output folder")
    ap.add_argument("--regime", choices=["C", "T", "J"], default="C")
    ap.add_argument("--hold-out", default="", help="truth contexts of C/J, comma-separated")
    ap.add_argument("--hold-out-mode", choices=["family", "group", "context"], default="family")
    ap.add_argument("--truth", default="", help="truth contexts of T (visible), comma-separated")
    ap.add_argument("--modalities", default="crispri", help="context modalities that train and feed m")
    ap.add_argument("--n-test", type=int, default=1000)
    ap.add_argument("--test-seed", type=int, default=0)
    ap.add_argument("--test-targets", type=Path, default=None)
    ap.add_argument("--min-groups", type=int, default=2, help="C: test targets measured in >= this many visible groups")
    ap.add_argument("--include-panel", action="store_true")
    ap.add_argument("--include-essential", action="store_true")
    ap.add_argument("--cis-group-bp", type=float, default=10000.0, help="T/J: neighbours hidden with a test target")
    ap.add_argument("--val-family", default="auto",
                    help="C/J: auto (the median visible family by rows), a family name, targets (held-out targets "
                         "in every visible family) or none (exactly --steps); T: auto or targets means targets")
    ap.add_argument("--val-frac", type=float, default=0.1, help="share of targets for a target-level validation")
    ap.add_argument("--val-rows", type=int, default=2000)
    ap.add_argument("--no-refit", action="store_true")
    ap.add_argument("--steps", type=int, default=20000, help="maximum steps (exact steps without validation)")
    ap.add_argument("--eval-every", type=int, default=250)
    ap.add_argument("--patience", type=int, default=8)
    ap.add_argument("--batch", type=int, default=256)
    ap.add_argument("--lr", type=float, default=1e-3)
    ap.add_argument("--weight-decay", type=float, default=1e-4)
    ap.add_argument("--platform-sd", type=float, default=0.5, help="per-gene log bias drawn on the controls in training")
    ap.add_argument("--m-drop", type=float, default=None, help="share of rows trained without m (default 0.2; 1 in T/J)")
    ap.add_argument("--q-drop", type=float, default=0.2)
    ap.add_argument("--depth-drop", type=float, default=0.5)
    ap.add_argument("--lam-gate", type=float, default=1e-3)
    ap.add_argument("--lam-amp", type=float, default=1e-3)
    ap.add_argument("--lam-r", type=float, default=1e-2)
    ap.add_argument("--tau2", type=float, default=0.01)
    ap.add_argument("--min-frac", type=float, default=0.5)
    ap.add_argument("--min-families", type=int, default=2)
    ap.add_argument("--gene-weight", choices=["context", "flat"], default="context")
    ap.add_argument("--strong-boost", type=float, default=0.0)
    ap.add_argument("--max-partners", type=int, default=16)
    ap.add_argument("--d-gene", type=int, default=32)
    ap.add_argument("--d-target", type=int, default=32)
    ap.add_argument("--d-context", type=int, default=8)
    ap.add_argument("--d-hidden", type=int, default=128)
    ap.add_argument("--k-gate", type=int, default=16)
    ap.add_argument("--k-inter", type=int, default=32)
    ap.add_argument("--dropout", type=float, default=0.1)
    ap.add_argument("--no-gate", action="store_true")
    ap.add_argument("--no-inter", action="store_true")
    ap.add_argument("--no-global-context", action="store_true")
    ap.add_argument("--no-partners", action="store_true")
    ap.add_argument("--use-depth", action="store_true", help="knockdown depth as a nuisance input (reference at prediction)")
    ap.add_argument("--target-embedding", action="store_true", help="ablation: free residual embedding per seen target")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--device", default="auto")
    ap.add_argument("--predict-contexts", default="", help="basal-only contexts to predict (e.g. A,B,C)")
    ap.add_argument("--predict-targets", type=Path, default=None)
    return ap


def train_config(args) -> TrainConfig:
    m_drop = args.m_drop if args.m_drop is not None else (1.0 if args.regime in ("T", "J") else 0.2)
    return TrainConfig(lr=args.lr, weight_decay=args.weight_decay, batch=args.batch, eval_every=args.eval_every,
                       patience=args.patience, platform_sd=args.platform_sd, m_drop=m_drop, q_drop=args.q_drop,
                       depth_drop=args.depth_drop, lam_gate=args.lam_gate, lam_amp=args.lam_amp, lam_r=args.lam_r,
                       seed=args.seed)


def run_design(args, pool: P.Pool | None = None, log=None) -> dict:
    """Train, predict and diagnose one design; everything goes to args.out, a new folder."""
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=False)
    (out / "checkpoints").mkdir()
    own_log = log is None
    log = log or Logger(out / "log.txt")
    started = time.time()
    device = resolve_device(args.device)
    pool = pool if pool is not None else P.Pool.from_dir(args.data)
    log(f"dataset: {pool.n_rows} rows, {pool.G} stored genes, {len(pool.context_names)} contexts, "
        f"{len(pool.target_names)} targets; device {device}; torch {torch.__version__}")
    design = make_design(pool, args, log)
    opts = P.PhaseOptions(tau2=args.tau2, min_frac=args.min_frac, min_families=args.min_families,
                          gene_weight=args.gene_weight, q_own_family=(args.regime == "T"),
                          max_partners=args.max_partners, strong_boost=args.strong_boost)
    tcfg = train_config(args)
    history, steps_final, val_info = [], args.steps, None
    if design["val"]["kind"] is not None:
        ph1 = P.Phase(pool, design["val"]["phase1_rows"], opts, device, log)
        ncfg = net_config(args, pool, ph1)
        vrows = design["val"]["val_rows"]
        val = {"spec": ph1.spec_rows(vrows), "centre": ph1.truth_centres(vrows)}
        model, hist, best_step, cal = fit(ph1, ncfg, tcfg, steps=args.steps, val=val, log=log)
        history += [{"phase": 1, **h} for h in hist]
        torch.save({"state_dict": model.state_dict(), "net_config": ncfg.to_dict(), "best_step": best_step},
                   out / "checkpoints" / "phase1_best.pt")
        val_info = {"kind": design["val"]["kind"], "family": design["val"].get("family"), "rows": int(vrows.size),
                    "best_step": int(best_step), "best_val_loss": min((h["val_loss"] for h in hist), default=None)}
        if args.no_refit:
            phase = ph1
        else:
            del model
            phase = P.Phase(pool, design["train_rows"], opts, device, log)
            ncfg = net_config(args, pool, phase)
            steps_final = max(int(best_step), 1)
            log(f"refit on every visible row for {steps_final} steps")
            model, hist, _, cal = fit(phase, ncfg, tcfg, steps=steps_final, val=None, log=log)
            history += [{"phase": 2, **h} for h in hist]
    else:
        phase = P.Phase(pool, design["train_rows"], opts, device, log)
        ncfg = net_config(args, pool, phase)
        model, hist, _, cal = fit(phase, ncfg, tcfg, steps=args.steps, val=None, log=log)
        history += [{"phase": 2, **h} for h in hist]
    torch.save({"state_dict": model.state_dict(), "net_config": ncfg.to_dict(), "calibration": cal},
               out / "checkpoints" / "final.pt")

    results = {"claim_type": "effect-space diagnostics on held-out public contexts; not VCC scores and not the "
                             "registered proxy (score_pred.py)", "contexts": {}, "e2": {}}
    names = pool.context_names
    by_ctx = {}
    drng = np.random.default_rng([args.test_seed, 3])
    test_gene_cols = pool.tgt_gene[design["test_targets"]]
    test_gene_cols = test_gene_cols[test_gene_cols >= 0]
    for c, rows in design["test_rows"].items():
        spec = phase.spec_rows(rows)
        tnames = [pool.target_names[t] for t in spec.target]
        sw = design["swap"].get(c)
        arms, m, q = predict_arms(phase, model, spec, None if sw is None else int(pool.ctx_basal[sw]), cal)
        truth, se = phase.read("raw", rows, "truth"), phase.read("se", rows, "truth")
        keep = phase.R[None, :] & ~pool.exclusion_mask(spec.target)
        gw = phase.gw[pool.ctx_basal[c]]
        diag = effect_diagnostics(truth, se, arms, gw, float(pool.ctx_se_factor[c]), args.tau2, keep, test_gene_cols, drng)
        results["contexts"][names[c]] = diag
        by_ctx[c] = (tnames, arms, truth, keep, gw)
        meta = {"context": names[c], "swap_context": None if sw is None else names[sw], "design": args.regime,
                "hold_out": args.hold_out, "amplitude": cal["amplitude"], "amplitude_q": cal["amplitude_q"],
                "amplitude_learned": float(torch.exp(model.log_amp.detach())),
                "amplitude_q_learned": float(torch.exp(model.log_amp_q.detach())),
                "transfer_and_partners": "unscaled m and q; multiply by the amplitudes to get the arms of metrics.json"}
        write_predictions(out / f"pred_{names[c]}.npz", pool, tnames, arms, m, q, meta)
        a = diag["arms"]
        log(f"{names[c]}: {diag['targets']} test targets; skill net {a['net']['skill']}, blind {a['blind']['skill']}, "
            f"transfer {a['transfer']['skill']}; net-blind {diag['contrasts']['net-blind']['all']['skill']}")
    truth_list = list(design["test_rows"])
    for i in range(len(truth_list)):
        for j in range(i + 1, len(truth_list)):
            c1, c2 = truth_list[i], truth_list[j]
            t1, arms1, y1, keep1, gw1 = by_ctx[c1]
            t2, arms2, y2, keep2, gw2 = by_ctx[c2]
            if t1 != t2:
                log(f"E2 {names[c1]}-{names[c2]}: different test targets, skipped")
                continue
            e2 = e2_diagnostics(y1, y2, arms1, arms2, 0.5 * (gw1 + gw2), keep1 & keep2, drng)
            results["e2"][f"{names[c1]}-{names[c2]}"] = e2
            log(f"E2 {names[c1]}-{names[c2]}: net {e2['net']}")

    if args.predict_contexts:
        tlist = read_list(args.predict_targets) if args.predict_targets else []
        known = [t for t in tlist if t in pool.target_index]
        if len(known) < len(tlist):
            log(f"predict: {len(tlist) - len(known)} of {len(tlist)} targets are not in the dataset and are skipped")
        tidx = np.array([pool.target_index[t] for t in known], dtype=np.int64)
        for name in [s.strip() for s in args.predict_contexts.split(",") if s.strip()]:
            if name not in pool.basal_index:
                raise SystemExit(f"{name!r} is not a basal row of the dataset ({pool.basal_names})")
            spec = phase.spec_basal(name, tidx)
            arms, m, q = predict_arms(phase, model, spec, None, cal)
            meta = {"context": name, "basal_only": True, "amplitude": cal["amplitude"], "amplitude_q": cal["amplitude_q"]}
            write_predictions(out / f"pred_{name}.npz", pool, known, arms, m, q, meta)
            log(f"predicted {len(known)} targets in {name}")

    config = {"stage": "rete_contesti_2026-09-27/train.py", "args": vars(args), "device": device,
              "torch": torch.__version__, "numpy": np.__version__,
              "dataset": {k: pool.manifest.get(k) for k in ("format", "counts", "bytes_total_before_manifest")},
              "design": {"regime": design["regime"], "truth": [names[c] for c in design["truth"]],
                         "hidden_contexts": [names[c] for c in design["hidden_contexts"]],
                         "visible_contexts": [names[c] for c in design["visible_contexts"]],
                         "visible_rows": int(design["train_rows"].size), "test_targets": int(design["test_targets"].size),
                         "hidden_targets": int(design["hidden_targets"].size),
                         "swap": {names[c]: (None if s is None else names[s]) for c, s in design["swap"].items()}},
              "validation": val_info, "final_steps": int(steps_final), "net_config": ncfg.to_dict(),
              "parameters": net.count_parameters(model), "train_config": asdict(tcfg), "calibration": cal,
              "phase": {"families": [pool.family_names[f] for f in phase.families], "genes_estimated": int(phase.R.sum()),
                        "profiles": int(phase.P.shape[0]), "partner_profiles": int(phase.Q.shape[0])},
              "seconds": round(time.time() - started, 1)}
    with (out / "config.json").open("x", encoding="utf-8") as fh:
        json.dump(jsonable(config), fh, indent=1)
    with (out / "metrics.json").open("x", encoding="utf-8") as fh:
        json.dump(jsonable(results), fh, indent=1)
    pd.DataFrame(history).to_csv(out / "history.csv", index=False)
    (out / "test_targets.txt").write_text("\n".join(pool.target_names[t] for t in design["test_targets"]) + "\n",
                                          encoding="utf-8")
    log(f"done: {out}")
    if own_log:
        log.close()
    return {"results": results, "design": design, "phase": phase, "model": model, "calibration": cal,
            "config": config}


# ---------------------------------------------------------------- self-test

def synthetic(out: Path, *, planted: bool, seed: int) -> dict:
    """A small dataset in the real format: 10 contexts in 8 families (f6: two conditions of one group; f7: two
    lines of one lab), 360 axis genes of which 320 stored, 340 targets (10 on the axis but not stored, 10 off
    it). Planted: the response of gene g to target t in context c is s[c, t] h[c, g] theta[t, g], with
    h = 2 sigmoid(1.6 x (log CPM of g in c minus its mean over contexts)), 0.15 for a gene silent in c, and
    s = exp(0.5 x the same deviation for the target's own gene): an interaction read from the controls alone.
    Null: s = h = 1. Every context adds its own template; the SE understates the noise by sqrt(se_factor)."""
    rng = np.random.default_rng(seed)
    A, GS, n_ctx, T = 360, 320, 10, 340
    axis = [f"g{i:03d}" for i in range(A)]
    names = [f"c{i}" for i in range(n_ctx)]
    family = ["f0", "f1", "f2", "f3", "f4", "f5", "f6", "f6", "f7", "f7"]
    group = ["f0", "f1", "f2", "f3", "f4", "f5", "f6", "f6", "f7a", "f7b"]
    se_factor = np.array([1, 1, 1, 1, 1, 1, 2, 2, 1, 1], dtype=float)
    weight = np.array([1, 1, 1, 1, 1, 1, 0.5, 0.5, 1, 1], dtype=float)
    basal_names = names + ["A", "B", "C"]
    nb = len(basal_names)
    mu = rng.uniform(0.3, 6.0, A)
    load = rng.normal(0.0, 0.9, (A, 2))
    v = rng.normal(0.0, 1.0, (nb, 2))
    logc = mu[None, :] + v @ load.T + rng.normal(0.0, 0.25, (nb, A))
    logc = np.where(logc < 0.8, 0.0, logc)
    cpm = np.expm1(logc)
    basal = cpm.astype(np.float32)
    basal[0, 5] = np.nan                                    # an unknown control value: imputed, flagged
    t_axis = np.r_[np.arange(330), np.full(10, -1)]
    tnames = axis[:330] + [f"x{i}" for i in range(10)]
    theta = np.zeros((T, A))
    nz = rng.random((T, A)) < 0.15
    theta[nz] = rng.normal(0.0, 0.7, int(nz.sum()))
    on = np.flatnonzero(t_axis >= 0)
    theta[on, t_axis[on]] = -2.0
    lc = logc[:n_ctx]
    dev = lc - lc.mean(axis=0, keepdims=True)
    h = np.ones((n_ctx, A))
    s = np.ones((n_ctx, T))
    if planted:
        h = 2.0 / (1.0 + np.exp(-1.6 * dev))
        h[cpm[:n_ctx] == 0] = 0.15
        s[:, on] = np.exp(0.5 * np.clip(dev[:, t_axis[on]], -2.0, 2.0))
    template = rng.normal(0.0, 0.05, (n_ctx, A))
    shared = rng.random(T) < 0.9
    measured = [rng.random(T) < 0.85 for _ in range(8)] + [shared, shared]
    n_rows = int(sum(m.sum() for m in measured))
    genes_axis = np.arange(GS)
    w = P.DatasetWriter(out, n_rows, genes_axis)
    written = {k: [] for k in P.ARRAYS}
    ctx_rows, pos, fin_frac = [], 0, np.zeros((n_ctx, A))
    for c in range(n_ctx):
        tg = np.flatnonzero(measured[c])
        n = tg.size
        signal = s[c, tg][:, None] * h[c][None, :] * theta[tg] + template[c][None, :]
        se = rng.uniform(0.08, 0.3, (n, A))
        raw = signal + rng.normal(0.0, 1.0, (n, A)) * se * np.sqrt(se_factor[c])
        silent = cpm[c] == 0
        raw[:, silent] = np.nan
        se[:, silent] = np.nan
        z2 = (raw / se) ** 2
        shrunk = raw * z2 / (z2 + 4.0)
        # float32 first, as the writer casts: float64 -> float16 directly could round differently
        raw, se, shrunk = (x.astype(np.float32) for x in (raw, se, shrunk))
        own = t_axis[tg]
        w.add(c, tg, rng.uniform(60, 400, n), raw, se, shrunk, own)
        written["raw"].append(P.f16_effect(raw[:, genes_axis]))
        written["se"].append(P.f16_se(se[:, genes_axis]))
        written["shrunk"].append(P.f16_effect(shrunk[:, genes_axis]))
        ctx_rows.append((pos, pos + n))
        pos += n
        fin_frac[c] = np.isfinite(raw).mean(axis=0)
    fam_ids = sorted(set(family))
    fam_frac = np.array([fin_frac[[i for i in range(n_ctx) if family[i] == f]].max(axis=0) for f in fam_ids])
    contexts = pd.DataFrame({"context": names, "family": family, "group": group, "se_factor": se_factor,
                             "weight": weight, "modality": "crispri", "basal_row": np.arange(n_ctx),
                             "row_start": [a for a, _ in ctx_rows], "row_stop": [b for _, b in ctx_rows]})
    tss = np.where(t_axis >= 0, t_axis * 3000.0, np.nan)
    targets = pd.DataFrame({"target": tnames, "axis_index": t_axis, "gene_index": np.where(t_axis < GS, t_axis, -1),
                            "in_panel": np.arange(T) < 20, "essential": (np.arange(T) >= 20) & (np.arange(T) < 30),
                            "chrom": np.where(t_axis >= 0, "1", ""), "tss": tss})
    targets = pd.concat([targets, basal_priors_frame(basal[:n_ctx], t_axis)], axis=1)
    cis_lists = [[int(j) for j in (t_axis[t] - 1, t_axis[t] + 1) if 0 <= j < GS] if 0 <= t_axis[t] else []
                 for t in range(T)]
    part = [set() for _ in range(T)]
    for t in range(T):
        for p in rng.choice(T, size=3, replace=False):
            if p != t:
                part[t].add(int(p))
                part[int(p)].add(t)
    scores = {}
    plist = []
    for t in range(T):
        ps = sorted(part[t])
        sc = {p: scores.setdefault((min(t, p), max(t, p)), float(rng.integers(700, 1000))) for p in ps}
        plist.append(sorted(ps, key=lambda p: (-sc[p], p)))
    targets["p_string_deg"] = np.log1p([len(p) for p in plist])
    p_ip, p_ix = P.csr(plist)
    p_sc = np.array([scores[(min(t, p), max(t, p))] for t in range(T) for p in plist[t]], dtype=np.float32)
    genes = pd.DataFrame({"gene": [axis[i] for i in genes_axis], "axis_index": genes_axis,
                          "n_families": (fam_frac[:, genes_axis] >= 0.5).sum(axis=0)})
    manifest = w.finish(contexts=contexts, targets=targets, genes=genes, axis=axis, basal=basal,
                        basal_names=basal_names, cis=P.csr(cis_lists), partners=(p_ip, p_ix, p_sc),
                        manifest={"stage": "train.py --selftest synthetic", "planted": planted, "seed": seed})
    return {"manifest": manifest, "written": {k: np.concatenate(v) for k, v in written.items()},
            "targets": tnames, "n_rows": n_rows}


def basal_priors_frame(cpm_sources: np.ndarray, t_axis: np.ndarray) -> pd.DataFrame:
    return P.basal_priors(cpm_sources, t_axis)


def poisoned(pool: P.Pool, invisible: np.ndarray, seed: int) -> P.Pool:
    """A copy of `pool` whose invisible rows (arrays, cells, own-gene values) are replaced by noise."""
    rng = np.random.default_rng(seed)
    arrays = {k: np.array(pool.arrays[k]) for k in P.ARRAYS}
    n = invisible.size
    arrays["raw"][invisible] = rng.normal(0, 5, (n, pool.G)).astype(np.float16)
    arrays["se"][invisible] = np.abs(rng.normal(0, 5, (n, pool.G))).astype(np.float16) + np.float16(0.01)
    arrays["shrunk"][invisible] = rng.normal(0, 5, (n, pool.G)).astype(np.float16)
    ncells = pool.row_ncells.copy()
    ncells[invisible] = rng.uniform(1, 5000, n)
    own = pool.row_own.copy()
    own[invisible] = rng.normal(0, 5, (n, 2))
    rows = {"row_context": pool.row_context, "row_target": pool.row_target, "row_ncells": ncells, "row_own": own}
    return P.Pool(arrays, pool.contexts, pool.targets, pool.genes, pool.axis, rows, pool.basal, pool.basal_names,
                  (pool.cis_indptr, pool.cis_index), (pool.partner_indptr, pool.partner_index, pool.partner_score),
                  pool.manifest)


def direct_m(pool: P.Pool, phase: P.Phase, rows: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """m recomputed row by row with plain loops (the reference for Phase.batch)."""
    G = pool.G
    out, ok_out = np.zeros((rows.size, G)), np.zeros((rows.size, G), dtype=bool)
    excl = pool.exclusion_mask(pool.row_target[rows])
    for i, r in enumerate(rows):
        t, own_fam = pool.row_target[r], pool.ctx_family[pool.row_context[r]]
        num, den = np.zeros(G), np.zeros(G)
        for f in phase.families:
            if f == own_fam:
                continue
            fn, fd, W = np.zeros(G), np.zeros(G), 0.0
            for c in phase.contexts:
                if pool.ctx_family[c] != f:
                    continue
                rr = phase.visible_rows_of(c)
                rr = rr[pool.row_target[rr] == t]
                if rr.size == 0:
                    continue
                sh = np.asarray(pool.arrays["shrunk"][rr[0]], dtype=np.float32) - phase.mu_sh[c]
                n = pool.row_ncells[rr[0]]
                wt = pool.ctx_weight[c] * n / (n + P.RELIABILITY)
                ok = np.isfinite(sh)
                fn += wt * np.where(ok, sh, 0.0)
                fd += wt * ok
                W += wt
            if W == 0:
                continue
            prof = np.where(fd > 0, fn / np.where(fd > 0, fd, 1.0), np.nan).astype(np.float16).astype(np.float64)
            okp = np.isfinite(prof)
            num += W * np.where(okp, prof, 0.0)
            den += W * okp
        keep = phase.R & ~excl[i] & (den > 0)
        out[i] = np.where(keep, num / np.where(den > 0, den, 1.0), 0.0)
        ok_out[i] = keep
    return out, ok_out


def fmt(x, spec: str = "+.3f") -> str:
    return "None" if x is None else format(x, spec)


def selftest() -> int:
    import tempfile
    results = []

    def check(name: str, ok: bool, detail: str) -> None:
        results.append(bool(ok))
        print(f"{'PASS' if ok else 'FAIL'} {name}: {detail}", flush=True)

    torch.set_num_threads(max(1, min(4, torch.get_num_threads())))
    small = ["--device", "cpu", "--steps", "1500", "--eval-every", "50", "--patience", "8", "--batch", "64",
             "--lr", "3e-3", "--d-gene", "16", "--d-target", "16", "--d-context", "4", "--d-hidden", "64",
             "--k-gate", "8", "--k-inter", "8", "--dropout", "0", "--platform-sd", "0", "--val-rows", "600",
             "--q-drop", "0.1", "--m-drop", "0.1"]
    logs = []
    # ignore_cleanup_errors: on Windows a memory-mapped file cannot be deleted while it is still open
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        tmp = Path(tmp)
        info = synthetic(tmp / "planted", planted=True, seed=11)
        pool = P.Pool.from_dir(tmp / "planted")
        same = all(np.array_equal(np.asarray(pool.arrays[k]), info["written"][k], equal_nan=True) for k in P.ARRAYS)
        sizes_ok = all((tmp / "planted" / f).stat().st_size == b for f, b in info["manifest"]["bytes"].items())
        check("dataset round trip", same and sizes_ok and pool.target_names == info["targets"],
              f"{pool.n_rows} rows x {pool.G} genes, float16 arrays identical after reading back; manifest sizes "
              f"{'match' if sizes_ok else 'DIFFER'} ({info['manifest']['bytes_total_before_manifest']} bytes)")

        args = build_parser().parse_args(small + ["--data", str(tmp / "planted"), "--out", str(tmp / "run_planted"),
                                                  "--hold-out", "c8,c9"])
        quiet = Logger(quiet=True)
        logs.append(quiet)
        design = make_design(pool, args, quiet)
        opts = P.PhaseOptions()
        train_rows = design["train_rows"]
        invisible = np.setdiff1d(np.arange(pool.n_rows), train_rows)
        ph_a = P.Phase(pool, train_rows, opts, "cpu", quiet)
        ph_b = P.Phase(poisoned(pool, invisible, 5), train_rows, opts, "cpu", quiet)
        derived = [np.array_equal(ph_a.R, ph_b.R), np.array_equal(ph_a.P, ph_b.P, equal_nan=True),
                   np.array_equal(ph_a.PW, ph_b.PW), np.array_equal(ph_a.PD, ph_b.PD, equal_nan=True),
                   np.array_equal(ph_a.Q, ph_b.Q, equal_nan=True), np.array_equal(ph_a.QW, ph_b.QW),
                   np.array_equal(ph_a.prior_z, ph_b.prior_z), np.array_equal(ph_a.blind_row, ph_b.blind_row),
                   all(np.array_equal(ph_a.mu_raw[c], ph_b.mu_raw[c]) and np.array_equal(ph_a.mu_sh[c], ph_b.mu_sh[c])
                       for c in ph_a.contexts)]
        sample = np.sort(np.random.default_rng(1).choice(train_rows, 128, replace=False))
        ba = ph_a.batch(ph_a.spec_rows(sample), labels="train", drop_m=0.3, drop_q=0.3, depth="train",
                        rng=np.random.default_rng(9))
        bb = ph_b.batch(ph_b.spec_rows(sample), labels="train", drop_m=0.3, drop_q=0.3, depth="train",
                        rng=np.random.default_rng(9))
        batch_same = all(torch.equal(ba[k], bb[k]) for k in ba)
        test_spec = ph_a.spec_rows(design["test_rows"][pool.context_index["c8"]])
        pa, _, _ = predict(ph_a, net.PerturbNet(net_config(args, pool, ph_a)), test_spec)
        torch.manual_seed(0)
        model_a = net.PerturbNet(net_config(args, pool, ph_a))
        torch.manual_seed(0)
        model_b = net.PerturbNet(net_config(args, pool, ph_b))
        pred_same = np.array_equal(predict(ph_a, model_a, test_spec)[0], predict(ph_b, model_b, test_spec)[0],
                                   equal_nan=True)
        raised = 0
        for fn in (lambda: ph_a.read("raw", invisible[:3], "train"), lambda: ph_a.read("raw", train_rows[:3], "truth")):
            try:
                fn()
            except P.LeakageError:
                raised += 1
        check("leakage canary", all(derived) and batch_same and pred_same and raised == 2 and pa.shape[0] > 0,
              f"{invisible.size} invisible rows overwritten with noise: centres, gene set, family and partner "
              f"profiles, priors, blind row, a training batch and test predictions identical "
              f"({sum(derived)}/{len(derived)} derived arrays, batch {batch_same}, predictions {pred_same}); "
              f"{raised}/2 wrong-kind reads refused")

        rows_chk = np.r_[design["test_rows"][pool.context_index["c8"]][:15],
                         pool.ctx_rows[pool.context_index["c6"]][:10], pool.ctx_rows[pool.context_index["c0"]][:5]]
        rows_chk = rows_chk[ph_a.visible[rows_chk] | np.isin(rows_chk, design["test_rows"][pool.context_index["c8"]])]
        b = ph_a.batch(ph_a.spec_rows(rows_chk), labels=None)
        want, want_ok = direct_m(pool, ph_a, rows_chk)
        got, got_ok = b["m"].numpy(), b["m_ok"].numpy()
        close = np.allclose(got, want, rtol=5e-3, atol=2e-3) and np.array_equal(got_ok, want_ok)
        check("transferred profile", close,
              f"{rows_chk.size} rows (held-out, and training rows of a two-context family and a one-context family): "
              f"leave-own-family-out reliability-weighted mean matches a plain loop (max abs diff "
              f"{float(np.max(np.abs(got - want))):.2e})")

        res = run_design(args, pool=pool, log=quiet)
        ctx_res = res["results"]["contexts"]
        for cname in ("c8", "c9"):
            d = ctx_res[cname]
            for other in ("transfer", "blind"):
                st = d["contrasts"][f"net-{other}"]["all"]["skill"]
                sn, so = d["arms"]["net"]["skill"], d["arms"][other]["skill"]
                ok = st["mean"] is not None and st["ci95"][0] > 0 and sn is not None and so is not None and sn - so >= 0.05
                check(f"planted {cname}: net beats {other}", ok,
                      f"skill net {fmt(sn, '.3f')} vs {other} {fmt(so, '.3f')}; paired gain {fmt(st['mean'])} "
                      f"({fmt(st['ci95'][0])}..{fmt(st['ci95'][1])}) over {st['n']} targets (needs CI above 0 and >= 0.05)")
        e2 = res["results"]["e2"].get("c8-c9", {})
        en = e2.get("net", {})
        zero_ok = e2.get("blind", {}).get("predicted_difference_is_zero") and e2.get("transfer", {}).get("predicted_difference_is_zero")
        e2_ok = en.get("mean") is not None and en["mean"] > 0.1 and en.get("perm_q975") is not None \
            and en["mean"] > en["perm_q975"] and en["ci95"][0] > 0 and bool(zero_ok)
        check("planted E2: predicted difference between two held-out lines", e2_ok,
              f"mean correlation {en.get('mean')} (CI {en.get('ci95')}), permutation q97.5 {en.get('perm_q975')}; "
              f"blind and transfer predict no difference: {bool(zero_ok)}")

        phase, model, cal = res["phase"], res["model"], res["calibration"]
        r8 = design["test_rows"][pool.context_index["c8"]]
        r9 = design["test_rows"][pool.context_index["c9"]]
        s8, s9 = phase.spec_rows(r8), phase.spec_rows(r9)
        same_t = np.array_equal(s8.target, s9.target)
        b8, _, _ = predict(phase, model, s8, feat="blind")
        b9, _, _ = predict(phase, model, s9, feat="blind")
        sw8, _, _ = predict(phase, model, s8, feat="swap", swap_basal=int(pool.ctx_basal[pool.context_index["c9"]]))
        t9, _, _ = predict(phase, model, s9, feat="true")
        t8, _, _ = predict(phase, model, s8, feat="true")
        sem = same_t and np.allclose(b8, b9, atol=1e-6, equal_nan=True) and np.allclose(sw8, t9, atol=1e-6, equal_nan=True) \
            and not np.allclose(t8, t9, atol=1e-3, equal_nan=True)
        check("blind and swap semantics", sem,
              "blind gives two lines of one family identical predictions; c8's rows with c9's controls equal c9's "
              "predictions; the true c8 and c9 predictions differ")

        args_d = build_parser().parse_args(small + ["--data", str(tmp / "planted"), "--out", str(tmp / "unused"),
                                                    "--hold-out", "c8,c9", "--seed", "3"])
        tc = train_config(args_d)
        runs, threads = [], torch.get_num_threads()
        torch.set_num_threads(1)                  # one thread: no reduction-order differences between runs
        for _ in range(2):
            ph = P.Phase(pool, train_rows, opts, "cpu", quiet)
            mdl, _, _, _ = fit(ph, net_config(args_d, pool, ph), tc, steps=40, val=None, log=quiet)
            runs.append(predict(ph, mdl, ph.spec_rows(r8))[0])
        torch.set_num_threads(threads)
        check("determinism on CPU", np.array_equal(runs[0], runs[1], equal_nan=True),
              "two trainings from seed 3, one thread, give bit-identical predictions")

        synthetic(tmp / "null", planted=False, seed=11)
        pool0 = P.Pool.from_dir(tmp / "null")
        args0 = build_parser().parse_args(small + ["--data", str(tmp / "null"), "--out", str(tmp / "run_null"),
                                                   "--hold-out", "c8,c9"])
        res0 = run_design(args0, pool=pool0, log=quiet)
        for cname in ("c8", "c9"):
            d = res0["results"]["contexts"][cname]
            st = d["contrasts"]["net-blind"]["all"]["skill"]
            bound = 2.5 * (st["sd"] or 0.0) + 0.005
            check(f"null {cname}: net does not beat blind beyond noise", st["mean"] is not None and st["mean"] <= bound,
                  f"paired gain {fmt(st['mean'], '+.4f')} <= {bound:.4f} (2.5 bootstrap SD + 0.005); skill net "
                  f"{fmt(d['arms']['net']['skill'], '.3f')}, blind {fmt(d['arms']['blind']['skill'], '.3f')}")
            sn, st_ = d["arms"]["net"]["skill"], d["arms"]["transfer"]["skill"]
            check(f"null {cname}: net not worse than the transfer", sn is not None and st_ is not None and sn - st_ >= -0.05,
                  f"skill net {fmt(sn, '.3f')}, transfer {fmt(st_, '.3f')} (tolerance 0.05)")
    n_fail = results.count(False)
    if n_fail:
        for lg in logs:
            print("\n".join(lg.lines[-40:]))
    print(f"selftest: {len(results) - n_fail} passed, {n_fail} failed", flush=True)
    return 1 if n_fail else 0


def main() -> None:
    args = build_parser().parse_args()
    if args.selftest:
        sys.exit(selftest())
    if args.data is None or args.out is None:
        raise SystemExit("--data and --out are required (or --selftest)")
    run_design(args)


if __name__ == "__main__":
    main()
