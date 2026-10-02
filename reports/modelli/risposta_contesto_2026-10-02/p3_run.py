"""R-LEAD P3, regime C: does a correction learned from the controls of a never-perturbed line beat transfer?

For every line group held out whole (all its studies, states and clones), every arm of `arms.py` is
fitted on the other groups only (`assert_no_leak` on the training rows of every arm) and scored on the
held-out tables with `metrics.score_table`, block by block (blocks of <= 300 targets, the PDS unit).
Corrections are fitted on out-of-fold transfers (no training row sees its own line).

Arms: null, generic, transfer (t25 recipe, amplitude 1.576), tm0 (context-free gains), m1 (per-gene
gains from the held-out controls), m1_swap (another group's controls), m1_tperm (another target's
shared effect), m1_null<r> (fitted with controls permuted across training groups, the run's own null),
m2_0 / m2 / m2_swap / m2_null<r> (low-rank bilinear, hyperparameters chosen by inner leave-one-group-out).

    py.cmd p3_run.py --cube <data>/processed/generalizzazione_contesti_2026-10-02/cube_r1 --protocol PROTOCOLLO.json
        --out <data>/processed/generalizzazione_contesti_2026-10-02/p3_c_r1
"""
from __future__ import annotations

import argparse
import itertools
import json
from pathlib import Path

import numpy as np
import pandas as pd

from arms import (AMPLITUDE_T25, BasalPCA, Cube, LinearGain, LowRankBilinear, combine_groups, derangement,
                  fit_keys, gain_features, gene_weight, generic_vector, group_mean, reference_basal, table_means)
from common import Timer, data_root, git_state, log, now_utc, sha256, write_json
from metrics import blocks_of, score_table
from splits import Split, assert_no_leak

F32 = np.float32


class GMCache:
    """Group means of fit keys, keyed by (source group, fit group): independent of the held-out group in C."""

    def __init__(self, cube: Cube, commons: dict, folder: Path):
        self.cube, self.commons, self.folder = cube, commons, folder
        folder.mkdir(parents=True, exist_ok=True)

    def get(self, src: str, keys: list[str], tag: str, held: str) -> np.ndarray:
        if src == held:
            raise AssertionError(f'group mean of the held-out group {held} requested')
        path = self.folder / f'{src}__{tag}.npy'
        if path.exists():
            return np.load(path).astype(F32)
        gm = group_mean(self.cube, src, keys, self.commons)
        np.save(path, gm.astype(np.float16))
        return gm


def transfer_for(cube: Cube, keys: list[str], groups: list[str], commons: dict) -> tuple[np.ndarray, np.ndarray]:
    return combine_groups([group_mean(cube, h, keys, commons) for h in groups])


def basis(rows: np.ndarray, k: int, max_rows: int = 2000) -> np.ndarray:
    """Top-k orthonormal gene directions of the training transfers (rows), via the row Gram matrix."""
    X = np.nan_to_num(rows, nan=0.0).astype(np.float64)
    if len(X) > max_rows:
        X = X[np.linspace(0, len(X) - 1, max_rows).astype(int)]
    X = X - X.mean(0, keepdims=True)
    vals, vecs = np.linalg.eigh(X @ X.T)
    top = np.argsort(vals)[::-1][:k]
    top = top[vals[top] > vals.max() * 1e-9]
    V = (X.T @ vecs[:, top]) / np.sqrt(vals[top])[None, :]
    return V.astype(F32)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--cube', type=Path, required=True)
    p.add_argument('--protocol', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--groups', nargs='*', default=None, help='held-out groups (default: all)')
    a = p.parse_args()
    if a.out.exists():
        raise FileExistsError(a.out)
    proto = json.loads(a.protocol.read_text(encoding='utf-8'))
    P = proto['parameters']
    timer = Timer()
    cube = Cube(a.cube, min_cells=P['min_cells'])
    keys_info = pd.read_csv(a.cube / 'keys.csv').set_index('target_key')
    coords = pd.read_csv(data_root() / P['gene_coordinates'], sep='\t')
    ens_to_sym = {str(gid).split('.')[0]: s for s, gid in zip(coords['symbol'], coords['gene_id']) if isinstance(gid, str)}
    a.out.mkdir(parents=True)
    log(f'cube: {len(cube.tables)} tables, {len(cube.groups)} groups, {len(cube.genes)} genes')
    all_split = Split('C', '__none__', None, P['n_folds'])
    commons, raw_means = table_means(cube, all_split)
    gm = GMCache(cube, commons, a.out / 'gm_cache')
    swap = derangement(cube.groups, 'swap')
    fits, leak_checks = {}, {}
    held_groups = a.groups or cube.groups
    for g in held_groups:
        records = []
        cube.reads.clear()
        split = Split('C', g, None, P['n_folds'])
        train_groups = [h for h in cube.groups if h != g]
        rows = cube.training_rows(split)
        assert_no_leak(rows, split, 'every arm (shared training rows)')
        # ---- training rows for the corrections: out-of-fold transfers
        fitdata = {}
        for h in train_groups:
            K = fit_keys(cube, h, split, P['n_fit'])
            others = [x for x in train_groups if x != h]
            parts = [gm.get(x, K, f'fit_{h}', g) for x in others]
            s, support = combine_groups(parts)
            keep = support > 0
            K = [k for k, kk in zip(K, keep) if kk]
            fitdata[h] = dict(keys=K, s=s[keep], parts_groups=others,
                              parts=[pp[keep] for pp in parts])
        stack = np.vstack([fd['s'] for fd in fitdata.values()])
        U = basis(stack * AMPLITUDE_T25, max(P['m2_k_grid']))
        del stack
        # ---- accumulate M1 statistics and M2 projections
        m1 = LinearGain(True, P['m1_ridge'])
        tm0 = LinearGain(False, P['m1_ridge'])
        perms = []
        order = sorted(train_groups)
        for r in range(1, len(order)):
            shift = {order[i]: order[(i + r) % len(order)] for i in range(len(order))}
            perms.append(shift)
        nulls = [LinearGain(True, P['m1_ridge']) for _ in perms]
        proj = []
        for h in train_groups:
            fd = fitdata[h]
            others = [x for x in train_groups if x != h]
            m_h = generic_vector(cube, raw_means, {g, h})
            xref = reference_basal(cube, {g, h})
            s = fd['s'] * AMPLITUDE_T25
            for t in cube.tables_of(h):
                y, have = cube.get(t, 'raw', fd['keys'])
                if not have.any():
                    continue
                yy, ss = y[have], s[have]
                w = gene_weight(cube.basal[t])
                m1.add(yy, ss, m_h, gain_features(cube.basal[t], xref, context=True), w)
                tm0.add(yy, ss, m_h, gain_features(cube.basal[t], xref, context=False), w)
                for nl, shift in zip(nulls, perms):
                    tp = cube.tables_of(shift[h])[0]
                    nl.add(yy, ss, m_h, gain_features(cube.basal[tp], xref, context=True), w)
                s0 = np.nan_to_num(ss, nan=0.0)
                resid = np.nan_to_num(yy - np.where(np.isfinite(ss), ss, 0.0), nan=0.0)
                proj.append(dict(group=h, table=t, z=s0 @ U, r=resid @ U,
                                 rr=(resid.astype(np.float64) ** 2).sum(1)))
        m1.solve()
        tm0.solve()
        for nl in nulls:
            nl.solve()
        # ---- M2: inner leave-one-group-out selection of (k, d, ridge) on full-gene error reduction
        def m2_fit(groups_in, k, d, ridge, pca, phi_override=None):
            model = LowRankBilinear(U[:, :k], d, ridge)
            for pr in proj:
                if pr['group'] not in groups_in:
                    continue
                phi = pca.coords(cube.basal[phi_override.get(pr['table'], pr['table']) if phi_override else pr['table']])[:d] \
                    if d else np.zeros(0, F32)
                model.add(pr['r'][:, :k], pr['z'][:, :k], phi)
            model.solve()
            return model

        def m2_gain(model, pr, k, d, pca):
            phi = pca.coords(cube.basal[pr['table']])[:d] if d else np.zeros(0, F32)
            corr = model._u(pr['z'][:, :k], phi) @ model.theta        # (R, k) projected correction
            return float((2 * (corr * pr['r'][:, :k]).sum(1) - (corr ** 2).sum(1)).sum())

        grid = list(itertools.product(P['m2_k_grid'], P['m2_d_grid'], P['m2_ridge_grid']))
        inner = {cfg: 0.0 for cfg in grid}
        for v in train_groups:
            fit_groups = [x for x in train_groups if x != v]
            pcas = {d: BasalPCA(cube, fit_groups, max(d, 1)) for d in P['m2_d_grid']}
            for (k, d, ridge) in grid:
                mdl = m2_fit(set(fit_groups), k, d, ridge, pcas[d])
                inner[(k, d, ridge)] += sum(m2_gain(mdl, pr, k, d, pcas[d]) for pr in proj if pr['group'] == v)
        best = max(grid, key=lambda c: inner[c])
        k, d, ridge = best
        pca = BasalPCA(cube, train_groups, max(d, 1))
        m2 = m2_fit(set(train_groups), k, d, ridge, pca)
        m2_0 = m2_fit(set(train_groups), k, 0, ridge, pca)
        m2_nulls = []
        for shift in perms:
            override = {t: cube.tables_of(shift[cube.group[t]])[0] for t in cube.tables if cube.group[t] in shift}
            m2_nulls.append(m2_fit(set(train_groups), k, d, ridge, pca, override))
        fits[g] = dict(m1_coef=m1.coef.tolist(), tm0_coef=tm0.coef.tolist(), m1_rows=m1.n,
                       m1_null_coefs=[nl.coef.tolist() for nl in nulls],
                       m2_choice=dict(k=k, d=d, ridge=ridge), m2_inner={str(c): v for c, v in inner.items()},
                       pca_explained=pca.explained, fit_keys={h: len(fd['keys']) for h, fd in fitdata.items()},
                       swap_group=swap[g], permutations=[{k2: v2 for k2, v2 in sh.items()} for sh in perms])
        log(f'{g}: fits done (m2 k={k} d={d} ridge={ridge}) ({timer()} s)')
        # ---- predictions on the held-out tables, block by block
        m_g = generic_vector(cube, raw_means, {g})
        xref_g = reference_basal(cube, {g})
        swap_table = cube.tables_of(swap[g])[0]
        for e in cube.tables_of(g):
            keys = cube.keys_of(e)
            for blk in blocks_of(keys, P['pds_block']):
                bkeys = [keys[i] for i in blk]
                s, support = transfer_for(cube, bkeys, train_groups, commons)
                keep = support > 0
                if not keep.any():
                    continue
                bkeys = [kk for kk, kp in zip(bkeys, keep) if kp]
                s = s[keep] * AMPLITUDE_T25
                truth, _ = cube.get(e, 'raw', bkeys, purpose='truth')
                se, _ = cube.get(e, 'se', bkeys, purpose='truth')
                w = gene_weight(cube.basal[e])
                tpos = cube.target_gene_positions(bkeys, ens_to_sym)
                f_true = gain_features(cube.basal[e], xref_g, context=True)
                f_cf = gain_features(cube.basal[e], xref_g, context=False)
                f_swap = gain_features(cube.basal[swap_table], xref_g, context=True)
                perm = derangement(bkeys, f'tperm:{e}')
                s_perm = s[[bkeys.index(perm[kk]) for kk in bkeys]]
                phi_true = pca.coords(cube.basal[e])[:d] if d else np.zeros(0, F32)
                phi_swap = pca.coords(cube.basal[swap_table])[:d] if d else np.zeros(0, F32)
                arms = {
                    'null': np.zeros_like(s),
                    'generic': np.broadcast_to(m_g, s.shape).copy(),
                    'transfer': np.nan_to_num(s, nan=0.0),
                    'tm0': tm0.predict(s, m_g, f_cf),
                    'm1': m1.predict(s, m_g, f_true),
                    'm1_swap': m1.predict(s, m_g, f_swap),
                    'm1_tperm': m1.predict(s_perm, m_g, f_true),
                    'm2_0': np.nan_to_num(m2_0.predict(s, np.zeros(0, F32)), nan=0.0),
                    'm2': np.nan_to_num(m2.predict(s, phi_true), nan=0.0),
                    'm2_swap': np.nan_to_num(m2.predict(s, phi_swap), nan=0.0),
                }
                for i, nl in enumerate(nulls):
                    arms[f'm1_null{i + 1}'] = nl.predict(s, m_g, f_true)
                for i, nl in enumerate(m2_nulls):
                    arms[f'm2_null{i + 1}'] = np.nan_to_num(nl.predict(s, phi_true), nan=0.0)
                for name, pred in arms.items():
                    sc = score_table(pred, truth, se, w, bkeys, tpos, block_size=len(bkeys))
                    for i, kk in enumerate(bkeys):
                        records.append(dict(regime='C', held_group=g, table=e, target_key=kk,
                                            stratum=keys_info['stratum'].get(kk, 'other'),
                                            support=int(support[keep][i]), n_cells=float(cube.cells(e, [kk])[0]),
                                            arm=name, **{m: float(v[i]) for m, v in sc.items()}))
            log(f'{g}/{e}: scored ({timer()} s)')
        leaked = cube.fit_reads_of(g)
        leak_checks[g] = dict(fit_reads_of_held_group=leaked,
                              truth_reads=sorted(t for t, pp in cube.reads if pp == 'truth'))
        if leaked:
            raise AssertionError(f'{g}: a fit read the held-out tables {leaked}')
        out = a.out / f'per_target_C_{g}.csv.gz'
        pd.DataFrame(records).to_csv(out, index=False, compression='gzip')
        del records
    write_json(a.out / 'fits.json', fits)
    write_json(a.out / 'run.json', dict(written_utc=now_utc(), git=git_state(), protocol=str(a.protocol),
                                        protocol_sha256=sha256(a.protocol), cube=str(a.cube),
                                        cube_manifest_sha256=sha256(a.cube / 'manifest.json'),
                                        groups=held_groups, seconds=timer(), leak_checks=leak_checks,
                                        outputs={f.name: sha256(f) for f in sorted(a.out.glob('per_target_*.csv.gz'))}))
    log(f'done in {timer()} s')


if __name__ == '__main__':
    main()
