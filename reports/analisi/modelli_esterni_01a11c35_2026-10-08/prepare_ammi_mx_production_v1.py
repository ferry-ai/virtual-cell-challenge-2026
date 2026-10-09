"""Prepare the preferred MX production destination; issue no access and launch nothing."""
from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
from ammi_inputs_v3 import checked
from build_ammi_runtime_v4 import pin
from continue_ammi_cells_once_v1 import write_new

HERE = Path(__file__).resolve().parent
DATI = HERE.parents[2]/'reports/modelli/dati_transfer_2026-10-08_01a11c34'
OWNER = 'davidmaisterx'
JOB = OWNER+'/ammi-production-cells-17-01a11c35-r1'


def main():
    inventory_path = DATI/'production_input_handoff_r1.json'
    inventory = json.loads(inventory_path.read_text())
    draft_path = HERE/'ammi_production_draft_prepared_r1.json'
    draft = json.loads(draft_path.read_text())
    checked(draft['runtime_template'])
    needed = {p['sha256']:p['bytes'] for p in draft['numeric_payloads']}
    selected = {}
    for item in inventory['files']:
        if item['private'] and item['source'].split('/')[0] != OWNER and not item['local_metadata']:
            if needed.get(item['sha256']) != item['bytes']:
                raise ValueError('transport outside actual production draft')
            selected.setdefault(item['sha256'], item)
    files = list(selected.values())
    total = sum(item['bytes'] for item in files)
    expected = inventory['accounts'][OWNER]['cross_account_payload_excluding_packaged_metadata']
    if (len(files), total) != (expected['files'], expected['bytes']):
        raise ValueError('exact MX payload inventory differs')
    groups = defaultdict(lambda: dict(files=0, bytes=0))
    for item in files:
        group = groups[item['source']]
        group['files'] += 1; group['bytes'] += item['bytes']
    metadata = dict(id=JOB, title=JOB.split('/')[1], code_file='run.py', language='python',
        kernel_type='script', is_private=True, enable_gpu=True, enable_internet=True,
        dataset_sources=[], competition_sources=[],
        kernel_sources=inventory['accounts'][OWNER]['required_kernel_sources'])
    metadata_path = HERE/'ammi_production_mx_native_sources_r1.json'
    write_new(metadata_path, metadata)
    request_path = HERE/'ammi_production_mx_access_request_r1.json'
    write_new(request_path, dict(jobs=[dict(slug=JOB, metadata=pin(metadata_path))],
                                purpose='read-only access preflight; no launch'))
    result = dict(utc=datetime.now(timezone.utc).isoformat(),
        status='EXACT_MX_PRODUCTION_PLAN_NOT_AUTHORIZED',
        supersedes_destination_proposal='ammi_production_access_plan_r1.json (df11)',
        reason='respect requested GPU destination; quota verified separately, not chosen only by transfer size',
        destination_job=JOB, destination_account=OWNER, files=files, by_source=dict(groups),
        unique_files=len(files), total_bytes=total, source_inventory=pin(inventory_path),
        production_draft=pin(draft_path), native_metadata=pin(metadata_path),
        read_only_access_request=pin(request_path), specific_production_consent_required=True,
        pilot_authorization_not_extended=True, private_only=True, purchases=False,
        no_local_numeric_download=True, URLs_issued=0, cloud_jobs_launched=0,
        fit_gate='actual two-fold readout and explicit technical decision required',
        promotion_and_submission_authorized=False)
    write_new(HERE/'ammi_production_mx_access_plan_r1.json', result)
    derived = []
    for base in ('package_ammi_production_v1.py', 'launch_ammi_production_v1.py',
                 'check_ammi_production_remote_v1.py', 'collect_ammi_production_v1.py'):
        source = HERE/base
        code = source.read_text()
        if 'davideferrante11' not in code:
            raise ValueError('expected df11 adaptation boundary absent')
        code = code.replace("Path.home()/'.kaggle-davideferrante11'", "Path.home()/'.kaggle'")
        code = code.replace('davideferrante11', OWNER)
        output = HERE/base.replace('_v1.py', '_mx_v1.py')
        compile(code, output.name, 'exec')
        with output.open('x', encoding='utf-8', newline='\n') as stream: stream.write(code)
        derived.append(dict(source=pin(source), derived=pin(output)))
    test_source = HERE/'test_ammi_production_tools_v1.py'
    test = test_source.read_text().replace('from package_ammi_production_v1', 'from package_ammi_production_mx_v1')
    test = test.replace('from launch_ammi_production_v1', 'from launch_ammi_production_mx_v1')
    test = test.replace("[('C-K562','davideferrante11'), ('production','davidmaisterx')]",
                        "[('C-K562','davidmaisterx'), ('production','davideferrante11')]")
    with (HERE/'test_ammi_production_tools_mx_v1.py').open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(test)
    write_new(HERE/'ammi_production_mx_tools_prepared_r1.json', dict(
        files=derived, destination_job=JOB, scientific_code_unchanged=True, cloud_jobs_launched=0))
    print(json.dumps(dict(files=len(files), bytes=total, job=JOB, by_source=dict(groups))))


if __name__ == '__main__':
    main()
