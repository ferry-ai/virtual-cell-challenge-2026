"""Freeze the minimal df11 production transport, without issuing any locator."""
from datetime import datetime, timezone
from pathlib import Path
import json
from ammi_inputs_v3 import checked
from build_ammi_runtime_v4 import pin
from continue_ammi_cells_once_v1 import write_new

HERE = Path(__file__).resolve().parent
DATI = HERE.parents[2]/'reports/modelli/dati_transfer_2026-10-08_01a11c34'
OWNER = 'davideferrante11'
JOB = OWNER+'/ammi-production-cells-17-01a11c35-r1'


def main():
    source = DATI/'production_input_handoff_r1.json'
    handoff = json.loads(source.read_text())
    draft_path = HERE/'ammi_production_draft_prepared_r1.json'
    draft = json.loads(draft_path.read_text())
    checked(draft['runtime_template'])
    needed = {p['sha256']:p['bytes'] for p in draft['numeric_payloads']}
    by_hash = {}
    for item in handoff['files']:
        if item['private'] and item['source'].split('/')[0] != OWNER and not item['local_metadata']:
            if needed.get(item['sha256']) != item['bytes']:
                raise ValueError('transport is not an actual draft input')
            by_hash.setdefault(item['sha256'], item)
    files = list(by_hash.values())
    total = sum(p['bytes'] for p in files)
    expected = handoff['accounts'][OWNER]['cross_account_payload_excluding_packaged_metadata']
    if len(files) != expected['files'] or total != expected['bytes']:
        raise ValueError('handoff payload count or bytes differ')
    metadata = dict(id=JOB, title=JOB.split('/')[1], code_file='run.py', language='python',
                    kernel_type='script', is_private=True, enable_gpu=True, enable_internet=True,
                    dataset_sources=[], competition_sources=[],
                    kernel_sources=handoff['accounts'][OWNER]['required_kernel_sources'])
    metadata_path = HERE/'ammi_production_native_sources_r1.json'
    write_new(metadata_path, metadata)
    request = HERE/'ammi_production_access_request_r1.json'
    write_new(request, dict(jobs=[dict(slug=JOB, metadata=pin(metadata_path))],
                            purpose='read-only native mount preflight, no cloud launch'))
    result = dict(utc=datetime.now(timezone.utc).isoformat(),
        status='PREPARED_EXACT_PRIVATE_TRANSPORT_NOT_AUTHORIZED',
        source_handoff=pin(source), production_draft=pin(draft_path), destination_account=OWNER,
        destination_job=JOB, files=files, unique_files=len(files), total_bytes=total,
        embedded_completion_metadata_files=18, embedded_completion_metadata_bytes=92730,
        private=True, public=False, local_numeric_download=False, purchases=False,
        no_new_extraction=True, URLs_issued=0, cloud_jobs_launched=0,
        requires_specific_production_transfer_consent=True,
        old_pilot_locator_scope_does_not_authorize_production=True,
        transport='temporary HTTPS locators in private package outside Git/logs; full byte/hash verification in cloud',
        pending=['specific private transfer consent','native mount preflight',
                 'actual two-fold pilot readout and explicit technical production decision',
                 'fresh runtime RAM/disk/CUDA preflight, final package and one guarded launch'],
        native_metadata=pin(metadata_path), read_only_access_request=pin(request))
    write_new(HERE/'ammi_production_access_plan_r1.json', result)
    print(json.dumps(dict(files=len(files), bytes=total, job=JOB, authorized=False)))


if __name__ == '__main__':
    main()
