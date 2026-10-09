"""Prepare frozen production inputs behind an explicitly closed scientific gate.

No numeric payload download, locator issuance, cloud launch or invented readout.
The final candidate must be rebuilt with the actual signed-off readout receipt.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
from build_ammi_runtime_v4 import build, read, pin
from continue_ammi_cells_once_v1 import write_new
from prepare_ammi_cells_v1 import REPORTS

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
DATI = ROOT/'reports/modelli/dati_transfer_2026-10-08_01a11c34'
OUT = Path('C:/Users/ferra/vcc2026-data/external_models/01a11c35/ammi_cloud/production-cells-draft-r1')


def main():
    gate = HERE/'ammi_production_readout_pending_r1.json'
    write_new(gate, dict(status='PENDING_ACTUAL_COMPARATIVE_READOUT',
        folds={fold: dict(cells_minus_T0_read=False, cells_minus_A0_read=False,
                         cells_minus_none_read=False, evidence=[])
               for fold in ('C-K562', 'C-iPSC')},
        production_technical_fit_decision='pending',
        benefit_demonstrated=False, promotion_authorized=False,
        purpose='closed gate for preparation only; never replace with ungrounded flags'))
    verifications = [DATI/name for name in REPORTS] + [DATI/'official_ntc_verified_r1.json']
    receipt = build('production', 'cells', OUT, DATI/'ammi_ntc_runtime_contract_r3.json',
                    verifications, HERE/'autorizzazione_chiusura_r1.json', gate)
    spec = read(OUT/'runtime_template.json')
    numeric = {}
    def add(item, role, source=None, remote_path=None):
        digest = item['sha256']
        if digest in numeric and numeric[digest]['bytes'] != item['bytes']:
            raise ValueError('conflicting numeric pin')
        value = numeric.setdefault(digest, dict(sha256=digest, bytes=item['bytes'], roles=[]))
        if role not in value['roles']: value['roles'].append(role)
        if source: value['source_job'] = source
        if remote_path: value['remote_path'] = remote_path
    anchor = read(DATI/'production_anchors_verified_r1.json')
    for name, item in spec['anchors'].items():
        add(item, 'production_anchor:'+name, anchor['slug'], 'anchors/'+name+'/effects_'+name+'.npz')
    for part in spec['ntc_parts']:
        completion = read(part['completion']['path'])
        for name, item in completion['files'].items():
            add(item, 'NTC:'+completion['part_id'], part.get('producer_job'),
                'ntc/'+completion['part_id']+'/'+name)
    for item in spec['chunk_pins'].values(): add(item, 'response_chunk')
    for item in spec['features'].values(): add(item, 'public_ESM2_feature')
    view = read(spec['view']['path'])
    coverage = {context: dict(lineage=info['lineage'], role=info['role'],
                eligible_panel_targets=len({t for chunk in view['chunks'] if chunk['context_id']==context
                    for t in chunk['targets'] if t in spec['panel'] and t != 'TMEM104'}))
                for context, info in read(spec['anchor_contract']['path'])['folds']['production']['contexts'].items()}
    payloads = list(numeric.values())
    result = dict(utc=datetime.now(timezone.utc).isoformat(),
        status='DRAFT_READY_CLOSED_READOUT_AND_ACCESS_GATES',
        runtime_template=receipt['template'], runtime_package=str(OUT),
        gate=pin(gate), gate_is_open=False, launchable=False, cloud_jobs_launched=0,
        numeric_payloads=payloads, unique_numeric_files=len(payloads),
        unique_numeric_bytes=sum(p['bytes'] for p in payloads),
        controls_parts=len(spec['ntc_parts']), control_contexts=len(spec['ntc_contexts']),
        destination_contexts=spec['destination_contexts'], response_coverage=coverage,
        fixed_training=dict(mode='cells', seed=17, epochs=2, batch_size=32,
                            target_cap_per_context=64, independent_validation=False),
        code=receipt['code'], complete_D053=False,
        pending=['actual cells/A0, cells/T0 and cells/none readout on both folds',
                 'explicit technical production decision grounded in those results',
                 'destination access and precise authorization for any additional private transport',
                 'fresh final template with actual gate, packaging, runtime preflight and one launch'],
        no_new_extraction=True, no_change_to_running_pilots=True)
    write_new(HERE/'ammi_production_draft_prepared_r1.json', result)
    print(json.dumps({k:result[k] for k in ('status','unique_numeric_files','unique_numeric_bytes',
                                         'controls_parts','control_contexts','launchable')}))


if __name__ == '__main__':
    main()
