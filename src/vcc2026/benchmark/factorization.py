"""Truncated SVD of an already-centred response matrix.

The benchmark keeps a handful of components and used to compute every
singular vector to get them (`numpy.linalg.svd`, LAPACK gesdd). This module
is the single place that choice lives.

Two methods, same contract:

* ``exact`` -- full economy SVD, then the leading ``k`` components. Reference.
* ``randomized`` -- Halko, Martinsson & Tropp 2011, Algorithm 4.4, with
  subspace iteration (their 4.3). Seed, oversampling and iteration count are
  required arguments, not hidden defaults that change between versions.

Callers centre. This function does not: a mean component mixed into the basis
is a modelling choice and has to stay visible at the call site.

Do not compare left/right singular vectors elementwise across methods or
seeds. Signs flip, and two bases of the same subspace need not match in any
particular basis. Reconstruction error, canonical angles, and downstream
predictions are the comparisons that mean something.

No new dependency: both paths are numpy. sklearn's ``randomized_svd`` is not
used, so a sklearn upgrade cannot silently change a fold.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

import numpy as np

__all__ = [
    "FactorizationSpec",
    "FactorizationResult",
    "factorization_from_config",
    "factorize",
    "ranks_compatible_with_shape",
    "reconstruct",
    "relative_reconstruction_error",
]


@dataclass(frozen=True)
class FactorizationSpec:
    """How to take a rank-k basis. Exact is the reference; randomized is opt-in."""

    method: str = "exact"
    n_oversamples: int = 10
    n_iter: int = 2
    seed: int | None = None

    def __post_init__(self) -> None:
        method = self.method.strip().lower()
        if method not in {"exact", "randomized"}:
            raise ValueError(
                f"factorization method must be 'exact' or 'randomized', got {self.method!r}"
            )
        object.__setattr__(self, "method", method)
        if int(self.n_oversamples) < 0:
            raise ValueError("n_oversamples must be >= 0")
        if int(self.n_iter) < 0:
            raise ValueError("n_iter must be >= 0")
        if method == "randomized" and self.seed is None:
            raise ValueError(
                "randomized SVD requires an explicit seed; pass the fold seed "
                "or set factorization.seed in the config"
            )

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FactorizationResult:
    """Leading k factors of a centred matrix, plus the knobs that produced them."""

    U: np.ndarray
    S: np.ndarray
    Vt: np.ndarray
    k: int
    spec: FactorizationSpec
    method_used: str
    fallback: str | None
    n_rows: int
    n_cols: int
    sketch_size: int | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "k": int(self.k),
            "method_requested": self.spec.method,
            "method_used": self.method_used,
            "n_oversamples": int(self.spec.n_oversamples),
            "n_iter": int(self.spec.n_iter),
            "seed": self.spec.seed,
            "fallback": self.fallback,
            "n_rows": int(self.n_rows),
            "n_cols": int(self.n_cols),
            "sketch_size": None if self.sketch_size is None else int(self.sketch_size),
            "singular_values": [float(x) for x in self.S],
        }


def factorization_from_config(cfg: dict | None, seed: int) -> FactorizationSpec:
    """Read the optional ``factorization:`` block. Missing means exact, as before."""
    block = (cfg or {}).get("factorization") or {}
    method = str(block.get("method", "exact"))
    raw_seed = block.get("seed", seed)
    if method.strip().lower() == "exact":
        seed_val = None if raw_seed is None else int(raw_seed)
    else:
        seed_val = int(seed if raw_seed is None else raw_seed)
    return FactorizationSpec(
        method=method,
        n_oversamples=int(block.get("n_oversamples", 10)),
        n_iter=int(block.get("n_iter", 2)),
        seed=seed_val,
    )


def ranks_compatible_with_shape(rank_grid, shape) -> list[int]:
    """Drop ranks that cannot be realised on this matrix.

    Rank k needs min(n, p) > k. Silently clipping two requested ranks to the
    same k would make the grid look like a comparison it is not.
    """
    cap = max(1, min(int(shape[0]), int(shape[1])) - 1)
    out: list[int] = []
    seen: set[int] = set()
    for raw in rank_grid:
        r = int(raw)
        if r < 1:
            raise ValueError(f"rank must be >= 1, got {raw!r}")
        if r > cap:
            continue
        if r not in seen:
            out.append(r)
            seen.add(r)
    if not out:
        out = [cap]
    return out


def reconstruct(U: np.ndarray, S: np.ndarray, Vt: np.ndarray) -> np.ndarray:
    """U * S @ Vt, the rank-k reconstruction."""
    return (U * S) @ Vt


def relative_reconstruction_error(
    matrix: np.ndarray, U: np.ndarray, S: np.ndarray, Vt: np.ndarray
) -> float:
    denom = float(np.linalg.norm(matrix, ord="fro"))
    if denom == 0.0:
        return 0.0
    residual = matrix - reconstruct(U, S, Vt)
    return float(np.linalg.norm(residual, ord="fro") / denom)


def factorize(
    matrix: np.ndarray, rank: int, spec: FactorizationSpec | None = None
) -> FactorizationResult:
    """Leading ``rank`` components of ``matrix``.

    ``matrix`` is whatever the caller wants to factorise -- the benchmark
    passes a gene-centred response matrix. This function does not centre,
    mask, or reorder genes.
    """
    spec = spec or FactorizationSpec()
    A = np.asarray(matrix, dtype=np.float64)
    if A.ndim != 2:
        raise ValueError(f"expected a 2-d array, got shape {A.shape}")
    n_rows, n_cols = int(A.shape[0]), int(A.shape[1])
    if min(n_rows, n_cols) < 2:
        raise ValueError("need at least two rows and two columns for a truncated SVD")
    k = max(1, min(int(rank), min(n_rows, n_cols) - 1))
    if spec.method == "exact":
        return _exact(A, k, spec, fallback=None)
    return _randomized(A, k, spec)


def _exact(
    A: np.ndarray, k: int, spec: FactorizationSpec, fallback: str | None
) -> FactorizationResult:
    U, S, Vt = np.linalg.svd(A, full_matrices=False)
    return FactorizationResult(
        U=np.ascontiguousarray(U[:, :k]),
        S=np.ascontiguousarray(S[:k]),
        Vt=np.ascontiguousarray(Vt[:k]),
        k=k,
        spec=spec,
        method_used="exact",
        fallback=fallback,
        n_rows=int(A.shape[0]),
        n_cols=int(A.shape[1]),
        sketch_size=None,
    )


def _randomized(A: np.ndarray, k: int, spec: FactorizationSpec) -> FactorizationResult:
    """Halko et al. 2011, Alg. 4.4 with QR subspace iteration (Alg. 4.3)."""
    n_rows, n_cols = int(A.shape[0]), int(A.shape[1])
    sketch = k + int(spec.n_oversamples)
    cap = min(n_rows, n_cols)
    if sketch >= cap:
        # A sketch as wide as the matrix is a full SVD with extra work.
        return _exact(
            A, k, spec,
            fallback=(
                f"sketch size {sketch} >= min(shape) {cap}; exact SVD is the "
                "cheaper exact answer"
            ),
        )
    rng = np.random.default_rng(spec.seed)
    omega = rng.standard_normal((n_cols, sketch))
    sample = A @ omega
    Q, _ = np.linalg.qr(sample, mode="reduced")
    n_iter = int(spec.n_iter)
    for _ in range(n_iter):
        Q, _ = np.linalg.qr(A.T @ Q, mode="reduced")
        Q, _ = np.linalg.qr(A @ Q, mode="reduced")
    B = Q.T @ A
    Uhat, S, Vt = np.linalg.svd(B, full_matrices=False)
    U = Q @ Uhat
    return FactorizationResult(
        U=np.ascontiguousarray(U[:, :k]),
        S=np.ascontiguousarray(S[:k]),
        Vt=np.ascontiguousarray(Vt[:k]),
        k=k,
        spec=spec,
        method_used="randomized",
        fallback=None,
        n_rows=n_rows,
        n_cols=n_cols,
        sketch_size=sketch,
    )
