"""Produce per-target coverage; distinguish library design from observed cells."""
import json
from pathlib import Path
import pandas as pd

ROOT=Path('reports/candidate_verification')
DATA=Path('C:/Users/ferra/vcc2026-data')
panel=pd.read_csv(DATA/'raw/controls/pert_counts.csv').target_gene
assert len(panel)==300 and panel.is_unique
table=pd.DataFrame(index=pd.Index(panel,name='target_gene'))
cd4=pd.read_csv(ROOT/'annotations/cd4_design.csv')
orion=pd.read_csv(ROOT/'annotations/orion_guide_library.csv')
table['cd4_library']=table.index.isin(cd4.perturbed_gene_name)
table['orion_library']=table.index.isin(orion.target_gene_name)
summary={}
for name,file in [('cd4_D1_Rest','cd4_curated_probe.json'),('orion_HCT116_Batch1','orion_probe.json'),
                  ('jurkat','jurkat_probe.json'),('hepg2','hepg2_probe.json'),('rpe1','rpe1_probe.json')]:
    r=json.loads((ROOT/file).read_text())
    counts=r.get('perturbation_counts',r.get('target_counts',{}))
    table[name+'_cells']=[int(counts.get(t,0)) for t in table.index]
    summary[name]={'observed_targets':int((table[name+'_cells']>0).sum()),
                   'targets_with_at_least_30_cells':int((table[name+'_cells']>=30).sum()),
                   'targets_with_at_least_100_cells':int((table[name+'_cells']>=100).sum()),
                   'output_gene_overlap':r['output_gene_overlap']}
for path in (DATA/'external/vcc2025').glob('pert_counts_*.csv'):
    table['H1_'+path.stem.split('_')[-1]]=table.index.isin(pd.read_csv(path).target_gene)
audit=json.loads(Path('reports/data_audit/audit.json').read_text())
summary['existing_assets']=audit
summary['library_coverage']={'cd4':int(table.cd4_library.sum()),'orion':int(table.orion_library.sum())}
summary['coverage_method']='Exact symbol intersection; library presence is not observed usable-cell coverage. Missing output genes are unmeasured, not zero effects.'
table.to_csv(ROOT/'panel_coverage.csv')
(ROOT/'coverage_summary.json').write_text(json.dumps(summary,indent=2),encoding='utf8')
print(json.dumps({k:v for k,v in summary.items() if k!='existing_assets'},indent=2))
