"""Reuse a frozen target-only ridge with its original transforms and feature pins."""
import argparse
import json
from pathlib import Path

import numpy as np

from embedding_ridge import MaskedRidge
from feature_policy import POLICY, validate_queries
from pie_adapter import sha256
from run_sufficient_probe_v2 import load_features


def predict(fit_root, esm2_root, queries):
    fit_root, esm2_root = Path(fit_root), Path(esm2_root)
    receipt = json.loads((fit_root/'manifest.json').read_text(encoding='utf-8'))
    manifest = receipt['manifest']
    if sha256(fit_root/'ridge.npz') != receipt['model_sha256']:
        raise ValueError('frozen model checksum differs')
    mapping = receipt['context_lineages']
    validate_queries(manifest['regime'], receipt['exposure']['targets_read'],
                     list(mapping.values()), list(mapping), queries)
    if len({(q['context_id'],q['target']) for q in queries}) != len(queries):
        raise ValueError('duplicate query')
    features, observed, _ = load_features(esm2_root, manifest['esm2']['sha256'], [q['target'] for q in queries])
    with np.load(fit_root/'ridge.npz', allow_pickle=False) as saved:
        if str(saved['feature_policy'].item()) != POLICY:
            raise ValueError('unsupported saved feature policy')
        model = MaskedRidge(manifest['alpha'])
        for name in ('coef','intercept','generic','support','feature_mean','feature_scale'):
            setattr(model,name,saved[name])
        imputation = saved['imputation_mean']
    if imputation.shape != (features.shape[1],) or not np.isfinite(imputation).all():
        raise ValueError('saved transform axis differs')
    x = np.column_stack((features, ~observed))
    x[~observed,:-1] = imputation
    effects, mask = model.predict(x, observed)
    return dict(effects=effects, observed=mask, esm2_observed=observed,
                genes=np.asarray(receipt['store_receipt']['source_manifest']['genes']),
                targets=np.asarray([q['target'] for q in queries]),
                context_ids=np.asarray([q['context_id'] for q in queries]),
                context_groups=np.asarray([q['context_group'] for q in queries]),
                generic=np.broadcast_to(model.generic,effects.shape),
                generic_observed=np.broadcast_to(model.support,effects.shape))


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--fit',type=Path,required=True)
    p.add_argument('--esm2',type=Path,required=True)
    p.add_argument('--queries',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    a=p.parse_args()
    if a.out.exists() or a.out.with_suffix('.receipt.json').exists():raise FileExistsError(a.out)
    result=predict(a.fit,a.esm2,json.loads(a.queries.read_text(encoding='utf-8')))
    with a.out.open('xb') as f:np.savez_compressed(f,**result)
    receipt=dict(training_receipt_sha256=sha256(a.fit/'manifest.json'),queries_sha256=sha256(a.queries),
                 prediction_sha256=sha256(a.out),code_sha256=sha256(__file__),
                 quantity='same as frozen training manifest',refitted=False,uses_context=False,
                 gain_applied=False,cis_added=False,emitter_scale_applied=False,scientific_benefit='not_scored')
    with a.out.with_suffix('.receipt.json').open('x',encoding='utf-8') as f:json.dump(receipt,f,indent=1)
