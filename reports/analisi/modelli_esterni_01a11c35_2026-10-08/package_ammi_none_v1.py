"""Package exactly the two authorized NONE pilots; remove NTC mounts only."""
import json
from pathlib import Path
from package_ammi_cloud_v4 import package
from ammi_inputs_v3 import checked
from ammi_io_v4 import write
from pie_adapter import sha256

HERE=Path(__file__).resolve().parent
DATI=HERE.parents[2]/'reports/modelli/dati_transfer_2026-10-08_01a11c34'
ROOT=Path('C:/Users/ferra/vcc2026-data/external_models/01a11c35/ammi_cloud')


def main():
    receipt=json.loads((DATI/'ammi_private_access_issued_r1.json').read_text())
    access=checked(receipt['private_locators']);original=checked(receipt['mount_plan'])
    mounts=json.loads(original.read_text())
    removed=[ref for ref in mounts['kernel_sources'] if '/dt-ntc-inputs-' in ref]
    if len(removed)!=3:raise ValueError('expected exactly three NTC-only mounts')
    mounts['kernel_sources']=[ref for ref in mounts['kernel_sources'] if ref not in removed]
    mounts['sources']=[s for s in mounts['sources'] if s['ref'] not in removed]
    mounts.update(controls_not_consumed=True,removed_NTC_mounts=removed,
                  original_mount_plan_sha256=sha256(original))
    mount_path=ROOT/'none_mount_plan_r1.json';write(mount_path,mounts)
    jobs=[]
    for fold in ('C-K562','C-iPSC'):
        runtime=ROOT/(fold+'-none-r5')
        spec=json.loads((runtime/'runtime_template.json').read_text())
        if spec.get('controls_not_consumed') is not True or spec['ntc_parts']:
            raise ValueError('control-free none runtime required')
        output=HERE/('ammi_'+fold.lower()+'_none_prepared_r1.json')
        package(runtime,access,mount_path,ROOT/(fold+'-none-r5-package'),output)
        jobs.append(json.loads(output.read_text()))
    write(HERE/'ammi_none_prepared_r1.json',dict(jobs=jobs,initial_fits_not_extra=True,
        controls_not_consumed=True,private=True,launch_pending=True))


if __name__=='__main__':main()
