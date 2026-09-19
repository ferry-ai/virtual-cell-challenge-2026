"""Compared predictors: ShrunkTransfer, masked low-rank, compact MLP, modular.

All of them emit a delta on the measured-gene universe. Unmeasured genes stay
masked. None of them zero-fills a missing panel before a factorisation.

A. ShrunkTransfer with leakage-free amplitude.
B. Linear low-rank (ridge from descriptors onto an SVD basis).
C. Compact MLP that predicts the delta vector.
D. Shared basis, frozen, plus a small coefficient MLP.
E. Same as D with a short joint fine-tune of basis and head.

Conditioned models also have a no-context variant: the context block is
dropped from the design matrix, not zeroed.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from vcc2026.models import ShrunkTransfer, WeightedTransfer
from vcc2026.signatures import SignatureSet

from .factorization import FactorizationSpec, factorize
from .protocol import TrainArrays, reject_forbidden_alpha
from .universe import GeneUniverse, assert_no_zero_fill

__all__ = [
    "count_params",
    "fit_amplitude",
    "MaskedLowRank",
    "CompactMLP",
    "ModularFrozen",
    "ModularJoint",
    "load_model",
]


def count_params(*arrays: np.ndarray) -> int:
    return int(sum(a.size for a in arrays))


def _relu(x):
    return np.maximum(x, 0.0)


def _standardize(X, mean=None, std=None):
    if mean is None:
        mean = X.mean(axis=0)
        std = X.std(axis=0)
        std = np.where(std < 1e-8, 1.0, std)
    return (X - mean) / std, mean, std


class _Adam:
    def __init__(self, params, lr, betas=(0.9, 0.999), eps=1e-8):
        self.params = params
        self.lr = float(lr)
        self.b1, self.b2 = betas
        self.eps = eps
        self.m = [np.zeros_like(p) for p in params]
        self.v = [np.zeros_like(p) for p in params]
        self.t = 0

    def step(self, grads, l2: float = 0.0):
        self.t += 1
        for i, g in enumerate(grads):
            if l2:
                g = g + l2 * self.params[i]
            self.m[i] = self.b1 * self.m[i] + (1.0 - self.b1) * g
            self.v[i] = self.b2 * self.v[i] + (1.0 - self.b2) * (g * g)
            mhat = self.m[i] / (1.0 - self.b1 ** self.t)
            vhat = self.v[i] / (1.0 - self.b2 ** self.t)
            self.params[i] -= self.lr * mhat / (np.sqrt(vhat) + self.eps)


def fit_amplitude(
    pred: np.ndarray,
    truth: np.ndarray,
    *,
    predetermined: float,
    forbidden: float,
    has_internal: bool,
    label: str = "internal_same_line_limited",
) -> dict:
    """Least-squares alpha on an internal pair, or a predetermined constant.

    Never the trial value 0.1974. Never called 'cross-context' when the
    internal pair is missing or is the same cell line.

    `label` says what kind of pair was used, and the caller has to supply it:
    it was hard-coded to `internal_same_line_limited`, which was true while the
    only internal pair available was K562 genome-wide against K562 essential and
    became a false label the moment a fold could calibrate between two different
    biological contexts. A wrong label here is worse than no label -- it travels
    into the comparison table as if it had been checked.
    """
    reject_forbidden_alpha(predetermined, forbidden=forbidden)
    if not has_internal or pred.size == 0:
        reject_forbidden_alpha(predetermined, forbidden=forbidden)
        return {
            "alpha": float(predetermined),
            "method": "predetermined_heuristic",
            "label": "predetermined_heuristic",
            "not_cross_context_calibration": True,
        }
    spp = float(np.sum(pred * pred))
    spy = float(np.sum(pred * truth))
    alpha = float(spy / spp) if spp > 0 else 0.0
    alpha = float(np.clip(alpha, 0.0, 2.0))
    reject_forbidden_alpha(alpha, forbidden=forbidden)
    return {
        "alpha": alpha,
        "method": "closed_form_least_squares_on_internal_pair",
        "label": label,
        "not_cross_context_calibration": label != "cross_context_within_training",
        "spp": spp,
        "spy": spy,
    }


def _ridge_fit(X, Y, ridge: float):
    mean = X.mean(axis=0)
    Xc = X - mean
    g = Xc.T @ Xc + ridge * np.eye(Xc.shape[1])
    coef = np.linalg.solve(g, Xc.T @ Y)
    return mean, coef


def _ridge_predict(X, mean, coef):
    return (X - mean) @ coef


def _init_linear(n_in, n_out, rng):
    w = rng.normal(0.0, np.sqrt(2.0 / max(n_in, 1)), size=(n_in, n_out))
    b = np.zeros(n_out)
    return w, b


@dataclass
class MaskedLowRank:
    """B. Linear map from descriptors onto an SVD basis of measured genes."""

    name: str = "lowrank_linear"
    uses_context: bool = True
    rank: int = 16
    ridge: float = 1.0
    universe: GeneUniverse | None = None
    factorization: FactorizationSpec = field(default_factory=FactorizationSpec)
    _basis: np.ndarray | None = None
    _mean_y: np.ndarray | None = None
    _x_mean: np.ndarray | None = None
    _coef: np.ndarray | None = None
    _k: int = 0
    _factorization_info: dict | None = None

    def fit(self, arrays: TrainArrays, universe: GeneUniverse) -> "MaskedLowRank":
        assert_no_zero_fill(universe, arrays.Y)
        self.universe = universe
        Y = arrays.Y
        # Centre genes so the first component is not the mean response.
        self._mean_y = Y.mean(axis=0, keepdims=True)
        Yc = Y - self._mean_y
        k = max(1, min(int(self.rank), min(Yc.shape) - 1))
        fac = factorize(Yc, k, self.factorization)
        self._basis = fac.Vt
        self._k = fac.k
        self._factorization_info = fac.as_dict()
        Z = Yc @ self._basis.T
        self._x_mean, self._coef = _ridge_fit(arrays.X, Z, self.ridge)
        return self

    def predict_delta(self, X: np.ndarray) -> np.ndarray:
        z = _ridge_predict(X, self._x_mean, self._coef)
        return z @ self._basis + self._mean_y

    def parameter_counts(self) -> dict:
        trainable = count_params(self._coef, self._x_mean)
        total = trainable + count_params(self._basis, self._mean_y)
        return {
            "n_total": total,
            "n_trainable": trainable,
            "n_frozen": total - trainable,
            "rank": self._k,
        }

    def save(self, path: Path) -> None:
        np.savez_compressed(
            path,
            name=np.array(self.name),
            uses_context=np.array(self.uses_context),
            rank=np.array(self.rank),
            ridge=np.array(self.ridge),
            observed=self.universe.observed,
            basis=self._basis,
            mean_y=self._mean_y,
            x_mean=self._x_mean,
            coef=self._coef,
            k=np.array(self._k),
            factorization_method=np.array(self.factorization.method),
            factorization_n_oversamples=np.array(self.factorization.n_oversamples),
            factorization_n_iter=np.array(self.factorization.n_iter),
            factorization_seed=np.array(
                -1 if self.factorization.seed is None else self.factorization.seed
            ),
        )


def _mlp_forward(X, W1, b1, W2, b2):
    h = _relu(X @ W1 + b1)
    return h @ W2 + b2, h


def _fit_mlp(X, Y, *, hidden, lr, l2, epochs, patience, batch, seed, val=None):
    rng = np.random.default_rng(seed)
    n, d = X.shape
    n_out = Y.shape[1]
    W1, b1 = _init_linear(d, hidden, rng)
    W2, b2 = _init_linear(hidden, n_out, rng)
    W2 *= 0.1
    opt = _Adam([W1, b1, W2, b2], lr=lr)
    best = None
    best_val = np.inf
    stall = 0
    Xs, mean, std = _standardize(X)
    Yv = None
    if val is not None:
        Xv, Yv = val
        Xv = (Xv - mean) / std
    history = []
    for epoch in range(int(epochs)):
        perm = rng.permutation(n)
        for lo in range(0, n, batch):
            idx = perm[lo : lo + batch]
            xb, yb = Xs[idx], Y[idx]
            pred, h = _mlp_forward(xb, W1, b1, W2, b2)
            err = (pred - yb) / max(len(idx), 1)
            dW2 = h.T @ err
            db2 = err.sum(axis=0)
            dh = (err @ W2.T) * (h > 0)
            dW1 = xb.T @ dh
            db1 = dh.sum(axis=0)
            opt.step([dW1, db1, dW2, db2], l2=l2)
        pred_tr, _ = _mlp_forward(Xs, W1, b1, W2, b2)
        tr = float(np.mean(np.square(pred_tr - Y)))
        if Yv is not None:
            pred_v, _ = _mlp_forward(Xv, W1, b1, W2, b2)
            va = float(np.mean(np.square(pred_v - Yv)))
        else:
            va = tr
        history.append({"epoch": epoch, "train_mse": tr, "val_mse": va})
        if va + 1e-12 < best_val:
            best_val = va
            stall = 0
            best = (W1.copy(), b1.copy(), W2.copy(), b2.copy(), mean.copy(), std.copy())
        else:
            stall += 1
            if stall >= patience:
                break
    if best is None:
        best = (W1, b1, W2, b2, mean, std)
    return best, history


@dataclass
class CompactMLP:
    """C. One small network, official-universe output, masked by construction."""

    name: str = "compact_mlp"
    uses_context: bool = True
    hidden: int = 24
    lr: float = 0.01
    l2: float = 1e-4
    epochs: int = 30
    patience: int = 6
    batch: int = 32
    seed: int = 2026
    universe: GeneUniverse | None = None
    _W1 = None
    _b1 = None
    _W2 = None
    _b2 = None
    _x_mean = None
    _x_std = None
    history: list = field(default_factory=list)

    def fit(
        self, arrays: TrainArrays, universe: GeneUniverse, val: tuple | None = None
    ) -> "CompactMLP":
        assert_no_zero_fill(universe, arrays.Y)
        self.universe = universe
        best, hist = _fit_mlp(
            arrays.X, arrays.Y,
            hidden=self.hidden, lr=self.lr, l2=self.l2, epochs=self.epochs,
            patience=self.patience, batch=self.batch, seed=self.seed, val=val,
        )
        self._W1, self._b1, self._W2, self._b2, self._x_mean, self._x_std = best
        self.history = hist
        return self

    def predict_delta(self, X: np.ndarray) -> np.ndarray:
        Xs = (X - self._x_mean) / self._x_std
        pred, _ = _mlp_forward(Xs, self._W1, self._b1, self._W2, self._b2)
        return pred

    def parameter_counts(self) -> dict:
        n = count_params(self._W1, self._b1, self._W2, self._b2)
        return {"n_total": n, "n_trainable": n, "n_frozen": 0, "hidden": self.hidden}

    def save(self, path: Path) -> None:
        np.savez_compressed(
            path,
            name=np.array(self.name),
            uses_context=np.array(self.uses_context),
            observed=self.universe.observed,
            W1=self._W1, b1=self._b1, W2=self._W2, b2=self._b2,
            x_mean=self._x_mean, x_std=self._x_std,
            hidden=np.array(self.hidden),
        )


def _coef_forward(X, W1, b1, W2, b2, basis, mean_y):
    a, h = _mlp_forward(X, W1, b1, W2, b2)
    return a @ basis + mean_y, a, h


@dataclass
class ModularFrozen:
    """D. SVD basis frozen; a small MLP predicts the coefficients."""

    name: str = "modular_frozen"
    uses_context: bool = True
    rank: int = 16
    hidden: int = 8
    lr: float = 0.01
    l2: float = 1e-4
    epochs: int = 30
    patience: int = 6
    batch: int = 32
    seed: int = 2026
    universe: GeneUniverse | None = None
    factorization: FactorizationSpec = field(default_factory=FactorizationSpec)
    _basis = None
    _mean_y = None
    _W1 = None
    _b1 = None
    _W2 = None
    _b2 = None
    _x_mean = None
    _x_std = None
    _k: int = 0
    history: list = field(default_factory=list)
    _factorization_info: dict | None = None

    def _fit_basis(self, Y: np.ndarray) -> None:
        self._mean_y = Y.mean(axis=0, keepdims=True)
        Yc = Y - self._mean_y
        k = max(1, min(int(self.rank), min(Yc.shape) - 1))
        fac = factorize(Yc, k, self.factorization)
        self._basis = fac.Vt.copy()
        self._k = fac.k
        self._factorization_info = fac.as_dict()

    def fit(
        self, arrays: TrainArrays, universe: GeneUniverse, val: tuple | None = None
    ) -> "ModularFrozen":
        assert_no_zero_fill(universe, arrays.Y)
        self.universe = universe
        self._fit_basis(arrays.Y)
        Z = (arrays.Y - self._mean_y) @ self._basis.T
        val_z = None
        if val is not None:
            Xv, Yv = val
            val_z = (Xv, (Yv - self._mean_y) @ self._basis.T)
        best, hist = _fit_mlp(
            arrays.X, Z,
            hidden=self.hidden, lr=self.lr, l2=self.l2, epochs=self.epochs,
            patience=self.patience, batch=self.batch, seed=self.seed, val=val_z,
        )
        self._W1, self._b1, self._W2, self._b2, self._x_mean, self._x_std = best
        self.history = hist
        return self

    def predict_delta(self, X: np.ndarray) -> np.ndarray:
        Xs = (X - self._x_mean) / self._x_std
        a, _ = _mlp_forward(Xs, self._W1, self._b1, self._W2, self._b2)
        return a @ self._basis + self._mean_y

    def parameter_counts(self) -> dict:
        head = count_params(self._W1, self._b1, self._W2, self._b2)
        frozen = count_params(self._basis, self._mean_y)
        return {
            "n_total": head + frozen,
            "n_trainable": head,
            "n_frozen": frozen,
            "rank": self._k,
            "hidden": self.hidden,
        }

    def save(self, path: Path) -> None:
        np.savez_compressed(
            path,
            name=np.array(self.name),
            uses_context=np.array(self.uses_context),
            observed=self.universe.observed,
            basis=self._basis, mean_y=self._mean_y,
            W1=self._W1, b1=self._b1, W2=self._W2, b2=self._b2,
            x_mean=self._x_mean, x_std=self._x_std,
            rank=np.array(self.rank), k=np.array(self._k),
            factorization_method=np.array(self.factorization.method),
            factorization_n_oversamples=np.array(self.factorization.n_oversamples),
            factorization_n_iter=np.array(self.factorization.n_iter),
            factorization_seed=np.array(
                -1 if self.factorization.seed is None else self.factorization.seed
            ),
        )


@dataclass
class ModularJoint(ModularFrozen):
    """E. Same architecture as D, then a short joint fine-tune of basis and head."""

    name: str = "modular_joint"
    joint_epochs: int = 12
    joint_lr: float = 0.003
    joint_history: list = field(default_factory=list)

    def fit(
        self, arrays: TrainArrays, universe: GeneUniverse, val: tuple | None = None
    ) -> "ModularJoint":
        super().fit(arrays, universe, val=val)
        # Joint: gradients through a @ B. Basis starts frozen-optimal.
        rng = np.random.default_rng(self.seed + 1)
        W1, b1, W2, b2 = self._W1, self._b1, self._W2, self._b2
        B = self._basis.copy()
        mean_y = self._mean_y
        Xs = (arrays.X - self._x_mean) / self._x_std
        Y = arrays.Y
        n = Xs.shape[0]
        opt = _Adam([W1, b1, W2, b2, B], lr=self.joint_lr)
        best = None
        best_val = np.inf
        stall = 0
        Xv = Yv = None
        if val is not None:
            Xv = (val[0] - self._x_mean) / self._x_std
            Yv = val[1]
        for epoch in range(int(self.joint_epochs)):
            perm = rng.permutation(n)
            for lo in range(0, n, self.batch):
                idx = perm[lo : lo + self.batch]
                xb, yb = Xs[idx], Y[idx]
                pred, a, h = _coef_forward(xb, W1, b1, W2, b2, B, mean_y)
                err = (pred - yb) / max(len(idx), 1)
                dB = a.T @ err
                da = err @ B.T
                dW2 = h.T @ da
                db2 = da.sum(axis=0)
                dh = (da @ W2.T) * (h > 0)
                dW1 = xb.T @ dh
                db1 = dh.sum(axis=0)
                opt.step([dW1, db1, dW2, db2, dB], l2=self.l2)
            pred_tr, _, _ = _coef_forward(Xs, W1, b1, W2, b2, B, mean_y)
            tr = float(np.mean(np.square(pred_tr - Y)))
            if Yv is not None:
                pred_v, _, _ = _coef_forward(Xv, W1, b1, W2, b2, B, mean_y)
                va = float(np.mean(np.square(pred_v - Yv)))
            else:
                va = tr
            self.joint_history.append({"epoch": epoch, "train_mse": tr, "val_mse": va})
            if va + 1e-12 < best_val:
                best_val = va
                stall = 0
                best = (W1.copy(), b1.copy(), W2.copy(), b2.copy(), B.copy())
            else:
                stall += 1
                if stall >= self.patience:
                    break
        if best is not None:
            self._W1, self._b1, self._W2, self._b2, self._basis = best
        else:
            self._W1, self._b1, self._W2, self._b2, self._basis = W1, b1, W2, b2, B
        return self

    def parameter_counts(self) -> dict:
        n = count_params(self._W1, self._b1, self._W2, self._b2, self._basis, self._mean_y)
        # After joint fine-tune the basis is trainable.
        return {
            "n_total": n,
            "n_trainable": n,
            "n_frozen": 0,
            "rank": self._k,
            "hidden": self.hidden,
            "joint_finetune_epochs_ran": len(self.joint_history),
            "initial_basis_cost_separate": True,
        }


def load_weights(path: Path) -> dict:
    with np.load(path, allow_pickle=False) as handle:
        return {k: handle[k] for k in handle.files}


def apply_loaded(model, payload: dict, universe: GeneUniverse) -> None:
    model.universe = universe
    if "basis" in payload:
        model._basis = payload["basis"]
        model._mean_y = payload["mean_y"]
        model._k = int(payload["k"]) if "k" in payload else int(payload.get("rank", 0))
    if "coef" in payload:
        model._coef = payload["coef"]
        model._x_mean = payload["x_mean"]
        model._mean_y = payload["mean_y"]
        model._basis = payload["basis"]
        model._k = int(payload["k"])
    if "W1" in payload:
        model._W1 = payload["W1"]
        model._b1 = payload["b1"]
        model._W2 = payload["W2"]
        model._b2 = payload["b2"]
        model._x_mean = payload["x_mean"]
        model._x_std = payload["x_std"]


def select_shrunk_transfer(
    train: SignatureSet,
    *,
    source: str | None,
    inner_dest: SignatureSet | None,
    inner_val_targets: tuple[str, ...],
    prior_sd_grid,
    predetermined_alpha: float,
    forbidden_alpha: float,
) -> tuple[ShrunkTransfer, dict]:
    """Pick prior_sd on an internal pair; never use the trial alpha."""
    reject_forbidden_alpha(predetermined_alpha, forbidden=forbidden_alpha)
    model = ShrunkTransfer(
        alpha=predetermined_alpha, prior_sd=4.0, source=source, collapse_guides=True
    )
    model.fit(train)
    calib = {
        "alpha": float(predetermined_alpha),
        "prior_sd": 4.0,
        "method": "predetermined_heuristic",
        "label": "predetermined_heuristic",
        "not_cross_context_calibration": True,
    }
    if inner_dest is None or len(inner_dest) == 0:
        return model, calib

    src = {s.target: s for s in train.collapse_guides()}
    dst = {s.target: s for s in inner_dest.collapse_guides()}
    val = [t for t in inner_val_targets if t in src and t in dst]
    fit_t = [t for t in src if t in dst and t not in set(inner_val_targets)]
    if len(fit_t) < 5 or len(val) < 3:
        # Internal pair too small after the unseen-target exclusion: predetermined.
        return model, calib

    def pack(targets):
        mask = src[targets[0]].observed & dst[targets[0]].observed
        sd = np.vstack([src[t].delta for t in targets])[:, mask]
        ss = np.vstack([src[t].se for t in targets])[:, mask]
        dd = np.vstack([dst[t].delta for t in targets])[:, mask]
        return sd, ss, dd

    best = None
    table = []
    sd, ss, dd = pack(fit_t)
    for prior_sd in prior_sd_grid:
        w = prior_sd ** 2 / (prior_sd ** 2 + np.square(ss))
        P = sd * w
        spp = float(np.sum(P * P))
        spy = float(np.sum(P * dd))
        alpha = float(spy / spp) if spp > 0 else 0.0
        alpha = float(np.clip(alpha, 0.0, 2.0))
        reject_forbidden_alpha(alpha, forbidden=forbidden_alpha)
        sdv, ssv, ddv = pack(val)
        wv = prior_sd ** 2 / (prior_sd ** 2 + np.square(ssv))
        Pv = alpha * sdv * wv
        mse = float(np.mean(np.square(Pv - ddv)))
        table.append({"prior_sd": float(prior_sd), "alpha": alpha, "val_mse": mse})
        if best is None or mse < best["val_mse"]:
            best = table[-1]
    # Refit alpha on all internal-overlapping training targets with chosen prior.
    all_t = [t for t in src if t in dst]
    sd, ss, dd = pack(all_t)
    prior_sd = float(best["prior_sd"])
    w = prior_sd ** 2 / (prior_sd ** 2 + np.square(ss))
    P = sd * w
    spp = float(np.sum(P * P))
    spy = float(np.sum(P * dd))
    alpha = float(np.clip(spy / spp if spp > 0 else 0.0, 0.0, 2.0))
    reject_forbidden_alpha(alpha, forbidden=forbidden_alpha)
    model = ShrunkTransfer(
        alpha=alpha, prior_sd=prior_sd, source=source, collapse_guides=True
    )
    model.fit(train)
    calib = {
        "alpha": alpha,
        "prior_sd": prior_sd,
        "method": "closed_form_least_squares_on_internal_pair",
        "label": "internal_same_line_limited",
        "not_cross_context_calibration": True,
        "n_fit_targets": len(fit_t),
        "n_val_targets": len(val),
        "grid": table,
    }
    return model, calib


def context_equal_weights(sources_by_context: dict[str, list[str]]) -> dict[str, float]:
    """Equal weight per biological context, split among that context's datasets.

    K562 appears twice in this project (genome-wide and essential). Weighting by
    dataset would give that cell line twice the say of RPE1 for no biological
    reason, and the imbalance would be invisible in the output. The rule is
    fixed here, in advance, and never selected on a test fold.
    """
    weights: dict[str, float] = {}
    for context, sources in sources_by_context.items():
        if not sources:
            continue
        share = 1.0 / float(len(sources))
        for source in sources:
            weights[source] = share
    return weights


def select_multi_source_transfer(
    train: SignatureSet,
    *,
    sources_by_context: dict[str, list[str]],
    inner_dest_context: str | None,
    inner_val_targets: tuple[str, ...],
    prior_sd_grid,
    predetermined_alpha: float,
    forbidden_alpha: float,
) -> tuple[WeightedTransfer, dict]:
    """Transfer from more than one training context, combined by a fixed rule.

    Two things are decided here, and they are different:

    * **How the sources combine** -- `context_equal_weights`, fixed in advance.
    * **How large the answer should be** -- alpha. With two training contexts one
      of them is held out *inside training* as the destination, and alpha is
      least squares on that pair. That is a genuine cross-context calibration:
      it never reads the test context, and unlike the same-line K562 pair it is
      not measuring a cell line against itself.

    The amplitude is fitted for one context pair and then applied to the
    combination predicting a third context. That is an approximation, and it is
    labelled `cross_context_within_training` rather than called a calibration
    for the test context, which nothing here can provide.
    """
    reject_forbidden_alpha(predetermined_alpha, forbidden=forbidden_alpha)
    weights = context_equal_weights(sources_by_context)
    model = WeightedTransfer(weights, alpha=predetermined_alpha, prior_sd=4.0)
    model.fit(train)
    calib = {
        "alpha": float(predetermined_alpha),
        "prior_sd": 4.0,
        "method": "predetermined_heuristic",
        "label": "predetermined_heuristic",
        "combination_rule": "context_equal_weights",
        "weights": {k: float(v) for k, v in weights.items()},
        "n_train_contexts": len(sources_by_context),
        "not_cross_context_calibration": True,
    }
    train_contexts = list(sources_by_context)
    if inner_dest_context is None or len(train_contexts) < 2:
        return model, calib
    if inner_dest_context not in sources_by_context:
        raise ValueError(f"{inner_dest_context!r} is not a training context")

    donor_contexts = {c: s for c, s in sources_by_context.items()
                      if c != inner_dest_context}
    donor_weights = context_equal_weights(donor_contexts)
    donor = WeightedTransfer(donor_weights, alpha=1.0, prior_sd=1.0)
    donor.fit(train)
    dest_sources = set(sources_by_context[inner_dest_context])
    dst = {
        s.target: s
        for s in SignatureSet(
            [s for s in train if s.source in dest_sources]
        ).collapse_guides()
    }
    donor_targets = {
        s.target
        for s in train
        if s.source in {src for srcs in donor_contexts.values() for src in srcs}
    }
    shared = sorted(donor_targets & set(dst))
    val = [t for t in inner_val_targets if t in set(shared)]
    fit_t = [t for t in shared if t not in set(inner_val_targets)]
    if len(fit_t) < 5 or len(val) < 3:
        calib["why_predetermined"] = (
            f"internal cross-context pair too small: {len(fit_t)} fit / {len(val)} val"
        )
        return model, calib

    def pack(targets, prior_sd):
        rows_p, rows_d, = [], []
        for target in targets:
            donor.prior_sd = prior_sd
            pred = donor.predict(target)
            sig = dst[target]
            mask = pred.observed & sig.observed
            if not mask.any():
                continue
            rows_p.append(pred.delta[mask])
            rows_d.append(sig.delta[mask])
        if not rows_p:
            return np.zeros(0), np.zeros(0)
        return np.concatenate(rows_p), np.concatenate(rows_d)

    best, table = None, []
    for prior_sd in prior_sd_grid:
        p_fit, d_fit = pack(fit_t, float(prior_sd))
        spp = float(np.sum(p_fit * p_fit))
        alpha = float(np.clip(float(np.sum(p_fit * d_fit)) / spp if spp > 0 else 0.0,
                              0.0, 2.0))
        reject_forbidden_alpha(alpha, forbidden=forbidden_alpha)
        p_val, d_val = pack(val, float(prior_sd))
        if p_val.size == 0:
            continue
        mse = float(np.mean(np.square(alpha * p_val - d_val)))
        table.append({"prior_sd": float(prior_sd), "alpha": alpha, "val_mse": mse})
        if best is None or mse < best["val_mse"]:
            best = table[-1]
    if best is None:
        calib["why_predetermined"] = "no usable internal validation rows"
        return model, calib

    prior_sd = float(best["prior_sd"])
    p_all, d_all = pack(shared, prior_sd)
    spp = float(np.sum(p_all * p_all))
    alpha = float(np.clip(float(np.sum(p_all * d_all)) / spp if spp > 0 else 0.0,
                          0.0, 2.0))
    reject_forbidden_alpha(alpha, forbidden=forbidden_alpha)
    model = WeightedTransfer(weights, alpha=alpha, prior_sd=prior_sd)
    model.fit(train)
    calib.update({
        "alpha": alpha,
        "prior_sd": prior_sd,
        "method": "closed_form_least_squares_on_internal_cross_context_pair",
        "label": "cross_context_within_training",
        "not_cross_context_calibration": False,
        "internal_dest_context": inner_dest_context,
        "internal_donor_contexts": sorted(donor_contexts),
        "n_fit_targets": len(fit_t),
        "n_val_targets": len(val),
        "grid": table,
        "approximation": (
            "alpha fitted on one training context pair, applied to the "
            "combination predicting a third context"
        ),
    })
    return model, calib
