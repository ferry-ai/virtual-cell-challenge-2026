"""Verify completed preparation080 bytes and metadata; never read cell outcomes."""
from datetime import datetime, timezone
import json
from pathlib import Path

import ledger
import preflight

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
RUN = Path('G:/Il mio Drive/vcc2026/runs/lead_stack_confirmation_prompts_2026-09-29_r2')
JOBS = RUN.parent / 'jobs'
OUT = HERE.parent / 'neural' / 'stack_confirmation_preparation_receipt_r2'
TARGETS = 'PCBP1 CDC20 RNF31 KIF11 C7orf26 RPS24 GINS2 YRDC DESI1 MRPL38 RSL1D1 MYBBP1A'.split()


def main():
    if OUT.exists():
        raise FileExistsError(OUT)
    completed = [s for s in (JOBS / 'dispatcher.log').read_text(encoding='utf-8').splitlines()
                 if 'finished 080_lead_stack_confirmation_prepare_r2.sh rc=' in s]
    assert len(completed) == 1 and completed[0].endswith('rc=0')
    originals = {'bundle.json': RUN / 'bundle' / 'bundle.json', 'plan.json': RUN / 'plan.json',
                 'effects_manifest.json': RUN / 'effects' / 'manifest.json'}
    blobs = {name: path.read_bytes() for name, path in originals.items()}
    assert all(len(value) < 250000 for value in blobs.values())
    bundle, plan, effect = [json.loads(blobs[k]) for k in ['bundle.json', 'plan.json', 'effects_manifest.json']]
    assert bundle['status'] == 'prepared_no_model_no_scores'
    assert bundle['targets'] == plan['targets'] == effect['targets'] == TARGETS
    for key, value in plan.items():
        if key != 'status':
            assert bundle[key] == value, key
    assert bundle['plan_sha256'] == preflight.digest(RUN / 'plan.json')
    assert bundle['destination_truth_rows_read'] == effect['destination_perturbed_rows_read'] == 0
    assert bundle['source_min_cells'] == 64 and bundle['source_max_cells'] == 128
    assert bundle['seed'] == 20260929 and bundle['n_output'] == 400
    assert bundle['inference_authorized'] is False
    assert bundle['adapter_sha256'] == 'b259371df3d0d515003597c4d9ce5755c25840f0d36fc96d8ac390ffe1275508'
    assert bundle['protocol_sha256'] == '2c2614532d49e35a60735858f150e6bd46f1cb9414ccc8b3914aaf12061245f2'
    assert bundle['inference_adapter_sha256'] == 'a6147fd5dc0aea614de9101a14c13fd4c627fcecab27c93971b81e89429c6b30'
    assert bundle['scoring_code_sha256'] == 'c69d41aac1aa4bc14bcb9239b39cea675430c944ea1e7c1078f659b483a6df71'
    assert bundle['packer_sha256'] == 'd009261694b2a808dc6c8ab77dacb204f5796eceadd0d69b65b7865221e43f44'
    assert effect['existing_generator_rows_bit_exact'] == 144 and effect['existing_pilot_rows_bit_exact'] == 12
    assert bundle['effects_sha256'] == effect['output_sha256'] == preflight.digest(RUN / 'effects' / 'confirmation_effects.npz')
    expected = {'destination_controls.h5ad', 'transfer.npz', *[f'source_{i:02d}.h5ad' for i in range(13)]}
    assert set(bundle['files']) == expected
    checks = []
    for name, digest in bundle['files'].items():
        path = RUN / 'bundle' / name
        item = {'id': name, 'paths': {'local': str(path)}, 'bytes': path.stat().st_size, 'sha256': digest}
        checks.append(preflight.check_file(item, 'local'))
    for name, digest in bundle['reused_files'].items():
        assert bundle['files'][name] == digest
    assert bundle['reused_files'] == {'source_00.h5ad': '616f18fe3f7b99a7239249150f67f991bfbbc48caf9d0b89d5e05520d19ee491',
        'destination_controls.h5ad': 'c989a3121caa5b96c1752c92fd811522caf60d19c994fa3e08237625adcff598'}
    transfer = {'id': 'transfer.npz', 'paths': {'local': str(RUN / 'bundle' / 'transfer.npz')}}
    target_check = preflight.check_targets({'input_id': 'transfer.npz', 'required': TARGETS}, {'transfer.npz': transfer}, 'local')
    assert target_check['available_count'] == 12
    all_rows = bundle['source_selected_rows']
    assert set(all_rows) == set(TARGETS) | {'non-targeting'}
    assert len(all_rows['non-targeting']) == len(set(all_rows['non-targeting'])) == 512
    source_rows = {target: all_rows[target] for target in TARGETS}
    assert all(len(rows) == len(set(rows)) == min(128, bundle['source_counts'][target]) for target, rows in source_rows.items())
    assert sum(map(len, source_rows.values())) == 1421
    OUT.mkdir()
    copied = []
    for name, raw in blobs.items():
        assert raw == originals[name].read_bytes()
        path = OUT / name
        with path.open('xb') as stream:
            stream.write(raw)
        assert preflight.digest(path) == preflight.digest(originals[name])
        copied.append({'name': name, 'source': str(originals[name]), 'bytes': len(raw), 'sha256': preflight.digest(path)})
    receipt = {'status': 'verified_prepared_bundle_no_model_no_scores', 'verified_utc': datetime.now(timezone.utc).isoformat(),
        'dispatcher_completion': completed[0], 'bundle_sha256': preflight.digest(OUT / 'bundle.json'),
        'targets': TARGETS, 'file_checks': checks, 'metadata_copies': copied, 'target_check': target_check,
        'source_rows': 1421, 'controls_hashes_match_pilot': True, 'manifest_declares_truth_rows_read': 0,
        'review_reads': 'Byte hashes and target metadata only; no count arrays or destination outcomes decoded',
        'scope': 'Preparation080 complete and all15 members match; no inference/confirmation authorized by this receipt'}
    proof = OUT / 'verification.json'
    with proof.open('x', encoding='utf-8') as stream:
        json.dump(receipt, stream, indent=2); stream.write('\n')
    prior = HERE / 'incidents' / 'E-20260929-004.r001.json'
    row = json.loads(prior.read_text())
    row['revision'] = 2; row['previous_sha256'] = ledger.sha(prior); row['recorded_utc'] = receipt['verified_utc']
    row['state'] = 'verified_remotely'
    row['scope'] = 'Job080rc0: bundle preparato completo,15hash verificati e12target presenti; nessuna inferenza o conferma eseguita da questa verifica.'
    evidence_path = proof.relative_to(REPO).as_posix()
    row['evidence'].append({'path': evidence_path, 'sha256': ledger.sha(proof), 'bytes': proof.stat().st_size,
                            'supports': 'Completamento remoto080, tutti15file conhash corretto, target riservati presenti'})
    row['remote_verification'] = {'evidence_path': evidence_path,
        'observed_utc': completed[0].split()[0] + '+00:00',
        'criterion': 'Dispatcher080rc0 e bundle completo con15hash corretti,12target,controlli riusati identici e provenienza congelata'}
    record = ledger.append(HERE / 'incidents', row)
    with (HERE / 'index_r4.json').open('x', encoding='utf-8') as stream:
        json.dump(ledger.index(HERE / 'incidents'), stream, indent=2, ensure_ascii=False); stream.write('\n')
    print(json.dumps({'verification': str(proof), 'bundle_sha256': receipt['bundle_sha256'], 'file_count': len(checks),
        'target_count': len(TARGETS), 'record': str(record), 'receipt_sha256': ledger.sha(proof)}))


if __name__ == '__main__':
    main()
