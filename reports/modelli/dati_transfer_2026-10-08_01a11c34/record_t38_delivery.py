"""Cross-check saved delivery evidence and preserve canonical stage receipts."""
from percorso import HERE, ROOT, read, pin, write_new, now
from collect_t38_generation import verify_receipts


def main():
    folder = HERE / 'cloud_delivery/r3'
    trial = ROOT / 'reports/invii/trial_2026-10-09'
    dest = folder / 'completion_r1'
    proof = read(folder / 'prepared.json')
    manifest = verify_receipts(dest, proof)
    watcher = read(folder / 'watcher_result_r1.json')
    receipt = read(dest / 'upload_receipt.json')
    submission = read(trial / 'submit_t38_cloud_result.json')
    server = read(watcher['receipt']['path'])
    for item in (watcher, receipt, submission, server):
        assert item['entry_id'] == 'LJmnhqqh1WTrx1JcoRlr'
    assert watcher['status'] == 'SERVER_RECEIPT_OBTAINED'
    assert pin(watcher['receipt']['path']) == watcher['receipt']
    assert pin(watcher['submission']['path']) == watcher['submission']
    assert receipt['status'] == 'UPLOAD_VERIFIED' and receipt['md5_verified']
    assert receipt['md5_local'] == receipt['md5_remote']
    assert receipt['sha256'] == manifest['sha256']
    assert receipt['bytes_uploaded'] == manifest['bytes'] == 3993702400
    assert read(trial / 't38_launch_response.json')['job_name'] == submission['job_name']
    assert server['status'] == 'launching' and server['score_avg'] is None
    mappings = {
        'generation_stage45_manifest.json': 't38_manifest_45_generate_prediction.json',
        'compact_diagnostics.json': 't38_generation_diagnostics.json',
        'manifest_48_package_prediction.json': 't38_manifest_48_package_prediction.json',
        'packaging.json': 't38_packaging.json',
        'generation_manifest.json': 't38_generation_manifest.json',
    }
    for source, target in mappings.items():
        data = (dest / source).read_bytes()
        output = trial / target
        if output.exists():
            assert output.read_bytes() == data
        else:
            with output.open('xb') as handle:
                handle.write(data)
    write_new(HERE / 't38_delivery_verified_r1.json', dict(
        utc=now(), status='DELIVERY_AND_SERVER_LAUNCH_VERIFIED', entry_id=receipt['entry_id'],
        upload_finished_utc=receipt['utc_upload_verified'], server_status_at_receipt=server['status'],
        product_bytes=manifest['bytes'], product_sha256=manifest['sha256'],
        source_sha256=read(dest / 'packaging.json')['input']['sha256'],
        shape=[360000, 18533], md5_verified=True, payload_bit_identical=True,
        scientific_score_available=False, scientific_promotion=False, claims_complete_D053=False,
        new_fit=False, new_generation=False, new_entry_during_recovery=False,
        watcher=pin(folder / 'watcher_result_r1.json'), upload=pin(dest / 'upload_receipt.json'),
        server_receipt=watcher['receipt'], submission=watcher['submission'],
        stage_receipts={target: pin(trial / target) for target in mappings.values()}))
    print('PASS: delivery, payload, upload checksum, and server launch receipts agree')


if __name__ == '__main__':
    main()
