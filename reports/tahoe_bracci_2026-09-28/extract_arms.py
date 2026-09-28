"""Extract selected Tahoe drugs plus vehicle by line, plate, drug and sample-derived dose.

Usage: scripts/py.cmd reports/tahoe_bracci_2026-09-28/extract_arms.py --selftest
Remote usage requires --drugs CSV --out NEW --revision FULL_COMMIT; no network in selftest.
Adapted from tahoe_dmso_2026-09-28/extract_dmso_subset.py (2026-09-28).
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import io
import json
import re
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from pathlib import Path

import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq

META = Path('C:/Users/ferra/vcc2026-data/external/tahoe100m/metadata')
VEHICLE = 'DMSO_TF'
N_SHARDS = 3388
COLUMNS = ['genes', 'expressions', 'drug', 'cell_line_id', 'plate', 'sample']


def sample_lookup(frame):
    """Parse literal singleton tuples; preserve units and reject ambiguous mixtures."""
    if frame['sample'].isna().any() or frame['sample'].duplicated().any():
        raise ValueError('Missing or duplicate sample IDs')
    result = {}
    for row in frame.to_dict('records'):
        items = ast.literal_eval(row['drugname_drugconc'])
        if not isinstance(items, (list, tuple)) or len(items) != 1 or len(items[0]) != 3:
            raise ValueError(f"Ambiguous dose: {row['sample']}")
        name, value, unit = items[0]
        dose = Decimal(str(value))
        if str(name).strip() != str(row['drug']).strip() or not dose.is_finite() or dose < 0 or not str(unit).strip():
            raise ValueError(f"Invalid dose: {row['sample']}")
        result[str(row['sample'])] = (str(row['plate']), str(row['drug']), f'{dose.normalize():f} {str(unit).strip()}')
    return result


class RangeFile(io.RawIOBase):
    """Strict HTTP ranges; reject a full-body response before reading its body."""
    def __init__(self, url, session):
        import time
        import requests
        self.session, self.pos, self.bytes = session, 0, 0
        for attempt in range(6):
            try:
                with session.head(url, allow_redirects=True, timeout=60) as r:
                    r.raise_for_status()
                    self.url, self.size = r.url, int(r.headers['Content-Length'])
                break
            except requests.RequestException:
                if attempt == 5: raise
                time.sleep(2 ** attempt)

    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.pos

    def seek(self, offset, whence=io.SEEK_SET):
        value = {0: offset, 1: self.pos + offset, 2: self.size + offset}[whence]
        if value < 0: raise ValueError('Negative seek')
        self.pos = value
        return value

    def readinto(self, b):
        import time
        import requests
        n = min(len(b), self.size - self.pos)
        if n <= 0: return 0
        end = self.pos + n - 1
        # Transient server errors (429, 5xx) and dropped connections are retried with backoff (28/09: a 503 on
        # Kaggle stopped the first run after 22 s); a wrong Content-Range on a 206 still fails at once.
        for attempt in range(6):
            try:
                with self.session.get(self.url, headers={'Range': f'bytes={self.pos}-{end}',
                                      'Accept-Encoding': 'identity'}, stream=True, timeout=120) as r:
                    if r.status_code == 429 or r.status_code >= 500:
                        raise requests.ConnectionError(f'HTTP {r.status_code}')
                    expected = f'bytes {self.pos}-{end}/{self.size}'
                    if r.status_code != 206 or r.headers.get('Content-Range') != expected:
                        raise IOError(f'Invalid Range response: {r.status_code}, {r.headers.get("Content-Range")}')
                    data = r.raw.read(n + 1)
                    if len(data) != n: raise requests.ConnectionError('Truncated or oversized range')
                break
            except requests.RequestException:
                if attempt == 5: raise
                time.sleep(2 ** attempt)
        self.bytes += len(data)
        b[:n] = data
        self.pos += n
        return n


def scan(pf, tokens, samples, wanted, shard):
    """Scan drug first; aggregate selected cells only, retaining observed sample counts."""
    if len(tokens) == 0 or (np.diff(tokens) <= 0).any():
        raise ValueError('Tokens must be nonempty, sorted and unique')
    out = {'shard': shard, 'row_groups': pf.num_row_groups, 'selected_row_groups': [],
           'groups': {}, 'selected_samples': {}, 'scanned_cells': pf.metadata.num_rows}
    for rg in range(pf.num_row_groups):
        drug = pf.read_row_group(rg, columns=['drug'])['drug']
        if not pc.any(pc.is_in(drug, value_set=pa.array(sorted(wanted)))).as_py(): continue
        out['selected_row_groups'].append(rg)
        table = pf.read_row_group(rg, columns=COLUMNS)
        table = table.filter(pc.is_in(table['drug'], value_set=pa.array(sorted(wanted))))
        genes, expr = (table[c].combine_chunks() for c in ('genes', 'expressions'))
        off = np.asarray(genes.offsets, dtype=np.int64)
        if not np.array_equal(off, np.asarray(expr.offsets)): raise ValueError('Misaligned counts')
        tok, val = np.asarray(genes.values, dtype=np.int64), np.asarray(expr.values, dtype=np.float64)
        drop = np.zeros(len(tok), dtype=bool)
        first = off[:-1][off[:-1] < off[1:]]
        drop[first[val[first] < 0]] = True
        valid = ~drop
        if not np.isfinite(val).all() or (val[valid] < 0).any(): raise ValueError('Invalid counts')
        pos = np.clip(np.searchsorted(tokens, tok), 0, len(tokens) - 1)
        if (tokens[pos[valid]] != tok[valid]).any(): raise ValueError('Unknown gene token')
        keys = []
        for row in table.select(['cell_line_id', 'plate', 'drug', 'sample']).to_pylist():
            sample = str(row['sample'])
            plate, name, dose = samples[sample]
            if plate != str(row['plate']) or name != row['drug']: raise ValueError('Sample/cell metadata disagree')
            if row['cell_line_id'] is None: raise ValueError('Missing cell line')
            keys.append((str(row['cell_line_id']), plate, name, dose))
            out['selected_samples'][sample] = out['selected_samples'].get(sample, 0) + 1
        unique = sorted(set(keys))
        lookup = {k: i for i, k in enumerate(unique)}
        code = np.array([lookup[k] for k in keys])
        cell = np.repeat(np.arange(len(keys)), np.diff(off))
        block = np.bincount(code[cell[valid]] * len(tokens) + pos[valid], weights=val[valid],
                            minlength=len(unique) * len(tokens)).reshape(len(unique), len(tokens))
        for j, key in enumerate(unique):
            acc = out['groups'].setdefault(key, [np.zeros(len(tokens)), 0, 0.0])
            acc[0] += block[j]
            acc[1] += int((code == j).sum())
            acc[2] += float(block[j].sum())
    return out


def read_shard(i, revision, tokens, samples, wanted):
    import requests
    url = f'https://huggingface.co/datasets/tahoebio/Tahoe-100M/resolve/{revision}/data/train-{i:05d}-of-{N_SHARDS:05d}.parquet'
    with requests.Session() as session, RangeFile(url, session) as f:
        with pa.PythonFile(f, mode='r') as stream:
            out = scan(pq.ParquetFile(stream), tokens, samples, wanted, i)
            out['bytes_read'], out['file_bytes'] = f.bytes, f.size
    return out


def write_output(out, groups, genes, manifest):
    keys = sorted(groups)
    if not keys: raise ValueError('No selected cells')
    controls = {(k[0], k[1]) for k in keys if k[2] == VEHICLE}
    missing = [k for k in keys if k[2] != VEHICLE and k[:2] not in controls]
    if missing: raise ValueError(f'No same-plate DMSO for {len(missing)} arms; first: {missing[:3]}; broaden shard coverage')
    np.savez_compressed(out / 'pseudobulk.npz', sums=np.stack([groups[k][0] for k in keys]),
                        n_cells=np.array([groups[k][1] for k in keys], dtype=np.int64),
                        library=np.array([groups[k][2] for k in keys]),
                        **{field: np.array([k[i] for k in keys], dtype=str)
                           for i, field in enumerate(('cell_line', 'plate', 'drug', 'dose'))},
                        **{c: genes[c].fillna('').to_numpy(dtype=str) for c in ('gene_symbol', 'ensembl_id')},
                        token_id=genes.token_id.to_numpy(dtype=np.int64))
    manifest.update(complete=True, groups=len(keys), selected_cells=sum(v[1] for v in groups.values()),
                    vehicle_cells=sum(v[1] for k, v in groups.items() if k[2] == VEHICLE))
    with (out / 'manifest.json').open('x', encoding='utf-8') as f: json.dump(manifest, f, indent=2)


def selftest():
    metadata = pd.DataFrame([
        dict(sample=s, plate=p, drug=d, drugname_drugconc=repr([(d, v, 'uM')]))
        for s, p, d, v in [('c1','p1',VEHICLE,0), ('a','p1','A',0.1), ('b','p1','A',1),
                            ('c2','p2',VEHICLE,0), ('a2','p2','A',0.1)]])
    samples = sample_lookup(metadata)
    rows = []
    for s, line, gs, xs in [('c1','L1',[0,3,8],[-1,2,4]), ('a','L1',[3,3,8],[1,2,5]),
                           ('b','L1',[],[]), ('c2','L2',[3],[7]), ('a2','L2',[8],[9]),
                           ('a','L1',[3],[4])]:
        p, d, _ = samples[s]
        rows.append(dict(sample=s, plate=p, drug=d, cell_line_id=line, genes=gs, expressions=xs))
    rows += [dict(sample='ignored', plate='p3', drug='X', cell_line_id='L3', genes=[999], expressions=[2])] * 2
    # Temporary artifacts stay under the authorized new folder.
    with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as tmp:
        path = Path(tmp) / 'tiny.parquet'
        pq.write_table(pa.Table.from_pylist(rows), path, row_group_size=2)
        got = scan(pq.ParquetFile(path), np.array([3,8]), samples, {'A',VEHICLE}, 0)
        ref = {}
        for row in rows[:6]:
            p, d, dose = samples[row['sample']]
            key = (row['cell_line_id'],p,d,dose)
            acc = ref.setdefault(key, [np.zeros(2),0,0.0]); acc[1] += 1
            for j, (token, count) in enumerate(zip(row['genes'], row['expressions'])):
                if j == 0 and count < 0: continue
                acc[0][{3:0,8:1}[token]] += count; acc[2] += count
        assert got['selected_row_groups'] == [0,1,2]
        assert got['selected_samples']['a'] == 2
        assert got['groups'].keys() == ref.keys()
        for k in ref:
            np.testing.assert_array_equal(got['groups'][k][0], ref[k][0])
            assert got['groups'][k][1:] == ref[k][1:]
        gm = pd.DataFrame(dict(token_id=[3,8], gene_symbol=['G1','G2'], ensembl_id=['E1','E2']))
        dest = Path(tmp)/'out'; dest.mkdir()
        write_output(dest, ref, gm, {})
        with np.load(dest/'pseudobulk.npz', allow_pickle=False) as z: assert z['n_cells'].sum() == 6
        try: dest.mkdir(exist_ok=False)
        except FileExistsError: pass
        else: raise AssertionError('Overwrite allowed')
        bad = dict(ref); del bad[('L2','p2',VEHICLE,'0 uM')]
        try: write_output(Path(tmp), bad, gm, {})
        except ValueError: pass
        else: raise AssertionError('Missing control accepted')
        rows[0]['expressions'] = [1,-2,3]
        pq.write_table(pa.Table.from_pylist(rows), path)
        try: scan(pq.ParquetFile(path), np.array([3,8]), samples, {'A',VEHICLE}, 0)
        except ValueError: pass
        else: raise AssertionError('Invalid counts accepted')
    print('PASS: synthetic parquet, reference sums, doses, plates, duplicates, marker, empty cells, RG filter, NPZ, missing controls, overwrite, invalid counts; no network')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--selftest', action='store_true')
    ap.add_argument('--drugs', type=Path); ap.add_argument('--out', type=Path)
    ap.add_argument('--metadata', type=Path, default=META)
    ap.add_argument('--revision', help='Full 40-character HF commit; local metadata must match')
    ap.add_argument('--step', type=int, default=5); ap.add_argument('--offset', type=int, default=0)
    ap.add_argument('--workers', type=int, default=4); ap.add_argument('--max-shards', type=int, default=0)
    args = ap.parse_args()
    if args.selftest: selftest(); return
    if not args.drugs or not args.out or not re.fullmatch('[0-9a-fA-F]{40}', args.revision or ''):
        ap.error('--drugs, --out and a full commit --revision are required')
    if args.step < 1 or not 0 <= args.offset < N_SHARDS or args.workers < 1 or args.max_shards < 0:
        ap.error('Invalid shard selection/workers')
    drugs = pd.read_csv(args.drugs, keep_default_na=False)['drug']
    if drugs.empty or (drugs.str.strip() == '').any(): raise ValueError('Empty drug selection')
    wanted = set(drugs) | {VEHICLE}
    sm = pd.read_parquet(args.metadata/'sample_metadata.parquet')
    if wanted - set(sm.drug): raise ValueError(f'Drugs absent from samples: {wanted - set(sm.drug)}')
    samples = sample_lookup(sm)
    genes = pd.read_parquet(args.metadata/'gene_metadata.parquet').sort_values('token_id')
    tokens = genes.token_id.to_numpy(dtype=np.int64)
    if (np.diff(tokens) <= 0).any(): raise ValueError('Duplicate gene tokens')
    args.out.mkdir(parents=True, exist_ok=False)
    (args.out/'metadata').mkdir()
    hashes = {}
    for name in ('sample','drug','gene','cell_line'):
        src = args.metadata/f'{name}_metadata.parquet'
        shutil.copy2(src, args.out/'metadata'/src.name)
        hashes[src.name] = hashlib.sha256(src.read_bytes()).hexdigest()
    shutil.copy2(args.drugs, args.out/'drugs.csv')
    shards = list(range(args.offset, N_SHARDS, args.step))
    if args.max_shards: shards = shards[:args.max_shards]
    groups, per_shard = {}, []
    with ThreadPoolExecutor(args.workers) as pool:
        # Bound in-flight results: a completed Future otherwise retains a dense block per shard.
        for start in range(0, len(shards), args.workers):
            futures = [pool.submit(read_shard, i, args.revision, tokens, samples, wanted)
                       for i in shards[start:start+args.workers]]
            for future in futures:
                result = future.result()
                for key, value in result.pop('groups').items():
                    acc = groups.setdefault(key, [np.zeros(len(tokens)),0,0.0])
                    acc[0] += value[0]; acc[1] += value[1]; acc[2] += value[2]
                per_shard.append(result)
            print(f'{len(per_shard)}/{len(shards)} shards; {sum(v[1] for v in groups.values())} selected cells', flush=True)
    manifest = dict(stage=__file__, repo='tahoebio/Tahoe-100M', revision=args.revision,
                    subset=dict(step=args.step, offset=args.offset, shards=shards), metadata_sha256=hashes,
                    requested_drugs=sorted(wanted), per_shard=per_shard,
                    bytes_read=sum(r['bytes_read'] for r in per_shard),
                    sample_map='No metadata shard map; selected_samples records observed cells only, not all samples in each shard',
                    claim_type='data extraction; no model result')
    write_output(args.out, groups, genes, manifest)
    print(json.dumps({k: manifest[k] for k in ('groups','selected_cells','vehicle_cells','bytes_read')}))


if __name__ == '__main__': main()
