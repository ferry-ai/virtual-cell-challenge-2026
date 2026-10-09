"""Freeze primary CELLS exports from completed metadata; never fetch payloads."""
import argparse
from datetime import datetime, timezone
from pathlib import Path
import json
from ammi_inputs_v3 import checked
from build_ammi_runtime_v4 import pin
from continue_ammi_cells_once_v1 import write_new
from plan_ammi_bank_access_v1 import PRIMARY

HERE = Path(__file__).resolve().parent


def prepare(out):
    out = Path(out)
    if out.exists(): raise FileExistsError(out)
    files, diagnostics, inputs, all_routes = [], [], [], []
    for fold, context in PRIMARY.items():
        source = HERE/('ammi_'+fold.lower()+'_cells_auto_retrieval_r1.json')
        if not source.exists():
            raise ValueError('both terminal metadata receipts required')
        report = json.loads(source.read_text())
        if report['status'] != 'METADATA_PASS_BINARY_HASH_AND_READOUT_PENDING':
            raise ValueError('completed native fit metadata required')
        for receipt in report['files'].values(): checked(receipt)
        inputs.append(pin(source))
        verification = report['verification']
        exports = verification['exports']
        all_routes.extend(dict(fold=fold, **entry) for entry in exports)
        chosen = [entry for entry in exports if entry['context_id'] == context]
        if sum(entry['intervention'] == 'native' for entry in chosen) != 1:
            raise ValueError('frozen primary context native export absent')
        for entry in chosen:
            files.append(dict(fold=fold, **entry))
        diagnostics.extend(dict(fold=fold, **entry)
                           for entry in verification['swapped_diagnostic_failures'])
    unique = {entry['sha256']:entry for entry in files}
    result = dict(utc=datetime.now(timezone.utc).isoformat(),
        status='PRIMARY_EXPORT_PLAN_NOT_TRANSFER_AUTHORIZATION',
        primary_contexts=PRIMARY, files=list(unique.values()), aliases=files,
        unique_files=len(unique), total_bytes=sum(entry['bytes'] for entry in unique.values()),
        all_descriptive_routes_preserved=all_routes, swapped_diagnostic_failures=diagnostics,
        metadata_inputs=inputs, destination_account='davideferrante11',
        readout_owner='VALIDAZIONE', numerical_hashes_verified_by_consumer=False,
        primary_contexts_not_selected_from_results=True, private_transfer_approval_required=True,
        no_local_array_download=True, no_urls_issued=True, no_cloud_job_launched=True)
    write_new(out, result)
    print(json.dumps(dict(files=result['unique_files'], bytes=result['total_bytes'], authorized=False)))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--out', required=True)
    args = parser.parse_args()
    prepare(args.out)
