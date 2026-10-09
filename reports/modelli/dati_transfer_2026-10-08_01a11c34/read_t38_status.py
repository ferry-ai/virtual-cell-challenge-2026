"""Save one read-only status response for the existing T38 entry."""
import argparse
import json
from percorso import ROOT, write_new
from cloud_t38_delivery_r2 import auth_context


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('label')
    args = parser.parse_args()
    if not args.label.replace('_', '').isalnum():
        raise ValueError('invalid label')
    entry = 'LJmnhqqh1WTrx1JcoRlr'
    destination = ROOT / 'reports/invii/trial_2026-10-09' / ('status_' + entry + '_' + args.label + '.json')
    if destination.exists():
        raise ValueError('receipt already exists')
    from vcc import api
    auth, profile, endpoint, token = auth_context()
    response = api.get_submission(endpoint, token, entry)
    write_new(destination, response)
    print(json.dumps({key: response.get(key) for key in ('entry_id', 'status', 'score_avg', 'error_info')}))
