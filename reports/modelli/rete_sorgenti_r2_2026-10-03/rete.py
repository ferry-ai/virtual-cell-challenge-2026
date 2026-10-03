"""Source-attention network r2: the r1 network (reports/modelli/rete_sorgenti_2026-10-03/rete.py) with three switches
for the failure the t30 score showed (CP-0056): the learned amplitude shrank the effects about 20-fold within 500 steps,
because with a validation cosine near 0.06 the MSE half of the loss rewards smaller effects.

* ``amp="fixed"``: A_L is the norm-match amplitude alone, no learned factor (r1: ``"learned"``);
* ``loss="cos"``: 1 - cosine only, which no rescaling of y_hat can lower (r1: ``"mse_cos"``);
* ``loss_genes="top"``: the loss reads, per target, only the genes whose truth is in the top ``top_frac`` by |effect|
  (r1: ``"all"``), where a held-out effect is more signal than noise.

With the r1 defaults this file computes what r1 computed (test_rete.py, unchanged, still passes).

r1 docstring follows.

Source-attention network: a learned weighting of measured source effects, conditioned on the target line's controls.

For a line L never seen perturbed, a target t and a gene g, with source keys k that measured (t, g):

    y_hat[t, g] = A_L * sum_k alpha_k(L, g) * E_k[t, g]
    alpha_k(L, g) = softmax_k( s(z_L, z_k) + <W h(z_L, z_k), m_g> + c * |b_L[g] - b_k[g]| )

* ``z`` encodes a line's basal profile (its controls only: available for D, E, F on 22 October);
* ``m_g`` is a small learned gene embedding (gene modules), ``b`` the basal log expression;
* ``A_L`` is the registered norm-match amplitude of the route C bench times exp(w . z_L).

Every output layer starts at zero, so at step 0 the network IS the equal-weight transfer over the allowed sources:
it can only learn which measured source to trust, never an effect no source measured, and it carries no per-target
parameter, so it applies to the final set's new targets unchanged. Params: a few thousand plus 8 per gene.

Training is leave-one-key-out by episodes: a key L of the training lines is the truth, the allowed sources are the
training keys outside L's study, group and line (the route C exclusions). Validation and test lines are never a
target nor a source in training. Health is logged at every evaluation (monitor.jsonl): loss of the net and of the
equal-weight start on the validation lines, attention entropy, effective number of sources, amplitude, gradient
norm. Early checkpoints are kept, never overwritten.

    python rete.py --keys chiavi --out run --val kolf jurkat --test h1 hepg2
"""
from __future__ import annotations

import argparse
import json
import math
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn

SAME_LINE = {"kolf": {"hipsci_targeted_19|kolf_2", "hipsci_targeted_19|kolf_3"}}


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# ---------------------------------------------------------------- corpus

@dataclass
class Key:
    key: str
    group: str
    type: str
    targets: np.ndarray
    eff: np.ndarray        # T x G float16, NaN = not usable
    basal: np.ndarray      # G float32
    measured: np.ndarray   # G bool

    @property
    def study(self) -> str:
        return self.key.split("|", 1)[0]

    def __post_init__(self):
        self.row = {t: i for i, t in enumerate(self.targets.astype(str))}


def load_keys(folder: Path) -> list[Key]:
    keys = []
    for f in sorted(folder.glob("*.npz")):
        z = np.load(f, allow_pickle=False)
        keys.append(Key(str(z["key"]), str(z["group"]), str(z["type"]), z["targets"].astype(str), z["eff"],
                        z["basal"].astype(np.float32), z["measured"].astype(bool)))
    return keys


def donor(key: str) -> str:
    """HipSci line names are <donor>_<clone> (eipl_1, eipl_3): two clones of one donor are one genome."""
    return key.split("|", 1)[1].split("_")[0]


def allowed_sources(L: Key, pool: list[Key]) -> list[Key]:
    """The route C exclusions: not L's study, not L's group, not a line L derives from (or that derives from L).
    One registered exception (PROTOCOLLO_R1): a HipSci line may read the HipSci lines of OTHER donors, which are other
    genomes of the same cell type; it only matters in training, since no test line is a HipSci line."""
    same_line = SAME_LINE.get(L.group, set())

    def ok(k: Key) -> bool:
        if k.key in same_line or L.key in SAME_LINE.get(k.group, set()):
            return False
        if L.group == "hipsci" and k.group == "hipsci":
            return donor(k.key) != donor(L.key)
        return k.study != L.study and k.group != L.group
    return [k for k in pool if ok(k)]


def basal_panel(keys: list[Key], n: int = 2000) -> np.ndarray:
    """Genes the basal encoder reads: measured in >= 80% of the keys, the n most variable across keys."""
    meas = np.mean([k.measured for k in keys], axis=0) >= 0.8
    B = np.stack([k.basal for k in keys])
    var = np.where(meas, B.var(axis=0), -1.0)
    return np.sort(np.argsort(var)[::-1][:min(n, int(meas.sum()))])


# ---------------------------------------------------------------- model

@dataclass
class Config:
    dim: int = 32
    gene_dim: int = 8
    panel: int = 2000
    targets_per_episode: int = 64
    genes_per_episode: int = 2048
    cos_weight: float = 1.0
    amp: str = "learned"              # "learned" (r1) | "fixed": A_L = norm-match only
    loss: str = "mse_cos"             # "mse_cos" (r1) | "cos"
    loss_genes: str = "all"           # "all" (r1) | "top": per target, the top_frac genes by |truth|
    top_frac: float = 0.1
    lr: float = 3e-3
    steps: int = 3000
    eval_every: int = 100
    keep_steps: tuple = (0, 100, 300, 1000, 3000)
    patience: int = 5                 # evaluations in a row worse than the equal-weight start -> stop
    min_steps: int = 300
    seed: int = 0


class SourceAttention(nn.Module):
    def __init__(self, n_genes: int, panel: np.ndarray, mu: np.ndarray, sd: np.ndarray, cfg: Config):
        super().__init__()
        self.register_buffer("panel", torch.as_tensor(panel, dtype=torch.long))
        self.register_buffer("mu", torch.as_tensor(mu, dtype=torch.float32))
        self.register_buffer("sd", torch.as_tensor(sd, dtype=torch.float32))
        d = cfg.dim
        self.enc = nn.Sequential(nn.Linear(panel.size, 64), nn.GELU(), nn.Linear(64, d), nn.LayerNorm(d))
        self.pair = nn.Sequential(nn.Linear(2 * d, d), nn.GELU())
        self.score = nn.Linear(d, 1)
        self.gene_mod = nn.Linear(d, cfg.gene_dim, bias=False)
        self.gene_emb = nn.Embedding(n_genes, cfg.gene_dim)
        self.basal_gap = nn.Parameter(torch.zeros(()))
        self.amp = nn.Linear(d, 1, bias=False)
        for layer in (self.score, self.gene_mod, self.amp):          # step 0 = equal weights, amplitude A0
            nn.init.zeros_(layer.weight)
            if getattr(layer, "bias", None) is not None:
                nn.init.zeros_(layer.bias)
        nn.init.normal_(self.gene_emb.weight, std=0.1)
        self.amp_mode = cfg.amp

    def encode(self, basal: torch.Tensor) -> torch.Tensor:
        x = (basal[..., self.panel] - self.mu) / self.sd
        return self.enc(x)

    def forward(self, E, avail, basal_L, basal_S, genes, A0, prior):
        """E (K, T, g) source effects with 0 where unavailable, avail (K, T, g) bool; basal_L (G,), basal_S (K, G);
        genes (g,) axis indices; A0 scalar; prior (K,) = -log(keys of the source's group), so that at step 0 every
        line group weighs the same, as the bench's `all` arm. Returns y_hat (T, g), alpha (K, T, g), amplitude."""
        zL, zS = self.encode(basal_L[None])[0], self.encode(basal_S)               # (d,), (K, d)
        h = self.pair(torch.cat([zS * zL[None], (zS - zL[None]).abs()], dim=-1))   # (K, d)
        s = self.score(h)[:, 0]                                                    # (K,)
        mod = self.gene_mod(h) @ self.gene_emb(genes).T                            # (K, g)
        gap = (basal_S[:, genes] - basal_L[genes][None]).abs()                     # (K, g)
        logit = (prior[:, None] + s[:, None] + mod - self.basal_gap * gap)[:, None, :].expand_as(E)
        logit = logit.masked_fill(~avail, -1e9)
        alpha = torch.softmax(logit, dim=0) * avail
        alpha = alpha / alpha.sum(0, keepdim=True).clamp_min(1e-12)
        A = A0 * torch.exp(self.amp(zL)[0]) if self.amp_mode == "learned" else torch.as_tensor(A0, dtype=torch.float32)
        return A * (alpha * E).sum(0), alpha, A


# ---------------------------------------------------------------- episodes

def norm_match(E: np.ndarray, avail: np.ndarray) -> float:
    """The route C amplitude rule, on the episode's own sources: median single-source norm / median pooled norm."""
    single = np.sqrt((E ** 2).sum(-1))[avail.any(-1)]
    with np.errstate(all="ignore"):
        pooled = (E * avail).sum(0) / avail.sum(0).clip(min=1)
    pn = np.sqrt((pooled ** 2).sum(-1))
    pn, single = pn[pn > 0], single[single > 0]
    return float(np.median(single) / np.median(pn)) if pn.size and single.size else 1.0


def episode(L: Key, sources: list[Key], rng, n_t: int, n_g: int, targets=None, genes=None):
    """Tensors for one held-out key: targets covered by L and at least one source; genes usable in L."""
    if targets is None:
        cov = [t for t in L.targets if any(t in k.row for k in sources)]
        if not cov:
            return None
        targets = rng.choice(cov, size=min(n_t, len(cov)), replace=False)
    if genes is None:
        usable = np.flatnonzero(np.isfinite(L.eff[[L.row[t] for t in targets]].astype(np.float32)).any(0))
        genes = np.sort(rng.choice(usable, size=min(n_g, usable.size), replace=False))
    K, T, g = len(sources), len(targets), genes.size
    E = np.zeros((K, T, g), np.float32)
    avail = np.zeros((K, T, g), bool)
    for ki, k in enumerate(sources):
        for ti, t in enumerate(targets):
            i = k.row.get(t)
            if i is not None:
                v = k.eff[i, genes].astype(np.float32)
                ok = np.isfinite(v)
                E[ki, ti, ok], avail[ki, ti, ok] = v[ok], True
    Y = np.full((T, g), np.nan, np.float32)            # a line never perturbed (D, E, F) has no truth
    for ti, t in enumerate(targets):
        i = L.row.get(t)
        if i is not None:
            Y[ti] = L.eff[i, genes].astype(np.float32)
    groups = [k.group for k in sources]
    prior = -np.log(np.array([groups.count(g) for g in groups], np.float32))
    return {"E": E, "avail": avail, "Y": Y, "genes": genes, "targets": list(targets), "A0": norm_match(E, avail),
            "basal_L": L.basal, "basal_S": np.stack([k.basal for k in sources]), "prior": prior}


def to_t(ep):
    return {k: torch.as_tensor(v) if isinstance(v, np.ndarray) else v for k, v in ep.items()}


def loss_fn(y_hat, Y, cfg):
    ok = torch.isfinite(Y)
    if cfg.loss_genes == "top":                 # per target, the genes whose truth is largest in size
        a = torch.where(ok, Y.abs(), torch.full_like(Y, -1.0))
        k = max(1, int(round(cfg.top_frac * Y.shape[1])))
        thr = a.topk(k, dim=1).values[:, -1:]
        ok = ok & (a >= thr) & (a > 0)
    Yz = torch.where(ok, Y, torch.zeros_like(Y))
    yh = torch.where(ok, y_hat, torch.zeros_like(y_hat))
    mse = ((yh - Yz) ** 2).sum() / ok.sum().clamp_min(1)
    cos = (yh * Yz).sum(1) / (yh.norm(dim=1) * Yz.norm(dim=1)).clamp_min(1e-8)
    if cfg.loss == "cos":
        return (1 - cos).mean(), mse.detach(), cos.mean().detach()
    return mse + cfg.cos_weight * (1 - cos).mean(), mse.detach(), cos.mean().detach()


def run_episode(model, ep, cfg, uniform=False):
    t = to_t(ep)
    if uniform:
        with torch.no_grad():
            E, av = t["E"], t["avail"]
            w = torch.exp(t["prior"])[:, None, None] * av
            y = t["A0"] * (w * E).sum(0) / w.sum(0).clamp_min(1e-12)
            return loss_fn(y, t["Y"], cfg), None, t["A0"]
    y, alpha, A = model(t["E"], t["avail"], t["basal_L"], t["basal_S"], t["genes"], t["A0"], t["prior"])
    return loss_fn(y, t["Y"], cfg), alpha, A


# ---------------------------------------------------------------- training

def attention_health(alpha, avail) -> dict:
    """Mean normalized entropy (1 = equal weights, 0 = one source), effective sources and the largest share."""
    a = alpha.detach().clamp_min(1e-12)
    n = avail.sum(0).float()
    multi = n > 1
    if not multi.any():
        return {"entropy_norm": None, "eff_sources": None, "max_share": None}
    H = -(a * a.log() * avail).sum(0)
    return {"entropy_norm": float((H[multi] / n[multi].log()).mean()), "eff_sources": float(H[multi].exp().mean()),
            "max_share": float(a.max(0).values[multi].mean())}


def evaluate(model, eps, cfg) -> dict:
    """The configured loss of the net and of the equal-weight start (for early stopping), plus fixed metrics that do
    not depend on the configuration, so runs with different switches compare: the r1 loss, the cosine on all genes,
    and the size ratio |y_hat| / |truth| on the observed genes (1 = natural size)."""
    ref = Config()
    out = {k: [] for k in ("net_loss", "uni_loss", "net_cos", "uni_cos", "net_r1loss", "uni_r1loss",
                           "net_cos_all", "uni_cos_all", "net_size", "uni_size")}
    with torch.no_grad():
        for ep in eps:
            for tag, uni in (("net", False), ("uni", True)):
                (l, _, c), _, _ = run_episode(model, ep, cfg, uniform=uni)
                (l1, _, c1), _, _ = run_episode(model, ep, ref, uniform=uni)
                out[f"{tag}_loss"].append(float(l)); out[f"{tag}_cos"].append(float(c))
                out[f"{tag}_r1loss"].append(float(l1)); out[f"{tag}_cos_all"].append(float(c1))
                y = predict(model, ep, uniform=uni)
                Y = torch.as_tensor(ep["Y"])
                ok = torch.isfinite(Y)
                out[f"{tag}_size"].append(float(y[ok].norm() / Y[ok].norm().clamp_min(1e-12)))
    return {k: float(np.mean(v)) for k, v in out.items()} | {"delta_loss": float(np.mean(out["net_loss"]) - np.mean(out["uni_loss"]))}


def predict(model, ep, uniform=False):
    t = to_t(ep)
    if uniform:
        w = torch.exp(t["prior"])[:, None, None] * t["avail"]
        return t["A0"] * (w * t["E"]).sum(0) / w.sum(0).clamp_min(1e-12)
    y, _, _ = model(t["E"], t["avail"], t["basal_L"], t["basal_S"], t["genes"], t["A0"], t["prior"])
    return y


def train(keys: list[Key], val_groups, test_groups, out: Path, cfg: Config) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    if (out / "monitor.jsonl").exists():
        raise SystemExit(f"{out} already holds a run; choose a new --out")
    torch.manual_seed(cfg.seed)
    rng = np.random.default_rng(cfg.seed)
    closed = set(val_groups) | set(test_groups)
    train_keys = [k for k in keys if k.group not in closed]
    if len(train_keys) < 3:
        raise SystemExit(f"{len(train_keys)} training keys: too few")
    G = keys[0].basal.size
    panel = basal_panel(train_keys, cfg.panel)
    B = np.stack([k.basal for k in train_keys])[:, panel]
    model = SourceAttention(G, panel, B.mean(0), B.std(0) + 1e-3, cfg)
    np.savez(out / "norm.npz", panel=panel, mu=B.mean(0), sd=B.std(0) + 1e-3, n_genes=G)
    opt = torch.optim.Adam(model.parameters(), lr=cfg.lr)
    val_eps = []
    vr = np.random.default_rng(cfg.seed + 1)                  # fixed validation episodes
    for k in keys:
        if k.group in val_groups:
            ep = episode(k, allowed_sources(k, train_keys), vr, 4 * cfg.targets_per_episode, cfg.genes_per_episode)
            if ep is not None:
                val_eps.append(ep)
    if not val_eps:
        raise SystemExit("no validation episode: check --val against the key groups")
    split = {"train": [k.key for k in train_keys], "val": [k.key for k in keys if k.group in val_groups],
             "test": [k.key for k in keys if k.group in test_groups], "config": asdict(cfg)}
    (out / "split.json").write_text(json.dumps(split, indent=1, default=str))
    log(f"{len(train_keys)} training keys, {len(val_eps)} validation episodes, {sum(p.numel() for p in model.parameters())} params")

    best, worse, history = math.inf, 0, []
    for step in range(cfg.steps + 1):
        if step % cfg.eval_every == 0 or step in cfg.keep_steps:
            ev = evaluate(model, val_eps, cfg)
            rec = {"step": step} | ev
            history.append(rec)
            with open(out / "monitor.jsonl", "a") as fh:
                fh.write(json.dumps(rec) + "\n")
            if step in cfg.keep_steps:
                torch.save(model.state_dict(), out / f"ckpt_step{step:06d}.pt")
            if ev["net_loss"] < best:
                best = ev["net_loss"]
                torch.save(model.state_dict(), out / "ckpt_best.pt")
            worse = worse + 1 if ev["delta_loss"] > 0 else 0
            log(f"step {step}: val net {ev['net_loss']:.4f} vs equal {ev['uni_loss']:.4f}, cos(all) {ev['net_cos_all']:.4f} "
                f"vs {ev['uni_cos_all']:.4f}, size {ev['net_size']:.3f} vs {ev['uni_size']:.3f}")
            if step >= cfg.min_steps and worse >= cfg.patience:
                log(f"stop: {worse} evaluations in a row worse than the equal-weight start")
                break
        L = train_keys[rng.integers(len(train_keys))]
        ep = episode(L, allowed_sources(L, train_keys), rng, cfg.targets_per_episode, cfg.genes_per_episode)
        if ep is None or not ep["avail"].any():
            continue
        (loss, mse, cos), alpha, A = run_episode(model, ep, cfg)
        opt.zero_grad()
        loss.backward()
        gnorm = float(torch.nn.utils.clip_grad_norm_(model.parameters(), 5.0))
        opt.step()
        if step % cfg.eval_every == 0:
            h = attention_health(alpha, torch.as_tensor(ep["avail"]))
            with open(out / "monitor.jsonl", "a") as fh:
                fh.write(json.dumps({"step": step, "train_key": L.key, "train_loss": float(loss), "train_mse": float(mse),
                                     "train_cos": float(cos), "amplitude": float(A), "grad_norm": gnorm} | h) + "\n")
    torch.save(model.state_dict(), out / "ckpt_last.pt")
    summary = {"steps_done": step, "best_val_loss": best, "history_tail": history[-3:]}
    (out / "done.json").write_text(json.dumps(summary, indent=1))
    return summary


def export_effects(model, L: Key, sources: list[Key], targets, path: Path, chunk: int = 50) -> None:
    """Predicted effects of ``targets`` in L on every gene, in the npz layout the benches read (targets, genes, lfc).
    The amplitude rule is applied once over all ``targets`` (as the bench does over its panel), not per chunk."""
    genes = np.arange(L.basal.size)
    targets = list(targets)
    parts, A0s = [], []
    full = episode(L, sources, None, 0, 0, targets=targets, genes=genes)
    A0 = full["A0"]
    del full
    with torch.no_grad():
        for i in range(0, len(targets), chunk):
            t = to_t(episode(L, sources, None, 0, 0, targets=targets[i:i + chunk], genes=genes))
            y, _, _ = model(t["E"], t["avail"], t["basal_L"], t["basal_S"], t["genes"], A0, t["prior"])
            parts.append(y.numpy().astype(np.float32))
    np.savez_compressed(path, targets=np.array(targets), genes=genes, lfc=np.vstack(parts), A0=A0)


def export_lines(keys_dir: Path, run: Path, line_keys: list[str], out: Path, ckpts=("ckpt_best.pt", "ckpt_step000000.pt"),
                 names=("net", "net0")) -> dict:
    """For each held-out key, the effects of every target its training sources cover, from each checkpoint:
    ``<name>_<group>.npz``. The training keys are read back from split.json, the encoder normalisation from norm.npz."""
    keys = load_keys(keys_dir)
    split = json.loads((run / "split.json").read_text())
    cfg = Config(**{k: (tuple(v) if k == "keep_steps" else v) for k, v in split["config"].items()})
    train_keys = [k for k in keys if k.key in set(split["train"])]
    nz = np.load(run / "norm.npz")
    out.mkdir(parents=True, exist_ok=True)
    done = {}
    for lk in line_keys:
        L = next(k for k in keys if k.key == lk)
        sources = allowed_sources(L, train_keys)
        targets = [t for t in L.targets if any(t in k.row for k in sources)]
        for ck, name in zip(ckpts, names):
            model = SourceAttention(int(nz["n_genes"]), nz["panel"], nz["mu"], nz["sd"], cfg)
            model.load_state_dict(torch.load(run / ck))
            model.eval()
            path = out / f"{name}_{L.group}.npz"
            export_effects(model, L, sources, targets, path)
            done[f"{name}_{L.group}"] = {"key": lk, "targets": len(targets), "sources": [k.key for k in sources],
                                         "checkpoint": ck}
    (out / "export.json").write_text(json.dumps(done, indent=1))
    return done


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--keys", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--val", nargs="+", required=True, help="line groups for early stopping (never trained on)")
    p.add_argument("--test", nargs="+", required=True, help="line groups kept for the real-scorer bench")
    p.add_argument("--steps", type=int, default=Config.steps)
    p.add_argument("--amp", choices=["learned", "fixed"], default=Config.amp)
    p.add_argument("--loss", choices=["mse_cos", "cos"], default=Config.loss)
    p.add_argument("--loss-genes", choices=["all", "top"], default=Config.loss_genes)
    p.add_argument("--top-frac", type=float, default=Config.top_frac)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--export-keys", nargs="*", default=[], help="held-out keys to export effects for, after training")
    p.add_argument("--export-out", type=Path, default=None)
    a = p.parse_args()
    cfg = Config(steps=a.steps, seed=a.seed, amp=a.amp, loss=a.loss, loss_genes=a.loss_genes, top_frac=a.top_frac)
    train(load_keys(a.keys), a.val, a.test, a.out, cfg)
    if a.export_keys:
        export_lines(a.keys, a.out, a.export_keys, a.export_out or a.out / "export")


if __name__ == "__main__":
    main()
