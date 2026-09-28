"""train.py with the context vector read from basal-profile embeddings: frozen (--context-embeddings FILE) or a
pre-trained encoder fine-tuned on the CRISPRi loss (--finetune-encoder DIR). --selftest runs selftest_emb.py.

train.py, net.py and pool.py (reports/modelli/rete_contesti_2026-09-27/) are not edited. With either flag, install()
routes train.py's constructors to the subclasses below -- EmbPhase for pool.Phase, EmbPerturbNet for
net.PerturbNet, emb_net_config for train.net_config -- and wraps train.predict_arms and train.write_predictions;
the design, training, validation, prediction and diagnostics are train.py's own code. Without either flag this
is train.py (run_design is called directly, nothing is patched).

The context vector. In net.py the trunk of every row reads u_c = MLP(drank-weighted mean of the gene embeddings),
a learned global vector. Here u_c = tanh(W e_c + b): e_c is the context's embedding, standardised on the training
contexts (below), and W a small linear map shared by all contexts (d_emb x --emb-dim-out, default --d-context).
--emb-mode add keeps the learned vector and concatenates the two. Everything else is the network: the per-gene
context features, the gates, the transfer path. At initialisation the head is zero, so the network is still
the calibrated transfer whatever the embeddings say.

Standardisation, from the phase's visible contexts only: e_c = (x_c - x_ref) / s, with x_ref the mean embedding
of the visible training contexts (--emb-blind families: the mean over families of the family means) and s the
root mean square of their deviations from it. The blind embedding is therefore exactly 0, and nothing about a
held-out context enters the constants (the self-test checks it).

Controls, from the same model (the first two are train.py's own arms, now with the embedding too):
* blind: the training-average gene features and the blind embedding (0);
* swap: another context's gene features and embedding;
* emb_blind: the row's true gene features with the blind embedding -- what the embedding path adds;
* emb_swap: the true gene features with the swap context's embedding -- whether it is the right context's.
emb_blind and emb_swap enter metrics.json (contrasts net-emb_blind and net-emb_swap, and E2) and are written to
predemb_<context>.npz beside train.py's pred_<context>.npz.

Contexts absent from the embeddings fail loudly: before training, for every context the design reads (visible,
truth, swap, --predict-contexts); in the forward pass, for any row whose embedding is missing. When the
embeddings' manifest lists the contexts excluded from pre-training, every held-out context of the design must be
among them (a design that holds out K562 cannot use an encoder that trained on K562 profiles), unless
--allow-seen-contexts (transductive use, e.g. production on A/B/C).

Fine-tuning (--finetune-encoder DIR --finetune-corpus C [--finetune-corpus C2 ...]): the encoder of pretrain.py
(DIR/encoder.pt) with its normalisation; a context's embedding is the mean of the encoder over its control
profiles (at most --finetune-max-profiles, in corpus order), recomputed at every step with gradients. The
pre-trained weights stay frozen; offsets (encoder.DeltaEncoder) start at 0 and enter as w0 + --finetune-scale x
delta, so the encoder moves --finetune-scale times slower than the network, and weight decay pulls it back to w0.
The standardisation constants come from the pre-trained encoder's embeddings of the visible contexts.

    python train_emb.py --selftest
    python train_emb.py --data DATASET --out NEW --hold-out k562 --context-embeddings PRE/context_embeddings.npz
    python train_emb.py --data DATASET --out NEW --hold-out orion_hct116,orion_hek293t --context-embeddings FILE
    python train_emb.py --data DATASET --out NEW --hold-out k562 --finetune-encoder PRE --finetune-corpus C1 ...
"""
from __future__ import annotations

import dataclasses
import json
import os
import sys
import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import torch
from torch import nn

HERE = Path(__file__).resolve().parent


def _network_dir() -> Path:
    env = os.environ.get("RETE_CONTESTI_CODE", "")
    for d in ([Path(env)] if env else []) + [HERE, HERE.parent / "rete_contesti_2026-09-27"]:
        if all((d / f).exists() for f in ("net.py", "pool.py", "train.py")):
            return d.resolve()
    raise SystemExit("net.py, pool.py and train.py (reports/modelli/rete_contesti_2026-09-27) not found: copy them beside "
                     "this file or set RETE_CONTESTI_CODE")


NET_DIR = _network_dir()
for _d in (NET_DIR, HERE):
    if str(_d) not in sys.path:
        sys.path.insert(0, str(_d))

import corpus as CO  # noqa: E402
import encoder as ENC  # noqa: E402
import net as N  # noqa: E402
import pool as P  # noqa: E402
import train as T  # noqa: E402

EXTRA_ARMS = ("emb_blind", "emb_swap")
SETTINGS = None          # EmbSettings while installed; read by EmbPhase and EmbPerturbNet
_ORIG = {"Phase": P.Phase, "PerturbNet": N.PerturbNet, "net_config": T.net_config,
         "predict_arms": T.predict_arms, "write_predictions": T.write_predictions, "ARM_PAIRS": list(T.ARM_PAIRS)}


@dataclass
class EmbSettings:
    table: dict                                       # embedding context name -> np.ndarray [dim]
    dim: int
    emb_map: dict = field(default_factory=dict)       # network basal name -> embedding context name
    blind: str = "contexts"
    finetune: dict | None = None                      # config, state_dict, profiles [n, G], ranges {name: (a, b)}
    provenance: dict = field(default_factory=dict)

    def key(self, basal_name: str) -> str:
        return self.emb_map.get(basal_name, basal_name)


@dataclass
class EmbNetConfig(N.NetConfig):
    d_emb_in: int = 0
    emb_mode: str = "replace"          # "replace": u = tanh(W e); "add": u = [learned global vector, tanh(W e)]
    d_emb_out: int = 8
    emb_noise: float = 0.0             # Gaussian noise on the standardised embedding, training only
    finetune: bool = False
    finetune_scale: float = 0.1


class ContextVector(nn.Module):
    """Takes the place of PerturbNet.u_mlp: u of each feature row in use, from its embedding (set in `current` by
    EmbPerturbNet.forward just before the parent's forward calls this module), and in "add" mode also from the
    learned global encoding, as net.py computes it."""

    def __init__(self, d_gene: int, d_learned: int, d_emb_in: int, d_emb_out: int):
        super().__init__()
        self.learned = (nn.Sequential(nn.Linear(d_gene, 32), nn.GELU(), nn.Linear(32, d_learned), nn.Tanh())
                        if d_learned > 0 else None)
        self.emb_map = nn.Linear(d_emb_in, d_emb_out)
        self.current = None

    def forward(self, pooled: torch.Tensor) -> torch.Tensor:
        if self.current is None:
            raise RuntimeError("the batch's context embeddings were not set (EmbPerturbNet.forward sets them)")
        u = torch.tanh(self.emb_map(self.current))
        if self.learned is not None:
            u = torch.cat([self.learned(pooled), u], dim=1)
        return u


class EmbPerturbNet(N.PerturbNet):
    """net.PerturbNet whose context vector comes from the context embeddings; with a plain NetConfig (or
    d_emb_in 0) it is net.PerturbNet unchanged."""

    def __init__(self, cfg, gene_init=None):
        if not (isinstance(cfg, EmbNetConfig) and cfg.d_emb_in > 0):
            super().__init__(cfg, gene_init)
            self.emb_cfg = None
            self.ctx_encoder = None
            return
        learned = cfg.emb_mode == "add" and cfg.use_global_context
        d_u = (cfg.d_context if learned else 0) + cfg.d_emb_out
        super().__init__(dataclasses.replace(cfg, d_context=d_u, use_global_context=True), gene_init)
        self.emb_cfg = cfg
        self.u_mlp = ContextVector(cfg.d_gene, cfg.d_context if learned else 0, cfg.d_emb_in, cfg.d_emb_out)
        self.ctx_encoder = None
        if cfg.finetune:
            ft = SETTINGS.finetune if SETTINGS is not None else None
            if ft is None:
                raise RuntimeError("fine-tuning needs the pre-trained encoder in the settings (install())")
            base = ENC.ContextEncoder(ENC.EncoderConfig(**ft["config"]))
            base.load_state_dict(ft["state_dict"])
            self.ctx_encoder = ENC.DeltaEncoder(base, cfg.finetune_scale)

    def forward(self, b: dict, feat: torch.Tensor, consts: dict) -> dict:
        if self.emb_cfg is None:
            return super().forward(b, feat, consts)
        used, inv = torch.unique(b["row_feat"], return_inverse=True)       # as the parent computes them
        er = b.get("emb_row")
        if er is None:
            e_used = used
        else:
            e_used = torch.zeros_like(used)
            e_used[inv] = er
            if not torch.equal(e_used[inv], er):
                raise ValueError("emb_row must be the same for every row that shares a feature row")
        vec = self.context_vectors(e_used, consts)
        if self.training and self.emb_cfg.emb_noise > 0:
            vec = vec + self.emb_cfg.emb_noise * torch.randn_like(vec)
        self.u_mlp.current = vec
        try:
            return super().forward(b, feat, consts)
        finally:
            self.u_mlp.current = None

    def context_vectors(self, e_used: torch.Tensor, consts: dict) -> torch.Tensor:
        vec = consts["ctx_emb"][e_used] if self.ctx_encoder is None else self._encode(e_used.tolist(), consts)
        ok = torch.isfinite(vec).all(dim=1)
        if not bool(ok.all()):
            names = consts["emb_names"]
            bad = [names[j] for j, good in zip(e_used.tolist(), ok.tolist()) if not good]
            raise ValueError(f"no embedding for {bad}")
        return vec

    def _encode(self, rows: list, consts: dict) -> torch.Tensor:
        """Fine-tuning: the standardised mean of the encoder over each context's control profiles; the blind row
        is the weighted mean over the visible contexts."""
        prof, ranges, blind = consts["emb_profiles"], consts["emb_ranges"], consts["emb_blind_index"]
        cache: dict = {}

        def one(j: int) -> torch.Tensor:
            if j not in cache:
                a, b = ranges[j]
                if b <= a:
                    cache[j] = prof.new_full((self.emb_cfg.d_emb_in,), float("nan"))
                else:
                    cache[j] = self.ctx_encoder(prof[a:b]).mean(dim=0)
            return cache[j]

        out = []
        for j in rows:
            if j == blind:
                out.append(sum(w * one(k) for k, w in zip(consts["emb_visible"], consts["emb_visible_weights"])))
            else:
                out.append(one(j))
        return (torch.stack(out) - consts["emb_center"]) / consts["emb_scale"]


class EmbPhase(P.Phase):
    """pool.Phase plus consts["ctx_emb"]: the embedding of every basal row, standardised on the phase's visible
    contexts, and the blind row (index n_basal, all zeros). With no settings installed it is pool.Phase."""

    def __init__(self, pool, train_rows, opts=None, device="cpu", log=print):
        super().__init__(pool, train_rows, opts, device, log)
        self.emb_override = None
        self.emb_info = None
        s = SETTINGS
        if s is None:
            return
        nb = len(pool.basal_names)
        keys = [s.key(b) for b in pool.basal_names]
        vis = [int(b) for b in np.unique(pool.ctx_basal[self.contexts])]
        missing = [pool.basal_names[b] for b in vis if keys[b] not in s.table]
        if missing:
            raise SystemExit(f"visible training contexts without an embedding: {missing}")
        raw = np.full((nb, s.dim), np.nan)
        for b in range(nb):
            v = s.table.get(keys[b])
            if v is not None:
                raw[b] = np.asarray(v, dtype=np.float64)
        weights = self.blind_weights(vis, s.blind)
        wv = np.array([weights[b] for b in vis])
        ref = (wv[:, None] * raw[vis]).sum(axis=0)
        scale = float(np.sqrt((wv * ((raw[vis] - ref[None, :]) ** 2).mean(axis=1)).sum()))
        if not np.isfinite(scale) or scale <= 1e-12:
            raise SystemExit("the visible contexts' embeddings do not vary: nothing to standardise on")
        table = np.vstack([(raw - ref[None, :]) / scale, np.zeros((1, s.dim))]).astype(np.float32)
        d = self.device
        self.consts["ctx_emb"] = torch.from_numpy(table).to(d)
        self.consts["emb_names"] = list(pool.basal_names) + ["<blind>"]
        self.consts["emb_center"] = torch.from_numpy(ref.astype(np.float32)).to(d)
        self.consts["emb_scale"] = scale
        self.consts["emb_blind_index"] = nb
        self.consts["emb_visible"] = vis
        self.consts["emb_visible_weights"] = [float(w) for w in wv]
        if s.finetune is not None:
            ft = s.finetune
            self.consts["emb_profiles"] = torch.from_numpy(ft["profiles"]).to(d)
            self.consts["emb_ranges"] = [tuple(ft["ranges"].get(k, (0, 0))) for k in keys] + [(0, 0)]
        absent = [pool.basal_names[b] for b in range(nb) if not np.isfinite(raw[b]).all()]
        self.emb_info = {"visible": [pool.basal_names[b] for b in vis], "weights": [float(w) for w in wv],
                         "blind": s.blind, "scale": scale, "center_norm": float(np.linalg.norm(ref)),
                         "rows_without_embedding": absent}
        log(f"context embeddings ({'fine-tuned encoder' if s.finetune is not None else 'frozen'}): standardised on "
            f"{len(vis)} visible contexts (scale {scale:.4g}); basal rows without an embedding: {absent}")

    def blind_weights(self, vis: list, mode: str) -> dict:
        """Weights of the visible basal rows in the reference (and the blind embedding): equal per context, or
        equal per family and equal within."""
        if mode == "contexts":
            return {b: 1.0 / len(vis) for b in vis}
        fam: dict = {}
        for c in self.contexts:
            fam.setdefault(int(self.pool.ctx_family[c]), set()).add(int(self.pool.ctx_basal[c]))
        w: dict = {}
        for bs in fam.values():
            for b in bs:
                w[b] = w.get(b, 0.0) + 1.0 / (len(fam) * len(bs))
        return w

    @contextmanager
    def override(self, kind: str, swap_basal: int | None = None):
        """Inside the block every batch carries emb_row: the blind row, or `swap_basal`, for every row."""
        old = self.emb_override
        self.emb_override = (kind, swap_basal)
        try:
            yield
        finally:
            self.emb_override = old

    def batch(self, spec, **kw):
        out = super().batch(spec, **kw)
        if self.emb_override is not None:
            kind, swap = self.emb_override
            if kind == "blind":
                er = np.full(len(spec), self.blind_index, dtype=np.int64)
            elif kind == "swap" and swap is not None:
                er = np.full(len(spec), int(swap), dtype=np.int64)
            else:
                raise ValueError(f"embedding override {self.emb_override!r}")
            out["emb_row"] = torch.from_numpy(er).to(self.device)
        return out


def emb_net_config(args, pool, phase):
    base = _ORIG["net_config"](args, pool, phase)
    s = SETTINGS
    if s is None:
        return base
    return EmbNetConfig(**base.to_dict(), d_emb_in=int(s.dim), emb_mode=args.emb_mode,
                        d_emb_out=args.emb_dim_out if args.emb_dim_out > 0 else args.d_context,
                        emb_noise=args.emb_noise, finetune=s.finetune is not None,
                        finetune_scale=args.finetune_scale)


def emb_predict_arms(phase, model, spec, swap_basal, cal):
    arms, m, q = _ORIG["predict_arms"](phase, model, spec, swap_basal, cal)
    if isinstance(phase, EmbPhase) and phase.emb_info is not None:
        with phase.override("blind"):
            arms["emb_blind"] = T.predict(phase, model, spec, feat="true")[0]
        if swap_basal is not None:
            with phase.override("swap", swap_basal):
                arms["emb_swap"] = T.predict(phase, model, spec, feat="true")[0]
    return arms, m, q


def emb_write_predictions(path, pool, targets, arms, m, q, meta) -> None:
    _ORIG["write_predictions"](path, pool, targets, arms, m, q, meta)
    extra = [k for k in EXTRA_ARMS if k in arms]
    if extra:
        path = Path(path)
        side = path.with_name("predemb_" + (path.name[len("pred_"):] if path.name.startswith("pred_") else path.name))
        payload = {"targets": np.array(targets, dtype=str), "axis_index": pool.genes_axis}
        for k in extra:
            payload[k] = T.full_axis(pool, arms[k])
        payload["meta"] = np.array(json.dumps(T.jsonable(meta)))
        with open(side, "xb") as fh:
            np.savez_compressed(fh, **payload)


def install(settings: EmbSettings | None) -> None:
    """Route train.py to the embedding-aware classes (module attributes of pool, net and train)."""
    global SETTINGS
    SETTINGS = settings
    P.Phase = EmbPhase
    N.PerturbNet = EmbPerturbNet
    T.net_config = emb_net_config
    T.predict_arms = emb_predict_arms
    T.write_predictions = emb_write_predictions
    T.ARM_PAIRS = _ORIG["ARM_PAIRS"] + [("net", a) for a in EXTRA_ARMS]


def uninstall() -> None:
    global SETTINGS
    SETTINGS = None
    P.Phase = _ORIG["Phase"]
    N.PerturbNet = _ORIG["PerturbNet"]
    T.net_config = _ORIG["net_config"]
    T.predict_arms = _ORIG["predict_arms"]
    T.write_predictions = _ORIG["write_predictions"]
    T.ARM_PAIRS = list(_ORIG["ARM_PAIRS"])


# ---------------------------------------------------------------- settings

def read_map(path) -> dict:
    """CSV with columns network, embedding: the embedding context name of a network basal row."""
    import pandas as pd
    tab = pd.read_csv(path, keep_default_na=False, na_values=[""], dtype=str)
    if not {"network", "embedding"} <= set(tab.columns):
        raise SystemExit(f"{path}: columns network, embedding are required")
    return dict(zip(tab["network"].str.strip(), tab["embedding"].str.strip()))


def manifest_summary(manifest: dict | None) -> dict | None:
    if manifest is None:
        return None
    keep = ("method", "stage", "created_utc", "genes", "exclusions", "contexts", "profiles", "normalisation",
            "encoder", "pca", "embeddings")
    out = {k: manifest.get(k) for k in keep if k in manifest}
    out["corpora"] = [{"argument": c.get("argument"), "npz": c.get("npz")} for c in manifest.get("corpora", [])]
    return out


def load_finetune(args, pool, emb_map: dict, log=print) -> tuple[dict, dict, dict]:
    """(initial table {name: embedding}, fine-tuning payload, provenance) from pretrain.py's encoder.pt and the
    control profiles of the dataset's basal rows in --finetune-corpus."""
    folder = Path(args.finetune_encoder)
    ckpt = folder / "encoder.pt" if folder.is_dir() else folder
    ck = ENC.load_checkpoint(ckpt)
    norm = ck["norm"]
    if not args.finetune_corpus:
        raise SystemExit("--finetune-encoder needs --finetune-corpus (the corpora with the contexts' controls)")
    names = sorted({emb_map.get(b, b) for b in pool.basal_names})
    X, ranges, corpora = CO.profiles_for_contexts(
        args.finetune_corpus, names, norm["genes_axis"].numpy().astype(np.int64), norm["mu"].numpy(),
        norm["sd"].numpy(), str(norm["mode"]), str(norm["denominator"]), args.finetune_max_profiles)
    base = ENC.build_encoder(ck)
    base.eval()
    table = {}
    with torch.no_grad():
        for name, (a, b) in ranges.items():
            table[name] = base(torch.from_numpy(X[a:b])).mean(dim=0).numpy().astype(np.float64)
    mp = ckpt.parent / "manifest.json"
    manifest = json.loads(mp.read_text(encoding="utf-8")) if mp.exists() else None
    log(f"fine-tuning: encoder {ckpt}; {X.shape[0]} control profiles of {len(ranges)} contexts, "
        f"{X.shape[1]} genes")
    ft = {"config": ck["config"], "state_dict": ck["state_dict"], "profiles": X, "ranges": ranges}
    prov = {"encoder": CO.provenance(ckpt), "corpora": corpora, "manifest": manifest_summary(manifest),
            "profiles": {n: b - a for n, (a, b) in ranges.items()}}
    return table, ft, prov | {"_manifest": manifest}


def make_settings(args, pool, log=print) -> EmbSettings:
    """Read the embeddings (or the encoder), and check them against the design before anything is trained:
    every context the design reads must have an embedding; no held-out context may have trained the encoder."""
    emb_map = read_map(args.emb_map) if args.emb_map else {}
    design = T.make_design(pool, args, T.Logger(quiet=True))
    names = pool.context_names
    need: dict = {}

    def want(basal_row, why):
        need.setdefault(int(basal_row), []).append(why)

    for c in design["visible_contexts"]:
        want(pool.ctx_basal[c], f"visible {names[c]}")
    for c in design["truth"]:
        want(pool.ctx_basal[c], f"truth {names[c]}")
    for c, sw in design["swap"].items():
        if sw is not None:
            want(pool.ctx_basal[sw], f"swap of {names[c]}")
    for name in CO.split_list(args.predict_contexts):
        if name not in pool.basal_index:
            raise SystemExit(f"{name!r} is not a basal row of the dataset ({pool.basal_names})")
        want(pool.basal_index[name], f"predict {name}")
    if args.finetune_encoder is not None:
        table, ft, prov = load_finetune(args, pool, emb_map, log)
        dim = int(ENC.EncoderConfig(**ft["config"]).d_emb)
        source = str(args.finetune_corpus)
    else:
        emb = CO.read_embeddings(args.context_embeddings)
        table = {n: emb["E"][i] for i, n in enumerate(emb["names"])}
        dim, ft, source = int(emb["E"].shape[1]), None, str(args.context_embeddings)
        prov = {"file": {k: emb.get(k) for k in ("path", "bytes", "sha256")}, "meta": emb["meta"],
                "manifest": manifest_summary(emb["manifest"]), "_manifest": emb["manifest"]}
    key = {b: emb_map.get(pool.basal_names[b], pool.basal_names[b]) for b in range(len(pool.basal_names))}
    missing = {pool.basal_names[b]: why for b, why in need.items() if key[b] not in table}
    if missing:
        have = sorted(table)
        raise SystemExit(f"contexts the design reads have no embedding in {source}: {missing}; it has "
                         f"{len(have)} contexts, e.g. {have[:20]} (map names with --emb-map)")
    manifest = prov.pop("_manifest", None)
    if manifest is not None and not args.allow_seen_contexts:
        excluded = set((manifest.get("contexts") or {}).get("excluded", []))
        hidden = [names[c] for c in design["hidden_contexts"]]
        seen = [h for h in hidden if key[int(pool.ctx_basal[pool.context_index[h]])] not in excluded]
        if seen:
            raise SystemExit(f"the encoder behind {source} was pre-trained on profiles of the held-out contexts "
                             f"{seen}: pre-train with the design's exclusions, or pass --allow-seen-contexts "
                             f"(transductive; no generalisation claim)")
    prov["needed"] = {pool.basal_names[b]: why for b, why in need.items()}
    return EmbSettings(table=table, dim=dim, emb_map=emb_map, blind=args.emb_blind, finetune=ft, provenance=prov)


def run_with(settings: EmbSettings, args, pool, log=None) -> dict:
    """train.run_design with the settings installed; writes emb_config.json beside train.py's outputs."""
    t0 = time.time()
    install(settings)
    try:
        res = T.run_design(args, pool=pool, log=log)
    finally:
        uninstall()
    info = {"stage": "encoder_contesto_2026-09-28/train_emb.py", "run_label": args.run_label,
            "mode": "finetune" if settings.finetune is not None else "frozen",
            "context_embeddings": args.context_embeddings, "finetune_encoder": args.finetune_encoder,
            "finetune_corpus": args.finetune_corpus, "emb_map": settings.emb_map, "emb_blind": settings.blind,
            "emb_mode": args.emb_mode, "emb_dim_out": args.emb_dim_out or args.d_context, "emb_noise": args.emb_noise,
            "finetune_scale": args.finetune_scale, "finetune_max_profiles": args.finetune_max_profiles,
            "dim": settings.dim, "provenance": settings.provenance,
            "phase": getattr(res["phase"], "emb_info", None), "parameters": res["config"].get("parameters"),
            "extra_arms": list(EXTRA_ARMS), "seconds": round(time.time() - t0, 1)}
    CO.write_json(Path(args.out) / "emb_config.json", info)
    res["emb_config"] = info
    return res


def build_parser():
    ap = T.build_parser()
    ap.description = __doc__
    g = ap.add_argument_group("context embeddings (train_emb.py)")
    g.add_argument("--context-embeddings", type=Path, default=None, help="context_embeddings.npz (frozen)")
    g.add_argument("--emb-map", type=Path, default=None, help="CSV network,embedding when the names differ")
    g.add_argument("--emb-mode", choices=["replace", "add"], default="replace")
    g.add_argument("--emb-dim-out", type=int, default=0, help="size of tanh(W e) (default: --d-context)")
    g.add_argument("--emb-blind", choices=["contexts", "families"], default="contexts")
    g.add_argument("--emb-noise", type=float, default=0.0)
    g.add_argument("--allow-seen-contexts", action="store_true",
                   help="accept embeddings whose encoder trained on held-out contexts (transductive)")
    g.add_argument("--finetune-encoder", type=Path, default=None, help="pretrain.py output folder (or its encoder.pt)")
    g.add_argument("--finetune-corpus", action="append", default=[])
    g.add_argument("--finetune-max-profiles", type=int, default=32)
    g.add_argument("--finetune-scale", type=float, default=0.1)
    g.add_argument("--run-label", default="", help="free text kept in emb_config.json (design, condition, seed)")
    return ap


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    if args.selftest:
        import selftest_emb
        return selftest_emb.main()
    if args.data is None or args.out is None:
        raise SystemExit("--data and --out are required (or --selftest)")
    if args.context_embeddings is None and args.finetune_encoder is None:
        T.run_design(args)
        return 0
    if args.context_embeddings is not None and args.finetune_encoder is not None:
        raise SystemExit("--context-embeddings and --finetune-encoder exclude each other")
    pool = P.Pool.from_dir(args.data)
    run_with(make_settings(args, pool), args, pool)
    return 0


if __name__ == "__main__":
    sys.exit(main())
