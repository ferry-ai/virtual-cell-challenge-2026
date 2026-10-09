"""Freeze the four-fit AMMI code capsule; numerical/private inputs stay separate."""
import argparse
import json
from pathlib import Path
import zipfile
from build_ammi_runtime_v4 import CODE,HERE,DATI,VALID,pin
from ammi_io_v4 import write

def build(out):
    out=Path(out)
    if out.exists():raise FileExistsError(out)
    files={n:HERE/n for n in CODE}
    files.update({'ntc_cells.py':DATI/'ntc_normalization_r1/ntc_cells.py',
                  'independent_metrics.py':VALID/'banco/metrics.py'})
    for n in ('PROTOCOLLO_AMMI_r2.md','CONTRATTO_CHIUSURA_AMMI_r4.md','ADDENDUM_AMMI_r2_coverage.md'):
        files[n]=HERE/n
    pins={n:pin(p) for n,p in files.items()}
    for n,p in files.items():
        if n.endswith('.py'):compile(p.read_text(encoding='utf-8'),n,'exec')
    out.mkdir(parents=True)
    with zipfile.ZipFile(out/'ammi_code.zip','x',compression=zipfile.ZIP_DEFLATED) as z:
        for n,p in sorted(files.items()):
            entry=zipfile.ZipInfo(n,date_time=(2026,10,9,0,0,0));entry.compress_type=zipfile.ZIP_DEFLATED
            z.writestr(entry,p.read_bytes())
        z.writestr('code_pins.json',json.dumps(pins,indent=2))
    receipt=dict(schema='AMMI-code-package/4',payload=pin(out/'ammi_code.zip'),files=pins,
        status='CODE_FROZEN_NUMERIC_INPUTS_PENDING',
        initial_fits=[dict(fold=f,mode=m,seed=17) for f in ('C-K562','C-iPSC') for m in ('cells','none')],
        swapped='inference from cells checkpoint; no additional fit',
        production='distinct contract and readout decision required',
        CPU_biological_training_allowed=False,new_cloud_jobs_launched=False,complete_D053=False)
    write(out/'manifest.json',receipt);print(json.dumps(dict(payload=receipt['payload'],fits=4)))

if __name__=='__main__':
    p=argparse.ArgumentParser(__doc__);p.add_argument('--out',required=True);a=p.parse_args();build(a.out)
