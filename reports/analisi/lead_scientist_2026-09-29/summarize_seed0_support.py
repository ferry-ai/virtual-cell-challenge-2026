"""Additional fixed descriptive counts of direct/fallback availability, from the saved audit table."""
import json
from pathlib import Path
import pandas as pd

HERE=Path(__file__).resolve().parent
rows=pd.read_csv(HERE/'neural_descriptive_r1/per_target_descriptive.csv',keep_default_na=False)
no_direct=rows.direct_contexts==0
zero_support=rows.source_supported_genes==0
out={'target_context_pairs':len(rows),'unique_targets':int(rows.target.nunique()),
     'without_direct_target':int(no_direct.sum()),
     'without_direct_but_fallback_possible':int((no_direct&(rows.fallback_possible_contexts>0)).sum()),
     'without_direct_and_without_fallback':int((no_direct&(rows.fallback_possible_contexts==0)).sum()),
     'zero_measured_source_gene_support':int(zero_support.sum()),
     'zero_support_despite_direct_target':int((zero_support&~no_direct).sum()),
     'with_any_fallback_possible':int((rows.fallback_possible_contexts>0).sum()),
     'availability_does_not_measure_token_weight':True,
     'by_context':{}}
for context,part in rows.groupby('context'):
    out['by_context'][context]={'n':len(part),'no_direct':int((part.direct_contexts==0).sum()),
                               'no_support':int((part.source_supported_genes==0).sum()),
                               'fallback_possible':int((part.fallback_possible_contexts>0).sum()),
                               'fallback_contexts_median':float(part.fallback_possible_contexts.median()),
                               'net_norm_ratio_quantiles':part.net_norm_ratio.quantile([.1,.5,.9]).to_dict()}
path=HERE/'neural_descriptive_r1/support_counts.json'
with path.open('x',encoding='utf-8') as f:
    json.dump(out,f,indent=2,allow_nan=False)
    f.write('\n')
print(json.dumps(out,indent=2))
