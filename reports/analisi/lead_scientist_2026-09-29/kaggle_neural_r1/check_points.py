"""Independent point-estimate reconstruction from downloaded CSVs, no model code."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
OUT = HERE / 'independent_points_r1.json'
if OUT.exists():
    raise FileExistsError(OUT)
files = sorted((HERE / 'results_small_r1/neural_sources_r1/folds').glob('*/per_target.csv'))
assert len(files) == 5
frame = pd.concat([pd.read_csv(p, keep_default_na=False) for p in files], ignore_index=True)
assert not frame.duplicated(['family', 'context', 'target', 'arm']).any()
assert frame[['rank', 'cosine', 'nmse']].notna().all().all()
wide = frame.pivot(index=['family', 'context', 'target'], columns='arm', values='rank')
assert wide.notna().all().all()
verdict = json.loads((HERE / 'readout_verified_r1/verdict.json').read_text())
points = {}
for arm in ('transfer', 'blind', 'swap', 'prior_permuted', 'null'):
    delta = wide['net'] - wide[arm]
    # Average contexts before families; each receives equal mass.
    per_family = delta.groupby(['family', 'context']).mean().groupby('family').mean()
    macro = float(per_family.mean())
    reported = verdict['contrasts'][arm]
    assert abs(macro - reported['macro_family_delta']) < 1e-14
    assert all(abs(float(v) - reported['per_family'][k]) < 1e-14 for k, v in per_family.items())
    points[arm] = {'macro': macro, 'per_family': per_family.to_dict()}
record = {'utc': datetime.now(timezone.utc).isoformat(), 'verified': True,
          'target_context_pairs': len(wide), 'distinct_targets': len(set(frame.target)),
          'contexts': len(set(frame.context)), 'families': len(set(frame.family)),
          'points': points, 'bootstrap_independently_recomputed': False,
          'input_sha256': {str(p.relative_to(HERE)): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}}
OUT.write_text(json.dumps(record, indent=2)+'\n', encoding='utf-8')
print(json.dumps({k: v for k, v in record.items() if k != 'input_sha256'}, indent=2))
