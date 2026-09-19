"""Effect predictors conditioned on the target and on the cell context (2026-09-18).

The question: can a model LEARN how a knockdown's response depends on the target and on
the context, instead of transferring a signature with a fixed amplitude? Two predictors
share every input and differ only in capacity:

* `ConditionedNet` -- a gene-wise transfer gate plus a bilinear target x gene term, both
  conditioned on the context (numpy, trained with the project's Adam);
* `ConditionedRidge` -- the same inputs with the nonlinearities removed: a linear gate and a
  multi-output ridge.

How the context enters, and why. In CP-0013 a context-level vector (NTC statistics) fed to a
compact MLP made it much worse: with two training contexts it is an interpolation between two
points. Here the context enters PER GENE: each output gene carries its basal expression in the
query context's controls and in the source context (K562), so every training context supplies
thousands of examples of how a response depends on the basal state. The target carries its
own basal expression in both. Nothing here reads a perturbed cell of the query context.

Target descriptors, and which are allowed when (the modes of `benchmark/protocol.py`):

* ``src``  -- the target's own K562 response (mode A only: the target was perturbed in the
  source). Masked when absent, and always masked on K562 rows, where it would be the answer;
* ``nbr``  -- the mean source response of the target's STRING physical partners that are
  training targets. Built from other genes' labels, never from the target's: available for a
  gene no screen ever perturbed (mode B), which is what "unseen target" requires;
* ``basal_q``, ``basal_src`` -- the target's log CPM in the query and source controls.

Response codes are projections on a PCA basis fitted on the TRAINING source rows only.
"""

from __future__ import annotations

import gzip
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

__all__ = [
    "log_cpm",
    "string_partners",
    "neighbour_mean",
    "PairBlock",
    "Encoder",
    "ConditionedNet",
    "ConditionedRidge",
]


def log_cpm(fraction: np.ndarray) -> np.ndarray:
    """log1p of counts per million from a pooled fraction of counts."""
    return np.log1p(np.asarray(fraction, dtype=np.float64) * 1e6)


def string_partners(links: Path, info: Path, *, min_score: int = 400) -> dict[str, set[str]]:
    """Symbol -> symbols it has a STRING physical link to, at `combined_score >= min_score`."""
    name = {}
    with gzip.open(info, "rt", encoding="utf-8") as f:
        next(f)
        for line in f:
            pid, sym = line.split("\t", 2)[:2]
            name[pid] = sym
    out: dict[str, set[str]] = {}
    with gzip.open(links, "rt", encoding="utf-8") as f:
        next(f)
        for line in f:
            a, b, s = line.split()
            if int(s) < min_score:
                continue
            sa, sb = name.get(a), name.get(b)
            if sa and sb and sa != sb:
                out.setdefault(sa, set()).add(sb)
                out.setdefault(sb, set()).add(sa)
    return out


def neighbour_mean(targets: list[str], partners: dict[str, set[str]], labels: dict[str, np.ndarray],
                   n_genes: int) -> tuple[np.ndarray, np.ndarray]:
    """Mean label of each target's partners that HAVE a label (the target's own never counts)."""
    out = np.zeros((len(targets), n_genes), dtype=np.float32)
    count = np.zeros(len(targets), dtype=np.int32)
    for i, t in enumerate(targets):
        ps = [p for p in partners.get(t, ()) if p != t and p in labels]
        if ps:
            out[i] = np.mean([labels[p] for p in ps], axis=0)
            count[i] = len(ps)
    return out, count


@dataclass
class PairBlock:
    """Every (target, context) pair of one context, with its inputs and (if known) its labels.

    ``y_src``/``nbr`` are on the gene universe; ``phi`` is the per-gene context block
    (basal in query, basal in source, their difference); ``y`` may be None at prediction.
    """

    context: str
    targets: list[str]
    y_src: np.ndarray            # (n, G) source response, zero where masked
    m_src: np.ndarray            # (n,) 1 if y_src is usable
    nbr: np.ndarray              # (n, G) neighbour mean response
    m_nbr: np.ndarray            # (n,) 1 if the target has a labelled partner
    basal_q_t: np.ndarray        # (n,) target log CPM in the query controls
    basal_src_t: np.ndarray      # (n,) target log CPM in the source controls
    phi: np.ndarray              # (G, 3) per-gene context features
    y: np.ndarray | None = None  # (n, G) labels

    def __post_init__(self) -> None:
        n = len(self.targets)
        for name in ("y_src", "nbr"):
            if getattr(self, name).shape[0] != n:
                raise ValueError(f"{name} has {getattr(self, name).shape[0]} rows for {n} targets")
        if self.y is not None and self.y.shape != self.y_src.shape:
            raise ValueError("labels and source responses are not on the same grid")

    def subset(self, keep) -> "PairBlock":
        idx = np.asarray([i for i, t in enumerate(self.targets) if t in set(keep)], dtype=int)
        return PairBlock(self.context, [self.targets[i] for i in idx], self.y_src[idx], self.m_src[idx],
                         self.nbr[idx], self.m_nbr[idx], self.basal_q_t[idx], self.basal_src_t[idx], self.phi,
                         None if self.y is None else self.y[idx])

    def with_context(self, phi: np.ndarray, basal_q_t: np.ndarray, context: str) -> "PairBlock":
        """The same targets, seen through another context's controls (the context ablation)."""
        return PairBlock(context, self.targets, self.y_src, self.m_src, self.nbr, self.m_nbr, basal_q_t,
                         self.basal_src_t, phi, self.y)


@dataclass
class Encoder:
    """Turns a PairBlock into the target-side design matrix. Fitted on training blocks only."""

    k: int = 32
    basis: np.ndarray | None = None          # (G, k) PCA of training source labels
    center: np.ndarray | None = None         # (G,)
    x_mean: np.ndarray | None = None
    x_std: np.ndarray | None = None
    phi_mean: np.ndarray | None = None
    phi_std: np.ndarray | None = None
    info: dict = field(default_factory=dict)

    def fit(self, source_labels: np.ndarray, blocks: list[PairBlock], *, max_rows: int = 3000,
            seed: int = 0) -> "Encoder":
        """PCA of the TRAINING source labels (a random subset of rows, for cost) and the
        standardisation of the training design. Nothing from a test row enters."""
        y = np.asarray(source_labels, dtype=np.float64)
        self.center = y.mean(axis=0)
        rows = np.random.default_rng(seed).permutation(y.shape[0])[:max_rows]
        _, s, vt = np.linalg.svd(y[rows] - self.center, full_matrices=False)
        self.basis = vt[: self.k].T
        self.info = {"n_source_rows": int(y.shape[0]), "pca_rows": int(rows.size),
                     "var_explained_on_pca_rows": float((s[: self.k] ** 2).sum() / (s ** 2).sum())}
        raw = np.vstack([self._raw(b) for b in blocks])
        self.x_mean, self.x_std = raw.mean(axis=0), raw.std(axis=0) + 1e-6
        phis = np.vstack([b.phi for b in blocks])
        self.phi_mean, self.phi_std = phis.mean(axis=0), phis.std(axis=0) + 1e-6
        return self

    def _code(self, y: np.ndarray, m: np.ndarray) -> np.ndarray:
        return ((y - self.center) @ self.basis) * m[:, None]

    def _raw(self, b: PairBlock) -> np.ndarray:
        return np.hstack([self._code(b.y_src, b.m_src), b.m_src[:, None], self._code(b.nbr, b.m_nbr),
                          b.m_nbr[:, None], b.basal_q_t[:, None], b.basal_src_t[:, None]])

    def x(self, b: PairBlock) -> np.ndarray:
        return (self._raw(b) - self.x_mean) / self.x_std

    def phi(self, b: PairBlock) -> np.ndarray:
        return (b.phi - self.phi_mean) / self.phi_std


def _sigmoid(z):
    return 1.0 / (1.0 + np.exp(-np.clip(z, -30, 30)))


class _Adam:
    """Adam, byte for byte as it was in `benchmark/models.py`.

    It lived there because the four pseudobulk decoders shared it. Those decoders are
    archived (`docs/ARCHIVIO_CODICE.md`, tag archivio/pre-pulizia-2026-09-19) and this
    is now its only caller, so the class moved here rather than keep the whole module
    alive for twenty lines. Copied without a single change: the training of stage 92
    has to take the same steps it took before.
    """

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


class ConditionedNet:
    """pred[t, g] = gate(phi_g) * y_src[t, g] * m_src[t] + u(x_t) . v(g, phi_g).

    gate: phi (3) -> hidden -> 1, as 2*sigmoid, so it starts at 1 (plain transfer) and can damp
    or amplify each gene by how its basal state differs between query and source; u: target MLP;
    v = E_g + phi_g W_v: a learned embedding per OUTPUT gene (the decoder), shifted by the context.
    """

    def __init__(self, n_in: int, n_genes: int, *, hidden: int = 64, k: int = 16, gate_hidden: int = 16,
                 seed: int = 0) -> None:
        rng = np.random.default_rng(seed)
        self.p = {
            "W1": rng.normal(0, np.sqrt(2.0 / n_in), (n_in, hidden)), "b1": np.zeros(hidden),
            "W2": rng.normal(0, np.sqrt(1.0 / hidden), (hidden, k)), "b2": np.zeros(k),
            "E": rng.normal(0, 0.01, (n_genes, k)), "Wv": rng.normal(0, 0.01, (3, k)),
            "G1": rng.normal(0, np.sqrt(2.0 / 3), (3, gate_hidden)), "g1": np.zeros(gate_hidden),
            "G2": np.zeros((gate_hidden, 1)), "g2": np.zeros(1),
        }
        self.config = {"hidden": hidden, "k": k, "gate_hidden": gate_hidden, "seed": seed}

    def forward(self, x, phi, y_src, m_src, cache: bool = False):
        p = self.p
        h1 = x @ p["W1"] + p["b1"]
        a1 = np.maximum(h1, 0.0)
        u = a1 @ p["W2"] + p["b2"]
        v = p["E"] + phi @ p["Wv"]
        gh = phi @ p["G1"] + p["g1"]
        ga = np.maximum(gh, 0.0)
        gate = 2.0 * _sigmoid(ga @ p["G2"] + p["g2"])[:, 0]
        src = y_src * m_src[:, None]
        pred = gate[None, :] * src + u @ v.T
        if cache:
            return pred, (x, phi, h1, a1, u, v, gh, ga, gate, src)
        return pred

    def grads(self, dpred, c):
        x, phi, h1, a1, u, v, gh, ga, gate, src = c
        p = self.p
        g = {}
        dgate = (dpred * src).sum(axis=0)
        s = gate / 2.0
        dz = dgate * 2.0 * s * (1.0 - s)
        g["G2"] = ga.T @ dz[:, None]
        g["g2"] = np.array([dz.sum()])
        dga = dz[:, None] @ p["G2"].T
        dgh = dga * (gh > 0)
        g["G1"] = phi.T @ dgh
        g["g1"] = dgh.sum(axis=0)
        du = dpred @ v
        dv = dpred.T @ u
        g["E"] = dv
        g["Wv"] = phi.T @ dv
        g["W2"] = a1.T @ du
        g["b2"] = du.sum(axis=0)
        dh1 = (du @ p["W2"].T) * (h1 > 0)
        g["W1"] = x.T @ dh1
        g["b1"] = dh1.sum(axis=0)
        return g

    def loss_and_grads(self, x, phi, y_src, m_src, y):
        pred, c = self.forward(x, phi, y_src, m_src, cache=True)
        r = pred - y
        loss = float(np.mean(r ** 2))
        return loss, self.grads(2.0 * r / r.size, c)

    def fit(self, batches, val, *, lr: float = 3e-3, l2: float = 1e-4, steps: int = 3000, check_every: int = 100,
            patience: int = 5, log=None) -> dict:
        """`batches()` yields (x, phi, y_src, m_src, y); `val` is a list of such tuples."""
        names = list(self.p)
        opt = _Adam([self.p[n] for n in names], lr)
        best, best_p, bad, hist = np.inf, None, 0, []
        for step in range(1, steps + 1):
            x, phi, ys, ms, y = batches()
            _, g = self.loss_and_grads(x, phi, ys, ms, y)
            opt.step([g[n] for n in names], l2=l2)
            if step % check_every == 0:
                vl = float(np.mean([np.mean((self.forward(*v[:4]) - v[4]) ** 2) for v in val]))
                hist.append((step, vl))
                if log:
                    log(f"  step {step} val_mse {vl:.5f}")
                if vl < best - 1e-7:
                    best, best_p, bad = vl, {n: a.copy() for n, a in self.p.items()}, 0
                else:
                    bad += 1
                    if bad >= patience:
                        break
        if best_p is not None:
            for n in names:
                self.p[n][...] = best_p[n]
        return {"best_val_mse": best, "history": hist, "steps_run": step}

    def n_params(self) -> int:
        return int(sum(a.size for a in self.p.values()))


class ConditionedRidge:
    """The same inputs, linear: pred = src * (phi_aug(g) . a) + [x, 1] B, phi_aug = [1, phi].

    Fitted by alternating two closed-form steps -- the gate coefficients `a` by least squares on
    what B leaves, then B by ridge on what the gate leaves -- until they settle. A single pass
    estimates the gate with the target term as noise and biases it (measured by the test), which
    would weaken the baseline the network is compared against. The gate step needs only
    sum_t src^2 and sum_t src * residual per gene, never a (rows x genes x 4) design.
    """

    def __init__(self, alpha: float = 1.0, n_iter: int = 8) -> None:
        self.alpha = float(alpha)
        self.n_iter = int(n_iter)
        self.a = np.zeros(4)
        self.B = None
        self.config = {"alpha": self.alpha}

    @staticmethod
    def _aug(phi):
        return np.hstack([np.ones((phi.shape[0], 1)), phi])

    def fit(self, rows: list[tuple]) -> "ConditionedRidge":
        den = np.zeros((4, 4))
        for x, phi, ys, ms, y in rows:
            src = ys * ms[:, None]
            s2 = (src.astype(np.float64) ** 2).sum(axis=0)
            pa = self._aug(phi)
            den += pa.T @ (pa * s2[:, None])
        X = np.vstack([np.hstack([r[0], np.ones((r[0].shape[0], 1))]) for r in rows])
        reg = self.alpha * np.eye(X.shape[1])
        reg[-1, -1] = 0.0
        solve_b = np.linalg.solve(X.T @ X + reg, X.T)            # (d+1, N): reused every pass
        offsets = np.cumsum([0] + [r[0].shape[0] for r in rows])
        self.B = np.zeros((X.shape[1], rows[0][4].shape[1]))
        for _ in range(self.n_iter):
            if den[0, 0] > 0:
                num = np.zeros(4)
                for k, (x, phi, ys, ms, y) in enumerate(rows):
                    resid = y - X[offsets[k]:offsets[k + 1]] @ self.B
                    num += self._aug(phi).T @ ((ys * ms[:, None]) * resid).sum(axis=0)
                self.a = np.linalg.solve(den + 1e-9 * np.eye(4), num)
            R = np.vstack([r[4] - self._gate(r[1], r[2], r[3]) for r in rows])
            self.B = solve_b @ R
        return self

    def _gate(self, phi, y_src, m_src):
        return (y_src * m_src[:, None]) * (self._aug(phi) @ self.a)[None, :]

    def forward(self, x, phi, y_src, m_src):
        return self._gate(phi, y_src, m_src) + np.hstack([x, np.ones((x.shape[0], 1))]) @ self.B

    def n_params(self) -> int:
        return int(self.a.size + (0 if self.B is None else self.B.size))
