"""Proxy evaluation, paired target differences, and resource accounting.

Numbers produced here live in pseudobulk log2FC space. They are not VCC
scores. Coverage is reported beside quality: a model that declines to predict
is scored as the null, with coverage 0.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from vcc2026.evaluation import delta_metrics
from vcc2026.resources import peak_rss_bytes, snapshot
from vcc2026.splits import bootstrap_targets

__all__ = [
    "PhaseClock",
    "aggregate_targets",
    "paired_difference",
    "paired_pooled_difference",
    "score_matrix",
    "write_comparison_table",
]


@dataclass
class PhaseClock:
    """Wall time and peak RSS for one named phase."""

    name: str
    t0: float = field(default_factory=time.perf_counter)
    rss0: int | None = field(default_factory=peak_rss_bytes)

    def stop(self) -> dict:
        rss1 = peak_rss_bytes()
        return {
            "phase": self.name,
            "seconds": float(time.perf_counter() - self.t0),
            "rss_bytes_at_start": self.rss0,
            "peak_rss_bytes_after": rss1,
            "rss_delta_bytes": (
                None if self.rss0 is None or rss1 is None else int(rss1 - self.rss0)
            ),
            "vram_bytes": None,
            "vram_note": "no CUDA device in this environment; VRAM not measured",
        }


def score_matrix(
    pred: np.ndarray,
    truth: np.ndarray,
    *,
    targets: list[str],
    strong_threshold: float,
) -> dict:
    """Per-target proxy metrics on an already-masked common universe."""
    if pred.shape != truth.shape:
        raise ValueError(f"shape mismatch {pred.shape} vs {truth.shape}")
    if pred.shape[0] != len(targets):
        raise ValueError("one row per target is required")
    n_genes = pred.shape[1]
    mask = np.ones(n_genes, dtype=bool)
    per = []
    sq_err = np.square(pred - truth)
    sq_null = np.square(truth)
    for i, t in enumerate(targets):
        m = delta_metrics(pred[i], truth[i], mask, strong_threshold=strong_threshold)
        d = m.as_dict()
        d["target"] = t
        sse = float(sq_err[i].sum())
        sst = float(sq_null[i].sum())
        d["sse"] = sse
        d["sst"] = sst
        d["mse_vs_null"] = (sse / sst) if sst > 0 else None
        per.append(d)
    pooled_mse = float(sq_err.mean())
    pooled_null = float(sq_null.mean())
    out = {
        "n_targets": len(targets),
        "n_genes": n_genes,
        "pooled_mse": pooled_mse,
        "pooled_mse_null": pooled_null,
        "pooled_mse_vs_null": (
            pooled_mse / pooled_null if pooled_null > 0 else None
        ),
        "metric_space": "pseudobulk_log2FC_proxy",
        "not_a_vcc_score": True,
        "per_target": per,
    }
    for key in ("pearson", "spearman", "cosine", "mse",
                "sign_agreement", "sign_agreement_strong", "mse_vs_null"):
        vals = np.array([p[key] for p in per if p.get(key) is not None], dtype=np.float64)
        vals = vals[np.isfinite(vals)]
        out[f"{key}_median"] = float(np.median(vals)) if vals.size else None
        out[f"{key}_mean"] = float(np.mean(vals)) if vals.size else None
    return out


def _pooled_ratio(sse: np.ndarray, sst: np.ndarray) -> float:
    total_sst = float(np.sum(sst))
    if not np.isfinite(total_sst) or total_sst <= 0:
        return float("nan")
    return float(np.sum(sse) / total_sst)


def aggregate_targets(result: dict, *, n_boot: int, seed: int) -> dict:
    """Bootstrap over targets of the already-computed per-target rows.

    Two aggregations, kept distinct because they are not the same number:

    * ``bootstrap_over_targets.mse_vs_null`` -- mean of per-target ratios.
    * ``pooled`` -- the primary metric, ``sum sse / sum sst``, recomputed on
      each resample of the same targets. That is the interval of
      ``pooled_mse_vs_null``, not an interval of the mean of ratios.
    """
    per = result["per_target"]
    keys = ("pearson", "mse", "mse_vs_null", "cosine", "sign_agreement_strong")
    boot = {}
    for key in keys:
        vals = np.array([p[key] for p in per], dtype=np.float64)
        finite = np.isfinite(vals)
        v = vals[finite]
        if v.size < 5:
            boot[key] = {
                "n": int(v.size),
                "skipped": "too few finite targets",
                "aggregation": "mean_of_per_target_values",
            }
            continue
        draws = bootstrap_targets(range(v.size), n_boot=n_boot, seed=seed)
        means = np.array([v[d].mean() for d in draws])
        boot[key] = {
            "n": int(v.size),
            "mean": float(v.mean()),
            "median": float(np.median(v)),
            "ci95": [float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))],
            "aggregation": "mean_of_per_target_values",
        }
    sse = np.array([p.get("sse") for p in per], dtype=np.float64)
    sst = np.array([p.get("sst") for p in per], dtype=np.float64)
    finite = np.isfinite(sse) & np.isfinite(sst) & (sst > 0)
    sse_f, sst_f = sse[finite], sst[finite]
    point = result.get("pooled_mse_vs_null")
    if sse_f.size >= 5:
        draws = bootstrap_targets(range(sse_f.size), n_boot=n_boot, seed=seed)
        ratios = np.array([_pooled_ratio(sse_f[d], sst_f[d]) for d in draws])
        pooled = {
            "pooled_mse_vs_null": point,
            "ci95": [float(np.percentile(ratios, 2.5)), float(np.percentile(ratios, 97.5))],
            "n": int(sse_f.size),
            "n_boot": n_boot,
            "unit": "target",
            "aggregation": "ratio_of_pooled_sums",
            "not_the_same_as": (
                "bootstrap_over_targets.mse_vs_null, which is the mean of "
                "per-target MSE/null ratios"
            ),
        }
    else:
        pooled = {
            "pooled_mse_vs_null": point,
            "n": int(sse_f.size),
            "n_boot": n_boot,
            "unit": "target",
            "aggregation": "ratio_of_pooled_sums",
            "skipped": "too few finite targets",
        }
    return {"bootstrap_over_targets": boot, "pooled": pooled}


def _shared_per_target(per_a: list[dict], per_b: list[dict]) -> tuple[list[dict], list[dict]]:
    by_a = {p["target"]: p for p in per_a}
    by_b = {p["target"]: p for p in per_b}
    shared = sorted(set(by_a) & set(by_b))
    return [by_a[t] for t in shared], [by_b[t] for t in shared]


def paired_difference(
    per_a: list[dict], per_b: list[dict], *, key: str, n_boot: int, seed: int
) -> dict:
    """Mean of (a - b) on shared targets, bootstrap over targets.

    This is the mean of per-target values, not the primary metric. For the
    interval of ``pooled_mse_vs_null`` see ``paired_pooled_difference``.
    """
    by_a = {p["target"]: p for p in per_a}
    by_b = {p["target"]: p for p in per_b}
    shared = sorted(set(by_a) & set(by_b))
    diffs = []
    for t in shared:
        va, vb = by_a[t].get(key), by_b[t].get(key)
        if va is None or vb is None:
            continue
        if not (np.isfinite(va) and np.isfinite(vb)):
            continue
        diffs.append(float(va) - float(vb))
    diffs = np.array(diffs, dtype=np.float64)
    if diffs.size < 5:
        return {"n": int(diffs.size), "skipped": "too few paired targets", "key": key}
    draws = bootstrap_targets(range(diffs.size), n_boot=n_boot, seed=seed)
    means = np.array([diffs[d].mean() for d in draws])
    return {
        "key": key,
        "n": int(diffs.size),
        "mean_a_minus_b": float(diffs.mean()),
        "median_a_minus_b": float(np.median(diffs)),
        "ci95": [float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))],
        "ci95_excludes_zero": not (
            np.percentile(means, 2.5) <= 0.0 <= np.percentile(means, 97.5)
        ),
        "aggregation": "mean_of_per_target_differences",
        "not_the_same_as": "paired_pooled_difference (primary metric)",
    }


def paired_pooled_difference(
    per_a: list[dict], per_b: list[dict], *, n_boot: int, seed: int
) -> dict:
    """Paired bootstrap of the primary metric on the same resampled targets.

    Each replicate draws one set of targets (with replacement) and recomputes
    ``sum sse / sum sst`` for both models on that draw. The interval is of
    their difference, not of a difference of already-normalised ratios.

    Opposite signs versus ``paired_difference(..., key='mse_vs_null')`` are
    not a contradiction: one is a mean of ratios, the other is a ratio of
    sums, and a large-effect target dominates the second.
    """
    aligned_a, aligned_b = _shared_per_target(per_a, per_b)
    sse_a = np.array([p.get("sse") for p in aligned_a], dtype=np.float64)
    sst_a = np.array([p.get("sst") for p in aligned_a], dtype=np.float64)
    sse_b = np.array([p.get("sse") for p in aligned_b], dtype=np.float64)
    sst_b = np.array([p.get("sst") for p in aligned_b], dtype=np.float64)
    ok = (
        np.isfinite(sse_a) & np.isfinite(sst_a) & (sst_a > 0)
        & np.isfinite(sse_b) & np.isfinite(sst_b) & (sst_b > 0)
    )
    sse_a, sst_a, sse_b, sst_b = sse_a[ok], sst_a[ok], sse_b[ok], sst_b[ok]
    n = int(sse_a.size)
    if n < 5:
        return {
            "n": n,
            "skipped": "too few paired targets",
            "key": "pooled_mse_vs_null",
            "aggregation": "paired_pooled_ratio_difference",
        }
    point_a = _pooled_ratio(sse_a, sst_a)
    point_b = _pooled_ratio(sse_b, sst_b)
    point = float(point_a - point_b)
    draws = bootstrap_targets(range(n), n_boot=n_boot, seed=seed)
    diffs = np.array([
        _pooled_ratio(sse_a[d], sst_a[d]) - _pooled_ratio(sse_b[d], sst_b[d])
        for d in draws
    ])
    lo, hi = float(np.percentile(diffs, 2.5)), float(np.percentile(diffs, 97.5))
    return {
        "key": "pooled_mse_vs_null",
        "n": n,
        "point_a": float(point_a),
        "point_b": float(point_b),
        "mean_a_minus_b": point,
        "ci95": [lo, hi],
        "ci95_excludes_zero": not (lo <= 0.0 <= hi),
        "aggregation": "paired_pooled_ratio_difference",
        "not_the_same_as": (
            "paired_difference on mse_vs_null, which averages per-target ratios"
        ),
    }


def _fmt(value, digits=4):
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "sì" if value else "no"
    if isinstance(value, float):
        if not np.isfinite(value):
            return "—"
        return f"{value:.{digits}f}"
    return str(value)


def write_comparison_table(rows: list[dict], path: Path) -> Path:
    """Markdown + CSV from already-computed result rows. No model selection."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    cols = [
        ("model", "modello"),
        ("uses_context", "usa contesto"),
        ("protocol", "protocollo"),
        ("direction_id", "direzione"),
        ("seed", "seed"),
        ("pooled_mse_vs_null", "MSE/nullo"),
        ("pearson_median", "Pearson med."),
        ("coverage_targets", "copertura bersagli"),
        ("n_total_params", "parametri tot."),
        ("n_trainable_params", "parametri addestrabili"),
        ("train_seconds", "train s"),
        ("infer_seconds", "infer s"),
        ("peak_rss_bytes", "picco RSS"),
        ("artifact_bytes", "artefatto B"),
        ("calibration_label", "ampiezza"),
        ("context_identifiable", "contesto identificabile"),
        ("verdict_eligible", "eleggibile sul test"),
    ]
    lines = [
        "# Tabella comparativa del pilot modulare",
        "",
        "Generata dai JSON di risultato, non a mano. "
        "Metrica primaria: `pooled_mse_vs_null` (più basso è meglio), "
        "spazio pseudobulk log2FC, **non** un punteggio VCC. "
        "Nessuna variante è scelta sul test esterno: la colonna "
        "`eleggibile sul test` è sempre no.",
        "",
        "| " + " | ".join(h for _, h in cols) + " |",
        "| " + " | ".join("---" for _ in cols) + " |",
    ]
    csv = [",".join(k for k, _ in cols)]
    for row in rows:
        md = []
        csv_row = []
        for key, _ in cols:
            val = row.get(key)
            md.append(_fmt(val))
            csv_row.append("" if val is None else str(val))
        lines.append("| " + " | ".join(md) + " |")
        csv.append(",".join(csv_row))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    path.with_suffix(".csv").write_text("\n".join(csv) + "\n", encoding="utf-8")
    return path


def machine_snapshot() -> dict:
    snap = snapshot()
    d = snap.as_dict()
    d["peak_rss_bytes_now"] = peak_rss_bytes()
    return d
