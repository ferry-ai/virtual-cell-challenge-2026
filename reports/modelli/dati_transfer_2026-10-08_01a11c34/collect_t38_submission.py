"""Preserve exact CLI receipts and query one completed upload, without a new entry."""
import argparse
import json
from pathlib import Path
import re
import subprocess
from percorso import DATA, HERE, ROOT, pin, read, write_new, now
from t38_submission import cli, MODEL

TRIAL = ROOT / 'reports/invii/trial_2026-10-09'


def preserve(source, destination):
    data = source.read_bytes()
    text = data.decode('utf-8-sig')
    if 'kaggleusercontent.com' in text or re.search(r'"(?:token|access_token|signed_url|upload_url)"\s*:', text):
        raise ValueError('potential private access material in raw receipt')
    if destination.exists():
        if destination.read_bytes() != data:
            raise ValueError('existing receipt differs')
    else:
        with destination.open('xb') as out:
            out.write(data)


def main(attempt, label):
    run = DATA / 'processed/dati_transfer_2026-10-08_01a11c34/submission_t38' / attempt
    finish = read(run / 'finished.json')
    if finish['returncode'] != 0:
        raise ValueError('submit has not succeeded; inspect pending upload before any resume')
    raw = run / 'submit_raw.json'
    receipt = read(raw)
    product = read(TRIAL / 't38_local_product.json')
    if (receipt['model_name'] != MODEL or receipt['bytes_uploaded'] != product['bytes']
            or receipt.get('md5_verified') is not True):
        raise ValueError('upload identity or checksum verification differs')
    entry = receipt['entry_id']
    if not re.fullmatch('[A-Za-z0-9_-]+', entry):
        raise ValueError('invalid entry identifier')
    preserve(raw, TRIAL / 'submit_t38_raw.json')
    preserve(raw, TRIAL / ('submit_' + entry + '.json'))
    private = run / ('status_' + label)
    private.mkdir(exist_ok=False)
    with (private / 'raw.json').open('x', encoding='utf-8') as out, (private / 'stderr.txt').open('x', encoding='utf-8') as err:
        result = subprocess.run([cli(), 'status', entry, '--json'], stdout=out, stderr=err)
    if result.returncode:
        raise ValueError('status request failed; no submission retry')
    status = read(private / 'raw.json')
    destination = TRIAL / ('status_' + entry + '_' + label + '.json')
    preserve(private / 'raw.json', destination)
    report = dict(utc=now(), entry_id=entry, bytes_uploaded=receipt['bytes_uploaded'], md5_verified=True,
        product_sha256=product['sha256'], submit_returned_utc=finish['utc'],
        official_submit=pin(TRIAL / ('submit_' + entry + '.json')), official_status=pin(destination),
        official_status_keys=list(status), new_submission_started=False)
    write_new(TRIAL / ('delivery_' + label + '.json'), report)
    print(json.dumps(report))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--attempt', default='delivery_r1')
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    try:
        main(args.attempt, args.label)
    except Exception as exc:
        print('Submission receipt collection failed: ' + type(exc).__name__)
        raise SystemExit(1)
