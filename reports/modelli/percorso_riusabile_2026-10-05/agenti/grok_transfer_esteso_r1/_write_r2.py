import json
from pathlib import Path
from linear_transfer import refuse
from reconcile import build_admission

here = Path(__file__).resolve().parent
admission = build_admission()
admission['corrects'] = 'admission.json counted HIPSCI verified parts as 0 because it required bank.state; the state file stores job.state and samples.state'
path = here / 'admission_r2.json'
if path.exists():
    raise SystemExit('admission_r2.json exists')
path.write_text(json.dumps(admission, indent=1), encoding='utf-8')
refusal = refuse(admission, here / 'refusal.json')
print(json.dumps({'fit_admitted': admission['fit_admitted'], 'hipsci': admission['hipsci']['bank_and_samples_verified'],
                  'units': admission['hipsci']['units'], 'blockers': admission['blockers'],
                  'fit_launched': refusal['fit_launched']}, indent=1))
