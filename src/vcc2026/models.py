"""Transfer baselines that predict a response delta for an unseen target.

Every model here answers the same question -- given signatures measured in one
or more source contexts, what delta do we predict for target `t` in a context
where we have never seen a perturbation -- and every one returns a masked
prediction, so a gene no source measured stays unmeasured rather than becoming
a confident zero (D-009).

The ladder is deliberate. `NullModel` is the thing to beat and is not a straw
man: on metrics with a floor at zero it can score better than a confidently
wrong prediction. `ShrunkTransfer` adds exactly one idea, that a noisy estimate
should be pulled toward zero, and its shrinkage is chosen on held-out targets
rather than asserted. `WeightedTransfer` adds a second, that sources should be
weighted by how well they transfer, again measured on held-out targets.
`LowRankRidge` is the only model that can predict a target no source measured
at all, and it is the first place where it becomes possible to fool ourselves,
so it is fitted and selected under the same held-out discipline.

None of these is a generative count model. That is intentional: the brief is to
get a calibrated, honestly-validated response estimate first.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from .genes import official_axis
from .signatures import SignatureSet

__all__ = [
    "Prediction",
    "NullModel",
    "ShrunkTransfer",
    "WeightedTransfer",
    "LowRankRidge",
    "MODEL_REGISTRY",
]


@dataclass(frozen=True)
class Prediction:
    """A predicted response with its support mask.

    `delta` is meaningful only where `observed` is True. `support` counts how
    many source signatures contributed, and is 0 for a target no source covers
    -- which is a legitimate answer, not a failure.
    """

    delta: np.ndarray
    observed: np.ndarray
    support: int
    detail: dict = field(default_factory=dict)

    def masked(self) -> np.ndarray:
        """delta with unobserved genes forced to zero, for scoring against a
        reference that itself defines those genes as unchanged. Use only at the
        boundary where a dense array is required; never inside the model."""
        return np.where(self.observed, self.delta, 0.0)


class _Base:
    name = "base"

    def fit(self, train: SignatureSet) -> "_Base":
        raise NotImplementedError

    def predict(self, target: str) -> Prediction:
        raise NotImplementedError

    def predict_many(self, targets) -> dict[str, Prediction]:
        return {t: self.predict(t) for t in targets}


class NullModel(_Base):
    """Predict no change everywhere. The floor every other model must clear."""

    name = "null"

    def fit(self, train: SignatureSet) -> "NullModel":
        self._n = len(official_axis())
        return self

    def predict(self, target: str) -> Prediction:
        n = getattr(self, "_n", len(official_axis()))
        return Prediction(
            delta=np.zeros(n), observed=np.ones(n, dtype=bool), support=0,
            detail={"model": self.name},
        )


class ShrunkTransfer(_Base):
    """Transfer one source's measured delta, shrunk toward zero by precision.

    Each gene is scaled by `prior_sd^2 / (prior_sd^2 + se^2)` and then by a
    global amplitude `alpha`. The two do different jobs and both are needed:
    `prior_sd` shrinks *per gene* according to how well that gene was measured,
    `alpha` scales the whole response to account for the source context not
    being the target context. Both are selected on held-out targets.
    """

    name = "shrunk_transfer"

    def __init__(self, *, alpha: float = 1.0, prior_sd: float = 0.5,
                 source: str | None = None, collapse_guides: bool = True) -> None:
        if alpha < 0:
            raise ValueError("alpha must be non-negative")
        if prior_sd <= 0:
            raise ValueError("prior_sd must be positive")
        self.alpha = alpha
        self.prior_sd = prior_sd
        self.source = source
        self.collapse_guides = collapse_guides

    def fit(self, train: SignatureSet) -> "ShrunkTransfer":
        sigs = train if self.source is None else train.filter(source=self.source)
        if self.collapse_guides:
            sigs = sigs.collapse_guides()
        self._by_target = {s.target: s for s in sigs}
        return self

    def predict(self, target: str) -> Prediction:
        n = len(official_axis())
        sig = self._by_target.get(target)
        if sig is None:
            return Prediction(np.zeros(n), np.zeros(n, dtype=bool), 0,
                              {"model": self.name, "reason": "target not in source"})
        return Prediction(
            delta=self.alpha * sig.shrunk(self.prior_sd),
            observed=sig.observed.copy(),
            support=1,
            detail={"model": self.name, "alpha": self.alpha,
                    "prior_sd": self.prior_sd, "n_cells": sig.n_cells},
        )


class WeightedTransfer(_Base):
    """Combine several sources for the same target with non-negative weights.

    Weights are supplied per source id and renormalised over the sources that
    actually cover the requested target, so a target present in only one source
    is not silently down-weighted for the absence of the others. Genes are
    combined only where a contributing source observed them; the result's mask
    is the union of contributors' masks.
    """

    name = "weighted_transfer"

    def __init__(self, weights: dict[str, float], *, alpha: float = 1.0,
                 prior_sd: float = 0.5) -> None:
        if not weights:
            raise ValueError("at least one source weight is required")
        if any(w < 0 for w in weights.values()):
            raise ValueError("weights must be non-negative")
        if sum(weights.values()) <= 0:
            raise ValueError("weights must not all be zero")
        self.weights = dict(weights)
        self.alpha = alpha
        self.prior_sd = prior_sd

    def fit(self, train: SignatureSet) -> "WeightedTransfer":
        self._by_source: dict[str, dict[str, object]] = {}
        for source in self.weights:
            sigs = train.filter(source=source).collapse_guides()
            self._by_source[source] = {s.target: s for s in sigs}
        return self

    def predict(self, target: str) -> Prediction:
        n = len(official_axis())
        num = np.zeros(n)
        wsum = np.zeros(n)
        observed = np.zeros(n, dtype=bool)
        used = []
        for source, weight in self.weights.items():
            sig = self._by_source.get(source, {}).get(target)
            if sig is None or weight <= 0:
                continue
            contrib = sig.shrunk(self.prior_sd)
            num += weight * np.where(sig.observed, contrib, 0.0)
            wsum += weight * sig.observed
            observed |= sig.observed
            used.append(source)
        delta = np.zeros(n)
        nz = wsum > 0
        delta[nz] = self.alpha * num[nz] / wsum[nz]
        return Prediction(delta, observed, len(used),
                          {"model": self.name, "sources_used": used,
                           "alpha": self.alpha})


class LowRankRidge(_Base):
    """Ridge regression onto a low-rank basis of observed responses.

    Motivation: most targets are absent from most sources, and a model that can
    only echo a measured delta predicts nothing for them. Responses across
    targets are strongly correlated, so a rank-`k` basis learned from the
    training targets spans most of the response space, and a new target is
    placed in that basis using descriptors (here, its basal expression profile
    in the target context).

    This is the first model that can be fooled by its own flexibility, so the
    rank and the ridge penalty are selected on held-out targets, never on the
    rows used to learn the basis.
    """

    name = "low_rank_ridge"

    def __init__(self, *, rank: int = 32, ridge: float = 1.0,
                 alpha: float = 1.0) -> None:
        if rank < 1:
            raise ValueError("rank must be >= 1")
        if ridge < 0:
            raise ValueError("ridge must be non-negative")
        self.rank = rank
        self.ridge = ridge
        self.alpha = alpha
        self._descriptors: dict[str, np.ndarray] | None = None

    def set_descriptors(self, descriptors: dict[str, np.ndarray]) -> "LowRankRidge":
        """Provide a feature vector per target (e.g. its basal profile)."""
        self._descriptors = {k: np.asarray(v, dtype=np.float64)
                             for k, v in descriptors.items()}
        return self

    def fit(self, train: SignatureSet) -> "LowRankRidge":
        if self._descriptors is None:
            raise RuntimeError("call set_descriptors() before fit()")
        collapsed = train.collapse_guides()
        rows, targets = [], []
        for s in collapsed:
            if s.target in self._descriptors:
                rows.append(np.where(s.observed, s.delta, 0.0))
                targets.append(s.target)
        if not rows:
            raise ValueError("no training target has a descriptor")

        Y = np.vstack(rows)                       # (n_train, n_genes)
        X = np.vstack([self._descriptors[t] for t in targets])  # (n_train, n_feat)

        self._observed = np.zeros(Y.shape[1], dtype=bool)
        for s in collapsed:
            if s.target in self._descriptors:
                self._observed |= s.observed

        k = min(self.rank, min(Y.shape) - 1) if min(Y.shape) > 1 else 1
        k = max(k, 1)
        # Basis over the response space.
        # WARNING: unobserved genes were filled with 0.0 above. That is not a
        # statistically neutral missing-data treatment (D-009) and must not be
        # reused across panels with different gene support. The modular pilot
        # uses vcc2026.benchmark (intersection universe / masked loss) instead.
        U, S, Vt = np.linalg.svd(Y, full_matrices=False)
        self._basis = Vt[:k]                       # (k, n_genes)
        Z = Y @ self._basis.T                      # (n_train, k) coordinates

        self._x_mean = X.mean(axis=0)
        Xc = X - self._x_mean
        G = Xc.T @ Xc + self.ridge * np.eye(Xc.shape[1])
        self._coef = np.linalg.solve(G, Xc.T @ Z)  # (n_feat, k)
        self._n_train = len(targets)
        self._k = k
        return self

    def predict(self, target: str) -> Prediction:
        n = len(official_axis())
        if self._descriptors is None or target not in self._descriptors:
            return Prediction(np.zeros(n), np.zeros(n, dtype=bool), 0,
                              {"model": self.name, "reason": "no descriptor"})
        x = self._descriptors[target] - self._x_mean
        z = x @ self._coef
        delta = self.alpha * (z @ self._basis)
        return Prediction(delta, self._observed.copy(), self._n_train,
                          {"model": self.name, "rank": self._k,
                           "ridge": self.ridge, "alpha": self.alpha})


MODEL_REGISTRY = {
    NullModel.name: NullModel,
    ShrunkTransfer.name: ShrunkTransfer,
    WeightedTransfer.name: WeightedTransfer,
    LowRankRidge.name: LowRankRidge,
}
