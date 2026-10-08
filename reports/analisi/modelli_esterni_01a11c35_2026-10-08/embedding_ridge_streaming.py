"""Gene-block masked ridge with mmap responses and bounded factor cache.

Same weighted objective and train-only feature scaling as embedding_ridge.py.
Response working arrays are R x gene_block, never the full R x G float64.
Features and coefficients still occupy O(RD + DG) RAM; preflight is required.
"""
from collections import OrderedDict

import numpy as np
from scipy.linalg import cho_factor, cho_solve

from embedding_ridge import MaskedRidge


class StreamingMaskedRidge(MaskedRidge):
    def fit(self, features, effects, mask, *, row_contexts, row_targets,
            excluded_contexts, excluded_targets, sample_weight=None,
            gene_block=64, factor_cache=2):
        if not isinstance(gene_block, int) or gene_block < 1 or factor_cache < 0:
            raise ValueError("positive gene block and nonnegative cache required")
        x = np.asarray(features, dtype=np.float64)
        if x.ndim != 2 or len(effects.shape) != 2 or effects.shape != mask.shape or len(x) != effects.shape[0]:
            raise ValueError("incompatible axes")
        if np.dtype(mask.dtype) != np.dtype(bool) or not np.isfinite(x).all():
            raise ValueError("invalid features or mask")
        if len(row_contexts) != len(x) or len(row_targets) != len(x):
            raise ValueError("row metadata mismatch")
        if set(row_contexts) & set(excluded_contexts) or set(row_targets) & set(excluded_targets):
            raise ValueError("excluded labels reached fit")
        w = np.ones(len(x)) if sample_weight is None else np.asarray(sample_weight, dtype=float)
        if not len(x) or w.shape != (len(x),) or not np.isfinite(w).all() or np.any(w <= 0):
            raise ValueError("positive finite weights and nonempty training required")
        self.feature_mean = np.average(x, axis=0, weights=w)
        self.feature_scale = np.sqrt(np.average((x-self.feature_mean)**2, axis=0, weights=w))
        self.feature_scale[self.feature_scale < 1e-12] = 1.0
        x = (x-self.feature_mean)/self.feature_scale
        n_genes = effects.shape[1]
        self.coef = np.zeros((x.shape[1], n_genes))
        self.intercept = np.zeros(n_genes)
        self.generic = np.zeros(n_genes)
        self.support = np.zeros(n_genes, dtype=bool)
        counts, weighted = np.zeros(n_genes, dtype=np.int64), np.zeros(n_genes)
        cache = OrderedDict()
        solves = hits = 0
        for start in range(0, n_genes, gene_block):
            stop = min(start+gene_block, n_genes)
            # Slicing happens before conversion: supports mmap and guarded readers.
            y = np.asarray(effects[:, start:stop], dtype=np.float64)
            m = np.asarray(mask[:, start:stop])
            if not np.isfinite(y[m]).all():
                raise ValueError("nonfinite observed response")
            counts[start:stop] = m.sum(axis=0)
            weighted[start:stop] = (m*w[:, None]).sum(axis=0)
            self.support[start:stop] = m.any(axis=0)
            groups = {}
            for j in range(stop-start):
                groups.setdefault(m[:, j].tobytes(), []).append(j)
            for key, cols in groups.items():
                observed = m[:, cols[0]]
                if not observed.any():
                    continue
                xg, wg = x[observed], w[observed]
                yg = y[np.ix_(observed, cols)]
                xm, ym = np.average(xg, axis=0, weights=wg), np.average(yg, axis=0, weights=wg)
                root = np.sqrt(wg/wg.sum())[:, None]
                a, b = (xg-xm)*root, (yg-ym)*root
                dual = a.shape[0] < a.shape[1]
                if key in cache:
                    factor = cache.pop(key)
                    hits += 1
                else:
                    gram = a@a.T if dual else a.T@a
                    gram.flat[::len(gram)+1] += self.alpha
                    factor = cho_factor(gram, check_finite=False)
                    solves += 1
                if factor_cache:
                    cache[key] = factor
                    while len(cache) > factor_cache:
                        cache.popitem(last=False)
                coef = a.T@cho_solve(factor, b, check_finite=False) if dual else cho_solve(factor, a.T@b, check_finite=False)
                columns = start+np.asarray(cols)
                self.coef[:, columns] = coef
                self.intercept[columns] = ym-xm@coef
                self.generic[columns] = ym
        self.receipt = dict(rows_read=len(x), contexts_read=sorted(set(row_contexts)),
                            targets_read=sorted(set(row_targets)), observed_per_gene=counts.tolist(),
                            weighted_observations_per_gene=weighted.tolist(), alpha=self.alpha,
                            uses_context=False, gene_block=gene_block, factor_cache=factor_cache,
                            factorizations=solves, cache_hits=hits,
                            maximum_response_columns=min(gene_block, n_genes),
                            full_response_float64_materialized=n_genes <= gene_block)
        return self
