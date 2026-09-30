"""Close the numerical repair only after the unchanged selector succeeds."""
import csv
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import ledger

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
NEURAL = HERE.parent / 'neural'


def table(path):
    with path.open(newline='') as stream:
        return {(r['perturbation'],r['metric']): float(r['value']) if r['value'] else math.nan for r in csv.DictReader(stream)}


def main():
    selection_path = NEURAL/'stack_ab_selection_r2'/'selection_manifest.json'
    selection = json.loads(selection_path.read_text())
    assert selection['status'] == 'selection_complete' and selection['selected_variant'] is None
    assert all(not r['eligible'] for r in selection['candidates'].values())
    assert selection['selector_sha256'] == ledger.sha(NEURAL/'select_stack_ab.py')
    assert selection['checks']['transfer_metric_values_exact'] is True
    new = NEURAL/'stack_paired_scoring_results_r1'
    assert (new/'A/per_pert_transfer.csv').read_bytes() == (new/'B/per_pert_transfer.csv').read_bytes()
    collection = json.loads((new/'collection.json').read_text())
    assert collection['dispatcher_completion'].endswith('finished 085_lead_stack_paired_rescore_r1.sh rc=0')
    deltas = {}
    for variant,old_name in [('A','stack_a_scoring_r2'),('B','stack_b_scoring_r1')]:
        old = NEURAL/old_name
        before,after = [json.loads((p/'pilot_comparison.json').read_text()) for p in [old,new/variant]]
        assert before['delta_projection'] == after['delta_projection']
        assert before['delta_pds_raw'] == after['delta_pds_raw']
        per_target = {}
        for arm in ['transfer','stack']:
            left,right = [table(p/f'per_pert_{arm}.csv') for p in [old,new/variant]]
            assert left.keys() == right.keys()
            assert all(math.isfinite(left[k]) == math.isfinite(right[k]) for k in left)
            per_target[arm] = max(abs(left[k]-right[k]) for k in left if math.isfinite(left[k]))
        deltas[variant] = {'delta_projection_change': 0.0,'delta_pds_change': 0.0,
                          'maximum_per_target_absolute_change': per_target}
    out = NEURAL/'stack_ab_numerical_diagnostic_r2'; out.mkdir()
    proof = out/'verification.json'
    result = {'verified_utc': datetime.now(timezone.utc).isoformat(), 'selector_status':'selection_complete',
        'selected_variant': None,'selector_sha256':selection['selector_sha256'],
        'selection_manifest_sha256':ledger.sha(selection_path),
        'baseline_csv_byte_identical':True,'baseline_csv_sha256':ledger.sha(new/'A/per_pert_transfer.csv'),
        'before_after':deltas,'scope':'Operational exact-baseline guard resolved; both scientific candidates remain ineligible',
        'causal_attribution':'Combined fixed threads/hashseed restored equality in this rerun; exact source of original11ULP remains unproved'}
    with proof.open('x',encoding='utf-8') as stream:
        json.dump(result,stream,indent=2);stream.write('\n')
    prior = HERE/'incidents'/'E-20260929-006.r001.json'
    row = json.loads(prior.read_text())
    row['revision']=2;row['previous_sha256']=ledger.sha(prior);row['recorded_utc']=result['verified_utc']
    row['state']='verified_remotely'
    row['scope']='085 remoto completa entrambi gli score; baselineCSV byte-identici, selettore invariato completa e sceglie nessun candidato. Causa specifica11ULP ancora non attribuita; nessuna conferma o nuovo job.'
    for path,supports in [(new/'collection.json','085rc0 e22report originali copiati conhash'),
                          (selection_path,'Selettore congelato completa conbaseline esatta e nessun candidato'),
                          (proof,'Delta primari invariati rispetto originali, dettagli differenze numeriche')]:
        row['evidence'].append({'path':path.relative_to(REPO).as_posix(),'sha256':ledger.sha(path),
                                'bytes':path.stat().st_size,'supports':supports})
    row['remote_verification']={'evidence_path':proof.relative_to(REPO).as_posix(),'observed_utc':result['verified_utc'],
        'criterion':'085rc0; stessiinput/scorer/versioni; baselineA/B byte-identica; selectorfrozenrc0 senza tolleranza ampliata'}
    record=ledger.append(HERE/'incidents',row)
    with (HERE/'index_r7.json').open('x',encoding='utf-8') as stream:
        json.dump(ledger.index(HERE/'incidents'),stream,indent=2,ensure_ascii=False);stream.write('\n')
    print(json.dumps(result|{'incident_record':str(record)},indent=2))


if __name__=='__main__':
    main()
