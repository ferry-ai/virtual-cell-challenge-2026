"""Full admitted-cell CD4 moments plus nested stratified sample identities. CPU only."""
import gc, gzip, hashlib, json, os, time
from collections import Counter
from pathlib import Path

import h5py
import numpy as np
import pandas as pd
import scipy.sparse as sp
from preparation import BIO, STRATA, NestedSampler

G = 18533
FIELDS = (*BIO, *STRATA, 'target', 'control_kind', 'cell_key')

def sha(p):
    h = hashlib.sha256()
    with open(p, 'rb') as f:
        for b in iter(lambda: f.read(8 << 20), b''): h.update(b)
    return h.hexdigest()

def col(g, name, n=None):
    if name not in g:
        if name in ('batch', 'chemistry'): return np.full(n, 'MISSING', object)
        raise ValueError(f'missing required metadata {name}')
    z = g[name]
    if isinstance(z, h5py.Group):
        if 'categories' in z:
            cats = z['categories'].asstr()[:] if z['categories'].dtype.kind in 'OS' else z['categories'][:].astype(str)
            codes = z['codes'][:]
            return np.where(codes >= 0, cats[np.maximum(codes, 0)], 'MISSING')
        return z['values'][:]
    return z.asstr()[:] if z.dtype.kind in 'OS' else z[:]

def metadata(h):
    n = int(h['X'].attrs['shape'][0])
    return pd.DataFrame({c: col(h['obs'], c, n).astype(str) for c in FIELDS})

def mapping(h):
    v = h['var']; oi = col(v, 'official_index').astype(int)
    ok = (oi >= 0) & (oi < G) & (col(v, 'mapping') == 'unique') & col(v, 'measured').astype(bool)
    hits = np.bincount(oi[ok], minlength=G)
    ok &= hits[np.clip(oi, 0, G-1)] == 1
    m = np.where(ok, oi, -1)
    return m, np.bincount(m[m >= 0], minlength=G).astype(bool)

def block(h, lo, hi, cmap, mask):
    x = h['X']; ptr = x['indptr'][lo:hi+1].astype(np.int64)
    vals = x['data'][ptr[0]:ptr[-1]].astype(np.float64)
    ix = x['indices'][ptr[0]:ptr[-1]]
    old = sp.csr_matrix((vals, ix, ptr-ptr[0]), shape=(hi-lo, len(cmap)))
    valid = (cmap >= 0) & mask[np.maximum(cmap, 0)]
    remap = sp.csr_matrix((np.ones(valid.sum()), (np.flatnonzero(valid), cmap[valid])), shape=(len(cmap), G))
    out = old @ remap
    if not np.isfinite(out.data).all() or (out.data < 0).any(): raise ValueError('invalid counts')
    return out

def run_unit(spec, root, out):
    started = time.time(); files = []; seen = set()
    if not spec.get('line_group'): raise ValueError('explicit biological identity required')
    for s in spec['files']:
        f = root/s['file']
        if s['file'] in seen: raise ValueError('duplicate source')
        seen.add(s['file'])
        if f.stat().st_size != s['bytes'] or sha(f) != s['sha256']: raise ValueError('raw archive changed')
        files.append((f,s['cells']))
    out.mkdir(parents=True, exist_ok=False)
    # First pass uses only metadata and axes; fixes full intersection before any normalisation.
    units = {}; rowkeys = set(); masks = {}; counts = Counter(); actual = 0
    for f, expected in files:
        with h5py.File(f) as h:
            obs = metadata(h); oi = col(h['var'],'official_index').astype(int)
            symbols = col(h['var'],'symbol').astype(str)
            axis = np.asarray(spec['axis'],object)
            valid = (oi >= 0) & (oi < G) & (col(h['var'],'mapping') == 'unique')
            if np.any(symbols[valid] != axis[oi[valid]]): raise ValueError('native mapping differs from pinned official axis')
            _, mask = mapping(h)
        if len(obs) != expected: raise ValueError('cell count mismatch')

        actual += len(obs)
        obs['target'] = np.where(obs.control_kind == 'NTC', 'NTC', obs.target)
        for k, ix in obs.groupby(list(BIO), sort=False, observed=True).groups.items():
            units.setdefault(k, len(units)); masks[k] = masks.get(k, np.ones(G, bool)) & mask
            for target, n in obs.loc[ix, 'target'].value_counts().items():
                rowkeys.add((*k, target)); counts[(*k, target)] += int(n)
    if actual != spec['cells']: raise ValueError(f"coverage {actual} != {spec['cells']}")
    keys = sorted(rowkeys); lookup = {k: i for i, k in enumerate(keys)}
    N = len(keys); shape = (N, G)
    need = N*G*28
    import shutil
    if shutil.disk_usage(out).free < N*G*21 + (2 << 30): raise OSError('insufficient output capacity')
    import psutil
    if psutil.virtual_memory().available < need + (3 << 30): raise MemoryError(f'bank requires {need} + reserve bytes')
    sums = np.zeros(shape, np.float64); props = np.zeros(shape, np.float64)
    squares = np.zeros(shape, np.float64); detected = np.zeros(shape, np.uint32)
    ns = np.zeros(N, np.int64); zero_depth = Counter(); sampler = NestedSampler()
    sources = []
    for fi, (f, expected) in enumerate(files):
        with h5py.File(f) as h:
            obs = metadata(h); cmap, _ = mapping(h)
            obs['target'] = np.where(obs.control_kind == 'NTC', 'NTC', obs.target)
            rkeys = list(obs[[*BIO, 'target']].itertuples(index=False, name=None))
            rid = np.array([lookup[k] for k in rkeys])
            mask = np.ones(G,bool)
            for lo in range(0, len(obs), 1024):
                hi = min(lo+1024, len(obs)); x = block(h, lo, hi, cmap, mask)
                cell_masks = np.stack([masks[k[:-1]] for k in rkeys[lo:hi]])
                x = x.multiply(cell_masks).tocsr()
                depth = np.asarray(x.sum(1)).ravel(); good = depth > 0
                for j in np.flatnonzero(~good): zero_depth[int(rid[lo+j])] += 1
                x = x[good]; rr = rid[lo:hi][good]; local, inv = np.unique(rr, return_inverse=True)
                if not len(rr): continue
                agg = sp.csr_matrix((np.ones(len(rr)), (inv, np.arange(len(rr)))), shape=(len(local), len(rr)))
                p = x.multiply(1/depth[good, None]).tocsr()
                sums[local] += (agg @ x).toarray()
                props[local] += (agg @ p).toarray()
                squares[local] += (agg @ p.multiply(p)).toarray()
                detected[local] += (agg @ (x > 0)).toarray().astype(np.uint32)
                ns[local] += np.bincount(inv, minlength=len(local))
                for j in np.flatnonzero(good):
                    row = lo + int(j); sampler.add(obs.iloc[row].to_dict(), f'{fi}:{row}')
        sources.append({'file': str(f.relative_to(root)), 'cells': expected})
        print(json.dumps({'unit': spec['name'], 'shard': fi+1, 'of': len(files), 'seconds': round(time.time()-started)}), flush=True)
    rows = pd.DataFrame(keys, columns=[*BIO, 'target']); rows['n'] = ns
    rows['line_group'] = spec['line_group']; rows['zero_depth_excluded'] = [zero_depth[i] for i in range(N)]
    rows.to_csv(out/'rows.csv', index=False)
    den = np.maximum(ns, 1)[:, None]
    # Write one compressed statistic at a time to stay under Kaggle's output limit.
    def save(name, a): np.savez_compressed(out/(name+'.npz'), value=a)
    save('count_sum', sums); del sums; gc.collect()
    props /= den
    save('mean_proportion', props.astype(np.float32))
    for lo in range(0, N, 256):
        hi = min(lo+256, N)
        squares[lo:hi] = np.maximum(squares[lo:hi]-ns[lo:hi, None]*props[lo:hi]**2, 0)/np.maximum(ns[lo:hi, None]-1, 1)
    save('variance_proportion', squares.astype(np.float32)); del squares; gc.collect()
    save('zero_fraction', (1-detected/den).astype(np.float32)); del detected; gc.collect()
    save('mask', np.stack([masks[k[:-1]] for k in keys]))
    selections = sampler.finish(); del sampler; gc.collect()
    control_means = {}; sample_count = 0
    with gzip.open(out/'samples.jsonl.gz', 'wt', encoding='utf-8') as dest:
        for selection in selections:
            dest.write(json.dumps(selection, separators=(',', ':'))+'\n')
            sample_count += len(selection['levels']['128']['cells'])
            if selection['target'] != 'NTC': continue
            bio = tuple(selection['context'][c] for c in BIO); r = lookup[(*bio, 'NTC')]
            value = np.zeros(G); pop = 0.
            chosen = selection['levels']['64']['cells']
            for cell in chosen:
                fi, row = map(int, cell['locator'].split(':'))
                with h5py.File(files[fi][0]) as h:
                    cmap, _ = mapping(h); x = block(h, row, row+1, cmap, masks[bio])
                v = x.toarray()[0]; v /= v.sum()
                w = 1/cell['inclusion_probability']; value += v*w; pop += w
            control_means[str(r)] = value/pop
    np.savez_compressed(out/'sampled_controls.npz', **control_means)
    if int(ns.sum()) + sum(zero_depth.values()) != actual: raise ValueError('unaccounted cells')
    receipt = {'complete': True, 'unit': spec['name'], 'cells_in': actual, 'cells_used': int(ns.sum()),
               'zero_depth_excluded': sum(zero_depth.values()), 'contexts': len(units), 'rows': N,
               'samples128': sample_count, 'seconds': round(time.time()-started), 'sources': sources,
               'source_verification': spec['receipt_sha256'], 'sample_levels': [32,64,128],
               'files': {p.name: {'bytes': p.stat().st_size, 'sha256': sha(p)} for p in out.iterdir()}}
    (out/'complete.json').write_text(json.dumps(receipt, indent=1))
    print(json.dumps({k: receipt[k] for k in ('unit','complete','cells_used','seconds')}), flush=True)

def main():
    import psutil, shutil
    p = json.loads(Path('params.json').read_text())
    root = Path(os.environ.get('BANK_INPUT', '/kaggle/input')); out = Path(os.environ.get('BANK_OUTPUT', '/kaggle/working/bank'))
    env = {'cpus': os.cpu_count(), 'ram_available': psutil.virtual_memory().available, 'disk_free': shutil.disk_usage('.').free}
    print(json.dumps(env), flush=True); Path('env.json').write_text(json.dumps(env))
    for spec in p['units']:
        run_unit(spec, root, out/spec['name']); gc.collect()
    Path('bank_done.json').write_text(json.dumps({'complete': True, 'units': [u['name'] for u in p['units']]}))

if __name__ == '__main__': main()
