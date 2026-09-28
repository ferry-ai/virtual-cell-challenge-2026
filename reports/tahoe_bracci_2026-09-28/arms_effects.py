"""Estimate Tahoe drug/dose effects per line using the project's pseudobulk estimator.

Usage: scripts/py.cmd reports/tahoe_bracci_2026-09-28/arms_effects.py --arms EXTRACT --out NEW
Plates are donors; each drug-dose is a target. Full Tahoe counts set library totals.
Then map first symbol occurrence in token order to the official axis, as corpus_tahoe.py.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'src'))
from vcc2026.genes import official_axis
from vcc2026.multisource import effects_from_pseudobulk
from extract_arms import VEHICLE


def estimate(pb, axis, min_cells=10, min_control_cells=10, min_expected=1.0):
    stored = pb['sums']
    sums = np.asarray(stored, dtype=np.float64)
    if not np.isfinite(sums).all() or (sums < 0).any(): raise ValueError('Invalid sums')
    # float32 sums (the axis-only extract of the Kaggle kernel, 28/09) round each row's total at ~1e-7
    rtol = 1e-6 if stored.dtype == np.float32 else 1e-10
    if not np.allclose(sums.sum(axis=1), pb['library'], rtol=rtol): raise ValueError('Library mismatch')
    meta = pd.DataFrame({c: pb[k].astype(str) for c, k in
                         [('line','cell_line'),('plate','plate'),('drug','drug'),('dose','dose')]})
    meta['n_cells'] = pb['n_cells']
    if meta.duplicated(['line','plate','drug','dose']).any(): raise ValueError('Duplicate pseudobulk groups')
    meta['target'] = [json.dumps([d,v]) if d != VEHICLE else 'non-targeting' for d,v in zip(meta.drug,meta.dose)]
    meta['donor'], meta['condition'] = meta.plate, 'tahoe'
    col = {g:i for i,g in enumerate(axis)}
    src, dst, seen = [], [], set()
    for i, symbol in enumerate(pb['gene_symbol'].astype(str)):
        if symbol in col and symbol not in seen:
            src.append(i); dst.append(col[symbol]); seen.add(symbol)
    payload = {k: [] for k in ('raw','shrunk','se')}
    rows, skipped = [], []
    for line in sorted(set(meta.line)):
        lm = meta.line.eq(line)
        controls = meta[lm & meta.drug.eq(VEHICLE)].groupby('plate').n_cells.sum()
        eligible = set(controls[controls >= min_control_cells].index)
        eligible &= set(meta[lm & meta.drug.eq(VEHICLE) & (sums.sum(axis=1) > 0)].plate)
        use = lm & meta.plate.isin(eligible) & (sums.sum(axis=1) > 0)
        for i in meta.index[lm & ~use]:
            skipped.append(dict(row=int(i), reason='Missing/small control or zero library'))
        targets = sorted(set(meta.loc[use & ~meta.drug.eq(VEHICLE), 'target']))
        if not targets: continue
        # Unique token labels avoid conflating duplicated gene symbols in the source estimator.
        result = effects_from_pseudobulk(sums[use], meta.loc[use], pb['token_id'].astype(str),
                                          targets=targets, min_cells=min_cells, min_expected=min_expected,
                                          min_control_frac=0.0, pseudo_scale='constant')
        for t in set(targets)-set(result.targets): skipped.append(dict(line=line,target=t,reason='Too few arm cells'))
        for j, t in enumerate(result.targets):
            drug, dose = json.loads(t)
            used = result.meta['per_donor_used'][t] if 'per_donor_used' in result.meta else sorted(
                meta.loc[use & meta.target.eq(t) & meta.n_cells.ge(min_cells), 'plate'].unique())
            rows.append(dict(cell_line=line, drug=drug, dose=dose, n_cells=int(result.n_cells[j]),
                             plates=json.dumps(used)))
            for field in payload:
                values = getattr(result, field)[j]
                row = np.full(len(axis), np.nan, dtype=np.float32)
                row[dst] = values[src]
                payload[field].append(row)
    if not rows: raise ValueError('No eligible arms')
    return {k:np.stack(v) for k,v in payload.items()}, pd.DataFrame(rows), skipped, len(dst)


def selftest():
    pb = dict(sums=np.array([[100,50,0],[20,40,0],[50,100,0],[60,20,0]],float),
              n_cells=np.array([20,10,20,10]), cell_line=np.array(['L']*4),
              plate=np.array(['p1','p1','p2','p2']), drug=np.array([VEHICLE,'A',VEHICLE,'A']),
              dose=np.array(['0 uM','1 uM','0 uM','1 uM']), gene_symbol=np.array(['G1','G2','RARE']),
              token_id=np.array([3,4,5]))
    pb['library'] = pb['sums'].sum(axis=1)
    got, rows, _, mapped = estimate(pb, ['G2','ABSENT','G1','RARE'])
    obs = pd.DataFrame(dict(target=['non-targeting','A','non-targeting','A'], donor=pb['plate'],
                            condition=['tahoe']*4, n_cells=pb['n_cells']))
    ref = effects_from_pseudobulk(pb['sums'],obs,['G1','G2','RARE'], targets=['A'],min_expected=1,min_control_frac=0)
    for k in got: np.testing.assert_array_equal(got[k][0,[2,0,3]],getattr(ref,k)[0])
    assert np.isnan(got['raw'][0,[1,3]]).all() and mapped == 3 and rows.n_cells.iloc[0] == 20
    doubled = {k: (v if k in ('gene_symbol','token_id') else np.concatenate([v,v])) for k,v in pb.items()}
    doubled['cell_line'][4:] = 'M'
    doubled['sums'][4:] = pb['sums'][:,[1,0,2]]
    doubled['library'] = doubled['sums'].sum(axis=1)
    two, two_rows, _, _ = estimate(doubled,['G2','ABSENT','G1','RARE'])
    assert two_rows.cell_line.tolist() == ['L','M']
    np.testing.assert_array_equal(two['raw'][0],got['raw'][0])
    np.testing.assert_array_equal(two['raw'][1,[2,0]],got['raw'][0,[0,2]])
    print('PASS: same-plate estimator parity, line isolation, two-plate aggregation, axis order, absent/low-evidence NaN')


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--selftest',action='store_true')
    ap.add_argument('--arms',type=Path); ap.add_argument('--out',type=Path)
    ap.add_argument('--min-cells',type=int,default=10); ap.add_argument('--min-control-cells',type=int,default=10)
    ap.add_argument('--min-expected',type=float,default=1.0)
    args = ap.parse_args()
    if args.selftest: selftest(); return
    if not args.arms or not args.out: ap.error('--arms and --out required')
    if args.min_cells < 1 or args.min_control_cells < 1 or not np.isfinite(args.min_expected) or args.min_expected < 0:
        ap.error('Invalid evidence thresholds')
    axis = np.asarray(official_axis().symbols)
    input_manifest = json.loads((args.arms/'manifest.json').read_text(encoding='utf-8'))
    if not input_manifest.get('complete'): raise ValueError('Incomplete extraction')
    with np.load(args.arms/'pseudobulk.npz',allow_pickle=False) as pb:
        values, rows, skipped, mapped = estimate(pb,axis,args.min_cells,args.min_control_cells,args.min_expected)
    args.out.mkdir(parents=True,exist_ok=False)
    np.savez_compressed(args.out/'effects.npz', **values, genes=axis,
                        **{c:rows[c].to_numpy(dtype=np.int64 if c == 'n_cells' else str) for c in rows})
    rows.to_csv(args.out/'index.csv',index=False)
    manifest = dict(input=str(args.arms), input_revision=input_manifest.get('revision'),
                    input_manifest_sha256=hashlib.sha256((args.arms/'manifest.json').read_bytes()).hexdigest(),
                    estimator='vcc2026.multisource.effects_from_pseudobulk', units='natural log fold change',
                    min_cells=args.min_cells,min_control_cells=args.min_control_cells,min_expected=args.min_expected,
                    pseudo_scale='constant',pseudo=0.5,phi=0.2,min_control_frac=0.0,
                    mapping='first symbol in token order; full source library before axis mapping',
                    axis_genes=len(axis),mapped_genes=mapped,rows=len(rows),skipped=skipped,
                    claim_type='effect estimation; no benchmark result')
    with (args.out/'manifest.json').open('x',encoding='utf-8') as f: json.dump(manifest,f,indent=2)
    print(f'{len(rows)} arms; {mapped}/{len(axis)} axis genes mapped')


if __name__ == '__main__': main()
