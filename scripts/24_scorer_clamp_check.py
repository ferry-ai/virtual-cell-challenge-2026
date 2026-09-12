"""Verify score floors with synthetic baseline/replicate anchors, not leaderboard estimates."""
from dataclasses import replace
from importlib.metadata import version
import hashlib
import inspect
import json
from pathlib import Path
import cell_eval2.scoring as scoring
from cell_eval2.catalog import CATALOG

assert version('cell-eval2')=='0.16.0'
result={'version':version('cell-eval2'),'synthetic_baseline':1.0,'synthetic_replicate_anchor':0.1,
        'source_sha256':hashlib.sha256(Path(inspect.getfile(scoring)).read_bytes()).hexdigest(),'scores':{}}
for name in ['expr_mse_unbiased_capped_norm','de_wilcoxon_lfc_nmae']:
    policy=replace(CATALOG[name].scoring,anchor=0.1)
    result['scores'][name]={str(u):scoring.score_one(u,1.0,policy) for u in [0.1,0.55,1.0,1.9,10.0]}
assert result['scores']['expr_mse_unbiased_capped_norm']['0.55']>result['scores']['expr_mse_unbiased_capped_norm']['1.0']
assert result['scores']['expr_mse_unbiased_capped_norm']['1.9']==0
assert result['scores']['de_wilcoxon_lfc_nmae']['10.0']==-6
out=Path('reports/candidate_verification/scorer_clamp_check.json')
out.write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result,indent=2))
