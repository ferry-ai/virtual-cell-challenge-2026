"""Stage-105 adapter: the network behind vcc2026.ctj.Predictor's fit/predict signature (needs torch).

    from adapter_ctj import NetPredictor
    model = NetPredictor("net", genes, contexts, basal).fit(train_sources, split["context"])
    pred = model.predict(targets, context)        # (T, len(genes)) on the official axis, NaN where not predicted

`genes`, `contexts` (source -> context label) and `basal` (label -> log1p CPM on `genes`) are what
scripts/105_ctj_bench.py builds; `train_sources` are its `training_sources(...)` AxisTables, so the held-out
contexts and targets of a frozen split never reach the network. Each fit builds an in-memory pool.Pool (one
context per source; family = its context label, group = the source), trains for a fixed number of steps (stage
105 has no validation split) and predicts with m from every training family but the predicted label's own, the
context features from `basal[context]` (105's swap control passes another label), and partner profiles from the
label's own family only when that label trained (regime T). No coordinates or STRING here unless given: the own
gene is the only exclusion and there are no partners. What stage 105 would need is in DISEGNO.md, section 8.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))

import pool as P  # noqa: E402
import train  # noqa: E402


class NetPredictor:
    """Same constructor arguments as vcc2026.ctj.Predictor (k, ridge and gamma are accepted and unused), plus the
    network's: steps, seed, device, se_factor {source: k} and train.py flags in `flags` (e.g. ["--no-inter"])."""

    def __init__(self, name: str = "net", genes=None, contexts=None, basal=None, k: int = 8, ridge: float = 0.01,
                 gamma: float = 0.0, reliability_scale: float = 100.0, *, steps: int = 3000, seed: int = 0,
                 device: str = "auto", se_factor: dict | None = None, flags: list | None = None, log=None):
        if genes is None or contexts is None or basal is None:
            raise ValueError("genes, contexts and basal are required")
        self.name, self.genes = name, [str(g) for g in genes]
        self.contexts, self.basal = dict(contexts), dict(basal)
        self.steps, self.seed = int(steps), int(seed)
        self.device = train.resolve_device(device)
        self.se_factor = dict(se_factor or {})
        self.flags = list(flags or [])
        self.log = log or train.Logger(quiet=True)
        if reliability_scale != P.RELIABILITY:
            raise ValueError(f"the network's profiles use n / (n + {P.RELIABILITY:g})")

    def fit(self, train_sources: dict, context: str) -> "NetPredictor":
        genes, A = self.genes, len(self.genes)
        tabs = [t for t in train_sources.values() if len(t.targets)]
        if not tabs:
            raise ValueError("no training source with targets")
        labels = sorted(self.basal)
        cpm = np.vstack([np.expm1(np.asarray(self.basal[lb], dtype=np.float64)) for lb in labels]).astype(np.float32)
        fam_of = [str(self.contexts[t.name]) for t in tabs]
        fams = sorted(set(fam_of))
        frac = {f: np.zeros(A) for f in fams}
        for t, f in zip(tabs, fam_of):
            frac[f] = np.maximum(frac[f], np.isfinite(t.raw).mean(axis=0))
        n_fam = np.sum([frac[f] >= 0.5 for f in fams], axis=0)
        genes_axis = np.flatnonzero(n_fam >= min(2, len(fams))).astype(np.int64)
        tnames = sorted(set(genes) | {str(x) for t in tabs for x in t.targets})
        tindex = {t: i for i, t in enumerate(tnames)}
        col = {g: i for i, g in enumerate(genes)}
        t_axis = np.array([col.get(t, -1) for t in tnames], dtype=np.int64)
        gpos = np.full(A, -1, dtype=np.int64)
        gpos[genes_axis] = np.arange(genes_axis.size)
        t_gene = np.where(t_axis >= 0, gpos[np.clip(t_axis, 0, None)], -1)
        src_cpm = np.vstack([cpm[labels.index(f)] for f in fams if f in labels]) if any(f in labels for f in fams) \
            else cpm
        targets = pd.concat([pd.DataFrame({"target": tnames, "axis_index": t_axis, "gene_index": t_gene,
                                           "in_panel": False, "essential": False, "chrom": "", "tss": np.nan}),
                             P.basal_priors(src_cpm, t_axis)], axis=1)
        raw, se, sh, rc, rt, nc, own, starts = [], [], [], [], [], [], [], []
        pos = 0
        for i, t in enumerate(tabs):
            s = np.asarray(t.se, dtype=np.float32).copy()
            r = np.asarray(t.raw, dtype=np.float32)
            missing = np.isfinite(r) & ~(np.isfinite(s) & (s > 0))
            if missing.any():            # a stage-98 mixture (cd4_mix) keeps no SE: its median SE stands in
                good = s[np.isfinite(s) & (s > 0)]
                s[missing] = float(np.median(good)) if good.size else 0.3
                self.log(f"{t.name}: {int(missing.sum())} measured values without SE set to {s[missing][0]:.3g}")
            ti = np.array([tindex[str(x)] for x in t.targets], dtype=np.int64)
            raw.append(P.f16_effect(r[:, genes_axis]))
            se.append(P.f16_se(s[:, genes_axis]))
            sh.append(P.f16_effect(np.asarray(t.shrunk, dtype=np.float32)[:, genes_axis]))
            rc.append(np.full(ti.size, i, dtype=np.int64))
            rt.append(ti)
            nc.append(np.asarray(t.n_cells, dtype=np.float64))
            ow = np.full((ti.size, 2), np.nan)
            ax = t_axis[ti]
            ok = np.flatnonzero(ax >= 0)
            ow[ok, 0] = r[ok, ax[ok]]
            ow[ok, 1] = s[ok, ax[ok]]
            own.append(ow)
            starts.append((pos, pos + ti.size))
            pos += ti.size
        contexts = pd.DataFrame({"context": [t.name for t in tabs], "family": fam_of, "group": [t.name for t in tabs],
                                 "se_factor": [float(self.se_factor.get(t.name, 1.0)) for t in tabs],
                                 "weight": 1.0, "modality": "crispri",
                                 "basal_row": [labels.index(f) for f in fam_of],
                                 "row_start": [a for a, _ in starts], "row_stop": [b for _, b in starts]})
        gtab = pd.DataFrame({"gene": [genes[g] for g in genes_axis], "axis_index": genes_axis,
                             "n_families": n_fam[genes_axis]})
        empty = (np.zeros(len(tnames) + 1, dtype=np.int64), np.zeros(0, dtype=np.int64))
        arrays = {"raw": np.concatenate(raw), "se": np.concatenate(se), "shrunk": np.concatenate(sh)}
        rows = {"row_context": np.concatenate(rc), "row_target": np.concatenate(rt), "row_ncells": np.concatenate(nc),
                "row_own": np.concatenate(own)}
        self.pool = P.Pool(arrays, contexts, targets, gtab, genes, rows, cpm, labels, empty,
                           (empty[0], empty[1], np.zeros(0, dtype=np.float32)))
        args = train.build_parser().parse_args(["--steps", str(self.steps), "--seed", str(self.seed),
                                                "--device", self.device, "--val-family", "none", *self.flags])
        self.phase = P.Phase(self.pool, np.arange(self.pool.n_rows), P.PhaseOptions(
            tau2=args.tau2, min_frac=args.min_frac, min_families=args.min_families, gene_weight=args.gene_weight,
            max_partners=args.max_partners), self.device, self.log)
        ncfg = train.net_config(args, self.pool, self.phase)
        self.model, self.history, _, self.cal = train.fit(self.phase, ncfg, train.train_config(args), steps=self.steps,
                                                          val=None, log=self.log)
        self.fit_context = context
        return self

    def _predict(self, targets, context: str, feat: str) -> np.ndarray:
        pool, phase = self.pool, self.phase
        out = np.full((len(targets), len(self.genes)), np.nan, dtype=np.float32)
        idx = np.array([pool.target_index.get(str(t), -1) for t in targets], dtype=np.int64)
        ok = np.flatnonzero(idx >= 0)
        if ok.size == 0:
            return out
        if context not in pool.basal_index:
            raise ValueError(f"no basal vector for {context!r}")
        fam = pool.family_names.index(context) if context in pool.family_names else -1
        phase.opts.q_own_family = fam >= 0          # a label that trained is regime T for its own partners
        spec = P.RowSpec(np.full(ok.size, pool.basal_index[context], dtype=np.int64),
                         np.full(ok.size, fam, dtype=np.int64), idx[ok])
        pred, _, _ = train.predict(phase, self.model, spec, feat=feat)
        out[ok] = train.full_axis(pool, pred)
        return out

    def predict(self, targets, context: str) -> np.ndarray:
        return self._predict(targets, context, "true")

    def predict_blind(self, targets, context: str) -> np.ndarray:
        """Every context given the training-average control profile: the control stage 105 does not have yet."""
        return self._predict(targets, context, "blind")
