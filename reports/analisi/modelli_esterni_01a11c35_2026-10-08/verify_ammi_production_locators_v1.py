"""Verify authorized locator metadata without downloading or exposing bearer URLs."""
from datetime import datetime, timezone
import json
from pathlib import Path
from urllib.parse import urlsplit
from ammi_inputs_v3 import checked
from build_ammi_runtime_v4 import pin
from continue_ammi_cells_once_v1 import write_new

HERE=Path(__file__).resolve().parent
DATI=HERE.parents[2]/'reports/modelli/dati_transfer_2026-10-08_01a11c34'


def main():
    receipt_path=DATI/'production_mx_private_access_issued_r1.json'
    receipt=json.loads(receipt_path.read_text())
    auth=json.loads(checked(receipt['authorization']).read_text())
    plan=json.loads(checked(receipt['plan']).read_text())
    locator_path=checked(receipt['private_locators'])
    if locator_path.resolve().is_relative_to(HERE.parents[2]): raise ValueError('private file in repository')
    locators=json.loads(locator_path.read_text())
    expected={row['sha256']:row for row in plan['files']}
    if (receipt['status']!='LOCATORS_ISSUED_CONSUMER_HASHES_PENDING'
            or locators['status']!='authorized' or not auth['granted']
            or len(expected)!=209 or set(locators['files'])!=set(expected)
            or locators['destination_job']!=auth['destination_job']
            or locators['destination_job']!=plan['destination_job']
            or locators['authorization']!=receipt['authorization']
            or locators['authorized_plan']!=receipt['plan']):
        raise ValueError('locator scope mismatch')
    for digest,row in locators['files'].items():
        if row['sha256']!=digest or row['bytes']!=expected[digest]['bytes']:
            raise ValueError('expected pin mismatch')
        parsed=urlsplit(row['url'])
        if parsed.scheme!='https' or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError('invalid locator protocol')
    write_new(HERE/'ammi_production_mx_locator_metadata_verified_r1.json',dict(
        utc=datetime.now(timezone.utc).isoformat(),status='METADATA_SCOPE_PASS_PAYLOAD_HASHES_PENDING',
        source_receipt=pin(receipt_path),authorization=receipt['authorization'],plan=receipt['plan'],
        private_locators=receipt['private_locators'],files=len(expected),
        bytes=sum(row['bytes'] for row in expected.values()),destination_job=auth['destination_job'],
        no_bearer_urls_in_report=True,no_payload_download=True,cloud_jobs_launched=0,
        remote_content_hashes_verified=False,scientific_gate_open=False,ready_for_training=False,
        verifier=pin(Path(__file__))))
    print(json.dumps(dict(status='METADATA_SCOPE_PASS_PAYLOAD_HASHES_PENDING',files=len(expected))))


if __name__=='__main__': main()
