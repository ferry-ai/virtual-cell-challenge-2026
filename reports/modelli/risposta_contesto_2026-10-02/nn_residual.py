"""R-LEAD P4: a nonlinear correction of the out-of-fold transfer, conditioned on the held-out controls (PyTorch, CPU).

Same bench as p3_run.py: every line group held out whole; training rows are the fit keys of the other
groups with their out-of-fold transfers (sources: the other training groups), read from the group-mean
cache of a finished p3_run (read only). The network (PROTOCOLLO_NN.json):

    y_hat[r, j] = MLP_gene([s, isnan s, m, d, level, low, E_j]) + U[j, :] . MLP_program([U^T s_r, phi(c)])

with s the transfer, m the generic response, (d, level, low) the gene features of the row's own controls
against the sources' reference (`arms.gain_features`), E a learned gene embedding, U the gene basis of the
training transfers and phi the principal coordinates of the controls. The twin ``nn0`` has the context
replaced by the sources' reference; three nulls are trained with controls permuted across training groups.

The number of steps is chosen on an inner validation group held out whole, with its transfers, basis,
PCA and references rebuilt without it (the correction asked of M2 by the external review), then each arm
is refitted on all training groups. Every table read is logged; a fit that reads the held-out group fails.

    py.cmd nn_residual.py --cube <cube_r1> --gm-cache <p3_c_r2>/gm_cache --protocol PROTOCOLLO_NN.json --out <new>
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from arms import (AMPLITUDE_T25, BasalPCA, Cube, combine_groups, derangement, fit_keys, gain_features,
                  gene_weight, generic_vector, reference_basal, table_means)
from common import Timer, coords_path, data_root, git_state, log, now_utc, sha256, write_json
from fitting import GMCache, ReadOnlyGMCache, basis, transfer_for
from metrics import blocks_of, score_table
from splits import Split, assert_no_leak, unit_hash

F32 = np.float32
DEVICE = torch.device('cpu')


class Net(torch.nn.Module):
    def __init__(self, n_genes: int, emb: int, hg: int, hp: int, k: int, d: int):
        super().__init__()
        self.E = torch.nn.Embedding(n_genes, emb)
        torch.nn.init.normal_(self.E.weight, std=0.01)
        self.g = torch.nn.Sequential(torch.nn.Linear(6 + emb, hg), torch.nn.SiLU(), torch.nn.Linear(hg, hg),
                                     torch.nn.SiLU(), torch.nn.Linear(hg, 1))
        self.p = torch.nn.Sequential(torch.nn.Linear(k + d, hp), torch.nn.SiLU(), torch.nn.Linear(hp, k))

    def forward(self, genes: torch.Tensor, gfeat: torch.Tensor, zphi: torch.Tensor, Ucols: torch.Tensor):
        x = torch.cat([gfeat, self.E(genes).unsqueeze(0).expand(gfeat.shape[0], -1, -1)], -1)
        return self.g(x).squeeze(-1) + self.p(zphi) @ Ucols.T


class RowSet:
    """Training rows of some groups with out-of-fold transfers excluding ``excluded`` groups (float16 in RAM)."""

    def __init__(self, cube: Cube, gm: ReadOnlyGMCache, rows_groups: list[str], all_train: list[str], held: str,
                 excluded: set, raw_means: dict, P: dict, cap_rows: int):
        self.groups = rows_groups
        Ys, Ss, tab, grp = [], [], [], []
        self.m, self.xref = {}, {}
        split = Split('C', held, None, P['n_folds'])
        for h in rows_groups:
            sources = [x for x in all_train if x != h and x not in excluded]
            if held in sources or h in sources:
                raise AssertionError('transfer sources include the row group or the held-out group')
            K800 = fit_keys(cube, h, split, 800)
            parts = [gm.get(x, K800, f'fit_{h}', held)[:P['n_fit']] for x in sources]
            s, support = combine_groups(parts)
            K = K800[:P['n_fit']]
            keep = support > 0
            K = [k for k, kk in zip(K, keep) if kk]
            s = s[keep] * AMPLITUDE_T25
            rows_h = []
            for t in cube.tables_of(h):
                y, have = cube.get(t, 'raw', K)
                for i in np.flatnonzero(have):
                    rows_h.append((unit_hash(f'{t}:{K[i]}', 'nn-rows'), t, y[i], s[i]))
            rows_h.sort(key=lambda r: r[0])
            for _, t, yi, si in rows_h[:cap_rows]:
                Ys.append(yi.astype(np.float16))
                Ss.append(si.astype(np.float16))
                tab.append(t)
                grp.append(h)
            self.m[h] = generic_vector(cube, raw_means, {held, h} | excluded)
            self.xref[h] = reference_basal(cube, {held, h} | excluded)
        self.Y = np.vstack(Ys)
        self.S = np.vstack(Ss)
        self.table = np.array(tab)
        self.group = np.array(grp)


def gene_features(s: np.ndarray, m: np.ndarray, feats: np.ndarray) -> np.ndarray:
    """(R, G, 6): [s, isnan s, m, d, level, low]."""
    R, G = s.shape
    out = np.empty((R, G, 6), F32)
    out[..., 0] = np.nan_to_num(s, nan=0.0)
    out[..., 1] = np.isnan(s)
    out[..., 2] = np.nan_to_num(m, nan=0.0)[None, :]
    out[..., 3:] = feats[None, :, :]
    return out


class Trainer:
    def __init__(self, cube: Cube, P: dict, rows: RowSet, U: np.ndarray, pca: BasalPCA | None, context: bool,
                 basal_of: dict | None = None):
        self.cube, self.P, self.rows, self.context = cube, P, rows, context
        self.U = torch.from_numpy(U)
        self.Ud = self.U.to(DEVICE)
        self.pca, self.basal_of = pca, basal_of or {}
        G = len(cube.genes)
        self.feats = {}
        for h in rows.groups:
            for t in set(rows.table[rows.group == h]):
                src = self.basal_of.get(t, t)
                self.feats[(h, t)] = gain_features(cube.basal[src], rows.xref[h], context=context)
        self.phi = {}
        for t in set(rows.table):
            src = self.basal_of.get(t, t)
            self.phi[t] = (pca.coords(cube.basal[src])[:P['pca_d']] if (context and pca is not None)
                           else np.zeros(P['pca_d'], F32))
        self.weights = {t: gene_weight(cube.basal[t]) for t in set(rows.table)}
        self.by_group = {h: np.flatnonzero(rows.group == h) for h in rows.groups}
        self.G = G

    def batch(self, rng: np.random.Generator):
        P = self.P
        hs = rng.choice(self.rows.groups, P['batch_rows'])
        idx = np.array([rng.choice(self.by_group[h]) for h in hs])
        genes = np.sort(rng.choice(self.G, min(P['batch_genes'], self.G), replace=False))
        return idx, genes

    def tensors(self, idx: np.ndarray, genes: np.ndarray):
        rows = self.rows
        s = rows.S[idx][:, genes].astype(F32)
        y = rows.Y[idx][:, genes].astype(F32)
        gf = np.empty((len(idx), len(genes), 6), F32)
        w = np.empty((len(idx), len(genes)), F32)
        zphi = np.empty((len(idx), self.U.shape[1] + self.P['pca_d']), F32)
        s_full = rows.S[idx].astype(F32)
        z = np.nan_to_num(s_full, nan=0.0) @ self.U.numpy()
        for i, r in enumerate(idx):
            h, t = rows.group[r], rows.table[r]
            gf[i] = gene_features(s[i:i + 1], rows.m[h][genes], self.feats[(h, t)][genes])[0]
            w[i] = self.weights[t][genes] * np.isfinite(y[i])
            zphi[i] = np.concatenate([z[i], self.phi[t]])
        return tuple(t.to(DEVICE) for t in (torch.from_numpy(genes.astype(np.int64)), torch.from_numpy(gf),
                                            torch.from_numpy(zphi), torch.from_numpy(np.nan_to_num(y)),
                                            torch.from_numpy(w)))

    def train(self, steps: int, seed: int, checkpoints=(), val: 'Trainer | None' = None):
        torch.manual_seed(seed)
        P = self.P
        net = Net(self.G, P['gene_embedding'], P['hidden_gene'], P['hidden_program'], self.U.shape[1], P['pca_d']).to(DEVICE)
        opt = torch.optim.AdamW(net.parameters(), lr=P['lr'], weight_decay=P['weight_decay'])
        rng = np.random.default_rng(seed)
        losses = {}
        for step in range(1, steps + 1):
            genes_t, gf, zphi, y, w = self.tensors(*self.batch(rng))
            pred = net(genes_t, gf, zphi, self.Ud[genes_t])
            loss = (w * (pred - y) ** 2).sum() / w.sum().clamp_min(1e-6)
            opt.zero_grad()
            loss.backward()
            opt.step()
            if step in checkpoints and val is not None:
                losses[step] = val.loss(net)
        return net, losses

    def loss(self, net: Net, n_genes: int = 2048, seed: int = 7) -> float:
        rng = np.random.default_rng(seed)
        genes = np.sort(rng.choice(self.G, min(n_genes, self.G), replace=False))
        tot = den = 0.0
        with torch.no_grad():
            for b0 in range(0, len(self.rows.Y), 256):
                idx = np.arange(b0, min(b0 + 256, len(self.rows.Y)))
                genes_t, gf, zphi, y, w = self.tensors(idx, genes)
                pred = net(genes_t, gf, zphi, self.Ud[genes_t])
                tot += float((w * (pred - y) ** 2).sum())
                den += float(w.sum())
        return tot / max(den, 1e-12)


def predict(net: Net, U: np.ndarray, s: np.ndarray, m: np.ndarray, feats: np.ndarray, phi: np.ndarray,
            chunk: int = 2048) -> np.ndarray:
    R, G = s.shape
    z = np.nan_to_num(s, nan=0.0) @ U
    zphi = torch.from_numpy(np.concatenate([z, np.broadcast_to(phi, (R, len(phi)))], 1).astype(F32)).to(DEVICE)
    out = np.empty((R, G), F32)
    Ut = torch.from_numpy(U).to(DEVICE)
    with torch.no_grad():
        prog = net.p(zphi)
        for g0 in range(0, G, chunk):
            genes = np.arange(g0, min(g0 + chunk, G))
            gt = torch.from_numpy(genes).to(DEVICE)
            gf = torch.from_numpy(gene_features(s[:, genes], m[genes], feats[genes])).to(DEVICE)
            x = torch.cat([gf, net.E(gt).unsqueeze(0).expand(R, -1, -1)], -1)
            out[:, genes] = (net.g(x).squeeze(-1) + prog @ Ut[gt].T).cpu().numpy()
    return out


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--cube', type=Path, required=True)
    p.add_argument('--gm-cache', type=Path, required=True)
    p.add_argument('--protocol', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--groups', nargs='*', default=None)
    p.add_argument('--cap-rows', type=int, default=1200, help='training rows per group (stable hash)')
    p.add_argument('--gm-cache-writable', action='store_true',
                   help='compute group means missing from --gm-cache (a new folder), instead of reading a finished run')
    a = p.parse_args()
    if a.out.exists():
        raise FileExistsError(a.out)
    proto = json.loads(a.protocol.read_text(encoding='utf-8'))
    P = proto['parameters']
    torch.set_num_threads(int(P.get('threads', torch.get_num_threads())))
    global DEVICE
    DEVICE = torch.device(P.get('device') or ('cuda' if torch.cuda.is_available() else 'cpu'))
    log(f'device {DEVICE}')
    timer = Timer()
    cube = Cube(a.cube, min_cells=P['min_cells'])
    keys_info = pd.read_csv(a.cube / 'keys.csv').set_index('target_key')
    coords = pd.read_csv(coords_path(P['gene_coordinates']), sep='\t')
    ens_to_sym = {str(gid).split('.')[0]: s for s, gid in zip(coords['symbol'], coords['gene_id']) if isinstance(gid, str)}
    a.out.mkdir(parents=True)
    commons, raw_means = table_means(cube, Split('C', '__none__', None, P['n_folds']))
    gm = (GMCache if a.gm_cache_writable else ReadOnlyGMCache)(cube, commons, a.gm_cache)
    swap = derangement(cube.groups, 'swap')
    fits, leak_checks = {}, {}
    for g in (a.groups or cube.groups):
        cube.reads.clear()
        split = Split('C', g, None, P['n_folds'])
        assert_no_leak(cube.training_rows(split), split, 'nn arms (shared training rows)')
        train_groups = [h for h in cube.groups if h != g]
        v = sorted(train_groups, key=lambda x: unit_hash(x, f'nn-val:{g}'))[0]
        inner_groups = [h for h in train_groups if h != v]
        order = sorted(train_groups)
        perms = [{order[i]: order[(i + r) % len(order)] for i in range(len(order))} for r in range(1, P['nulls'] + 1)]
        # inner selection: rows, basis and PCA without v; validation rows of v with transfers excluding v
        inner_rows = RowSet(cube, gm, inner_groups, train_groups, g, {v}, raw_means, P, a.cap_rows)
        val_rows = RowSet(cube, gm, [v], train_groups, g, set(), raw_means, P, a.cap_rows)
        U_in = basis(inner_rows.S.astype(F32), P['basis_k'])
        pca_in = BasalPCA(cube, inner_groups, P['pca_d'])
        arms_spec = [('nn0', False, None), ('nn', True, None)] + \
                    [(f'nn_null{i + 1}', True, sh) for i, sh in enumerate(perms)]
        chosen = {}
        for name, context, shift in arms_spec[:2]:          # nn0 and nn; the nulls reuse nn's steps
            tr = Trainer(cube, P, inner_rows, U_in, pca_in, context)
            va = Trainer(cube, P, val_rows, U_in, pca_in, context)
            _, losses = tr.train(max(P['step_grid']), P['seed'], set(P['step_grid']), va)
            chosen[name] = dict(steps=min(losses, key=losses.get), val_loss=losses)
        for name, _, _ in arms_spec[2:]:
            chosen[name] = dict(steps=chosen['nn']['steps'], val_loss=None, note='steps of nn')
        del inner_rows, val_rows
        # final fits on all training groups
        rows = RowSet(cube, gm, train_groups, train_groups, g, set(), raw_means, P, a.cap_rows)
        U = basis(rows.S.astype(F32), P['basis_k'])
        pca = BasalPCA(cube, train_groups, P['pca_d'])
        nets = {}
        for name, context, shift in arms_spec:
            basal_of = ({t: cube.tables_of(shift[cube.group[t]])[0] for t in cube.tables if cube.group[t] in shift}
                        if shift else None)
            tr = Trainer(cube, P, rows, U, pca, context, basal_of)
            nets[name], _ = tr.train(chosen[name]['steps'], P['seed'])
        del rows
        fits[g] = dict(validation_group=v, chosen=chosen, permutations=perms, swap_group=swap[g])
        log(f'{g}: networks trained (val {v}; steps {[c["steps"] for c in chosen.values()]}) ({timer()} s)')
        # predictions on the held-out tables
        m_g = generic_vector(cube, raw_means, {g})
        xref_g = reference_basal(cube, {g})
        swap_table = cube.tables_of(swap[g])[0]
        records = []
        for e in cube.tables_of(g):
            keys = cube.keys_of(e)
            w = gene_weight(cube.basal[e])
            f_true = gain_features(cube.basal[e], xref_g, context=True)
            f_cf = gain_features(cube.basal[e], xref_g, context=False)
            f_swap = gain_features(cube.basal[swap_table], xref_g, context=True)
            phi_true = pca.coords(cube.basal[e])[:P['pca_d']]
            phi_swap = pca.coords(cube.basal[swap_table])[:P['pca_d']]
            zero = np.zeros(P['pca_d'], F32)
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
                tpos = cube.target_gene_positions(bkeys, ens_to_sym)
                arms = {'nn0': predict(nets['nn0'], U, s, m_g, f_cf, zero),
                        'nn': predict(nets['nn'], U, s, m_g, f_true, phi_true),
                        'nn_swap': predict(nets['nn'], U, s, m_g, f_swap, phi_swap)}
                for i in range(P['nulls']):
                    arms[f'nn_null{i + 1}'] = predict(nets[f'nn_null{i + 1}'], U, s, m_g, f_true, phi_true)
                cells = cube.cells(e, bkeys)
                for name, pred in arms.items():
                    sc = score_table(pred, truth, se, w, bkeys, tpos, block_size=len(bkeys))
                    for i, kk in enumerate(bkeys):
                        records.append(dict(regime='C', held_group=g, table=e, target_key=kk,
                                            stratum=keys_info['stratum'].get(kk, 'other'),
                                            support=int(support[keep][i]), n_cells=float(cells[i]), arm=name,
                                            **{m: float(val[i]) for m, val in sc.items()}))
        leaked = cube.fit_reads_of(g)
        leak_checks[g] = dict(fit_reads_of_held_group=leaked)
        if leaked:
            raise AssertionError(f'{g}: a fit read the held-out tables {leaked}')
        pd.DataFrame(records).to_csv(a.out / f'per_target_C_{g}.csv.gz', index=False, compression='gzip')
        log(f'{g}: scored ({timer()} s)')
        del records, nets
    write_json(a.out / 'fits.json', fits)
    write_json(a.out / 'run.json', dict(written_utc=now_utc(), git=git_state(), protocol=str(a.protocol),
                                        protocol_sha256=sha256(a.protocol), cube=str(a.cube), gm_cache=str(a.gm_cache),
                                        cap_rows=a.cap_rows, torch=torch.__version__, threads=torch.get_num_threads(), device=str(DEVICE),
                                        seconds=timer(), leak_checks=leak_checks,
                                        outputs={f.name: sha256(f) for f in sorted(a.out.glob('per_target_*.csv.gz'))}))
    log(f'done in {timer()} s')


if __name__ == '__main__':
    main()
