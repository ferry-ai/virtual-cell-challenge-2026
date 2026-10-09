"""Write the spec of the AMMI `none` read for one fold (LETTURA_AMMI_NONE.md), with pins taken from receipts.

Expected sha256: the manifest arms from the consumption receipt of the closure run; the nested anchor A0 and the
`none` export AN from MODELLI-ESTERNI's bench access plan (the anchor's hash is the one of the zero-residual parity
receipt of the fit); the truth from the pin of release r1; the published results from the retrieval receipt.

    py prepara_spec_ammi.py <fold id> <arms dir> <A0 npz> <AN npz> <truth npz> <spec out.json>
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
LINEAGE = {'C-K562': 'K562', 'C-iPSC': 'iPSC'}


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def pins(fold):
    plan = read(MODELLI / 'ammi_bank_access_plan_r1.json')
    retrieval = read(MODELLI / 'esm2_closure_retrieval_r1.json')['files']
    consumption = {(c['label'], c['context']): c for c in read(retrieval['consumption.json']['path'])}
    published = read(retrieval['results.json']['path'])['folds'][fold]['truth']
    tname = next(t for t, v in published.items() if v['role'] == 'primary')
    anchor = next(a for a in plan['native_anchors'] if a['fold'] == fold)
    export = next(e for e in plan['known_export_files'] if e['fold'] == fold and e['mode'] == 'none')
    release = read(RELEASE)['voted'][tname]
    return {'truth_table': tname, 'arms': {a: consumption[(a, fold)]['effects_sha256'] for a in ARMS},
            'A0': {'bytes': anchor['bytes'], 'sha256': anchor['sha256'], 'source': anchor['source'], 'file': anchor['file']},
            'AN': {'bytes': export['bytes'], 'sha256': export['sha256'], 'source': export['source'], 'file': export['file']},
            'truth': {'bytes': release['bytes'], 'sha256': release['sha256']},
            'published_results': {'bytes': retrieval['results.json']['bytes'], 'sha256': retrieval['results.json']['sha256'],
                                  'path': retrieval['results.json']['path']}}


def main() -> None:
    fold, arms_dir, a0, an, truth, out = sys.argv[1], Path(sys.argv[2]), sys.argv[3], sys.argv[4], sys.argv[5], Path(sys.argv[6])
    p = pins(fold)
    spec = {'fold': fold, 'truth_table': p['truth_table'], 'lineage': LINEAGE[fold],
            'arms': {a: {'path': str(arms_dir / (a + '.npz')), 'sha256': p['arms'][a]} for a in ARMS},
            'extra': {'A0': {'path': a0, 'sha256': p['A0']['sha256'], 'what': 'nested anchor of the AMMI fit'},
                      'AN': {'path': an, 'sha256': p['AN']['sha256'], 'what': 'AMMI none export, seed 17'}},
            'pairs': [['AN', 'A0'], ['A0', 'T0'], ['AN', 'T0']],
            'truth': {'path': truth, 'sha256': p['truth']['sha256']},
            'published_results': {'path': p['published_results']['path'], 'sha256': p['published_results']['sha256']}}
    with out.open('x', encoding='utf-8') as fh:
        json.dump(spec, fh, indent=1)
        fh.write('\n')
    print(json.dumps({'fold': fold, 'truth': p['truth_table']}))


if __name__ == '__main__':
    main()
