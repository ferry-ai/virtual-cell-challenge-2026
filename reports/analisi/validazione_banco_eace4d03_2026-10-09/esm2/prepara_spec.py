"""Write the spec of the fallback support audit for one fold, from receipts already committed.

Every expected sha256 comes from a receipt of the assignment that produced the file, never from the file
itself: the fold effects of the manifest arms from the consumption receipt of the closure run (stage 100
recomputed there), the fallback and the two external arms from MODELLI-ESTERNI's conversion receipt, the
truth table from the pin of release r1, the published results from the retrieval receipt. Paths are local
copies in the data root; nothing is downloaded.

    py prepara_spec.py <fold id> <arms dir> <truth npz> <spec out.json>
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
MODELLI = REPO / 'reports/analisi/modelli_esterni_01a11c35_2026-10-08'
RELEASE = REPO / 'reports/modelli/banca_canonica_2026-10-07/fit/release_r1.json'
ARMS = ('T0', 'R1', 'T1', 'P4')
AMPLITUDE = 1.576


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def main() -> None:
    fold, arms_dir, truth_path, out = sys.argv[1], Path(sys.argv[2]), Path(sys.argv[3]), Path(sys.argv[4])
    conversion = read(MODELLI / 'esm2_closure_conversion_r1.json')['folds'][fold]
    retrieval = read(MODELLI / 'esm2_closure_retrieval_r1.json')
    results = retrieval['files']['results.json']
    consumption = {(c['label'], c['context']): c
                   for c in read(Path(retrieval['files']['consumption.json']['path']))}
    published = read(results['path'])['folds'][fold]['truth']
    tname = next(t for t, v in published.items() if v['role'] == 'primary')
    integration = conversion['integration']
    if integration['t0_sha256'] != consumption[('T0', fold)]['effects_sha256']:
        raise SystemExit('the fallback was built on another T0 than the one the closure run measured')
    if abs(integration['amplitude_applied_once_to_fallback'] - AMPLITUDE) > 0:
        raise SystemExit('unexpected amplitude in the conversion receipt')
    spec = {
        'fold': fold, 'truth_table': tname, 'amplitude': AMPLITUDE, 'fallback_label': 'E2f',
        'integration_contrast': 'C_integration', 'expected_filled_pairs': integration['fallback_pairs'],
        'arms': {a: {'path': str(arms_dir / (a + '.npz')), 'sha256': consumption[(a, fold)]['effects_sha256'],
                     'sha256_from': 'closure consumption.json, stage 100 recomputed in that run'} for a in ARMS},
        'fallback': {'path': integration['path'], 'sha256': integration['sha256'],
                     'sha256_from': 'esm2_closure_conversion_r1.json'},
        'E2': {'path': conversion['stage100']['E2']['path'], 'sha256': conversion['stage100']['E2']['sha256'],
               'sha256_from': 'esm2_closure_conversion_r1.json'},
        'E2g': {'path': conversion['stage100']['E2g']['path'], 'sha256': conversion['stage100']['E2g']['sha256'],
                'sha256_from': 'esm2_closure_conversion_r1.json'},
        'truth': {'path': str(truth_path), 'sha256': read(RELEASE)['voted'][tname]['sha256'],
                  'sha256_from': 'release_r1.json, voted.' + tname},
        'closure_results': {'path': results['path'], 'sha256': results['sha256'],
                            'sha256_from': 'esm2_closure_retrieval_r1.json'},
    }
    with out.open('x', encoding='utf-8') as fh:
        json.dump(spec, fh, indent=1)
        fh.write('\n')
    print(json.dumps({'fold': fold, 'truth': tname, 'expected_filled_pairs': spec['expected_filled_pairs']}))


if __name__ == '__main__':
    main()
