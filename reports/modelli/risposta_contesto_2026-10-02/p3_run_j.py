"""R-LEAD P3, regime J: new line AND new target; does the held-out line's controls improve a memoryless reference?

For each line group g and target fold f (sha256 folds of P1), every fit uses only groups other than g
and keys outside f, in every table. The reference ``embed`` is memoryless: a target is described by
the loading of its own gene on the basis of training responses (how that gene moves when OTHER genes
are knocked down), mapped to an effect by ridge; a target whose gene is off the cube genes gets the
common response. ``jm1`` adds the per-gene gains of `arms.LinearGain` read from the held-out controls;
``jm1_0`` the same gains without context; swaps, target permutation and five permuted-control nulls as in C.

Training rows of the gains use out-of-fold references: a row of group h in inner fold f' uses an
embedding (gene basis, common response and ridge map) refitted without h and without the keys of f'.
This is stricter than the approximation PROTOCOLLO.json declared (basis shared within an outer split):
tightened before any J result, after the external review of the inner selection of M2.

    py.cmd p3_run_j.py --cube <cube_r1> --protocol PROTOCOLLO.json --out <data>/.../p3_j_r1
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

from arms import (Cube, LinearGain, derangement, gain_features, gene_weight, group_mean, reference_basal)
from common import Timer, coords_path, data_root, git_state, log, now_utc, sha256, write_json
from metrics import blocks_of, score_table
from splits import Split, assert_no_leak, target_fold, unit_hash

F32 = np.float32


def fold_means(cube: Cube, n_folds: int, block: int = 1000) -> dict:
    """Per table and fold: sums and counts of raw over usable rows, to get means without any fold."""
    out = {}
    for t in cube.tables:
        keys = cube.keys_of(t)
        folds = np.array([target_fold(k, n_folds) for k in keys])
        S = np.zeros((n_folds, len(cube.genes)))
        N = np.zeros((n_folds, len(cube.genes)))
        for b0 in range(0, len(keys), block):
            x, _ = cube.get(t, 'raw', keys[b0:b0 + block])
            ok = np.isfinite(x)
            fb = folds[b0:b0 + block]
            for f in range(n_folds):
                m = fb == f
                if m.any():
                    S[f] += np.where(ok[m], x[m], 0).sum(0)
                    N[f] += ok[m].sum(0)
        out[t] = (S, N)
    return out


def generic_without(cube: Cube, fm: dict, exclude_groups: set, fold: int) -> np.ndarray:
    parts = []
    for g in cube.groups:
        if g in exclude_groups:
            continue
        vals = []
        for t in cube.tables_of(g):
            S, N = fm[t]
            s = S.sum(0) - S[fold]
            n = N.sum(0) - N[fold]
            vals.append(np.divide(s, n, out=np.full(len(cube.genes), np.nan), where=n > 0))
        parts.append(np.nanmean(np.vstack(vals), 0))
    return np.nanmean(np.vstack(parts), 0).astype(F32)


class RawGroupMeans:
    """Within-group reliability-weighted raw means for a fixed key list, computed once per key list."""

    def __init__(self, cube: Cube, keys: list[str]):
        self.cube, self.keys = cube, keys
        self.gm = {h: group_mean(cube, h, keys, {}, gamma=0.0, kind='raw').astype(np.float16) for h in cube.groups}

    def pooled(self, groups: list[str], held: str) -> np.ndarray:
        if held in groups:
            raise AssertionError(f'pooled responses would include the held-out group {held}')
        tot = np.zeros((len(self.keys), len(self.cube.genes)), F32)
        cnt = np.zeros(tot.shape, np.int8)
        for h in groups:
            x = self.gm[h].astype(F32)
            ok = np.isfinite(x)
            tot += np.where(ok, x, 0)
            cnt += ok
        return np.divide(tot, cnt, out=np.full_like(tot, np.nan), where=cnt > 0)


class Embed:
    """Memoryless reference: b + V A z_t, with z_t the target gene's row of V."""

    def __init__(self, Y: np.ndarray, gene_pos: np.ndarray, k: int, ridge: float):
        self.b = np.nanmean(Y, 0)
        self.b = np.nan_to_num(self.b, nan=0.0).astype(F32)
        X = np.nan_to_num(Y - self.b, nan=0.0).astype(np.float64)
        vals, vecs = np.linalg.eigh(X @ X.T)
        top = np.argsort(vals)[::-1][:k]
        top = top[vals[top] > vals.max() * 1e-9]
        self.V = ((X.T @ vecs[:, top]) / np.sqrt(vals[top])[None, :]).astype(F32)
        self.k, self.ridge = self.V.shape[1], ridge
        self.C = (X @ self.V).astype(F32)            # projected responses of the training keys
        self.Z = self.descriptors(gene_pos)

    def descriptors(self, gene_pos: np.ndarray) -> np.ndarray:
        z = np.zeros((len(gene_pos), self.k), F32)
        ok = gene_pos >= 0
        z[ok] = self.V[gene_pos[ok]]
        return z

    def fit_map(self, rows: np.ndarray) -> np.ndarray:
        Z, C = self.Z[rows].astype(np.float64), self.C[rows].astype(np.float64)
        G = Z.T @ Z
        reg = self.ridge * max(np.trace(G), 1e-12) / self.k
        return np.linalg.solve(G + reg * np.eye(self.k), Z.T @ C).T.astype(F32)     # (k, k): c = A z

    def specific(self, A: np.ndarray, z: np.ndarray) -> np.ndarray:
        return (z @ A.T) @ self.V.T


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--cube', type=Path, required=True)
    p.add_argument('--protocol', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--groups', nargs='*', default=None)
    p.add_argument('--folds', nargs='*', type=int, default=None)
    p.add_argument('--max-train-keys', type=int, default=1200)
    p.add_argument('--fit-keys-per-group', type=int, default=300)
    a = p.parse_args()
    if a.out.exists():
        raise FileExistsError(a.out)
    proto = json.loads(a.protocol.read_text(encoding='utf-8'))
    P = proto['parameters']
    nf = P['n_folds']
    timer = Timer()
    cube = Cube(a.cube, min_cells=P['min_cells'])
    keys_info = pd.read_csv(a.cube / 'keys.csv').set_index('target_key')
    coords = pd.read_csv(coords_path(P['gene_coordinates']), sep='\t')
    ens_to_sym = {str(gid).split('.')[0]: s for s, gid in zip(coords['symbol'], coords['gene_id']) if isinstance(gid, str)}
    a.out.mkdir(parents=True)
    all_keys = sorted({k for t in cube.tables for k in cube.keys_of(t)})
    fold_of = {k: target_fold(k, nf) for k in all_keys}
    fm = fold_means(cube, nf)
    swap = derangement(cube.groups, 'swap')
    leak_checks, fits = {}, {}
    for f in (a.folds if a.folds is not None else range(nf)):
        # one key sample per fold: training keys outside f, by stable hash (shared by every held group)
        pool = sorted([k for k in all_keys if fold_of[k] != f], key=lambda k: unit_hash(k, f'j-train:{f}'))
        train_keys = pool[:a.max_train_keys]
        if any(fold_of[k] == f for k in train_keys):
            raise AssertionError('a held-fold key entered the J training sample')
        rgm = RawGroupMeans(cube, train_keys)
        tpos_train = cube.target_gene_positions(train_keys, ens_to_sym)
        log(f'fold {f}: raw group means of {len(train_keys)} training keys ({timer()} s)')
        for g in (a.groups or cube.groups):
            cube.reads.clear()
            split = Split('J', g, f, nf)
            assert_no_leak(cube.training_rows(split), split, 'every J arm (shared training rows)')
            train_groups = [h for h in cube.groups if h != g]
            present = {h: np.isfinite(rgm.gm[h].astype(F32)).any(1) for h in train_groups}
            outer_rows = np.flatnonzero(np.any([present[h] for h in train_groups], axis=0))
            emb = Embed(rgm.pooled(train_groups, g)[outer_rows], tpos_train[outer_rows], P['j_embed_k'], P['j_embed_ridge'])
            A_outer = emb.fit_map(np.arange(len(outer_rows)))
            m_g = generic_without(cube, fm, {g}, f)
            # ---- gain training rows with out-of-fold references
            jm1 = LinearGain(True, P['m1_ridge'])
            jm0 = LinearGain(False, P['m1_ridge'])
            order = sorted(train_groups)
            perms = [{order[i]: order[(i + r) % len(order)] for i in range(len(order))} for r in range(1, len(order))]
            nulls = [LinearGain(True, P['m1_ridge']) for _ in perms]
            for h in train_groups:
                rows_h = np.flatnonzero(np.any([present[x] for x in train_groups if x != h], axis=0))
                pooled_h = rgm.pooled([x for x in train_groups if x != h], g)[rows_h]
                keys_h = [train_keys[i] for i in rows_h]
                tpos_h = tpos_train[rows_h]
                fit_idx = [i for i in np.argsort([unit_hash(k, f'j-fit:{h}') for k in keys_h])
                           if present[h][rows_h[i]]][:a.fit_keys_per_group]
                xref = reference_basal(cube, {g, h})
                for f2 in range(nf):
                    if f2 == f:
                        continue
                    sel = [i for i in fit_idx if fold_of[keys_h[i]] == f2]
                    if not sel:
                        continue
                    # strict inner reference: basis, common response and map all fitted without fold f2
                    tr = np.array([i for i in range(len(keys_h)) if fold_of[keys_h[i]] != f2])
                    emb_hf = Embed(pooled_h[tr], tpos_h[tr], P['j_embed_k'], P['j_embed_ridge'])
                    A = emb_hf.fit_map(np.arange(len(tr)))
                    s = emb_hf.specific(A, emb_hf.descriptors(tpos_h[sel]))
                    m_h = np.nan_to_num(emb_hf.b)
                    ks = [keys_h[i] for i in sel]
                    for t in cube.tables_of(h):
                        y, have = cube.get(t, 'raw', ks)
                        if not have.any():
                            continue
                        w = gene_weight(cube.basal[t])
                        jm1.add(y[have], s[have], m_h, gain_features(cube.basal[t], xref, context=True), w)
                        jm0.add(y[have], s[have], m_h, gain_features(cube.basal[t], xref, context=False), w)
                        for nl, sh in zip(nulls, perms):
                            tp = cube.tables_of(sh[h])[0]
                            nl.add(y[have], s[have], m_h, gain_features(cube.basal[tp], xref, context=True), w)
            for mdl in [jm1, jm0] + nulls:
                mdl.solve()
            fits[f'{g}:f{f}'] = dict(jm1=jm1.coef.tolist(), jm1_0=jm0.coef.tolist(), rows=jm1.n,
                                     embed_k=emb.k, train_keys=len(outer_rows))
            # ---- held-out targets of fold f
            xref_g = reference_basal(cube, {g})
            swap_table = cube.tables_of(swap[g])[0]
            records = []
            for e in cube.tables_of(g):
                keys = [k for k in cube.keys_of(e) if fold_of[k] == f]
                for blk in blocks_of(keys, P['pds_block']):
                    bkeys = [keys[i] for i in blk]
                    if len(bkeys) < 2:
                        continue
                    truth, _ = cube.get(e, 'raw', bkeys, purpose='truth')
                    se, _ = cube.get(e, 'se', bkeys, purpose='truth')
                    w = gene_weight(cube.basal[e])
                    tpos = cube.target_gene_positions(bkeys, ens_to_sym)
                    z = emb.descriptors(tpos)
                    s = emb.specific(A_outer, z)
                    perm = derangement(bkeys, f'tperm:{e}:{f}')
                    s_perm = s[[bkeys.index(perm[k]) for k in bkeys]]
                    f_true = gain_features(cube.basal[e], xref_g, context=True)
                    f_cf = gain_features(cube.basal[e], xref_g, context=False)
                    f_swap = gain_features(cube.basal[swap_table], xref_g, context=True)
                    arms = {'null': np.zeros_like(s), 'generic': np.broadcast_to(m_g, s.shape).copy(),
                            'embed': (emb.b[None, :] + s).astype(F32),
                            'jm1_0': jm0.predict(s, emb.b, f_cf), 'jm1': jm1.predict(s, emb.b, f_true),
                            'jm1_swap': jm1.predict(s, emb.b, f_swap), 'jm1_tperm': jm1.predict(s_perm, emb.b, f_true)}
                    for i, nl in enumerate(nulls):
                        arms[f'jm1_null{i + 1}'] = nl.predict(s, emb.b, f_true)
                    for name, pred in arms.items():
                        sc = score_table(pred, truth, se, w, bkeys, tpos, block_size=len(bkeys))
                        for i, kk in enumerate(bkeys):
                            records.append(dict(regime='J', held_group=g, fold=f, table=e, target_key=kk,
                                                stratum=keys_info['stratum'].get(kk, 'other'),
                                                target_gene_in_cube=bool(tpos[i] >= 0),
                                                n_cells=float(cube.cells(e, [kk])[0]), arm=name,
                                                **{m: float(v[i]) for m, v in sc.items()}))
            leaked = cube.fit_reads_of(g)
            leak_checks[f'{g}:f{f}'] = dict(fit_reads_of_held_group=leaked)
            if leaked:
                raise AssertionError(f'J {g} f{f}: a fit read the held-out tables {leaked}')
            pd.DataFrame(records).to_csv(a.out / f'per_target_J_{g}_f{f}.csv.gz', index=False, compression='gzip')
            log(f'J {g} f{f}: {len(records)} records ({timer()} s)')
        del rgm
    write_json(a.out / 'fits.json', fits)
    write_json(a.out / 'run.json', dict(written_utc=now_utc(), git=git_state(), protocol=str(a.protocol),
                                        protocol_sha256=sha256(a.protocol), cube=str(a.cube),
                                        cube_manifest_sha256=sha256(a.cube / 'manifest.json'), seconds=timer(),
                                        leak_checks=leak_checks, max_train_keys=a.max_train_keys,
                                        fit_keys_per_group=a.fit_keys_per_group,
                                        outputs={x.name: sha256(x) for x in sorted(a.out.glob('per_target_*.csv.gz'))}))
    log(f'done in {timer()} s')


if __name__ == '__main__':
    main()
