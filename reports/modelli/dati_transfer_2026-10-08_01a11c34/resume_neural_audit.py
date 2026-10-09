"""Resume metadata audit; no remote job, array read, or source mutation."""
import argparse
import json
from pathlib import Path
from percorso import HERE, ROOT, DATA, read, pin, now, write_new
from verify_external_consumption import verify

MODELS = ROOT / 'reports/analisi/modelli_esterni_01a11c35_2026-10-08'
RUNS = DATA / 'external_models/01a11c35/verified_cloud_outputs'


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('--inspect', action='store_true')
    parser.add_argument('--regime')
    parser.add_argument('--slug')
    parser.add_argument('--prepared')
    parser.add_argument('--owner', default='davideferrante11')
    parser.add_argument('--out', type=Path)
    parser.add_argument('--run-root', type=Path, default=RUNS)
    args = parser.parse_args()
    if args.inspect:
        manifest=read(HERE/'neural_input_contract_manifest_r2.json')
        contract = read(manifest['contract']['path'])
        print(json.dumps(dict(summary=contract['summary'], samples=[dict(
            unit=unit, role=record['current_role'],
            receipt_count=len(record['sample_receipts']))
            for unit, record in contract['bank_units'].items()]), indent=2))
        return
    release = read(HERE / ('training_release_' + args.regime + '_r1.json'))
    run = args.run_root / args.slug / args.slug
    result = verify(release['view']['path'], release['view']['sha256'],
                    run / 'fit/manifest.json', run / 'complete.json',
                    run / 'resolution_receipt.json', MODELS / args.prepared,
                    expected_owner=args.owner,
                    access_authorization=HERE / 'multi_account_authorization_r3.json')
    result.update(utc=now(), inputs=dict(view=release['view'], completion=pin(run/'complete.json')))
    write_new(args.out, result)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
