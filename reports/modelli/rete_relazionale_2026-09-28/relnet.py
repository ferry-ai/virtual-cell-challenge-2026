"""The relational network (DISEGNO.md §2) and the pieces that graft it onto r1's train.py without editing it.

For a row i = (context c, target t) and a stored response gene g:

    yhat[i, g] = h[i, g] (A s_i m[i, g] + A_q s^q_i q[i, g] + a_c qc[i, g])
               + sum_k rho[g, k] ((gamma[c, k] - 1) z[i, k] + u[t, k])

* m, q: r1's transferred profile and STRING-partner profile (pool.Phase), unchanged; qc: the card-neighbour profile
  (relphase.RelPhase); a_c starts at 0.
* s = exp(2 tanh(tctx . w_s)), s^q likewise with w_sq: the 8 target-in-context features of net.row_inputs.
* h = 2 sigmoid(beta1 gref): one parameter; gref from net.row_inputs.
* rho: the phase's gene cards rho0 [G, K] (a buffer), plus a learned residual d_rho with --rel-cards learned (rel1),
  pulled back to rho0 by --lam-card on mean(d_rho^2).
* z = base @ rho0, base = A s m + A_q s^q q: the gain acts on the module part of the row's own baseline only.
* log gamma[c, k] = 0.5 tanh((theta0 + theta_k) a[c, k]), a = omega_mod-weighted mean of the drank channel of the
  controls (net.context_features channel 4): the blind row has drank 0, hence gamma = 1 exactly. --rel-gain shared
  keeps theta0 only, none removes the term.
* u[t] = w_self * card(t) * card_ok(t) + W_p priors(t): a K-vector self-feedback (--rel-self none removes it) and a
  linear map of the standardised priors (--no-rel-priors removes it).
At initialisation every new parameter is 0, so yhat = A m + A_q q exactly, r1's calibrated start.

Grafting (the encoder's pattern, encoder_contesto_2026-09-28/train_emb.py): install(args) routes train.py's
module attributes -- fit (step-0 evaluation, extra penalties, parameter groups; builds net.PerturbNet for --arch r1
or RelNet), net_config, and for --arch rel pool.Phase (-> RelPhase), predict_arms (adds tperm, norel, cardnb),
write_predictions (adds predrel_<context>.npz) and ARM_PAIRS -- and uninstall() restores them. With --arch r1 only
fit is routed; with --eval-every 250 --no-eval-step0 it is train.fit bit for bit (selftest_rel.py, check 7).
--val-m as-train (default keep, train.py's) makes early stopping withhold m from the validation rows when training
withholds it from every row (regime J), for either architecture.

Arms added at prediction time, free:
* tperm: the relational inputs (qc, card, card_ok, priors) permuted among the rows' targets with a fixed
  derangement (--rel-card-seed); m and q stay the row's own;
* norel: r = 0 and a_c = 0 (gates and amplitudes kept);
* cardnb: the least-squares amplitude of the training labels on qc (loss weights, the calibration sample of
  train.calibrate, fixed seed) times qc: the card-neighbour hypothesis without any learned parameter.
"""
from __future__ import annotations

import argparse
import json
import math
from contextlib import contextmanager
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import torch
from torch import nn

import relphase as RP
import net as N  # noqa: E402  (relphase put the r1 folder on sys.path)
import pool as P  # noqa: E402
import train as T  # noqa: E402

EXTRA_ARMS = ("tperm", "norel", "cardnb")
EXTRA_PAIRS = [("net", "tperm"), ("net", "norel"), ("net", "cardnb"), ("cardnb", "partners")]
_ORIG = {"Phase": P.Phase, "fit": T.fit, "net_config": T.net_config, "predict_arms": T.predict_arms,
         "write_predictions": T.write_predictions, "ARM_PAIRS": list(T.ARM_PAIRS)}


@dataclass
class RelConfig:
    n_genes: int
    n_priors: int
    k: int
    learned_cards: bool = False
    gain: str = "module"             # none | shared | module
    self_term: str = "diag"          # none | diag
    priors: bool = True
    neighbours: bool = True          # the a_c qc term (needs --rel-nb > 0)
    amp_bound: float = 2.0           # |log s - log A| <= amp_bound, as net.NetConfig

    def to_dict(self) -> dict:
        return asdict(self)


class RelNet(nn.Module):
    """See the module docstring. forward(batch, feat, consts) -> {"yhat", "ds", "logit", "r", "h"}, as
    net.PerturbNet, so train.objective, train.predict and train.run_design use it unchanged."""

    def __init__(self, cfg: RelConfig):
        super().__init__()
        if cfg.gain not in ("none", "shared", "module") or cfg.self_term not in ("none", "diag"):
            raise ValueError(f"gain {cfg.gain!r}, self_term {cfg.self_term!r}")
        self.cfg = cfg
        G, K = cfg.n_genes, cfg.k
        self.log_amp = nn.Parameter(torch.zeros(()))
        self.log_amp_q = nn.Parameter(torch.tensor(math.log(0.1)))
        self.a_c = nn.Parameter(torch.zeros(())) if cfg.neighbours else None
        self.beta1 = nn.Parameter(torch.zeros(()))
        self.w_s = nn.Parameter(torch.zeros(N.N_TC))
        self.w_sq = nn.Parameter(torch.zeros(N.N_TC))
        self.theta0 = nn.Parameter(torch.zeros(())) if cfg.gain != "none" else None
        self.theta = nn.Parameter(torch.zeros(K)) if cfg.gain == "module" else None
        self.w_self = nn.Parameter(torch.zeros(K)) if cfg.self_term == "diag" else None
        self.W_p = nn.Parameter(torch.zeros(K, cfg.n_priors)) if cfg.priors and cfg.n_priors > 0 else None
        self.d_rho = nn.Parameter(torch.zeros(G, K)) if cfg.learned_cards else None
        self.register_buffer("rho0", torch.zeros(G, K))
        self.register_buffer("omega_mod", torch.zeros(G, K))
        self.norel = False

    def set_amplitude(self, a: float, a_q: float) -> None:
        """As net.PerturbNet.set_amplitude (train.calibrate's least-squares amplitudes)."""
        with torch.no_grad():
            self.log_amp.fill_(math.log(max(float(a), 1e-4)))
            self.log_amp_q.fill_(math.log(max(float(a_q), 1e-5)))

    def set_cards(self, rho0: torch.Tensor, omega_mod: torch.Tensor) -> None:
        with torch.no_grad():
            self.rho0.copy_(rho0)
            self.omega_mod.copy_(omega_mod)

    @contextmanager
    def relational_off(self):
        old = self.norel
        self.norel = True
        try:
            yield
        finally:
            self.norel = old

    def forward(self, b: dict, feat: torch.Tensor, consts: dict) -> dict:
        cfg = self.cfg
        m, q = b["m"], b["q"]
        ctx_gene, tctx, gref = N.row_inputs(feat, consts["genes_axis"], b["row_feat"], b["tgt_axis"], b["omega"],
                                            consts["rbar"], consts["ref_rank"])
        ds = cfg.amp_bound * torch.tanh(tctx @ self.w_s)
        ds_q = cfg.amp_bound * torch.tanh(tctx @ self.w_sq)
        logit = self.beta1 * gref
        h = 2.0 * torch.sigmoid(logit)
        base = torch.exp(self.log_amp + ds).unsqueeze(1) * m + torch.exp(self.log_amp_q + ds_q).unsqueeze(1) * q
        full = base
        if self.a_c is not None and not self.norel:
            full = full + self.a_c * b["qc"]
        yhat = h * full
        coef = None
        if not self.norel:
            if self.theta0 is not None:
                used, inv = torch.unique(b["row_feat"], return_inverse=True)
                act = (ctx_gene[used][..., 4] @ self.omega_mod)[inv]              # [B, K] basal module activity
                slope = self.theta0 + (self.theta if self.theta is not None else 0.0)
                g = 0.5 * torch.tanh(slope * act)
                coef = (torch.exp(g) - 1.0) * (base @ self.rho0)
            if self.w_self is not None:
                u = self.w_self * b["rho_t"] * b["t_rel"].unsqueeze(1)
                coef = u if coef is None else coef + u
            if self.W_p is not None:
                u = b["priors_u"] @ self.W_p.T
                coef = u if coef is None else coef + u
        if coef is None:
            r = torch.zeros_like(yhat)
        else:
            rho = self.rho0 if self.d_rho is None else self.rho0 + self.d_rho
            r = coef @ rho.T
        return {"yhat": yhat + r, "ds": ds, "logit": logit, "r": r, "h": h}

    def penalty(self, lam: dict) -> torch.Tensor:
        """The L2 terms of the new parameters (DISEGNO.md §2, map §2.3), added to train.objective's loss."""
        z = self.log_amp.new_zeros(())
        if self.theta0 is not None:
            z = z + lam["theta0"] * self.theta0 ** 2
        if self.theta is not None:
            z = z + lam["theta"] * (self.theta ** 2).sum()
        if self.w_self is not None:
            z = z + lam["self"] * (self.w_self ** 2).sum()
        if self.W_p is not None:
            z = z + lam["prior"] * (self.W_p ** 2).sum()
        if self.d_rho is not None:
            z = z + lam["card"] * (self.d_rho ** 2).mean()
        return z

    def summary(self) -> dict:
        def f(p):
            return None if p is None else float(p.detach().float().pow(2).mean().sqrt())
        return {"amplitude": float(torch.exp(self.log_amp.detach())), "amplitude_q": float(torch.exp(self.log_amp_q.detach())),
                "a_c": None if self.a_c is None else float(self.a_c.detach()), "beta1": float(self.beta1.detach()),
                "theta0": None if self.theta0 is None else float(self.theta0.detach()), "theta_rms": f(self.theta),
                "w_self_rms": f(self.w_self), "W_p_rms": f(self.W_p), "d_rho_rms": f(self.d_rho),
                "w_s_rms": f(self.w_s), "w_sq_rms": f(self.w_sq)}


# ---------------------------------------------------------------- settings and arguments

def add_args(ap) -> None:
    g = ap.add_argument_group("relational network (train_rel.py)")
    g.add_argument("--arch", choices=["r1", "rel"], default="rel", help="r1: net.PerturbNet (the none condition)")
    g.add_argument("--rel-cards", choices=["svd", "learned"], default="svd", help="svd: rel0; learned: rel1")
    g.add_argument("--rel-k", type=int, default=32)
    g.add_argument("--rel-nb", type=int, default=16)
    g.add_argument("--rel-min-strength", type=float, default=10.0)
    g.add_argument("--rel-gain", choices=["none", "shared", "module"], default="module")
    g.add_argument("--rel-self", choices=["none", "diag"], default="diag")
    g.add_argument("--no-rel-priors", action="store_true")
    g.add_argument("--rel-card-null", choices=["none", "bins"], default="none")
    g.add_argument("--rel-omega-top", type=int, default=200)
    g.add_argument("--rel-card-seed", type=int, default=0)
    g.add_argument("--rel-svd-iters", type=int, default=4)
    g.add_argument("--rel-lr", type=float, default=3e-3, help="rel: scalars and small maps (--lr is r1's)")
    g.add_argument("--rel-lr-card", type=float, default=1e-3, help="rel1: the card residual")
    g.add_argument("--lam-theta0", type=float, default=1e-3)
    g.add_argument("--lam-theta", type=float, default=1e-2)
    g.add_argument("--lam-self", type=float, default=1e-3)
    g.add_argument("--lam-prior", type=float, default=1e-3)
    g.add_argument("--lam-card", type=float, default=1e-1)
    g.add_argument("--eval-step0", action=argparse.BooleanOptionalAction, default=True,
                   help="evaluate the validation loss at step 0 (the calibrated start) too")
    g.add_argument("--val-m", choices=["keep", "as-train"], default="keep",
                   help="keep: train.py's validation (m present); as-train: m withheld from the validation rows when "
                        "training withholds it from every row (J, T). Not in the registered rule")
    g.add_argument("--run-label", default="", help="free text kept in rel_config.json (design, condition, seed)")


def settings_from_args(args) -> RP.RelSettings:
    return RP.RelSettings(k=args.rel_k, nb=args.rel_nb, min_strength=args.rel_min_strength,
                          card_null=args.rel_card_null, omega_top=args.rel_omega_top, cis_bp=args.cis_group_bp,
                          card_seed=args.rel_card_seed, svd_iters=args.rel_svd_iters)


def lambdas(args) -> dict:
    return {"theta0": args.lam_theta0, "theta": args.lam_theta, "self": args.lam_self, "prior": args.lam_prior,
            "card": args.lam_card}


def rel_config(args, pool, phase) -> RelConfig:
    return RelConfig(n_genes=pool.G, n_priors=phase.n_priors, k=int(phase.rho0.shape[1]),
                     learned_cards=args.rel_cards == "learned", gain=args.rel_gain, self_term=args.rel_self,
                     priors=not args.no_rel_priors, neighbours=args.rel_nb > 0)


def config_factory(args):
    def net_config(a, pool, phase):
        if args.arch == "r1":
            return _ORIG["net_config"](a, pool, phase)
        return rel_config(args, pool, phase)
    return net_config


# ---------------------------------------------------------------- training

def build_model(phase, ncfg):
    if isinstance(ncfg, RelConfig):
        model = RelNet(ncfg).to(phase.device)
        model.set_cards(phase.t_rho0, phase.t_omega_mod)
        return model
    return N.PerturbNet(ncfg).to(phase.device)


@torch.no_grad()
def validation_loss_without_m(phase, model, val: dict, batch: int) -> float:
    """train.validation_loss with m withheld from every validation row, as training withholds it when m_drop >= 1
    (regimes J and T): drop_m 1 drops every row whatever the generator draws, and no other draw is made."""
    model.eval()
    feats = phase.features(0.0, None)
    num = den = 0.0
    spec = val["spec"]
    for i in range(0, len(spec), batch):
        b = phase.batch(spec.take(slice(i, i + batch)), labels="truth", centre=val["centre"], depth="ref",
                        drop_m=1.0, rng=np.random.default_rng(0))
        yhat = model(b, feats, phase.consts)["yhat"]
        num += float((b["w"] * (yhat - b["y"]) ** 2).sum())
        den += float(b["w"].sum())
    return num / max(den, 1e-12)


def fit_rel(phase, ncfg, tcfg, *, steps: int, val: dict | None = None, log=print, eval_step0: bool = True,
            rel_lr: float = 3e-3, rel_lr_card: float = 1e-3, lam: dict | None = None, val_m: str = "keep"):
    """train.fit with an optional validation at step 0, the relational penalties and parameter groups.

    The statements are train.fit's, in its order (seed, generators, model, calibration, optimiser, loop), so that
    with net.PerturbNet, eval_step0 False and the same TrainConfig it is train.fit bit for bit. The step-0
    evaluation reads no random number. A best step 0 means the calibrated start was never beaten on the validation
    family (run_design then refits for max(0, 1) = 1 step).

    val_m "keep" is train.py's validation (m present on the validation rows even when training withholds it from
    every row, as in J); "as-train" withholds m from the validation rows when tcfg.m_drop >= 1, so that early
    stopping sees the condition of the J test rows. Not in the registered rule: an option the lead may declare."""
    vloss = T.validation_loss
    if val_m == "as-train" and tcfg.m_drop >= 1.0:
        vloss = validation_loss_without_m
    elif val_m not in ("keep", "as-train"):
        raise ValueError(f"val_m {val_m!r}")
    T.set_seed(tcfg.seed)
    rng = np.random.default_rng(tcfg.seed)
    gen = torch.Generator(device=phase.device)
    gen.manual_seed(tcfg.seed)
    model = build_model(phase, ncfg)
    rel = isinstance(model, RelNet)
    cal = T.calibrate(phase, tcfg, rng)
    model.set_amplitude(cal["amplitude"], cal["amplitude_q"])
    log(f"calibration: A {cal['amplitude_ls']:.4g} (used {cal['amplitude']:.4g}), A_q {cal['amplitude_q_ls']:.4g} "
        f"(used {cal['amplitude_q']:.4g}), mean row weight {cal['row_weight']:.4g} on {cal['rows']} rows; "
        f"parameters {N.count_parameters(model)['total']}")
    if rel:
        card = [p for n, p in model.named_parameters() if n == "d_rho"]
        small = [p for n, p in model.named_parameters() if n != "d_rho"]
        groups = [{"params": small, "lr": rel_lr}] + ([{"params": card, "lr": rel_lr_card}] if card else [])
        opt = torch.optim.AdamW(groups, lr=rel_lr, weight_decay=tcfg.weight_decay)
        lam = lam or {"theta0": 1e-3, "theta": 1e-2, "self": 1e-3, "prior": 1e-3, "card": 1e-1}
    else:
        opt = torch.optim.AdamW(model.parameters(), lr=tcfg.lr, weight_decay=tcfg.weight_decay)
    rows = phase.train_rows
    order, pos = rng.permutation(rows), 0
    history, best, bad = [], {"loss": math.inf, "step": 0, "state": None}, 0

    def record(step: int, train_loss: float) -> dict:
        rec = {"step": step, "train_loss": train_loss,
               "amplitude": float(torch.exp(model.log_amp.detach())),
               "amplitude_q": float(torch.exp(model.log_amp_q.detach()))}
        return rec

    def with_rel(rec: dict) -> dict:
        if rel:
            s = model.summary()
            for k_ in ("a_c", "beta1", "theta0", "theta_rms", "w_self_rms", "W_p_rms", "d_rho_rms"):
                if s[k_] is not None:
                    rec[k_] = s[k_]
        return rec

    if eval_step0 and val is not None:
        rec = with_rel(record(0, float("nan")))
        vl = vloss(phase, model, val, tcfg.batch)
        rec["val_loss"] = vl
        best = {"loss": vl, "step": 0, "state": {k: v.detach().to("cpu", copy=True) for k, v in model.state_dict().items()}}
        history.append(rec)
        log("step " + ", ".join(f"{k} {v:.5g}" if isinstance(v, float) else f"{k} {v}" for k, v in rec.items()))
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
        loss, data = T.objective(out, b, tcfg, cal["row_weight"])
        if rel:
            loss = loss + model.penalty(lam)
        if not math.isfinite(float(loss.detach())):
            raise FloatingPointError(f"non-finite loss at step {step}")
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), tcfg.grad_clip)
        opt.step()
        run_sum, run_n = run_sum + data, run_n + 1
        if step % tcfg.eval_every == 0 or step == steps:
            rec = record(step, run_sum / max(run_n, 1))
            run_sum, run_n = 0.0, 0
            if val is not None:
                vl = vloss(phase, model, val, tcfg.batch)
                rec["val_loss"] = vl
                if vl < best["loss"]:
                    best = {"loss": vl, "step": step,
                            "state": {k: v.detach().to("cpu", copy=True) for k, v in model.state_dict().items()}}
                    bad = 0
                else:
                    bad += 1
            rec = with_rel(rec)
            history.append(rec)
            log("step " + ", ".join(f"{k} {v:.5g}" if isinstance(v, float) else f"{k} {v}" for k, v in rec.items()))
            if val is not None and bad >= tcfg.patience:
                log(f"early stop at step {step}: no validation gain in {tcfg.patience} evaluations; best step {best['step']}")
                break
    if val is not None and best["state"] is not None:
        model.load_state_dict(best["state"])
        return model, history, best["step"], cal
    return model, history, step, cal


def fit_factory(args):
    def fit(phase, ncfg, tcfg, *, steps: int, val: dict | None = None, log=print):
        return fit_rel(phase, ncfg, tcfg, steps=steps, val=val, log=log, eval_step0=args.eval_step0,
                       rel_lr=args.rel_lr, rel_lr_card=args.rel_lr_card, lam=lambdas(args), val_m=args.val_m)
    return fit


# ---------------------------------------------------------------- arms and outputs

def derangement(targets: np.ndarray, n_targets: int, seed: int) -> np.ndarray:
    """A map over all targets: identity, except the given targets sent to one another along one random cycle."""
    u = np.unique(np.asarray(targets, dtype=np.int64))
    out = np.arange(n_targets, dtype=np.int64)
    if u.size >= 2:
        order = np.random.default_rng([int(seed), 4]).permutation(u)
        out[order] = np.roll(order, -1)
    return out


@contextmanager
def target_map(phase, mapping):
    old = phase.rel_target_map
    phase.rel_target_map = mapping
    try:
        yield
    finally:
        phase.rel_target_map = old


@torch.no_grad()
def cardnb_amplitude(phase, rows: int = 4000, batch: int = 256, seed: int = 0) -> dict:
    """Weighted least-squares amplitude of the training labels on qc (train.calibrate's weights), on a fixed sample
    of the phase's training rows; cached on the phase."""
    if getattr(phase, "_cardnb", None) is not None:
        return phase._cardnb
    rng = np.random.default_rng([int(seed), 7])
    take = np.sort(rng.choice(phase.train_rows, size=min(rows, phase.train_rows.size), replace=False))
    num = den = 0.0
    for i in range(0, take.size, batch):
        b = phase.batch(phase.spec_rows(take[i:i + batch]), labels="train")
        num += float((b["w"] * b["y"] * b["qc"]).sum())
        den += float((b["w"] * b["qc"] * b["qc"]).sum())
    phase._cardnb = {"amplitude": num / den if den > 0 else 0.0, "rows": int(take.size)}
    return phase._cardnb


@torch.no_grad()
def qc_arm(phase, spec, amplitude: float, chunk: int = 256) -> np.ndarray:
    G = phase.pool.G
    if len(spec) == 0:
        return np.zeros((0, G), dtype=np.float32)
    parts = []
    for i in range(0, len(spec), chunk):
        b = phase.batch(spec.take(slice(i, i + chunk)), labels=None, depth="ref")
        nan = torch.full_like(b["qc"], float("nan"))
        parts.append(torch.where(b["qc_ok"], amplitude * b["qc"], nan).cpu().numpy())
    return np.concatenate(parts)


def rel_predict_arms(phase, model, spec, swap_basal, cal):
    """train.predict_arms, then tperm, norel and cardnb when the model is a RelNet on a RelPhase."""
    arms, m, q = _ORIG["predict_arms"](phase, model, spec, swap_basal, cal)
    if isinstance(model, RelNet) and getattr(phase, "rel", None) is not None:
        mapping = derangement(spec.target, len(phase.pool.target_names), phase.rel.card_seed)
        with target_map(phase, mapping):
            arms["tperm"] = T.predict(phase, model, spec, feat="true")[0]
        with model.relational_off():
            arms["norel"] = T.predict(phase, model, spec, feat="true")[0]
        cn = None
        if phase.rel.nb > 0:
            cn = cardnb_amplitude(phase, seed=phase.rel.card_seed)
            arms["cardnb"] = qc_arm(phase, spec, cn["amplitude"])
        u = np.unique(spec.target)
        LAST_EXTRA_META.clear()
        LAST_EXTRA_META.update({"tperm_seed": phase.rel.card_seed, "tperm_moved": int((mapping[u] != u).sum()),
                                "cardnb_amplitude": None if cn is None else cn["amplitude"],
                                "cardnb_rows": None if cn is None else cn["rows"]})
    return arms, m, q


LAST_EXTRA_META: dict = {}


def rel_write_predictions(path, pool, targets, arms, m, q, meta) -> None:
    """train.write_predictions, then predrel_<context>.npz with the extra arms (full axis, NaN where none)."""
    _ORIG["write_predictions"](path, pool, targets, arms, m, q, meta)
    extra = [k for k in EXTRA_ARMS if k in arms]
    if not extra:
        return
    path = Path(path)
    side = path.with_name("predrel_" + (path.name[len("pred_"):] if path.name.startswith("pred_") else path.name))
    payload = {"targets": np.array(targets, dtype=str), "axis_index": pool.genes_axis}
    for k in extra:
        payload[k] = T.full_axis(pool, arms[k])
    payload["meta"] = np.array(json.dumps(T.jsonable({**meta, **LAST_EXTRA_META,
                                                      "extra_arms": "tperm, norel: the network's arms; cardnb: "
                                                                    "cardnb_amplitude x qc"})))
    with open(side, "xb") as fh:
        np.savez_compressed(fh, **payload)


# ---------------------------------------------------------------- install

def install(args) -> None:
    """Route train.py to the relational pieces (module attributes of pool and train)."""
    RP.CREATED.clear()
    T.fit = fit_factory(args)
    T.net_config = config_factory(args)
    if args.arch == "rel":
        RP.SETTINGS = settings_from_args(args)
        P.Phase = RP.RelPhase
        T.predict_arms = rel_predict_arms
        T.write_predictions = rel_write_predictions
        T.ARM_PAIRS = _ORIG["ARM_PAIRS"] + EXTRA_PAIRS


def uninstall() -> None:
    RP.SETTINGS = None
    P.Phase = _ORIG["Phase"]
    T.fit = _ORIG["fit"]
    T.net_config = _ORIG["net_config"]
    T.predict_arms = _ORIG["predict_arms"]
    T.write_predictions = _ORIG["write_predictions"]
    T.ARM_PAIRS = list(_ORIG["ARM_PAIRS"])


def installed_is_original() -> bool:
    return (P.Phase is _ORIG["Phase"] and T.fit is _ORIG["fit"] and T.net_config is _ORIG["net_config"]
            and T.predict_arms is _ORIG["predict_arms"] and T.write_predictions is _ORIG["write_predictions"]
            and list(T.ARM_PAIRS) == _ORIG["ARM_PAIRS"])
