import json
from pathlib import Path
from linear_transfer import refuse
from reconcile import build_admission

here = Path(__file__).resolve().parent
admission = build_admission()
admission['corrects'] = (
    'admission.json missed HIPSCI job.state; admission_r2.json marked ingested rows as open_adapter '
    'because that section has no adapter field')
path = here / 'admission_r3.json'
refusal_path = here / 'refusal_r3.json'
if path.exists() or refusal_path.exists():
    raise SystemExit('r3 files exist')
path.write_text(json.dumps(admission, indent=1), encoding='utf-8')
refusal = refuse(admission, refusal_path)
print(json.dumps({'open_adapter': len(admission['open_adapter_ids']),
                  'tags': admission['tag_counts'], 'fit_launched': refusal['fit_launched'],
                  'blockers': admission['blockers']}, indent=1))
