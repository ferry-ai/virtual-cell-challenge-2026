"""Post-hoc biology and failure diagnostics from completed small confirmation reports.

Does not read cells, modify predictions, or select candidates. GO/HGNC inputs are
the immutable public snapshots already present in the project data root.
"""
from __future__ import annotations
import argparse
from collections import defaultdict, Counter
from datetime import datetime, timezone
import gzip
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd
from scipy.stats import spearmanr, rankdata, fisher_exact, t as tdist

HERE = Path(__file__).resolve().parent
LEAD = HERE.parent
PROGRAMS = {'ribosome': ['GO:0005840','GO:0042254'],
            'spliceosome_rna_splicing': ['GO:0005681','GO:0008380'],
            'mitochondrion': ['GO:0005739'],
            'cell_cycle': ['GO:0007049'],
            'intracellular_vesicle_trafficking': ['GO:0016192','GO:0006886']}


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as f:
        for b in iter(lambda:f.read(1<<20),b''): h.update(b)
    return h.hexdigest()


def text_stream(path):
    with Path(path).open('rb') as f: compressed=f.read(2)==b'\x1f\x8b'
    return gzip.open(path,'rt',encoding='utf-8') if compressed else Path(path).open(encoding='utf-8')


def ontology(path):
    terms, header, current = {}, [], None
    with text_stream(path) as f:
        for line in f:
            line=line.strip()
            if line=='[Term]':
                if current and 'id' in current: terms[current['id']]=current
                current={'parents':[],'alt':[],'obsolete':False}
            elif line.startswith('['):
                if current and 'id' in current: terms[current['id']]=current
                current=None
            elif current is None:
                if line.startswith(('data-version:','date:')): header.append(line)
            elif line.startswith('id: '): current['id']=line[4:]
            elif line.startswith('name: '): current['name']=line[6:]
            elif line.startswith('alt_id: '): current['alt'].append(line[8:])
            elif line.startswith('is_a: '): current['parents'].append(line[6:].split()[0])
            elif line.startswith('relationship: part_of '): current['parents'].append(line.split()[2])
            elif line=='is_obsolete: true': current['obsolete']=True
    if current and 'id' in current: terms[current['id']]=current
    children=defaultdict(set)
    for tid,v in terms.items():
        if not v['obsolete']:
            for parent in v['parents']: children[parent].add(tid)
    def descendants(roots):
        seen=set(roots); todo=list(roots)
        while todo:
            for child in children[todo.pop()]:
                if child not in seen: seen.add(child); todo.append(child)
        return seen
    groups={k:descendants(v) for k,v in PROGRAMS.items()}
    aliases={alias:tid for tid,v in terms.items() for alias in v['alt']}
    return terms,groups,aliases,header


def annotate(snapshot, wanted):
    hgnc=pd.read_csv(snapshot/'hgnc_complete_set',sep='\t',keep_default_na=False)
    hgnc=hgnc[hgnc.status=='Approved']
    approved=set(hgnc.symbol); synonyms=defaultdict(set); protein=defaultdict(set)
    for row in hgnc.itertuples():
        for field in (row.prev_symbol,row.alias_symbol):
            for name in field.split('|'):
                if name: synonyms[name].add(row.symbol)
        for acc in row.uniprot_ids.split('|'):
            if acc: protein[acc].add(row.symbol)
    def resolve(name):
        if name in approved: return name,'approved'
        options=synonyms.get(name,set())
        return (next(iter(options)),'unique_previous_or_alias') if len(options)==1 else ('','ambiguous_or_unmapped')
    mapping={name:resolve(name) for name in sorted(wanted)}
    requested={v[0] for v in mapping.values() if v[0]}
    terms,groups,aliases,obo_header=ontology(snapshot/'go_basic_obo')
    membership={name:set() for name in requested}; experimental={name:set() for name in requested}
    evidence=[]; headers=[]; ignored_not=0; annotations=Counter(); unknown=Counter()
    experimental_codes={'EXP','IDA','IPI','IMP','IGI','IEP','HTP','HDA','HMP','HGI','HEP'}
    with text_stream(snapshot/'goa_human_gaf') as f:
        for line in f:
            if line.startswith('!'):
                if len(headers)<15: headers.append(line.strip())
                continue
            cols=line.rstrip('\n').split('\t')
            if len(cols)<15 or not cols[12].split('|')[0]=='taxon:9606': continue
            candidates=protein.get(cols[1],set())
            gene=next(iter(candidates)) if len(candidates)==1 else resolve(cols[2])[0]
            if gene not in requested: continue
            if 'NOT' in cols[3].split('|'): ignored_not+=1; continue
            go=aliases.get(cols[4],cols[4]); annotations[gene]+=1
            if go not in terms: unknown[go]+=1
            for name,desc in groups.items():
                if go in desc:
                    membership[gene].add(name)
                    if cols[6] in experimental_codes: experimental[gene].add(name)
                    evidence.append({'approved_symbol':gene,'program':name,'go_id':go,
                        'go_name':terms.get(go,{}).get('name',''),'evidence_code':cols[6],
                        'reference':cols[5],'assigned_by':cols[14],'annotation_date':cols[13],
                        'protein_id':cols[1], 'qualifier':cols[3]})
    out=[]
    for target,(canonical,resolution) in mapping.items():
        out.append({'target':target,'approved_symbol':canonical,'resolution':resolution,
                    'positive_go_annotations':annotations[canonical],
                    **{p:p in membership.get(canonical,set()) for p in PROGRAMS},
                    **{p+'_experimental':p in experimental.get(canonical,set()) for p in PROGRAMS}})
    return pd.DataFrame(out).set_index('target'),pd.DataFrame(evidence).drop_duplicates(),{
        'ontology_header':obo_header,'gaf_header':headers,'NOT_annotations_excluded':ignored_not,
        'unknown_go_terms':dict(unknown),'roots':{p:{t:terms[t]['name'] for t in roots} for p,roots in PROGRAMS.items()},
        'resolution_counts':dict(Counter(v[1] for v in mapping.values())),
        'propagation':'is_a and part_of only; no regulates/has_part inference',
        'absence_of_annotation_is_not_evidence_of_absence':True}


def bh(p):
    p=np.asarray(p,float); order=np.argsort(p); q=np.ones(len(p))
    ranked=np.minimum.accumulate((p[order]*len(p)/np.arange(1,len(p)+1))[::-1])[::-1]
    q[order]=np.minimum(ranked,1); return q


def corr(y,x,controls=None):
    y,x=np.asarray(y,float),np.asarray(x,float)
    ok=np.isfinite(y)&np.isfinite(x)
    if controls is not None: ok &= np.isfinite(controls).all(1)
    y,x=y[ok],x[ok]
    if len(y)<5 or len(np.unique(x))<2: return {'n':len(y),'rho':None,'p_exploratory':None}
    if controls is None: r,p=spearmanr(y,x)
    else:
        z=np.asarray(controls)[ok]; z=np.c_[np.ones(len(x)),np.stack([rankdata(z[:,j]) for j in range(z.shape[1])],axis=1)]
        yr,xr=rankdata(y),rankdata(x)
        yr-=z@np.linalg.lstsq(z,yr,rcond=None)[0]; xr-=z@np.linalg.lstsq(z,xr,rcond=None)[0]
        r=float(np.corrcoef(yr,xr)[0,1]); df=len(x)-z.shape[1]-1
        p=float(2*tdist.sf(abs(r)*np.sqrt(df/max(1-r*r,1e-15)),df))
    return {'n':len(y),'rho':float(r),'p_exploratory':float(p)}


def ols_hc3(y,x):
    x=np.c_[np.ones(len(y)),np.asarray(x,float)]
    inverse=np.linalg.pinv(x.T@x); beta=inverse@x.T@y; resid=y-x@beta
    h=np.einsum('ij,jk,ik->i',x,inverse,x)
    cov=inverse@(x.T@((resid/np.maximum(1-h,1e-8))[:,None]**2*x))@inverse
    se=np.sqrt(np.maximum(np.diag(cov),0)); df=len(y)-np.linalg.matrix_rank(x)
    pv=2*tdist.sf(np.abs(beta)/np.maximum(se,1e-15),df)
    return {'coefficient':float(beta[-1]),'se_hc3':float(se[-1]),'p_exploratory':float(pv[-1]),
            'design_rank':int(np.linalg.matrix_rank(x)),'condition_number':float(np.linalg.cond(x))}


def load_metrics():
    p=LEAD/'generator_confirmation_r3/confirmation'; metrics={}
    for arm in ('a1_p0','a1p5_p1'):
        tables=[]
        for seed in (1,2,3):
            table=pd.read_csv(p/f'per_pert_{arm}_s{seed}.csv',keep_default_na=False)
            table['value']=pd.to_numeric(table.value,errors='coerce')
            tables.append(table.pivot(index='perturbation',columns='metric',values='value'))
        metrics[arm]=sum(tables)/3
    return metrics


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--data-root',type=Path,required=True); p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.out.exists(): raise FileExistsError(a.out)
    analysis=LEAD/'confirmation_analysis/results_r1'
    table=pd.read_csv(analysis/'target_contributions.csv').query("arm == 'a1p5_p1'").set_index('target')
    byseed=pd.read_csv(analysis/'target_by_seed.csv').query("arm == 'a1p5_p1'")
    baseline=pd.read_csv(LEAD/'generator_confirmation_r3/confirmation/components_a1_p0_s1.csv').set_index('target')
    metrics=load_metrics(); truth=metrics['a1_p0']['expr_distance_unbiased'].reindex(table.index)
    table['true_effect_distance_unbiased']=truth
    table['baseline_PDS']=metrics['a1_p0']['pds_cosine'].reindex(table.index)
    table['baseline_FID']=metrics['a1_p0']['de_wilcoxon_direction_fidelity_yield_raw'].reindex(table.index)
    table['baseline_REACH']=metrics['a1_p0']['de_wilcoxon_direction_reach_raw'].reindex(table.index)
    table['baseline_NMAE']=metrics['a1_p0']['de_wilcoxon_lfc_nmae'].reindex(table.index)
    table['baseline_JAC']=metrics['a1_p0']['de_wilcoxon_sig_jaccard'].reindex(table.index)
    for short,name in [('FID','de_wilcoxon_direction_fidelity_yield_raw'),('REACH','de_wilcoxon_direction_reach_raw'),
                       ('PDS','pds_cosine'),('NMAE','de_wilcoxon_lfc_nmae'),('JAC','de_wilcoxon_sig_jaccard')]:
        table['raw_delta_'+short]=(metrics['a1p5_p1'][name]-metrics['a1_p0'][name]).reindex(table.index)
    byseed['precision']=byseed.k/byseed.n_pred
    byseed['baseline_precision']=byseed.reference_k/byseed.reference_n_pred
    byseed['precision_delta']=byseed.precision-byseed.baseline_precision
    byseed['n_pred_delta']=byseed.n_pred-byseed.reference_n_pred
    for col in ('precision','baseline_precision','precision_delta','n_pred','reference_n_pred','k','reference_k','n_pred_delta'):
        table[col]=byseed.groupby('target')[col].mean().reindex(table.index)
    table['negative_in_all_seeds']=byseed.groupby('target').contribution_to_projection.max().reindex(table.index)<0
    table['positive_in_all_seeds']=byseed.groupby('target').contribution_to_projection.min().reindex(table.index)>0
    diagnostics=pd.DataFrame(json.loads((LEAD/'generator_confirmation_r3/confirmation/diagnostics_a1_p0_s1.json').read_text())).set_index('target')
    table['source_expected_energy_all_genes']=diagnostics.expected_energy_all_genes.reindex(table.index)
    manifest_path=LEAD/'generator_confirmation_r3/target_manifest.json'
    manifest=json.loads(manifest_path.read_text()); eligible=set(manifest['eligible'])
    panel_path=a.data_root/'processed/rete_contesti_r2/targets.csv'
    panel_table=pd.read_csv(panel_path,keep_default_na=False)
    panel=set(panel_table.loc[panel_table.in_panel.astype(str).str.lower()=='true','target'])
    annotations,evidence,annotation_meta=annotate(a.data_root/'interim/encoder_inputs_2026-09-14', eligible|panel)
    table=table.join(annotations)
    y=table.contribution_to_projection.to_numpy()*96
    core=['true_effect_distance_unbiased','n_conf','real_cells','source_expected_energy_all_genes',
          'baseline_precision','baseline_FID','baseline_REACH','baseline_PDS','baseline_NMAE','baseline_JAC']
    correlations=[]
    for feature in core:
        correlations.append({'feature':feature,'kind':'baseline_or_truth',**corr(y,table[feature])})
    for feature in ['precision_delta','raw_delta_FID','raw_delta_REACH','raw_delta_PDS','raw_delta_NMAE','raw_delta_JAC','n_pred_delta']:
        correlations.append({'feature':feature,'kind':'algebraically_or_outcome_coupled',**corr(y,table[feature])})
    for kind in ('baseline_or_truth','algebraically_or_outcome_coupled'):
        subset=[r for r in correlations if r['kind']==kind and r['p_exploratory'] is not None]
        for r,q in zip(subset,bh([r['p_exploratory'] for r in subset])):r['q_BH_exploratory']=float(q)
    controls=np.c_[table.n_conf,table.real_cells]
    partial={'true_distance_given_nconf_cells':corr(y,table.true_effect_distance_unbiased,controls),
             'nconf_given_true_distance_cells':corr(y,table.n_conf,np.c_[truth,table.real_cells]),
             'cells_given_true_distance_nconf':corr(y,table.real_cells,np.c_[truth,table.n_conf])}
    signed=np.sign(truth)*np.log1p(np.abs(truth))
    adjust=np.c_[np.log1p(table.n_conf),np.log1p(table.real_cells),signed]
    group_results=[]; sampling=[]
    conf=set(table.index); remainder=eligible-conf
    for program in PROGRAMS:
        flag=table[program].to_numpy(bool); n=int(flag.sum()); other=~flag
        estimate=ols_hc3(y,np.c_[adjust,flag.astype(float)]) if 3<=n<=len(y)-3 else None
        members=table.index[flag].tolist()
        group_results.append({'program':program,'n':n,'members':members,
            'n_experimental':int(table[program+'_experimental'].sum()),
            'mean_target_contribution_times96':float(y[flag].mean()) if n else None,
            'mean_other_times96':float(y[other].mean()),
            'net_contribution':float(table.loc[flag,'contribution_to_projection'].sum()),
            'positive_fraction':float(np.mean(y[flag]>0)) if n else None,
            'median_nconf':float(table.loc[flag,'n_conf'].median()) if n else None,
            'median_true_distance':float(table.loc[flag,'true_effect_distance_unbiased'].median()) if n else None,
            'median_cells':float(table.loc[flag,'real_cells'].median()) if n else None,
            'adjusted_hc3_exploratory':estimate})
        counts={name:[int(annotations.loc[sorted(cohort),program].sum()),len(cohort)]
                for name,cohort in [('confirmation',conf),('remaining_eligible',remainder),('challenge_panel',panel)]}
        for comparison in ('remaining_eligible','challenge_panel'):
            k0,n0=counts['confirmation'];k1,n1=counts[comparison]
            odds,pval=fisher_exact([[k0,n0-k0],[k1,n1-k1]])
            sampling.append({'program':program,'comparison':comparison,'selected':k0,'selected_total':n0,
                'comparison_count':k1,'comparison_total':n1,'odds_ratio':float(odds),'p_exploratory':float(pval)})
    valid=[r for r in group_results if r['adjusted_hc3_exploratory']]
    for r,q in zip(valid,bh([r['adjusted_hc3_exploratory']['p_exploratory'] for r in valid])):
        r['adjusted_hc3_exploratory']['q_BH_five_programs']=float(q)
    for comparison in ('remaining_eligible','challenge_panel'):
        rows=[r for r in sampling if r['comparison']==comparison]
        for r,q in zip(rows,bh([r['p_exploratory'] for r in rows])):r['q_BH_five_programs']=float(q)
    quartiles=[]
    for feature in ('n_conf','true_effect_distance_unbiased','real_cells'):
        cut=pd.qcut(table[feature].rank(method='first'),4,labels=False)
        for q in range(4):
            subset=table[cut==q]
            quartiles.append({'feature':feature,'quartile':q+1,'n':len(subset),
                'feature_min':float(subset[feature].min()),'feature_max':float(subset[feature].max()),
                'gain_contribution':float(subset.contribution_to_projection.sum()),
                'positive':int((subset.contribution_to_projection>0).sum()),
                'median_n_conf':float(subset.n_conf.median()),'median_cells':float(subset.real_cells.median())})
    keepcols=['contribution_to_projection','n_conf','real_cells','true_effect_distance_unbiased','baseline_precision',
              'precision_delta','raw_delta_FID','raw_delta_REACH','raw_delta_PDS','raw_delta_NMAE','raw_delta_JAC',
              'negative_in_all_seeds',*PROGRAMS]
    source_paths=[analysis/'target_contributions.csv',analysis/'target_by_seed.csv',manifest_path,panel_path,
                  *[a.data_root/'interim/encoder_inputs_2026-09-14'/n for n in ('hgnc_complete_set','goa_human_gaf','go_basic_obo')]]
    result={'created_utc':datetime.now(timezone.utc).isoformat(),'claim_type':'POST HOC exploratory biology; no candidate selection or changed criteria',
        'targets':len(table),'all_truth_distances_finite':bool(np.isfinite(truth).all()),'negative_true_distances':int((truth<0).sum()),
        'annotation':annotation_meta,'correlations':correlations,'partial_rank_correlations':partial,
        'programs':group_results,'sampling_comparisons':sampling,'quartiles':quartiles,
        'all_three_seeds_negative':table.index[table.negative_in_all_seeds].tolist(),
        'all_three_seeds_positive':int(table.positive_in_all_seeds.sum()),
        'worst10':table.nsmallest(10,'contribution_to_projection')[keepcols].reset_index().to_dict('records'),
        'pds_worst10':table.nsmallest(10,'raw_delta_PDS')[keepcols].reset_index().to_dict('records'),
        'source_files':{str(path):{'bytes':path.stat().st_size,'sha256':sha(path)} for path in source_paths},
        'script_sha256':sha(Path(__file__))}
    a.out.mkdir(parents=True)
    table.reset_index().to_csv(a.out/'per_target.csv',index=False)
    annotations.reset_index().to_csv(a.out/'annotations_by_target.csv',index=False)
    evidence.to_csv(a.out/'annotation_evidence.csv',index=False)
    (a.out/'analysis.json').write_text(json.dumps(result,indent=2,default=lambda x:x.item() if isinstance(x,np.generic) else str(x))+'\n',encoding='utf-8')
    print(json.dumps({'out':str(a.out),'targets':len(table),'program_counts':{r['program']:r['n'] for r in group_results},
                      'correlations':correlations,'partial':partial},indent=2))


if __name__=='__main__':main()
