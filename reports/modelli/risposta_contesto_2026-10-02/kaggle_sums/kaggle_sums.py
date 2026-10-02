"""Kaggle CPU kernel (R-LEAD P4 data): per-target and control count sums of three published R-LAB studies.

Reads the contract shards of the private datasets attached to the kernel and writes, for each study kept,
the summed raw counts on the 18,533-gene official axis: per target (all cells, and two halves drawn by
md5 of the cell key), and for the NTC controls (same halves). Features map through the shard's own
`official_index` when `mapping == unique` and `measured`; two features on one axis gene are both dropped,
never summed. Cells with zero depth, unassigned, combined or non-CRISPRi labels are skipped and counted.
No estimator runs here: effects are computed locally with the live `effects_from_pseudobulk`.

Studies: jurkat_nadig, h1_vcc2025 (train and validation only; the 2025 test split is not in the dataset),
tian2021_crispri (iPSC-induced neurons). Output: /kaggle/working/<study>_sums.npz and sums_manifest.json.
"""
import glob
import hashlib
import json
import os
import time
from collections import defaultdict

import h5py
import numpy as np
import scipy.sparse as sp

AXIS = 18533
DATASETS = {'rlab-jurkat-nadig': None, 'rlab-h1-vcc2025-trainval': None, 'rlab-tian-norman': {'tian2021_crispri'}}
CONTROL = 'NTC'
INPUT = os.environ.get('SUMS_INPUT', '/kaggle/input')
OUTPUT = os.environ.get('SUMS_OUTPUT', '/kaggle/working')
t0 = time.time()


def text(a):
    return np.array([x.decode() if isinstance(x, bytes) else str(x) for x in a], dtype=object)


def col(group, name):
    node = group[name]
    if isinstance(node, h5py.Group) and 'categories' in node:
        cats = text(node['categories'][:])
        codes = node['codes'][:].astype(np.int64)
        return np.where(codes >= 0, cats[np.clip(codes, 0, None)], 'MISSING').astype(object)
    if isinstance(node, h5py.Group) and 'values' in node:
        return text(node['values'][:])
    return node[:] if node.dtype.kind in 'iufb' else text(node[:])


def half_of(keys):
    return np.array([int(hashlib.md5(k.encode()).hexdigest()[:8], 16) % 2 for k in keys], dtype=np.int64)


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(1 << 22), b''):
            h.update(b)
    return h.hexdigest()


acc = defaultdict(lambda: {'targets': {}, 'sums': [], 'sa': [], 'sb': [], 'n': [], 'na': [], 'nb': [],
                           'ctrl': np.zeros(AXIS), 'ca': np.zeros(AXIS), 'cb': np.zeros(AXIS),
                           'cn': 0, 'can': 0, 'cbn': 0, 'measured': np.zeros(AXIS, bool), 'skipped': defaultdict(int),
                           'shards': [], 'contexts': set(), 'conditions': set()})
manifest = {'datasets': {}, 'notes': __doc__}
for slug, keep in DATASETS.items():
    # Kaggle mounts private datasets at /kaggle/input/datasets/<owner>/<slug>/ (older layout: /kaggle/input/<slug>/)
    files = sorted(set(glob.glob(f'{INPUT}/**/{slug}/**/*.h5ad', recursive=True)
                       + glob.glob(f'{INPUT}/{slug}/**/*.h5ad', recursive=True)))
    manifest['datasets'][slug] = {'shards_found': len(files)}
    if not files:
        raise SystemExit(f'no shard of {slug} under {INPUT}: refusing an empty result')
    for f in files:
        with h5py.File(f, 'r') as h:
            o, v = h['obs'], h['var']
            study = col(o, 'study')
            if keep is not None and not set(study.tolist()) & keep:
                continue
            target = col(o, 'target')
            kind = col(o, 'control_kind')
            modality = col(o, 'modality')
            cell_key = col(o, 'cell_key')
            depth = col(o, 'depth_on_file_axis').astype(float)
            context = col(o, 'context')
            condition = col(o, 'condition')
            oi = col(v, 'official_index').astype(np.int64)
            mapping = col(v, 'mapping')
            measured = col(v, 'measured').astype(bool)
            X = h['X']
            shape = tuple(int(s) for s in X.attrs['shape'])
            data, indices, indptr = X['data'][:], X['indices'][:], X['indptr'][:].astype(np.int64)
        colmap = np.where((oi >= 0) & (mapping == 'unique') & measured, oi, -1)
        hits = np.bincount(colmap[colmap >= 0], minlength=AXIS)
        colmap = np.where((colmap >= 0) & (hits[np.clip(colmap, 0, None)] > 1), -1, colmap)
        newc = colmap[indices]
        ok = newc >= 0
        rows = np.repeat(np.arange(shape[0]), np.diff(indptr))[ok]
        M = sp.csr_matrix((data[ok].astype(np.float64), (rows, newc[ok])), shape=(shape[0], AXIS))
        halves = half_of(cell_key)
        for s in sorted(set(study.tolist())):
            if keep is not None and s not in keep:
                continue
            A = acc[s]
            A['shards'].append({'file': os.path.relpath(f, INPUT), 'sha256': sha(f), 'cells': int((study == s).sum())})
            A['measured'][colmap[colmap >= 0]] = True
            sel = study == s
            labels = target.astype(str)
            is_ctrl = sel & ((kind == CONTROL) | (labels == CONTROL))
            ctrl = is_ctrl & (depth > 0)
            cand = sel & ~is_ctrl
            live = cand & (depth > 0)
            crispri = live & (modality == 'CRISPRi')
            unassigned = crispri & np.isin(labels, ['UNASSIGNED', 'MISSING'])
            combo = crispri & ~unassigned & np.array(['+' in t or '|' in t or ';' in t for t in labels])
            pert = crispri & ~unassigned & ~combo
            for name, m in (('zero_depth', (sel & (depth <= 0))), ('other_modality', live & ~crispri),
                            ('unassigned', unassigned), ('combined', combo)):
                A['skipped'][name] += int(m.sum())
            A['contexts'].update(set(context[sel].tolist()))
            A['conditions'].update(set(condition[sel].tolist()))
            for which, mask in (('ctrl', ctrl), ('ca', ctrl & (halves == 0)), ('cb', ctrl & (halves == 1))):
                A[which] += np.asarray(M[np.flatnonzero(mask)].sum(axis=0)).ravel()
            A['cn'] += int(ctrl.sum())
            A['can'] += int((ctrl & (halves == 0)).sum())
            A['cbn'] += int((ctrl & (halves == 1)).sum())
            idx = np.flatnonzero(pert)
            uniq, inv = np.unique(labels[idx], return_inverse=True)
            for j, t in enumerate(uniq):
                if t not in A['targets']:
                    A['targets'][t] = len(A['sums'])
                    A['sums'].append(np.zeros(AXIS))
                    A['sa'].append(np.zeros(AXIS, np.float32))
                    A['sb'].append(np.zeros(AXIS, np.float32))
                    A['n'].append(0)
                    A['na'].append(0)
                    A['nb'].append(0)
                k = A['targets'][t]
                rr = idx[inv == j]
                ha = rr[halves[rr] == 0]
                hb = rr[halves[rr] == 1]
                A['sums'][k] += np.asarray(M[rr].sum(axis=0)).ravel()
                A['sa'][k] += np.asarray(M[ha].sum(axis=0)).ravel().astype(np.float32)
                A['sb'][k] += np.asarray(M[hb].sum(axis=0)).ravel().astype(np.float32)
                A['n'][k] += int(rr.size)
                A['na'][k] += int(ha.size)
                A['nb'][k] += int(hb.size)
        print(json.dumps({'t': round(time.time() - t0, 1), 'shard': os.path.basename(f)}), flush=True)

for s, A in acc.items():
    targets = sorted(A['targets'], key=A['targets'].get)
    np.savez_compressed(f'{OUTPUT}/{s}_sums.npz', targets=np.array(targets),
                        sums=np.vstack(A['sums']), sums_a=np.vstack(A['sa']), sums_b=np.vstack(A['sb']),
                        n=np.array(A['n']), n_a=np.array(A['na']), n_b=np.array(A['nb']),
                        ctrl=A['ctrl'], ctrl_a=A['ca'], ctrl_b=A['cb'],
                        ctrl_n=np.array([A['cn'], A['can'], A['cbn']]), measured=A['measured'])
    manifest[s] = {'targets': len(targets), 'perturbed_cells': int(sum(A['n'])), 'controls': A['cn'],
                   'controls_halves': [A['can'], A['cbn']], 'axis_genes_measured': int(A['measured'].sum()),
                   'skipped': dict(A['skipped']), 'contexts': sorted(A['contexts']),
                   'conditions': sorted(A['conditions']), 'shards': A['shards']}
manifest['seconds'] = round(time.time() - t0, 1)
with open(f'{OUTPUT}/sums_manifest.json', 'w') as fh:
    json.dump(manifest, fh, indent=1)
print('done', manifest['seconds'])
