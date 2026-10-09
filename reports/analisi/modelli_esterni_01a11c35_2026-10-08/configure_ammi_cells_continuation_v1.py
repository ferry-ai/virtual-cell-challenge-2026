"""Freeze code and the scope of one authorized cells continuation; do not start it."""
import json
from pathlib import Path
from continue_ammi_cells_once_v1 import sha,write_new

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
DATI=ROOT/'reports/modelli/dati_transfer_2026-10-08_01a11c34'
DATA=Path('C:/Users/ferra/vcc2026-data/external_models/01a11c35')


def main():
    capsule=json.loads((HERE/'ammi_code_package_r8/manifest.json').read_text())
    files=[Path(p['path']) for p in capsule['files'].values()]
    files += [HERE/name for name in ('continue_ammi_cells_once_v1.py','prepare_ammi_cells_v1.py',
        'build_ammi_runtime_v4.py','package_ammi_cloud_v4.py','compact_ammi_package_v1.py',
        'launch_ammi_cloud_v4.py','preflight_ammi_quota_v4.py','check_ammi_remote_v1.py',
        'collect_ammi_evidence_v1.py','summarize_ammi_metadata_v1.py','autorizzazione_chiusura_r1.json',
        'autorizzazione_trasferimenti_AMMI_r1.json','ammi_code_package_r8/manifest.json')]
    files += [DATI/name for name in ('extend_ammi_access_ntc.py','issue_ammi_private_access.py',
        'preflight_neural_inputs.py','cloud_campaign.py','percorso.py',
        'ammi_private_access_authorization_r1.json','ammi_private_access_plan_r1.json',
        'ammi_ntc_runtime_contract_r3.json')]
    files.append(ROOT/'reports/modelli/percorso_riusabile_2026-10-05/pipeline_state.py')
    value=dict(schema='AMMI-cells-one-shot-continuation/1',repo=str(ROOT),own=str(HERE),dati=str(DATI),
        state_directory=str(DATA/'ammi_cells_continuation_r1'),evidence_root=str(DATA),
        code_pins={str(p):sha(p) for p in dict.fromkeys(files)},
        cloud_destination='davidmaisterx',fits=['C-K562/cells/17','C-iPSC/cells/17'],
        existing_transfer_scope='only the approved 105 derivatives and 12 NTC parts, after verification',
        authorization_scope='four original AMMI logical fits, of which both NONE are complete; only two CELLS remain',
        no_extractions=True,no_refits=True,no_production=True,no_bank_transfers=True,no_submission=True,
        inputs_wait='local DATI sentinels only; collector and producer unchanged',
        stop='create STOP in state_directory; does not cancel already running remote jobs',
        restart_policy='no restart or retry after failure; inspect immutable receipts first')
    out=HERE/'ammi_cells_continuation_config_r1.json';write_new(out,value)
    print(json.dumps(dict(config=str(out),pinned_files=len(value['code_pins']),started=False)))


if __name__=='__main__':main()
