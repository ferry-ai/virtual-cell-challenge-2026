"""Post-hoc descriptive source-coverage audit from small reports and metadata; no effect reads."""
import argparse
from datetime import datetime,timezone
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

HERE=Path(__file__).resolve().parent
FAMILIES=['k562','cd4','orion','ipsc','rpe1']


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize(frame):
    cells=frame.groupby(['family','context'],sort=True).agg(
        delta_transfer=('delta_transfer','mean'),delta_blind=('delta_blind','mean'),
        baseline_cosine=('baseline_cosine','mean'),support_fraction=('support_fraction','mean'),
        direct_contexts=('direct_contexts','mean'),net_norm_ratio=('net_norm_ratio','mean'),
        n=('target','size'))
    macro=cells.groupby(level='family').mean(numeric_only=True).mean(numeric_only=True)
    return {'n':len(frame),'families':int(frame.family.nunique()),'contexts':int(frame.context.nunique()),
            'macro_equal_family_context_delta_transfer':float(macro.delta_transfer),
            'macro_equal_family_context_delta_blind':float(macro.delta_blind),
            'support_fraction_median':float(frame.support_fraction.median()),
            'direct_contexts_median':float(frame.direct_contexts.median()),
            'baseline_cosine_median':float(frame.baseline_cosine.median()),
            'net_norm_ratio_median':float(frame.net_norm_ratio.median())}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--data',type=Path,required=True)
    ap.add_argument('--out',type=Path,required=True)
    args=ap.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    reports=HERE/'kaggle_neural_r1/results_small_r1/neural_sources_r1/folds'
    base=json.loads((reports/'C_k562_s0/manifest.json').read_text())
    metadata_names=['manifest.json','contexts.csv','targets.csv','row_target.npy','row_context.npy',
                    'partner_index.npy','partner_indptr.npy','partner_score.npy']
    for name in metadata_names:
        if digest(args.data/name)!=base['data_files'][name]['sha256']:
            raise ValueError(f'Metadata differs from seed0: {name}')
    targets=pd.read_csv(args.data/'targets.csv',keep_default_na=False)
    contexts=pd.read_csv(args.data/'contexts.csv',keep_default_na=False)
    target_index={name:i for i,name in enumerate(targets.target)}
    tss=pd.to_numeric(targets.tss,errors='coerce').to_numpy(float)
    chrom=targets.chrom.to_numpy(str)
    arrays={name:np.load(args.data/f'{name}.npy',mmap_mode='r',allow_pickle=False)
            for name in ('row_target','row_context','partner_index','partner_indptr','partner_score')}
    all_rows=[];run_summaries={}
    for family in FAMILIES:
        run=reports/f'C_{family}_s0'
        manifest=json.loads((run/'manifest.json').read_text())
        table=pd.read_csv(run/'per_target.csv',keep_default_na=False)
        refit=np.asarray(manifest['design']['refit'],int)
        visible_contexts=np.unique(arrays['row_context'][refit])
        available={int(c):set(arrays['row_target'][refit[arrays['row_context'][refit]==c]].tolist()) for c in visible_contexts}
        wide={metric:table.pivot(index=['family','context','target'],columns='arm',values=metric)
              for metric in ('rank','cosine','norm_ratio','source_supported_genes','common_genes','zero_baseline')}
        frame=wide['rank'][['net','transfer','blind','swap','prior_permuted']].reset_index()
        frame['delta_transfer']=frame.net-frame.transfer
        frame['delta_blind']=frame.net-frame.blind
        frame['delta_swap']=frame.net-frame.swap
        frame['baseline_cosine']=wide['cosine']['transfer'].to_numpy(float)
        frame['net_norm_ratio']=wide['norm_ratio']['net'].to_numpy(float)
        frame['blind_norm_ratio']=wide['norm_ratio']['blind'].to_numpy(float)
        frame['support_fraction']=wide['source_supported_genes']['net'].to_numpy(float)/13248
        frame['source_supported_genes']=wide['source_supported_genes']['net'].to_numpy(int)
        frame['common_truth_genes']=wide['common_genes']['net'].to_numpy(int)
        # Coverage is over all modelled response genes, not divided by the smaller
        # common truth mask; no ratio can silently exceed one from incompatible axes.
        if not ((frame.support_fraction>=0)&(frame.support_fraction<=1)).all():
            raise ValueError('Response support ratio is outside its modelled axis')
        availability=[]
        for target in frame.target:
            t=target_index[target]
            direct=[c for c,visible in available.items() if t in visible]
            a,b=arrays['partner_indptr'][t:t+2]
            partners=arrays['partner_index'][a:b]
            partners=partners[partners!=t]
            if np.isfinite(tss[t]):
                partners=partners[~((chrom[partners]==chrom[t])&(np.abs(tss[partners]-tss[t])<=5000))]
            possible=[c for c,visible in available.items() if c not in direct and any(int(p) in visible for p in partners)]
            availability.append({'direct_contexts':len(direct),
                                 'direct_families':len(set(contexts.iloc[direct].family)),
                                 'fallback_possible_contexts':len(possible),
                                 'source_contexts':len(available),
                                 'no_direct_anywhere':len(direct)==0})
        frame=pd.concat([frame,pd.DataFrame(availability)],axis=1)
        all_rows.append(frame)
        run_summaries[family]=json.loads((run/'summary.json').read_text())['best_steps']
    rows=pd.concat(all_rows,ignore_index=True)
    per_context=[]
    for context,part in rows.groupby('context',sort=True):
        family=part.family.iloc[0]
        counts=int((contexts.family==family).sum())
        per_context.append({'context':context,'family':family,**summarize(part),
                            'contribution_to_primary_macro':float(part.delta_transfer.mean()/(5*counts)),
                            'spearman_coverage_delta':float(part.support_fraction.rank().corr(part.delta_transfer.rank()))
                                if part.support_fraction.nunique()>1 else None,
                            'zero_direct_fraction':float(part.no_direct_anywhere.mean()),
                            'common_truth_genes':int(part.common_truth_genes.iloc[0])})
    if not np.isclose(sum(x['contribution_to_primary_macro'] for x in per_context),.0022223326402478804,atol=1e-12):
        raise ValueError('Context contributions do not reproduce the verified primary point')
    strata={}
    for feature in ('support_fraction','baseline_cosine'):
        column=feature+'_within_context_quartile'
        rows[column]=rows.groupby('context')[feature].transform(lambda x:pd.qcut(x,4,labels=False,duplicates='drop'))
        strata[column]={str(int(q)):summarize(part) for q,part in rows.groupby(column,dropna=True)}
    strata['direct_families']={str(int(q)):summarize(part) for q,part in rows.groupby('direct_families')}
    strata['no_direct_anywhere']={str(bool(q)):summarize(part) for q,part in rows.groupby('no_direct_anywhere')}
    result={'created_utc':datetime.now(timezone.utc).isoformat(),'claim_type':'post-hoc descriptive, noncausal, not a new promotion criterion',
            'raw_effect_values_read':False,'targets_contexts':len(rows),'unique_targets':int(rows.target.nunique()),
            'per_context':per_context,'strata':strata,'best_steps':run_summaries,
            'absolute_truth_strength':'not saved in small reports; not replaced by cosine, PDS or NMSE',
            'own_target_response':'own/cis response genes excluded by original protocol; no own-response outcome in these reports',
            'fallback':'metadata-only availability; actual token weight, SE-valid support and direct-only ablation are unavailable here',
            'macro_weighting':'equal families then equal represented contexts inside each descriptive stratum; inspect contexts/families counts',
            'uncertainty':'no post-hoc significance claims; target recurrence and subgroup composition preclude causal interpretation',
            'source_hashes':{name:digest(args.data/name) for name in metadata_names}}
    args.out.mkdir(parents=True)
    rows.to_csv(args.out/'per_target_descriptive.csv',index=False)
    pd.DataFrame(per_context).to_csv(args.out/'context_contributions.csv',index=False)
    (args.out/'summary.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print(json.dumps({'per_context':per_context,'strata':strata,'best_steps':run_summaries},indent=2,allow_nan=False))


if __name__=='__main__':
    main()
