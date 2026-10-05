import json
from collections import Counter
from pathlib import Path
here = Path(__file__).resolve().parent
admission = json.loads((here / 'admission_r2.json').read_text(encoding='utf-8'))
print('records', admission['n_records'])
print('modality', admission['modality_counts'])
print('tags', admission['tag_counts'])
print('unit_counts', admission['units']['counts'])
print('consumer', admission['units']['consumer_access'])
print('n_units', admission['units']['n'])
print('aliases', admission['unit_ref_without_transfer_source_id'])
print('open_adapter', admission['open_adapter_ids'])
for ledger in admission['hipsci']['ledgers']:
    print(ledger['path'], ledger['n'], ledger['accepted'], ledger['owners'], 'differs', len(ledger['planned_slug_differs']))
print('ipsc', admission['ipsc_private_sample_input'])
unparsed = [row['unit'] for row in admission['units']['units'] if row.get('parsed') is False]
print('unparsed', unparsed)
states = Counter((row.get('bank_state'), row.get('samples_state')) for row in admission['units']['units'])
print('bank_sample', dict(states))
