"""Count planned code work from small metadata only; not a timing model or effect read."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--data', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    with (args.data/'contexts.csv').open(newline='', encoding='utf-8') as f:
        contexts = [row for row in csv.DictReader(f) if row['modality'] == 'crispri']
    with (args.data/'targets.csv').open(newline='', encoding='utf-8') as f:
        panel = np.asarray([row['in_panel'].lower() in {'true','1','1.0'} for row in csv.DictReader(f)])
    row_targets = np.load(args.data/'row_target.npy', mmap_mode='r', allow_pickle=False)
    for c in contexts:
        c['rows'] = int(c['row_stop'])-int(c['row_start'])
        c['eligible_nonpanel'] = int((~panel[row_targets[int(c['row_start']):int(c['row_stop'])]]).sum())
    manifest = json.loads((args.data/'manifest.json').read_text())
    genes = manifest['counts']['genes']
    families = ['k562','cd4','orion','ipsc','rpe1']
    family_rows = {f:sum(c['rows'] for c in contexts if c['family']==f) for f in families}
    folds = []
    for family in families:
        visible = [c for c in contexts if c['family'] != family]
        ordered = sorted((family_rows[f], f) for f in families if f != family)
        validation_family = ordered[len(ordered)//2][1]
        val = [c for c in visible if c['family']==validation_family]
        held = [c for c in contexts if c['family']==family]
        model_batches = sum(math.ceil(min(512,c['eligible_nonpanel'])/16)*math.ceil(genes/1024)*5 for c in held)
        max_validation_batches = 2*21*sum(math.ceil(min(128,c['eligible_nonpanel'])/16)*math.ceil(min(2048,genes)/1024) for c in val)
        targets = sum(min(512,c['eligible_nonpanel']) for c in held)
        profiles = sum(min(512,c['eligible_nonpanel'])*math.ceil(genes/1024)*5*len(visible) for c in held)
        features_bytes = targets*genes*5*len(visible)*20*4
        folds.append({'family':family, 'validation_family':validation_family, 'visible_contexts':len(visible),
                      'test_contexts':len(held), 'test_targets':targets, 'test_forward_batches':model_batches,
                      'test_profile_calls':profiles, 'test_feature_bytes_cumulative':features_bytes,
                      'max_validation_forward_batches':max_validation_batches,
                      'centering_rows_once':sum(c['rows'] for c in visible),
                      'training_forward_steps_upper_bound':4000})
    result = {'created_utc':datetime.now(timezone.utc).isoformat(),
              'claim_type':'static work counts from frozen code and input metadata; no remote progress or elapsed prediction',
              'effect_values_read':False, 'genes':genes, 'contexts':len(contexts), 'folds':folds,
              'totals':{key:sum(f[key] for f in folds) for key in ('test_contexts','test_targets','test_forward_batches',
                        'test_profile_calls','test_feature_bytes_cumulative','max_validation_forward_batches',
                        'centering_rows_once','training_forward_steps_upper_bound')},
              'feature_bytes_max_one_batch':16*max(f['visible_contexts'] for f in folds)*1024*20*4,
              'centering_raw_shrunk_se_float16_source_bytes':sum(f['centering_rows_once'] for f in folds)*genes*3*2,
              'training_fit_calls':20, 'model_selection_fit_calls':10, 'refit_calls':10,
              'sources':{str(path):digest(path) for path in (HERE/'train_neural_sources.py', HERE/'neural_sources.py',
                          args.data/'manifest.json', args.data/'contexts.csv', args.data/'targets.csv', args.data/'row_target.npy')},
              'limitations':['Training/refit can stop early; counts labelled upper bound are not measured execution.',
                             'Feature bytes are cumulative allocated/uploaded float32 payload, not peak RAM.',
                             'No claim which operation dominates wall time without profiling.',
                             'NPZ compression, metrics, label reads and tensor intermediates are additional work.']}
    with args.out.open('x', encoding='utf-8') as f:
        json.dump(result,f,indent=2)
        f.write('\n')
    print(json.dumps({key:result[key] for key in ('totals','feature_bytes_max_one_batch','centering_raw_shrunk_se_float16_source_bytes')}))


if __name__ == '__main__':
    main()
