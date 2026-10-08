"""Exact target-only ridge via weighted sufficient statistics, in bounded blocks.

Response rows remain separate scientific observations. Aggregation here is only
an algebraic reduction of an already frozen quadratic loss, after masks, weights
and fold exclusions. It is not pooling counts, creating a bank or re-shrinking.
"""
from collections import Counter, OrderedDict

import numpy as np
from scipy.linalg import cho_factor, cho_solve

from embedding_ridge import MaskedRidge
from pie_adapter import unique


class TargetSufficientRidge(MaskedRidge):
    def fit(self, features, effects, mask, *, feature_targets, row_feature_indices,
            row_contexts, row_targets, excluded_contexts, excluded_targets,
            sample_weight=None, gene_block=64, row_block=128, factor_cache=2):
        for name, value, minimum in (("gene_block",gene_block,1),("row_block",row_block,1),
                                     ("factor_cache",factor_cache,0)):
            if not isinstance(value,int) or isinstance(value,bool) or value < minimum:
                raise ValueError(f"invalid {name}")
        feature_targets = unique(feature_targets, "feature targets")
        x = np.asarray(features, dtype=np.float64)
        indices = np.asarray(row_feature_indices)
        if x.ndim != 2 or len(x) != len(feature_targets) or not np.isfinite(x).all():
            raise ValueError("invalid unique-target features")
        if len(effects.shape) != 2 or effects.shape != mask.shape or np.dtype(mask.dtype) != bool:
            raise ValueError("response axes/mask mismatch")
        n, g = effects.shape
        if not n or not g or indices.shape != (n,) or not np.issubdtype(indices.dtype,np.integer):
            raise ValueError("nonempty rows/genes and integer row-feature map required")
        if np.any(indices < 0) or np.any(indices >= len(x)):
            raise ValueError("row-feature index outside axis")
        if len(row_contexts) != n or len(row_targets) != n:
            raise ValueError("row metadata mismatch")
        if any(feature_targets[int(i)] != target for i,target in zip(indices,row_targets)):
            raise ValueError("target identifiers disagree with row-feature map")
        if set(row_contexts) & set(excluded_contexts) or set(row_targets) & set(excluded_targets):
            raise ValueError("excluded labels reached fit")
        w = np.ones(n) if sample_weight is None else np.asarray(sample_weight,dtype=np.float64)
        if w.shape != (n,) or not np.isfinite(w).all() or np.any(w <= 0) or not np.isfinite(w.sum()):
            raise ValueError("positive finite row weights and total required")
        # Statistics of the original rows; repeated targets retain all row weights.
        total_by_target = np.bincount(indices,weights=w,minlength=len(x))
        if np.any(total_by_target <= 0):
            raise ValueError("unique feature table must contain exactly the consumed targets")
        self.feature_mean = np.average(x,axis=0,weights=total_by_target)
        self.feature_scale = np.sqrt(np.average((x-self.feature_mean)**2,axis=0,weights=total_by_target))
        self.feature_scale[self.feature_scale < 1e-12] = 1.0
        x = (x-self.feature_mean)/self.feature_scale
        self.coef = np.zeros((x.shape[1],g))
        self.intercept = np.zeros(g)
        self.generic = np.zeros(g)
        self.support = np.zeros(g,dtype=bool)
        counts, weighted = np.zeros(g,dtype=np.int64), np.zeros(g)
        cache = OrderedDict()
        factorizations = hits = blocks_read = 0
        for start in range(0,g,gene_block):
            stop = min(g,start+gene_block)
            # These two statistics are U x B, independent of the number of contexts.
            weight_sum = np.zeros((len(x),stop-start))
            response_sum = np.zeros_like(weight_sum)
            for row_start in range(0,n,row_block):
                row_stop = min(n,row_start+row_block)
                y = np.asarray(effects[row_start:row_stop,start:stop],dtype=np.float64)
                m = np.asarray(mask[row_start:row_stop,start:stop])
                expected = (row_stop-row_start,stop-start)
                if y.shape != expected or m.shape != expected or m.dtype != bool:
                    raise ValueError("block reader axes/mask differ")
                if not np.isfinite(y[m]).all():
                    raise ValueError("nonfinite observed response")
                wm = m*w[row_start:row_stop,None]
                np.add.at(weight_sum,indices[row_start:row_stop],wm)
                np.add.at(response_sum,indices[row_start:row_stop],wm*np.where(m,y,0.0))
                counts[start:stop] += m.sum(axis=0)
                blocks_read += 1
            weighted[start:stop] = weight_sum.sum(axis=0)
            self.support[start:stop] = weighted[start:stop] > 0
            groups = {}
            for j in range(stop-start):
                groups.setdefault(weight_sum[:,j].tobytes(),[]).append(j)
            for key,cols in groups.items():
                wg = weight_sum[:,cols[0]]
                active = wg > 0
                if not active.any():
                    continue
                wg = wg[active]
                xg = x[active]
                total = wg.sum()
                xm = np.average(xg,axis=0,weights=wg)
                sums = response_sum[np.ix_(active,cols)]
                ym = sums.sum(axis=0)/total
                # Weighted target means are an algebraic sufficient statistic only.
                root = np.sqrt(wg/total)[:,None]
                a = (xg-xm)*root
                b = (sums/wg[:,None]-ym)*root
                dual = a.shape[0] < a.shape[1]
                if key in cache:
                    factor = cache.pop(key)
                    hits += 1
                else:
                    gram = a@a.T if dual else a.T@a
                    gram.flat[::len(gram)+1] += self.alpha
                    factor = cho_factor(gram,check_finite=False)
                    factorizations += 1
                if factor_cache:
                    cache[key] = factor
                    while len(cache) > factor_cache:
                        cache.popitem(last=False)
                coef = a.T@cho_solve(factor,b,check_finite=False) if dual else cho_solve(factor,a.T@b,check_finite=False)
                columns = start+np.asarray(cols)
                self.coef[:,columns] = coef
                self.intercept[columns] = ym-xm@coef
                self.generic[columns] = ym
        self.receipt = dict(rows_read=n,unique_feature_targets=len(x),
                            contexts_read=sorted(set(row_contexts)),
                            rows_by_context_group=dict(Counter(row_contexts)),
                            targets_read=sorted(set(row_targets)),
                            observed_per_gene=counts.tolist(),weighted_observations_per_gene=weighted.tolist(),
                            total_row_weight=float(w.sum()),alpha=self.alpha,uses_context=False,
                            gene_block=gene_block,row_block=row_block,blocks_read=blocks_read,
                            factor_cache=factor_cache,factorizations=factorizations,cache_hits=hits,
                            expanded_row_features_materialized=False,
                            sufficient_statistics=["sum_row_weight_by_target_gene", "sum_weighted_response_by_target_gene"],
                            changes_to_bank_or_shrinkage=False)
        return self
