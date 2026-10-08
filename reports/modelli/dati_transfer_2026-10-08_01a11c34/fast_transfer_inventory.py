"""Inspect transfer-relevant identities and overlap without reading response arrays."""
from collections import defaultdict
import json
from percorso import DATA, HERE, read

t1 = read(HERE/'release_t1_r1.json')
consumption = read(HERE/'fit/dt1-01a11c34-r1/consumo.json')
view = read(read(HERE/'training_release_production_r1.json')['view']['path'])
panel = set(consumption['votes_by_target']) if 'votes_by_target' in consumption else set()
if not panel:
    import csv
    with (DATA/'raw/controls/pert_counts.csv').open(encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    print(json.dumps(dict(panel_columns=list(rows[0]), consumption_keys=list(consumption),
                         audit_keys=list(read(HERE/'audit_r1.json')))))
    panel = {r['target_gene'] for r in rows} if 'target_gene' in rows[0] else {r['gene'] for r in rows}
studies = defaultdict(lambda:dict(targets=set(), contexts=set(), units=set(), rows=0))
for chunk in view['chunks']:
    d = studies[chunk['identity']['study']]
    d['targets'].update(chunk['targets']); d['contexts'].add(chunk['context_id'])
    d['rows'] += len(chunk['targets'])
for name, d in studies.items():
    print(json.dumps(dict(study=name, contexts=len(d['contexts']), rows=d['rows'],
        targets=len(d['targets']), panel_targets=len(d['targets'] & panel),
        panel_new_to_corresponding_t1=sorted((d['targets'] & panel) - set(consumption['sources'].get(name,{}).get('targets',[]))),
        has_same_name_t1_source=name in consumption['sources'])))
print(json.dumps(dict(t1_sources={s:dict(targets=v['panel_targets_voted'],sha256=v['sha256'])
    for s,v in consumption['sources'].items()}, reference=t1['reference'],
    t1_new_sources=consumption['sources_added_to_reference'],
    t1_new_vote_targets=consumption['targets_with_added_votes'],
    not_voted=t1['derived_not_voted'], not_admitted=t1['derived_not_admitted'],
    not_launched=t1['not_launched']), indent=1))
