"""Build an immutable code-only AMMI payload without launching or transferring it.

The runtime contract is intentionally separate: numeric inputs and the independent
guard routing must be pinned before this payload can perform a biological fit.
"""
import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import zipfile

from pie_adapter import sha256
from run_ammi_pilot_v3 import ARMS

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]


def build(out):
    out=Path(out)
    if out.exists(): raise FileExistsError(out)
    out.mkdir(parents=True)
    names=['run_ammi_pilot_v3.py','ammi_inputs_v3.py','ammi_guard_v3.py','ammi_context.py',
           'ammi_train_v2.py','ammi_contract_v2.py','pie_adapter.py','PROTOCOLLO_AMMI_r2.md',
           'ADDENDUM_AMMI_r2_coverage.md','RICHIESTA_GUARDIA_AMMI_r3.md','NOTA_ROUTING_AMMI_r4.md']
    files={name:HERE/name for name in names}
    files['ntc_cells.py']=ROOT/'reports/modelli/dati_transfer_2026-10-08_01a11c34/ntc_cells.py'
    files['independent_metrics.py']=HERE.parent/'validazione_indipendente_8a8ca58a_2026-10-08/banco/metrics.py'
    pins={name:dict(bytes=path.stat().st_size,sha256=sha256(path)) for name,path in files.items()}
    for name,path in files.items():
        if name.endswith('.py'): compile(path.read_text(encoding='utf-8'),name,'exec')
    payload=out/'ammi_code.zip'
    with zipfile.ZipFile(payload,'x',compression=zipfile.ZIP_DEFLATED) as archive:
        for name,path in sorted(files.items()):
            entry=zipfile.ZipInfo(name,date_time=(2026,10,9,0,0,0))
            entry.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(entry,path.read_bytes())
        archive.writestr('code_pins.json',json.dumps(pins,indent=2))
    jobs=[dict(fold=fold,mode=mode,seed=seed,account='davidmaisterx',device='cuda',private=True,
        inference_interventions=['native','swapped'] if mode=='cells' else ['native'],
        command=f'python run_ammi_pilot_v3.py --manifest {fold}.runtime.json --sha256 <verified-runtime-sha256> --mode {mode} --seed {seed} --out /kaggle/working/{fold}-{mode}-{seed}')
        for fold in ('C-K562','C-iPSC') for mode,seed in ARMS]
    receipt=dict(schema='AMMI-code-package/3',utc=datetime.now(timezone.utc).isoformat(),
        status='CODE_READY_NUMERIC_INPUTS_AND_ROUTING_PENDING',
        payload=dict(path=str(payload),bytes=payload.stat().st_size,sha256=sha256(payload)),files=pins,jobs=jobs,
        runtime_manifest_schema='AMMI-biological-runtime/3',
        required_runtime_fields=['protocol','authorization','anchor_contract','view','panel','panel_file',
            'anchor_completion','anchors','ntc_parts','ntc_expected_parts','ntc_contexts','ntc_context_lineages',
            'ntc_reader','outer_queries','features','chunk_locations','guard','metrics','code'],
        unresolved=['verified numeric NTC parts and anchor completions',
            'DATI/VALIDAZIONE fixed context-to-truth routing and guard review',
            'private input access on GPU runtime',
            'fresh quota/session/resource preflight and applicable authorization check'],
        new_cloud_jobs_launched=False,new_data_transfers=False,complete_D053=False,
        note='14 declared arm/seed fits; scheduling only after preflight, no implied quota or publication')
    (out/'manifest.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
    return receipt


if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('--out',required=True)
    a=p.parse_args();result=build(a.out)
    print(json.dumps(dict(status=result['status'],payload=result['payload'],fits=len(result['jobs']))))
