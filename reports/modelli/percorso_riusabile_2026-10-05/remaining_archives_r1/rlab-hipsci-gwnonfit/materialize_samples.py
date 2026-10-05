"""Materialize existing nested selections, preserving counts, masks and raw lineage.

CPU/cloud only on real data. Does not resample, pool donors, fit transforms or train.
One sparse matrix per original shard; each sampled cell is stored only once.
"""
from collections import defaultdict
import gc
import gzip
import json
import os
from pathlib import Path
import shutil
import time
import h5py
import numpy as np
import pandas as pd
import scipy.sparse as sp
from bank import BIO, STRATA, block, mapping, metadata, sha


def plan_rows(bank_root, receipt):
    rows = pd.read_csv(bank_root/'rows.csv', keep_default_na=False)
    row_of = {tuple(str(r[c]) for c in (*BIO, 'target')): i for i, r in rows.iterrows()}
    if len(row_of) != len(rows) or len(rows) != receipt['rows']:
        raise ValueError('duplicate or missing bank row')
    plans = defaultdict(dict)
    totals = defaultdict(int)
    seen_targets = set()
    with gzip.open(bank_root/'samples.jsonl.gz', 'rt', encoding='utf-8') as f:
        for line in f:
            s = json.loads(line)
            key = (*[str(s['context'][c]) for c in BIO], str(s['target']))
            if key in seen_targets or key not in row_of:
                raise ValueError('sample target duplicate or missing from bank')
            seen_targets.add(key)
            row = row_of[key]
            if s['admitted'] != int(rows.iloc[row]['n']):
                raise ValueError('sample population differs from full bank')
            largest = {c['locator']: c for c in s['levels']['128']['cells']}
            levels = {k: {c['locator']: c for c in s['levels'][k]['cells']} for k in ('32','64','128')}
            if not (set(levels['32']) <= set(levels['64']) <= set(levels['128'])):
                raise ValueError('samples are not nested')
            for loc, cell in largest.items():
                fi, raw_row = map(int, loc.split(':'))
                if fi < 0 or fi >= len(receipt['sources']) or raw_row < 0 or raw_row >= receipt['sources'][fi]['cells']:
                    raise ValueError('invalid source locator')
                if raw_row in plans[fi]:
                    raise ValueError('cell selected more than once')
                probabilities = {k: levels[k][loc]['inclusion_probability'] for k in levels if loc in levels[k]}
                if not all(0 < v <= 1 for v in probabilities.values()):
                    raise ValueError('invalid selection probability')
                plans[fi][raw_row] = {'bank_row': row, 'cell_key': cell['cell_key'],
                                      'stratum': cell['stratum'], 'probabilities': probabilities}
                for level in probabilities:
                    totals[level] += 1
    if set(row_of) != seen_targets or totals['128'] != receipt['samples128']:
        raise ValueError('sample coverage differs from bank')
    return rows, plans, dict(totals)


def run(p, root, out):
    started = time.time()
    hits = [Path(p['bank_input_path'])/'complete.json']
    if len(hits) != 1 or sha(hits[0]) != p['bank_receipt_sha256']:
        raise ValueError('bank input identity mismatch')
    bank_root = hits[0].parent
    receipt = json.loads(hits[0].read_text())
    if not receipt['complete'] or receipt['source_verification'] != p['spec']['receipt_sha256']:
        raise ValueError('bank source lineage mismatch')
    # Only consumed bank files are hashed; full means/statistics are not read here.
    for name in ('rows.csv','mask.npz','samples.jsonl.gz'):
        f = bank_root/name; expected = receipt['files'][name]
        if f.stat().st_size != expected['bytes'] or sha(f) != expected['sha256']:
            raise ValueError('bank file changed: '+name)
    source_files = {s['file']:(root/s['file'],s) for s in p['spec']['files']}
    if set(source_files) != {s['file'].replace('\\', '/') for s in receipt['sources']}:
        raise ValueError('raw sources differ from bank lineage')
    rows, plans, totals = plan_rows(bank_root, receipt)
    with np.load(bank_root/'mask.npz', allow_pickle=False) as z:
        masks = z['value']
    if masks.shape[0] != len(rows):
        raise ValueError('mask row mismatch')
    out.mkdir(parents=True, exist_ok=False)
    shutil.copyfile(bank_root/'rows.csv', out/'bank_rows.csv')
    shutil.copyfile(bank_root/'mask.npz', out/'mask.npz')
    output_files = {}
    counts = defaultdict(int)
    total_bytes = 0
    for fi, source in enumerate(receipt['sources']):
        if fi not in plans:
            continue
        f, expected = source_files[source['file'].replace('\\', '/')]
        if f.stat().st_size != expected['bytes'] or sha(f) != expected['sha256']:
            raise ValueError('raw shard identity mismatch')
        selected = plans.pop(fi)
        selected_rows = np.array(sorted(selected), dtype=np.int64)
        with h5py.File(f) as h:
            obs = metadata(h)
            cmap, _ = mapping(h)
            selected_bank_rows = np.array([selected[int(r)]['bank_row'] for r in selected_rows])
            mask = np.ones(masks.shape[1],bool)
            matrices = []
            for lo in range(0, len(obs), 1024):
                chosen = selected_rows[(selected_rows >= lo) & (selected_rows < lo+1024)]
                if len(chosen):
                    x = block(h, lo, min(lo+1024,len(obs)), cmap, mask)
                    matrices.append(x[chosen-lo])
            x = sp.vstack(matrices, format='csr').multiply(masks[selected_bank_rows]).tocsr()
            if (np.asarray(x.sum(1)).ravel() <= 0).any() or not np.equal(x.data, np.floor(x.data)).all():
                raise ValueError('invalid sampled counts')
            if x.data.max(initial=0) > np.iinfo(np.uint32).max:
                raise ValueError('counts exceed uint32')
            x = x.astype(np.uint32)
            records = []
            for raw_row in selected_rows:
                selected_cell = selected[int(raw_row)]
                actual = obs.iloc[int(raw_row)]
                bank_row = rows.iloc[selected_cell['bank_row']]
                target = 'NTC' if actual.control_kind == 'NTC' else actual.target
                if (actual.cell_key != selected_cell['cell_key'] or str(target) != str(bank_row.target)
                    or [str(actual[c]) for c in STRATA] != selected_cell['stratum']
                    or any(str(actual[c]) != str(bank_row[c]) for c in BIO)):
                    raise ValueError('sample locator resolves to another biological identity')
                records.append({**selected_cell, 'source_row': int(raw_row)})
                for level in selected_cell['probabilities']:
                    counts[level] += 1
        name = f'shard_{fi:05d}'
        sp.save_npz(out/(name+'.npz'), x, compressed=True)
        with gzip.open(out/(name+'.jsonl.gz'), 'wt', encoding='utf-8') as dest:
            for r in records:
                dest.write(json.dumps(r, separators=(',', ':'))+'\n')
        for suffix in ('.npz','.jsonl.gz'):
            path = out/(name+suffix)
            output_files[path.name] = {'bytes': path.stat().st_size, 'sha256': sha(path),
                                       'source_file': source['file'], 'source_sha256': expected['sha256'],
                                       'cells': len(selected_rows)}
            total_bytes += path.stat().st_size
        if total_bytes > p.get('max_output_bytes', 18 << 30) or shutil.disk_usage(out).free < 1 << 30:
            raise RuntimeError('output capacity guard; preserve partial shards, repartition remaining work')
        print(json.dumps({'unit':p['unit'],'shard':fi+1,'of':len(receipt['sources']),
                          'cells':len(selected_rows),'output_bytes':total_bytes,'seconds':round(time.time()-started)}), flush=True)
        del x, matrices, records, selected, obs
        gc.collect()
    if dict(counts) != totals:
        raise ValueError('materialized coverage mismatch')
    for name in ('bank_rows.csv','mask.npz'):
        path = out/name
        output_files[name] = {'bytes':path.stat().st_size,'sha256':sha(path)}
    done = {'complete':True,'unit':p['unit'],'bank_receipt_sha256':p['bank_receipt_sha256'],
            'source_verification':receipt['source_verification'],'genes':masks.shape[1],
            'gene_axis':'original ingestion official_index; mask preserved; names still require axis binding in trainer',
            'levels':totals,'files':output_files,'seconds':round(time.time()-started),
            'training_used':False}
    (out/'complete.json').write_text(json.dumps(done,indent=1))
    print(json.dumps({k:v for k,v in done.items() if k!='files'}), flush=True)


if __name__ == '__main__':
    import psutil
    p = json.loads(Path('params.json').read_text())
    env = {'cpus':os.cpu_count(),'ram_available':psutil.virtual_memory().available,
           'disk_free':shutil.disk_usage('.').free}
    print(json.dumps(env), flush=True)
    Path('environment.json').write_text(json.dumps(env))
    if env['ram_available'] < 8 << 30 or env['disk_free'] < 19 << 30:
        raise RuntimeError('insufficient resources for sample materialization')
    run(p, Path('/kaggle/input'), Path('/kaggle/working/samples')/p['unit'])
