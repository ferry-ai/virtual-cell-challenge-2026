"""Context-conditioned modulation of a transferred response.

What this module is, and what it deliberately is not.

The competition gives three destination contexts and not one perturbation in
any of them. Nothing at the *context* level can therefore be learned: three
points do not train an encoder, and no gradient can reach one. What can be
learned, from the thousands of (target x gene) pairs of a source -> destination
development experiment, is how a response's **transferability** depends on
properties of the destination that are measurable without perturbing it --
which is exactly what its 18,400 unperturbed cells provide.

So the object here is not a learned embedding of a context. It is the global
amplitude of `ShrunkTransfer` generalised from one scalar to a combination of
components, fitted the same way and selected on the same held-out targets:

    ShrunkTransfer     delta_hat = alpha * s
    ComponentTransfer  delta_hat = sum_k theta_k * C_k

where each component `C_k` is an (n_genes,) vector for that target. With the
single component `source` the two models coincide and `theta_0` is `alpha`, so
the generalisation is **nested inside the incumbent** and can be tested against
it rather than asserted over it. `fit_components` refuses to report a fit whose
normal matrix is singular, because a component nobody can identify is not a
component -- it is a way to overfit quietly.

The fit stays a small linear solve because the prediction is linear in `theta`,
the same property that let stage 44 close its amplitude grid in three dot
products.

Two components matter beyond the incumbent:

* `common` and `specific` split the source response into the part shared by
  every target and the part that distinguishes them. They exist because the
  competition's zero is the mean perturbed profile, not the control profile, so
  one amplitude for both compresses the two against different origins.
* `expression` scales the response by how strongly the destination expresses
  each gene, which is the cheapest thing a context can say about itself.

**Nothing here is measured.** This is machinery. Whether any component earns
its coefficient is decided on held-out targets against a real evaluation
bundle, which does not exist yet (D-003, roadmap R-1 and R-8).
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .genes import official_axis
from .models import Prediction, _Base
from .signatures import SignatureSet

__all__ = [
    "COMPONENT_NAMES",
    "ComponentFit",
    "basal_gene_features",
    "build_components",
    "common_response",
    "fit_components",
    "ComponentTransfer",
]

COMPONENT_NAMES = ("source", "common", "specific", "expression")


def basal_gene_features(profile: np.ndarray) -> dict[str, np.ndarray]:
    """Per-gene features of a destination context, from its basal profile alone.

    `profile` is summed counts over the control cells, which is what
    `inference.BasalProfile` carries. Only ratios matter, so the sum is turned
    into CPM and then into a z-scored log, which keeps the fitted coefficient
    on a scale comparable to the other components.

    `expression_z` is z-scored over **expressed genes only**: a context where
    half the axis is zero would otherwise push every expressed gene into the
    same corner of the scale, and the coefficient would be reading the zeros.
    """
    profile = np.asarray(profile, dtype=np.float64)
    if profile.ndim != 1:
        raise ValueError("profile must be one-dimensional")
    total = profile.sum()
    cpm = profile / total * 1e6 if total > 0 else np.zeros_like(profile)
    detected = cpm > 0
    log_cpm = np.log10(cpm + 1.0)
    z = np.zeros_like(log_cpm)
    if detected.any():
        vals = log_cpm[detected]
        sd = vals.std()
        z[detected] = (vals - vals.mean()) / sd if sd > 0 else 0.0
    return {"cpm": cpm, "log_cpm": log_cpm, "expression_z": z, "detected": detected}


def common_response(train: SignatureSet, *, prior_sd: float = 1e6) -> np.ndarray:
    """The response shared by every training target: the per-gene mean delta.

    Averaged over the targets that observed each gene, so a gene measured by
    few targets is not pulled toward zero by the ones that never saw it.

    This is fitted from the training targets and from nothing else. A common
    response computed over all targets, held-out ones included, would leak the
    test rows into the model through the back door -- the leak is small per
    target and invisible in the result, which is what makes it dangerous.
    """
    collapsed = train.collapse_guides()
    n = len(official_axis())
    if len(collapsed) == 0:
        return np.zeros(n)
    total = np.zeros(n)
    count = np.zeros(n)
    for sig in collapsed:
        shrunk = sig.shrunk(prior_sd)
        total[sig.observed] += shrunk[sig.observed]
        count[sig.observed] += 1.0
    out = np.zeros(n)
    seen = count > 0
    out[seen] = total[seen] / count[seen]
    return out


def build_components(
    signature,
    *,
    names: tuple[str, ...],
    prior_sd: float,
    common: np.ndarray | None = None,
    features: dict[str, np.ndarray] | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Components for one target: (K, n_genes) matrix and its observed mask.

    Returns the mask alongside because a component is only defined where the
    source measured the target: an unobserved gene keeps a mask, never a
    confident zero (D-009).
    """
    shrunk = signature.shrunk(prior_sd)
    observed = signature.observed.copy()
    rows = []
    for name in names:
        if name == "source":
            rows.append(shrunk)
        elif name == "common":
            if common is None:
                raise ValueError("component 'common' needs a fitted common response")
            rows.append(common)
        elif name == "specific":
            if common is None:
                raise ValueError("component 'specific' needs a fitted common response")
            rows.append(shrunk - common)
        elif name == "expression":
            if features is None or "expression_z" not in features:
                raise ValueError("component 'expression' needs basal_gene_features")
            rows.append(shrunk * features["expression_z"])
        else:
            raise ValueError(f"unknown component {name!r}; known: {COMPONENT_NAMES}")
    return np.vstack(rows), observed


@dataclass(frozen=True)
class ComponentFit:
    """Fitted coefficients, with what is needed to judge whether to believe them."""

    names: tuple[str, ...]
    theta: np.ndarray
    n_targets: int
    n_pairs: int
    mse: float
    mse_null: float
    condition_number: float
    detail: dict = field(default_factory=dict)

    @property
    def mse_vs_null(self) -> float:
        """Below 1 the fit beats predicting no response; at 1 it ties it."""
        return float(self.mse / self.mse_null) if self.mse_null > 0 else float("nan")


def fit_components(
    source: SignatureSet,
    truth: SignatureSet,
    *,
    names: tuple[str, ...] = ("source",),
    prior_sd: float = 4.0,
    targets: tuple[str, ...] | None = None,
    features: dict[str, np.ndarray] | None = None,
    ridge: float = 0.0,
    max_condition: float = 1e10,
) -> ComponentFit:
    """Least squares for `theta` on the targets given, in closed form.

    `source` supplies the components, `truth` the destination response they are
    fitted against, and only genes observed on both sides enter the sum -- the
    same rule the transfer experiment uses, so the numbers stay comparable.

    The caller chooses `targets`: this function does no splitting, exactly as
    `ShrunkTransfer` does not choose its own alpha. Holding targets out is the
    caller's job and stays visible in the caller's code.

    Raises:
        ValueError: no usable target, or a normal matrix too ill-conditioned to
            identify the components -- reported rather than silently pinned.
    """
    src = source.collapse_guides()
    dst = truth.collapse_guides()
    by_src = {s.target: s for s in src}
    by_dst = {s.target: s for s in dst}
    chosen = tuple(targets) if targets is not None else tuple(
        sorted(set(by_src) & set(by_dst))
    )
    common = common_response(
        src.filter(targets=chosen), prior_sd=prior_sd
    ) if ("common" in names or "specific" in names) else None

    k = len(names)
    gram = np.zeros((k, k))
    rhs = np.zeros(k)
    sq_truth = 0.0
    n_pairs = 0
    used = 0
    for target in chosen:
        s_sig, d_sig = by_src.get(target), by_dst.get(target)
        if s_sig is None or d_sig is None:
            continue
        comps, s_obs = build_components(
            s_sig, names=names, prior_sd=prior_sd, common=common, features=features
        )
        mask = s_obs & d_sig.observed
        if not mask.any():
            continue
        c = comps[:, mask]
        y = d_sig.delta[mask]
        gram += c @ c.T
        rhs += c @ y
        sq_truth += float(y @ y)
        n_pairs += int(mask.sum())
        used += 1
    if used == 0 or n_pairs == 0:
        raise ValueError("no target is present in both source and truth with shared genes")

    regularised = gram + ridge * np.eye(k)
    condition = float(np.linalg.cond(regularised))
    if not np.isfinite(condition) or condition > max_condition:
        raise ValueError(
            f"normal matrix is ill-conditioned (cond={condition:.3g} > {max_condition:.3g}): "
            f"components {names} are not separable on these targets. Drop one, or add ridge."
        )
    theta = np.linalg.solve(regularised, rhs)
    # MSE of the fit, recomputed from the same sums: ||y||^2 - 2 theta.b + theta' G theta
    residual = sq_truth - 2.0 * float(theta @ rhs) + float(theta @ gram @ theta)
    return ComponentFit(
        names=tuple(names),
        theta=theta,
        n_targets=used,
        n_pairs=n_pairs,
        mse=max(residual, 0.0) / n_pairs,
        mse_null=sq_truth / n_pairs,
        condition_number=condition,
        detail={"prior_sd": prior_sd, "ridge": ridge,
                "common_from_n_targets": used if common is not None else 0},
    )


class ComponentTransfer(_Base):
    """Apply fitted component coefficients to a source signature.

    Coefficients are given, never chosen here -- `fit_components` finds them on
    the targets the caller holds in, and the caller keeps the split visible.
    This mirrors `ShrunkTransfer`, whose alpha is likewise selected outside.
    """

    name = "component_transfer"

    def __init__(self, *, names: tuple[str, ...] = ("source",),
                 theta: np.ndarray | None = None, prior_sd: float = 4.0,
                 source: str | None = None,
                 features: dict[str, np.ndarray] | None = None) -> None:
        if theta is None:
            theta = np.ones(len(names))
        theta = np.asarray(theta, dtype=np.float64)
        if theta.shape != (len(names),):
            raise ValueError(f"theta has shape {theta.shape}, expected ({len(names)},)")
        if prior_sd <= 0:
            raise ValueError("prior_sd must be positive")
        self.names = tuple(names)
        self.theta = theta
        self.prior_sd = float(prior_sd)
        self.source = source
        self.features = features
        self._common: np.ndarray | None = None

    def fit(self, train: SignatureSet) -> "ComponentTransfer":
        sigs = train if self.source is None else train.filter(source=self.source)
        sigs = sigs.collapse_guides()
        self._by_target = {s.target: s for s in sigs}
        if "common" in self.names or "specific" in self.names:
            self._common = common_response(sigs, prior_sd=self.prior_sd)
        return self

    def predict(self, target: str) -> Prediction:
        n = len(official_axis())
        sig = getattr(self, "_by_target", {}).get(target)
        if sig is None:
            return Prediction(np.zeros(n), np.zeros(n, dtype=bool), 0,
                              {"model": self.name, "reason": "target not in source"})
        comps, observed = build_components(
            sig, names=self.names, prior_sd=self.prior_sd,
            common=self._common, features=self.features,
        )
        return Prediction(
            delta=self.theta @ comps,
            observed=observed,
            support=1,
            detail={"model": self.name, "components": list(self.names),
                    "theta": [float(t) for t in self.theta],
                    "prior_sd": self.prior_sd, "n_cells": sig.n_cells},
        )
