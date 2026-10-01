"""Post-hoc reading of r3 after completion; no checkpoint weights or reserve are opened."""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F

import analyze_outputs as audit


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--out', required=True, type=Path)
    a = p.parse_args()
    a.out.mkdir(exist_ok=False)
    base = audit.MODEL / 'cellnet_completo_2026-10-01/esito/training_r3'
    ev = {arm: audit.read(base / 'train' / arm / 'eval.json') for arm in ('desc', 'ident')}
    old = audit.read(audit.MODEL / 'cellnet_esteso_2026-10-01/esito/training_r2/train/desc/eval.json')
    outcome = audit.read(base / 'outcome.json')
    result = {'scope': 'post hoc; splits and exposure differ; neither causal corpus comparison nor VCC score',
              'technical': outcome['A'], 'evaluation': {}, 'same_role_intersections': {}}
    for arm in ev:
        result['evaluation'][arm] = {}
        for cl in ('C', 'T', 'J'):
            rows = [r for r in ev[arm][cl] if 'skipped' not in r]
            groups = defaultdict(list)
            for r in rows:
                groups[r['key']].append(r)
            result['evaluation'][arm][cl] = {
                'all': audit.stats(rows), 'by_key': {k:audit.stats(v) for k,v in groups.items()},
                'pi_below_1e6_fraction': float(np.mean([r['pi_mean'] < 1e-6 for r in rows])),
                'all_ll_gain_zero': all(r['ll_gain_vs_no_effect'] == 0 for r in rows)}
    for cl in ('C', 'T', 'J'):
        before = {(r['key'], r['symbol']):r for r in old[cl] if 'skipped' not in r}
        after = {(r['key'], r['symbol']):r for r in ev['desc'][cl] if 'skipped' not in r}
        common = sorted(before.keys() & after.keys())
        result['same_role_intersections'][cl] = {
            'groups': len(common),
            'r2_cosine': float(np.mean([before[k]['cos_model'] for k in common])) if common else None,
            'r3_cosine': float(np.mean([after[k]['cos_model'] for k in common])) if common else None,
            'caveat': 'common labels only; corpus, controls, training exposure and fitted model differ'}
    # A better response component cannot reopen the clamped gate below epsilon.
    # Keep float64 to expose derivative signs, not floating-point rounding of 1 - pi.
    gate = {}
    for mode in ('current_clamp', 'logsigmoid'):
        z = torch.tensor(float(np.log(1e-8 / (1 - 1e-8))), dtype=torch.float64, requires_grad=True)
        pi = torch.sigmoid(z)
        l0, l1 = z.new_tensor(-2.), z.new_tensor(-1.)
        if mode == 'current_clamp':
            mix = torch.logsumexp(torch.stack([torch.log(pi.clamp_min(1e-6)) + l1,
                                              torch.log((1-pi).clamp_min(1e-6)) + l0]), 0)
        else:
            mix = torch.logsumexp(torch.stack([F.logsigmoid(z) + l1, F.logsigmoid(-z) + l0]), 0)
        (-mix).backward()
        gate[mode] = {'pi': pi.item(), 'negative_loglik_gradient_gate_logit': z.grad.item()}
    assert gate['current_clamp']['negative_loglik_gradient_gate_logit'] > 0
    assert gate['logsigmoid']['negative_loglik_gradient_gate_logit'] < 0
    result['gate_counterexample'] = {
        'response_loglik_better_by': 1., 'results': gate,
        'interpretation': 'below clamp, current gradient descent further closes gate despite better response; stable log weights reopen it',
        'limit': 'mechanism after collapse, not demonstrated cause of its onset in r3'}
    for file in (Path(__file__), Path(audit.__file__), base / 'train/train_log.jsonl',
                 audit.MODEL / 'risposta_biologica_2026-09-30/train_cellnet.py'):
        audit.INPUTS[str(file.relative_to(audit.ROOT))] = {'sha256':hashlib.sha256(file.read_bytes()).hexdigest()}
    (a.out / 'diagnostics.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    (a.out / 'manifest.json').write_text(json.dumps(audit.INPUTS, indent=2), encoding='utf-8')
    print(json.dumps({'desc':{cl:result['evaluation']['desc'][cl]['all'] for cl in ('C','T','J')},
                      'identity_gate':{cl:result['evaluation']['ident'][cl]['pi_below_1e6_fraction'] for cl in ('C','T','J')},
                      'common':result['same_role_intersections'], 'gate':result['gate_counterexample']}, indent=2))


if __name__ == '__main__':
    main()
