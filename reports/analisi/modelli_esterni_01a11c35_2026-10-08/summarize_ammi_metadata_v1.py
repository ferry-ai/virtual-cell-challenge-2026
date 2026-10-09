"""Check and summarize pinned AMMI metadata without loading biological arrays."""
import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path

from ammi_inputs_v3 import checked
from ammi_io_v4 import write
from pie_adapter import sha256


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def summarize(receipt_path, remote_path, out):
    report = read(receipt_path)
    remote = read(remote_path)
    if report['status'] != 'METADATA_PASS_BINARY_HASH_AND_READOUT_PENDING':
        raise ValueError('passing metadata receipt required')
    if (remote['slug'] != report['slug'] or remote['state'] != 'COMPLETE'
            or remote['remote_code_matches'] is not True or remote['private'] is not True):
        raise ValueError('completed exact private source required')
    metadata = {name: read(checked(pin)) for name, pin in report['files'].items()}
    training = metadata['training_receipt.json']
    audit = metadata['input_audit.json']['training']
    complete = metadata['complete.json']
    selected = {c: info['selected'] for c, info in audit['contexts'].items() if info['selected']}
    epochs = []
    for epoch in training['epochs']:
        contexts = epoch['coverage']['context']
        if {r['id']: r['seen_rows'] for r in contexts} != selected:
            raise ValueError('selected context rows were not consumed')
        for level in ('context', 'lineage'):
            for row in epoch['coverage'][level]:
                if (row['seen_rows'] != row['expected_rows'] or not math.isclose(
                        row['expected_mass'], row['consumed_mass'], rel_tol=1e-10, abs_tol=1e-12)):
                    raise ValueError('epoch coverage or weighting mismatch')
        if epoch['guard']['pass'] is not True:
            raise ValueError('failed epoch guard')
        epochs.append(dict(epoch=epoch['epoch'], rows=sum(selected.values()),
            contexts=len(selected), lineages=len(epoch['coverage']['lineage']),
            loss=epoch['loss'], optimization_seconds=epoch['optimization_seconds'],
            epoch_seconds=epoch['epoch_seconds'], guard_pass=True))
    if (audit['outer_response_arrays_read'] != 0 or audit['inner_response_arrays_used_for_fit'] != 0
            or training['device'] != 'cuda' or complete['no_outer_truth_read'] is not True):
        raise ValueError('isolation or CUDA attestation missing')
    result = dict(utc=datetime.now(timezone.utc).isoformat(), slug=report['slug'],
        status='METADATA_AND_REMOTE_CODE_PASS_BINARY_HASH_AND_READOUT_PENDING',
        evidence={str(p): sha256(p) for p in (receipt_path, remote_path)},
        epochs=epochs, excluded_lineages=training['excluded_lineages'],
        coverage= audit['contexts'],
        all_selected_rows_consumed_each_epoch=True,
        expected_weight_mass_consumed_each_epoch=True,
        controls_not_consumed=training.get('controls_not_consumed', False),
        numerical_arrays_downloaded=False, complete_D053=False,
        binary_payload_hashes_independently_verified=False,
        benefit_verified=False, outer_readout_pending=True,
        checkpoint_reload_parity='enforced by verified producer code before complete.json',
        native_exports=sum(e['intervention']=='native' for e in complete['exports']),
        phases={name: value for name, value in metadata.items() if name.startswith('timing_')})
    write(out, result)
    print(json.dumps({k: result[k] for k in ('status', 'slug', 'epochs', 'native_exports')}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    for name in ('receipt', 'remote', 'out'):
        parser.add_argument('--'+name, required=True)
    args = parser.parse_args()
    summarize(args.receipt, args.remote, args.out)
