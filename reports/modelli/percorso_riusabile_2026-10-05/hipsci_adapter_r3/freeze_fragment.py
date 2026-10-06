"""Freeze a new source fragment without changing t36 or declaring full admission."""
import hashlib
import json
from collections import Counter
from pathlib import Path

here=Path(__file__).resolve().parent
proof_dir=here/'completion_r1'
receipt=json.loads((proof_dir/'fit_receipt.json').read_text())
verification=json.loads((proof_dir/'verification.json').read_text())
assert verification['verified'] and verification['saved_code_matches']
assert not receipt['mixer_consumed'] and not receipt['full_training']
roles=Counter()
for row in receipt['lineage']['roles']:
    roles[row['role']]+=row['cells']
assert sum(roles.values())==1161865
assert sum(receipt['n_cells'])==7583
def pin(path):
    return dict(path=path.relative_to(here.parent).as_posix(),bytes=path.stat().st_size,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest())
candidate=dict(kind='new_production_source_fragment_candidate_not_full_release',
    cloud=dict(job=verification['job'],version=verification['version']),
    output=receipt['output'],receipt=pin(proof_dir/'fit_receipt.json'),
    verification=pin(proof_dir/'verification.json'),original_model_package=pin(here.parent/'release_t36_reuse_r1.json'),
    params_sha256=verification['params_sha256'],axis_sha256=receipt['axis_sha256'],panel_sha256=receipt['panel_sha256'],
    source_name='hipsci_targeted_19',source_weight=1,source_vote=receipt['source_vote'],
    targets=receipt['targets'],target_cells=sum(receipt['n_cells']),roles_cells=dict(roles),
    contexts=receipt['contexts'],recipe=receipt['recipe'],
    chemistry_policy='UNREPORTED isolated within hipsci_targeted_19; no inferred chemistry',
    full_training=False,mixer_consumed=False,scientific_admission_complete=False,
    pending=['Verify exact NPZ bytes, axis, panel and recipe in the downstream consumer',
             'Record knockdown/QC policy and weak-clone evidence before scientific admission',
             'Resolve remaining native/off-panel target identities and auxiliary roles for D-053',
             'Freeze a new expanded release with source accounting; keep t36 immutable',
             'Production fragment is not held-out C/J validation; derive legal split dependencies separately'])
path=proof_dir/'source_candidate.json'
with path.open('x',encoding='utf-8') as f:json.dump(candidate,f,indent=1);f.write('\n')
print(json.dumps(dict(targets=candidate['targets'],target_cells=candidate['target_cells'],roles_cells=dict(roles),contexts=len(candidate['contexts']))))
