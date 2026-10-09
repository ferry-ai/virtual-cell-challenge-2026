"""Read the existing T39 server entry; never launch or change its state."""
import argparse
import json
from percorso import read, write_new, now
from prepare_t39_t3_runtime_r2 import FOLDER, TRIAL
from cloud_t38_delivery_r2 import auth_context


def main(label):
    from vcc import api
    proof = read(FOLDER / 'prepared.json')
    receipt = read(FOLDER / 'server_receipt_obtained.json')
    if receipt['entry_id'] != proof['entry_id']:
        raise ValueError('entry mismatch')
    auth, profile, endpoint, token = auth_context()
    result = api.get_submission(endpoint, token, proof['entry_id'])
    destination = TRIAL / ('status_' + proof['entry_id'] + '_' + label + '.json')
    write_new(destination, result)
    print(json.dumps(dict(utc=now(), entry_id=proof['entry_id'],
                         status=result.get('status'), receipt=str(destination))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('label', choices=['delivery_check_r1', 'delivery_check_r2'])
    try:
        main(parser.parse_args().label)
    except Exception as exc:
        print('T39 observation stopped: ' + type(exc).__name__)
        raise SystemExit(1)
