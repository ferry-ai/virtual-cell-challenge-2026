"""Six-metric bench machinery shared by the single-cell benches (stages 73 and 75).

A bench is a val-shaped scoring problem built from real perturbed cells:

* truth = half A of each target's cells + a control pool (`control_source: real`);
* point 0 = the official generic baseline (cell_eval2's own profile and dispersed
  emission) on that truth;
* point 1 = half B of each target's cells, scored as a prediction;
* arms = generated predictions.

All DE tables come from `de_tools.fast_scorer_de`, which reproduces the scorer's
CPU DE (same rows, same significance calls on the validation fixture) at a
fraction of the cost, and are handed to `cell_eval2.compute_metrics`, which
computes everything else itself under the competition configuration. The local
scale ``(u - b) / (r - b)`` is ours: it compares arms, it is not a VCC score.
"""

from __future__ import annotations

import json
import time
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import scipy.sparse as sp

from .de_tools import ReferencePool, fast_scorer_de, scorer_config

__all__ = ["SCORED", "SHORT", "Bench", "load_effects", "log"]

SCORED = {
    "pds_cosine": "higher",
    "expr_mse_unbiased_capped_norm": "lower",
    "de_wilcoxon_lfc_nmae": "lower",
    "de_wilcoxon_direction_fidelity_yield_raw": "higher",
    "de_wilcoxon_direction_reach_raw": "higher",
    "de_wilcoxon_sig_jaccard": "higher",
}
SHORT = {"pds_cosine": "PDS", "expr_mse_unbiased_capped_norm": "MSE", "de_wilcoxon_lfc_nmae": "NMAE",
         "de_wilcoxon_direction_fidelity_yield_raw": "FID", "de_wilcoxon_direction_reach_raw": "REACH",
         "de_wilcoxon_sig_jaccard": "JAC"}
CONTROL = "non-targeting"


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}", flush=True)


def load_effects(specs, genes) -> dict:
    """``NAME=PATH`` npz files (targets, genes, lfc in ln units) -> {NAME: {target: vector on genes}}.

    How effects computed elsewhere (stage 100, or the archived stage 92) enter a bench: the same
    generator, the same scorer and the same targets as every other arm. Genes the file lacks get 0.
    """
    out = {}
    for spec in specs or []:
        name, _, path = spec.partition("=")
        if "_a" in name or "+" in name or ":" in name:
            raise SystemExit(f"effects name {name!r} must not contain '_a', '+' or ':'")
        z = np.load(path)
        pos = pd.Index(z["genes"].astype(str)).get_indexer(np.asarray(genes).astype(str))
        rows = {}
        for i, t in enumerate(z["targets"].astype(str)):
            v = np.zeros(len(genes))
            v[pos >= 0] = z["lfc"][i, pos[pos >= 0]]
            rows[t] = v
        out[name] = rows
    return out


def to_anndata(x, labels, genes):
    import anndata as ad

    cfg = scorer_config()
    obs = pd.DataFrame({cfg.pert_col: pd.Categorical(np.asarray(labels).astype(str))},
                       index=pd.Index([f"c{i}" for i in range(x.shape[0])]))
    return ad.AnnData(X=sp.csr_matrix(x, dtype=np.float32), obs=obs,
                      var=pd.DataFrame(index=pd.Index(np.asarray(genes).astype(str))))


def aggregate(per_pert) -> dict:
    import cell_eval2

    agg = cell_eval2.aggregate_metrics(per_pert)
    out = {str(r[0]): (None if r[1] is None else float(r[1])) for r in agg.iter_rows()}
    return {m: out.get(m) for m in SCORED}


def direction_components(de_pred, de_real, cfg) -> pd.DataFrame:
    """Per-target ``n_conf``, ``n_pred`` and ``k`` of the direction metrics, from the scorer itself.

    ``fidelity_yield_raw = k / max(n_pred, n_conf)`` per target, so the per-target metric alone
    cannot tell precision (``k / n_pred``) from call volume. This rebuilds the PreparedDE the way
    `cell_eval2.run._prepare_de_cached` does (without its cache) and reads
    `metrics.direction._components`. That is private API of cell_eval2 0.16.0: a change there
    breaks this diagnostic, never the metrics, and the test pins it against the scored fidelity.
    """
    from cell_eval2.de import assemble_prepared_de, prep_de_side, rank_de_side, resolve_target_genes
    from cell_eval2.metrics.direction import _components

    d = cfg.de
    sides = {}
    for name, table in (("real", de_real), ("pred", de_pred)):
        df, perts = prep_de_side(table, name=name, sort_by=d.sort_by, nan_lfc_policy=d.nan_lfc_policy,
                                 min_abs_log2fc=d.min_abs_log2fc)
        sides[name] = (rank_de_side(df, sort_by=d.sort_by, p_adj_threshold=d.p_adj_threshold), perts, df)
    (r_rank, r_perts, r_df), (p_rank, p_perts, p_df) = sides["real"], sides["pred"]
    resolution = resolve_target_genes(r_df, r_perts, target_gene_map=cfg.target_gene_map)
    prepared = assemble_prepared_de(r_rank, r_perts, p_rank, p_perts, control=cfg.control, sort_by=d.sort_by,
                                    p_adj_threshold=d.p_adj_threshold, real_df=r_df, pred_df=p_df,
                                    target_resolution=resolution)
    comp = _components(prepared).select("target", "n_conf", "n_pred", "k")
    return pd.DataFrame(comp.to_dict(as_series=False))


def summarize_components(comp: pd.DataFrame) -> dict:
    n_pred, n_conf, k = (comp[c].to_numpy(dtype=float) for c in ("n_pred", "n_conf", "k"))
    return {"n_pred_median": float(np.median(n_pred)), "n_pred_mean": float(n_pred.mean()),
            "n_conf_median": float(np.median(n_conf)),
            "precision_pooled": float(k.sum() / n_pred.sum()) if n_pred.sum() else None,
            # the regime where fidelity IS precision; targets with no confident gene say nothing
            "frac_targets_n_pred_ge_n_conf": float(np.mean(n_pred[n_conf > 0] >= n_conf[n_conf > 0]))
            if np.any(n_conf > 0) else None}


def scale(raw: dict, b: dict, r: dict) -> dict:
    out = {}
    for m in SCORED:
        u, lo, hi = raw.get(m), b.get(m), r.get(m)
        if None in (u, lo, hi) or hi == lo:
            out[m] = None
            continue
        s = (u - lo) / (hi - lo)
        if m == "expr_mse_unbiased_capped_norm":
            s = min(max(s, 0.0), 1.0)
        out[m] = s
    vals = [v for v in out.values() if v is not None]
    out["avg"] = float(np.mean(vals)) if len(vals) == len(SCORED) else None
    return out


class Bench:
    def __init__(self, x: sp.csr_matrix, target_rows: dict[str, np.ndarray], ctrl_rows: np.ndarray,
                 genes: np.ndarray, out: Path, *, seed: int = 2026, backend: str = "scanpy") -> None:
        import cell_eval2  # noqa: F401  (fail early if the scorer is missing)

        self.out = Path(out)
        self.out.mkdir(parents=True, exist_ok=True)
        self.genes = np.asarray(genes).astype(str)
        self.rng = np.random.default_rng(seed)
        self.seed = seed
        cfg = scorer_config()
        self.cfg = replace(cfg, de=replace(cfg.de, backend=backend))
        self.targets = sorted(target_rows)
        self.half_a, self.half_b = {}, {}
        for t in self.targets:
            rows = self.rng.permutation(target_rows[t])
            h = rows.size // 2
            self.half_a[t], self.half_b[t] = rows[:h], rows[h:2 * h]
        self.x = x
        self.ctrl = x[ctrl_rows]
        a_rows = np.concatenate([self.half_a[t] for t in self.targets])
        a_labels = np.concatenate([np.full(self.half_a[t].size, t) for t in self.targets])
        self.real_ad = to_anndata(sp.vstack([x[a_rows], self.ctrl]).tocsr(),
                                  np.concatenate([a_labels, np.full(self.ctrl.shape[0], CONTROL)]), self.genes)
        log(f"bench: {len(self.targets)} targets, median half {np.median([v.size for v in self.half_a.values()]):.0f} "
            f"cells, control pool {self.ctrl.shape[0]}, genes {self.genes.size}")
        self.pool = ReferencePool(self.ctrl, self.genes)
        self.de_real = fast_scorer_de(x[a_rows], a_labels, self.pool)
        self.results: dict[str, dict] = {}

    def n_pred(self, t: str) -> int:
        return int(self.half_a[t].size)

    def score(self, name: str, pred_x: sp.csr_matrix, pred_labels: np.ndarray, extra: dict | None = None) -> dict:
        import cell_eval2

        ta = time.time()
        pred_ad = to_anndata(sp.vstack([pred_x, self.ctrl]).tocsr(),
                             np.concatenate([pred_labels, np.full(self.ctrl.shape[0], CONTROL)]), self.genes)
        de_pred = fast_scorer_de(pred_x, pred_labels, self.pool)
        per = cell_eval2.compute_metrics(pred_ad, self.real_ad, config=self.cfg,
                                         de_real=self.de_real, de_pred=de_pred)
        raw = aggregate(per)
        sig = de_pred.filter(de_pred["p_adj"] < 0.05)
        n_sig = sig.height / max(len(set(np.asarray(pred_labels).astype(str))), 1)
        res = {"raw": raw, "n_sig_per_target": n_sig, "seconds": time.time() - ta} | (extra or {})
        self._components(name, res, de_pred, self.cfg)
        self.results[name] = res
        pd.DataFrame({c: per[c].to_numpy() for c in per.columns}).to_csv(self.out / f"per_pert_{name}.csv", index=False)
        log(f"{name}: " + " ".join(f"{SHORT[m]}={raw[m]:.4f}" if raw[m] is not None else f"{SHORT[m]}=NA"
                                   for m in SCORED) + f" sig/t={n_sig:.1f} ({time.time() - ta:.0f}s)")
        return res

    def anchors(self) -> None:
        import cell_eval2
        from cell_eval2.baseline import (_lock_from_adata, _prediction_from_adata, baseline_config,
                                         generic_response_profile)

        b_rows = np.concatenate([self.half_b[t] for t in self.targets])
        b_labels = np.concatenate([np.full(self.half_b[t].size, t) for t in self.targets])
        self.score("replicate", self.x[b_rows], b_labels)
        ta = time.time()
        cfg = self.cfg
        prof = generic_response_profile(self.real_ad, pert_col=cfg.pert_col, control=cfg.control)
        base_pred = _prediction_from_adata(self.real_ad, prof, pert_col=cfg.pert_col, control=cfg.control,
                                           emit="dispersed", seed=self.seed)
        base_cfg = baseline_config(_lock_from_adata(self.real_ad, base_pred, cfg, de_real=self.de_real))
        lab = base_pred.obs[cfg.pert_col].astype(str).to_numpy()
        nc = lab != CONTROL
        de_base = fast_scorer_de(base_pred.X[nc], lab[nc], self.pool)
        per = cell_eval2.compute_metrics(base_pred, self.real_ad, config=base_cfg,
                                         de_real=self.de_real, de_pred=de_base)
        raw = aggregate(per)
        sig = de_base.filter(de_base["p_adj"] < 0.05)
        self.results["baseline"] = {"raw": raw, "n_sig_per_target": sig.height / max(len(self.targets), 1),
                                    "seconds": time.time() - ta}
        self._components("baseline", self.results["baseline"], de_base, base_cfg)
        log("baseline: " + " ".join(f"{SHORT[m]}={v:.4f}" for m, v in raw.items() if v is not None))

    def _components(self, name: str, res: dict, de_pred, cfg) -> None:
        """Write ``components_<arm>.csv`` and a summary into ``res``; a failure is logged, not raised."""
        try:
            comp = direction_components(de_pred, self.de_real, cfg)
        except Exception as exc:  # a diagnostic must not cost the bench its metrics
            log(f"{name}: direction components NOT written ({type(exc).__name__}: {exc})")
            return
        comp.to_csv(self.out / f"components_{name}.csv", index=False)  # named like per_pert_<arm>.csv
        res["components"] = summarize_components(comp)

    def real_n_conf(self) -> dict:
        sig = self.de_real.filter(self.de_real["p_adj"] < 0.05)
        per_t = sig.group_by("target").len()
        vals = np.array(per_t["len"].to_list())
        return {"median": float(np.median(vals)) if vals.size else 0.0,
                "q10_q90": [float(np.quantile(vals, 0.1)), float(np.quantile(vals, 0.9))] if vals.size else None,
                "n_targets_with_calls": int(vals.size)}

    def finish(self, payload: dict) -> pd.DataFrame:
        b = self.results["baseline"]["raw"]
        r = self.results["replicate"]["raw"]
        for res in self.results.values():
            res["scaled_local"] = scale(res["raw"], b, r)
        table = pd.DataFrame({name: {SHORT.get(k, k): v for k, v in res["scaled_local"].items()}
                              for name, res in self.results.items()}).T
        table["sig/t"] = [self.results[n]["n_sig_per_target"] for n in table.index]
        table.to_csv(self.out / "scaled_local.csv")
        log("\n" + table.round(3).to_string())
        payload = payload | {
            "finished_utc": datetime.now(timezone.utc).isoformat(),
            "not_a_vcc_score": "local anchors on a half-depth truth; compare arms, not leaderboards",
            "n_targets": len(self.targets),
            "control_pool": int(self.ctrl.shape[0]),
            "real_n_conf": self.real_n_conf(),
            "backend_note": "DE from vcc2026.de_tools.fast_scorer_de (validated against the scanpy path)",
            "results": self.results,
        }
        (self.out / "bench.json").write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")
        return table
