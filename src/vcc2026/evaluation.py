"""Two levels of evaluation, kept apart on purpose.

**Level 1, delta-space proxies** (`delta_metrics`). Cheap, computable today from
pseudobulk alone, and useful for choosing between transfer rules. They are *not*
the competition score and must never be reported as one.

**Level 2, the real scorer** (`score_bundle`). Runs the installed `cell-eval2`
on single-cell count h5ads. This is the only thing entitled to be called a VCC
metric.

The gap between them is the project's open bottleneck, and it is worth being
precise about why. The official config is `input_type: counts`,
`control_source: real` (`reports/scorer/vcc2026_contract.json`): the scorer
compares predicted cells against the *real* control cells and its unbiased MSE
correction depends on the dispersion between predicted cells. Pseudobulk has
already averaged that dispersion away, so it cannot produce a VCC score no
matter how it is reshaped.

A further distinction that the score formula makes unavoidable. `score_metrics`
rescales each raw metric as `(u - b) / (r - b)`, with `b` a published baseline
and `r` a split-half replicate. **We do not have `b` or `r`.** So this module
returns raw aggregate metrics by default and marks `normalized: false`. A raw
metric is comparable between two of our own runs; it is not comparable with a
leaderboard number, and `score_bundle` refuses to imply otherwise.
"""

from __future__ import annotations

from dataclasses import dataclass
from importlib.metadata import version
from pathlib import Path

import numpy as np

__all__ = [
    "VCC_SCORED_METRICS",
    "load_eval_config",
    "delta_metrics",
    "score_bundle",
    "scorer_fingerprint",
]

VCC_SCORED_METRICS = (
    "pds_cosine",
    "expr_mse_unbiased_capped_norm",
    "de_wilcoxon_lfc_nmae",
    "de_wilcoxon_direction_fidelity_yield_raw",
    "de_wilcoxon_direction_reach_raw",
    "de_wilcoxon_sig_jaccard",
)


def load_eval_config(profile: str = "vcc2026"):
    """The official scorer configuration, taken from the installed package.

    Read from the package's own shipped YAML rather than reconstructed here, so
    that a change in the competition profile shows up as a changed config rather
    than as a silent disagreement between our copy and theirs.
    """
    from cell_eval2.config import EvalConfig

    if hasattr(EvalConfig, "from_preset"):
        try:
            return EvalConfig.from_preset(profile)
        except Exception:
            pass
    import cell_eval2

    path = Path(cell_eval2.__file__).parent / "configs" / f"{profile}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"no scorer profile {profile!r} at {path}")
    return EvalConfig.from_yaml(str(path))


def scorer_fingerprint() -> dict:
    """Record exactly which scorer produced a number.

    D-008 fixes the evaluation on cell-eval2 0.16.0 because the per-metric
    clamps are properties of the installed version, and the strategy rests on
    them. A run that silently changed version would make two of our own numbers
    incomparable, so the version travels with every result.
    """
    out = {"expected_cell_eval2": "0.16.0"}
    try:
        out["cell_eval2"] = version("cell-eval2")
    except Exception as exc:  # package not installed in this environment
        out["cell_eval2"] = None
        out["error"] = f"{type(exc).__name__}: {exc}"
    try:
        out["vcc_cli"] = version("vcc-cli")
    except Exception:
        out["vcc_cli"] = None
    out["matches_decision_D008"] = out.get("cell_eval2") == "0.16.0"

    # The DE backend is NOT fixed by the package version, and the package itself
    # warns that "DE numbers differ between engines". Two runs of the same
    # version on different machines can therefore disagree on four of the six
    # scored metrics, so the resolved backend belongs in the fingerprint.
    backends = {}
    for name in ("pdex", "gpudge"):
        try:
            backends[name] = version(name)
        except Exception:
            backends[name] = None
    try:
        import torch  # noqa: PLC0415

        backends["cuda_available"] = bool(torch.cuda.is_available())
    except Exception:
        backends["cuda_available"] = False
    resolved = (
        "gpudge" if backends.get("gpudge") and backends["cuda_available"]
        else "pdex" if backends.get("pdex")
        else "scanpy"
    )
    out["de_backends_available"] = backends
    out["de_backend_resolved"] = resolved
    out["de_backend_note"] = (
        "de.backend='auto' picks gpudge (CUDA) > pdex > scanpy. The engines do "
        "not agree exactly, so a DE-based metric is only comparable across runs "
        "that resolved the same backend. Record it beside every number."
    )
    return out


@dataclass(frozen=True)
class DeltaMetrics:
    """Proxy agreement between a predicted and an observed response vector."""

    n_genes: int
    pearson: float
    spearman: float
    cosine: float
    mse: float
    sign_agreement: float
    sign_agreement_strong: float
    n_strong: int

    def as_dict(self) -> dict:
        return {
            "n_genes": self.n_genes,
            "pearson": self.pearson,
            "spearman": self.spearman,
            "cosine": self.cosine,
            "mse": self.mse,
            "sign_agreement": self.sign_agreement,
            "sign_agreement_strong": self.sign_agreement_strong,
            "n_strong": self.n_strong,
        }


def delta_metrics(
    predicted: np.ndarray,
    observed_truth: np.ndarray,
    mask: np.ndarray,
    *,
    strong_threshold: float = 0.5,
) -> DeltaMetrics:
    """Compare two response vectors on the genes both actually measured.

    Args:
        predicted: (n_genes,) predicted log2 fold change.
        observed_truth: (n_genes,) measured log2 fold change.
        mask: (n_genes,) bool, True where BOTH sides measured the gene. Genes
            outside the mask are excluded, not zero-filled -- zero-filling both
            sides would inflate every correlation toward agreement on a shared
            absence of evidence.
        strong_threshold: |truth| above which a gene counts as a confident
            non-null, used for `sign_agreement_strong`. Sign agreement over all
            genes is dominated by genes whose true effect is indistinguishable
            from zero, where a coin flip scores 0.5.

    Returns:
        DeltaMetrics; degenerate inputs give NaN rather than a fabricated 0.
    """
    predicted = np.asarray(predicted, dtype=np.float64)
    observed_truth = np.asarray(observed_truth, dtype=np.float64)
    mask = np.asarray(mask, dtype=bool)
    if not (predicted.shape == observed_truth.shape == mask.shape):
        raise ValueError(
            f"shape mismatch: {predicted.shape} / {observed_truth.shape} / {mask.shape}"
        )

    good = mask & np.isfinite(predicted) & np.isfinite(observed_truth)
    p, t = predicted[good], observed_truth[good]
    n = int(good.sum())
    nan = float("nan")
    if n == 0:
        return DeltaMetrics(0, nan, nan, nan, nan, nan, nan, 0)

    def _pearson(a, b):
        # A correlation needs at least three points to mean anything; below
        # that it is either undefined or identically +-1 by construction. The
        # error metrics below are well defined for a single gene, so they are
        # computed regardless rather than discarded with it.
        if a.size < 3:
            return nan
        if a.std() == 0 or b.std() == 0:
            return nan
        return float(np.corrcoef(a, b)[0, 1])

    def _rank(x):
        order = np.argsort(np.argsort(x))
        return order.astype(np.float64)

    denom = float(np.linalg.norm(p) * np.linalg.norm(t))
    cosine = float(p @ t / denom) if denom > 0 else nan

    nz = t != 0
    sign_all = float(np.mean(np.sign(p[nz]) == np.sign(t[nz]))) if nz.any() else nan
    strong = np.abs(t) >= strong_threshold
    sign_strong = (
        float(np.mean(np.sign(p[strong]) == np.sign(t[strong]))) if strong.any() else nan
    )

    return DeltaMetrics(
        n_genes=n,
        pearson=_pearson(p, t),
        spearman=_pearson(_rank(p), _rank(t)),
        cosine=cosine,
        mse=float(np.mean(np.square(p - t))),
        sign_agreement=sign_all,
        sign_agreement_strong=sign_strong,
        n_strong=int(strong.sum()),
    )


def score_bundle(
    pred_h5ad: Path | str,
    real_h5ad: Path | str,
    *,
    profile: str = "vcc2026",
    baseline_metrics=None,
    outdir: Path | str | None = None,
    **overrides,
) -> dict:
    """Run the installed cell-eval2 on a prediction/ground-truth pair.

    Args:
        pred_h5ad: predicted single-cell counts.
        real_h5ad: ground-truth single-cell counts, including real controls.
        profile: metric profile; "vcc2026" is the competition set.
        baseline_metrics: a baseline result frame. Supply it to obtain
            normalized `(u - b) / (r - b)` scores. Without it only raw
            aggregates are returned and `normalized` is False.
        outdir: optional directory for the scorer's own artifacts.
        **overrides: forwarded to `compute_metrics` to override config fields.

    Returns:
        A JSON-safe dict with the scorer fingerprint, raw per-metric aggregates,
        and -- only when a baseline was supplied -- normalized scores.
    """
    import cell_eval2

    pred_h5ad, real_h5ad = Path(pred_h5ad), Path(real_h5ad)
    for p in (pred_h5ad, real_h5ad):
        if not p.exists():
            raise FileNotFoundError(p)

    config = load_eval_config(profile)
    kwargs = dict(overrides)
    if outdir is not None:
        kwargs["outdir"] = str(outdir)

    per_pert = cell_eval2.compute_metrics(
        str(pred_h5ad), str(real_h5ad), config=config, **kwargs
    )

    # Aggregation can legitimately fail. `expr_mse_unbiased_capped_norm` is a
    # ratio of sums, and cell-eval2 raises when the denominator is non-positive
    # -- which is what a reference with no real effect produces. That is a
    # property of the reference, not a bug, and losing the per-perturbation
    # numbers to an exception would discard the measurement that proves it.
    aggregate: dict = {}
    aggregate_error = None
    try:
        agg = cell_eval2.aggregate_metrics(per_pert)
        aggregate = {
            str(r[0]): (None if r[1] is None else float(r[1]))
            for r in agg.iter_rows()
        }
    except Exception as exc:
        aggregate_error = f"{type(exc).__name__}: {exc}"

    by_metric: dict[str, dict] = {}
    try:
        for metric, group in per_pert.group_by("metric"):
            name = str(metric[0] if isinstance(metric, tuple) else metric)
            vals = np.array(
                [v for v in group["value"].to_list() if v is not None],
                dtype=np.float64,
            )
            vals = vals[np.isfinite(vals)]
            by_metric[name] = {
                "n_perturbations": int(group.height),
                "n_finite": int(vals.size),
                "mean": float(vals.mean()) if vals.size else None,
                "median": float(np.median(vals)) if vals.size else None,
                "min": float(vals.min()) if vals.size else None,
                "max": float(vals.max()) if vals.size else None,
            }
    except Exception as exc:
        by_metric = {"_error": f"{type(exc).__name__}: {exc}"}

    result = {
        "scorer": scorer_fingerprint(),
        "profile": profile,
        "pred": str(pred_h5ad),
        "real": str(real_h5ad),
        "normalized": False,
        "raw_aggregate": aggregate,
        "aggregate_error": aggregate_error,
        "per_metric_over_perturbations": by_metric,
        "note": (
            "Raw aggregate metrics. Competition scores rescale each metric as "
            "(u - b) / (r - b) using a published baseline and a split-half "
            "replicate anchor, neither of which is available to this project. "
            "These numbers compare our own runs with each other and nothing else."
        ),
    }

    if baseline_metrics is not None:
        scored = cell_eval2.score_metrics(per_pert, baseline_metrics)
        result["normalized"] = True
        result["scores"] = {
            str(r[0]): (None if r[1] is None else float(r[1]))
            for r in scored.iter_rows()
        }
        result["note"] = "Normalized against the supplied baseline frame."

    missing = [
        m for m in VCC_SCORED_METRICS
        if m not in result["raw_aggregate"] and m not in by_metric
    ]
    result["missing_scored_metrics"] = missing
    result["all_six_present"] = not missing
    result["all_six_aggregated"] = all(
        m in result["raw_aggregate"] for m in VCC_SCORED_METRICS
    )
    return result
