"""Inspect real remote HDF5 bytes under a bounded budget, no full download."""
import argparse
import json
from pathlib import Path
import h5py
import numpy as np
import pandas as pd
from vcc2026.remote_ranges import HTTPRangeReader


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('url')
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--max-mib', type=int, default=64)
    p.add_argument('--coverage', action='store_true')
    p.add_argument('--obs-col', default='gene')
    p.add_argument('--qc-col', default=None, help='Boolean low-quality column; keep False')
    p.add_argument('--curated-guides', type=Path, help='CD4 sgRNA_library_curated.csv')
    args=p.parse_args()
    result={}
    with HTTPRangeReader(args.url, max_bytes=args.max_mib*1024**2) as remote:
        with h5py.File(remote, 'r') as f:
            result['roots']=list(f)
            for name in ['X','obs','var','layers']:
                if name not in f: continue
                g=f[name]
                if isinstance(g,h5py.Dataset):
                    result[name]={'shape':g.shape,'dtype':str(g.dtype)}
                else:
                    result[name]={key: {'kind':'dataset','shape':item.shape,'dtype':str(item.dtype)} if isinstance(item,h5py.Dataset) else {'kind':'group','keys':list(item)} for key,item in g.items()}
            x=f['X']
            sample=x[:8,:] if isinstance(x,h5py.Dataset) else x['data'][:10000]
            result['sample']={'min':float(np.min(sample)), 'max':float(np.max(sample)), 'n':sample.size,
                              'finite':bool(np.isfinite(sample).all()), 'integer':bool(np.equal(sample,np.rint(sample)).all())}
            if args.coverage:
                def values(group, key):
                    node = group[key]
                    if isinstance(node, h5py.Group):
                        cats = node['categories'].asstr()[:]
                        codes = node['codes'][:]
                    elif '__categories' in group and key in group['__categories']:
                        cats = group['__categories'][key].asstr()[:]
                        codes = node[:]
                    else:
                        return node.asstr()[:]
                    out = np.full(len(codes), '', dtype=object)
                    valid = codes >= 0
                    out[valid] = cats[codes[valid]]
                    return out
                obs = values(f['obs'], args.obs_col)
                keep = np.ones(len(obs), dtype=bool)
                if args.qc_col:
                    quality=f['obs'][args.qc_col][:]
                    if quality.dtype != np.bool_: raise ValueError('QC column must be boolean')
                    keep = ~quality
                result['cells_kept_by_qc'] = int(keep.sum())
                if 'guide_type' in f['obs']:
                    types=values(f['obs'],'guide_type')
                    result['guide_type_counts']={str(k):int(v) for k,v in pd.Series(types[keep]).value_counts().items()}
                    keep &= np.isin(types, ['targeting', 'non-targeting'])
                    result['explicit_ntc_count'] = int(((types == 'non-targeting') & keep).sum())
                    if args.curated_guides:
                        design=pd.read_csv(args.curated_guides)
                        if design.sgrna_id.duplicated().any(): raise ValueError('Ambiguous guide map')
                        mapped=pd.Series(values(f['obs'],'guide_id')).map(design.set_index('sgrna_id').perturbed_gene_name).fillna('').to_numpy()
                        result['unmapped_targeting_cells'] = int((keep & (types == 'targeting') & (mapped == '')).sum())
                        keep &= (types == 'non-targeting') | (mapped != '')
                        obs = mapped
                        obs[types == 'non-targeting'] = 'non-targeting'
                        result['curated_guide_map'] = str(args.curated_guides)
                result['cells_kept_for_ingestion'] = int(keep.sum())
                obs=obs[keep]
                counts = pd.Series(obs).value_counts()
                panel = set(pd.read_csv('C:/Users/ferra/vcc2026-data/raw/controls/pert_counts.csv').target_gene)
                result['perturbation_counts'] = {str(k): int(v) for k,v in counts.items()}
                result['target_hits'] = sorted(panel & set(counts.index))
                result['ntc_labels'] = {str(k): int(v) for k,v in counts.items() if str(k) == 'non-targeting'}
                names = values(f['var'], 'gene_name')
                genes = set(pd.read_csv('C:/Users/ferra/vcc2026-data/raw/controls/gene_names.csv').gene_name)
                result['output_gene_overlap'] = len(genes & set(names))
                result['output_gene_names'] = names.tolist()
        result.update(url=args.url,bytes_transferred=remote.transferred,remote_size=remote.size)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['perturbation_counts','output_gene_names']},indent=2))


if __name__=='__main__': main()
