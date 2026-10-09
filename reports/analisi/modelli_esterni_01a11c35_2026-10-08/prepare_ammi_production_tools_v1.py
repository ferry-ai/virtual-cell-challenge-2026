"""Derive dedicated df11 transport tools without changing any running pilot code."""
from pathlib import Path
import json
from build_ammi_runtime_v4 import pin
from continue_ammi_cells_once_v1 import write_new

HERE = Path(__file__).resolve().parent
JOB = 'davideferrante11/ammi-production-cells-17-01a11c35-r1'


def derive(source_name, output_name, replacements):
    source = HERE/source_name
    code = source.read_text(encoding='utf-8')
    for before, after in replacements:
        if code.count(before) != 1:
            raise ValueError('source adaptation boundary differs: '+source_name)
        code = code.replace(before, after, 1)
    compile(code, output_name, 'exec')
    out = HERE/output_name
    with out.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(code)
    return dict(source=pin(source), derived=pin(out), changed_boundaries=len(replacements))


def main():
    gate = '''    if prepared['fold']!='production' or prepared['mode']!='cells' or spec['mode']!='production':
        raise ValueError('dedicated production package required')
    readout=json.loads(checked(spec['production_readout']).read_text())
    if (set(readout['folds'])!={'C-K562','C-iPSC'}
            or any(not readout['folds'][f].get('cells_minus_T0_read') or not readout['folds'][f].get('cells_minus_none_read') for f in readout['folds'])
            or readout.get('production_technical_fit_decision')!='proceed'):
        raise ValueError('actual comparative readout and explicit decision required before packaging')
'''
    outputs = []
    outputs.append(derive('package_ammi_cloud_v4.py', 'package_ammi_production_v1.py', [
        ("    locators=json.loads(Path(access).read_text())", gate+"    locators=json.loads(Path(access).read_text())"),
        ("mount['owner']!='davidmaisterx'", "mount['owner']!='davideferrante11'"),
        ("slug='ammi-'+prepared['fold'].lower()+'-'+prepared['mode']+'-17-01a11c35-r5'",
         "slug='ammi-production-cells-17-01a11c35-r1'")]))
    outputs.append(derive('launch_ammi_cloud_v4.py', 'launch_ammi_production_v1.py', [
        ("    if owner!='davidmaisterx' or not prepared['private']:",
         "    if prepared['slug']!='"+JOB+"' or prepared['fold']!='production' or prepared['mode']!='cells' or not prepared['private']:"),
        ("Path.home()/'.kaggle'", "Path.home()/'.kaggle-davideferrante11'")]))
    outputs.append(derive('check_ammi_remote_v1.py', 'check_ammi_production_remote_v1.py', [
        ("if owner!='davidmaisterx':", "if prepared['slug']!='"+JOB+"':"),
        ("Path.home()/'.kaggle'", "Path.home()/'.kaggle-davideferrante11'")]))
    outputs.append(derive('collect_ammi_evidence_v1.py', 'collect_ammi_production_v1.py', [
        ("if owner != 'davidmaisterx' or prepared.get('private') is not True:",
         "if prepared['slug'] != '"+JOB+"' or prepared.get('private') is not True:"),
        ("Path.home()/'.kaggle'", "Path.home()/'.kaggle-davideferrante11'"),
        ("if prepared['mode'] == 'cells':", "if prepared['mode'] == 'cells' and prepared['fold'] != 'production':")]))
    write_new(HERE/'ammi_production_tools_prepared_r1.json',
        dict(status='PREPARED_NOT_EXECUTED', files=outputs, destination_job=JOB,
             pilot_code_unchanged=True, scientific_runner_unchanged=True,
             locator_issuance_performed=False, cloud_jobs_launched=0,
             actual_readout_and_private_access_required=True))
    print(json.dumps(dict(derived_tools=len(outputs), cloud_jobs_launched=0)))


if __name__ == '__main__':
    main()
