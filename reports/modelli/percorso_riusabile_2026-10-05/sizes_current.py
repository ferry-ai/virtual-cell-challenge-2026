"""Summarize metadata sizes and explicitly approximate unfinished sample parts."""
import json
from pathlib import Path
HERE=Path(__file__).resolve().parent
catalog=json.loads((HERE/'cloud_catalog_r1/manifest.json').read_text())
progress=json.loads((HERE/'other_sample_progress_r7.json').read_text())
launches={r['slug']:r for r in map(json.loads,(HERE/'other_sample_launches.jsonl').read_text().splitlines()) if r['accepted']}
banks=[];raw_bytes=0
for unit,e in catalog['units'].items():
    r=json.loads(Path(e['bank']['receipt']).read_text())
    banks.append({'unit':unit,'contexts':r['contexts'],'cells':r['cells_used'],
                  'rows':r['rows'],'bytes':sum(f['bytes'] for f in r['files'].values())})
    raw=json.loads(Path(e['raw']['receipt']).read_text())
    raw_bytes+=sum(p.get('bytes',0) for p in raw['parts'])
estimated={};remaining={}
for job,entry in progress['jobs'].items():
    p=launches[job]['parameters'];events=[e for e in entry['events'] if 'output_bytes' in e]
    if not events:continue
    last=events[-1];done=(last['shard']-1-p['part'])//p['parts']+1
    total=len(range(p['part'],last['of'],p['parts']))
    estimated.setdefault(p['unit'],[]).append(last['output_bytes']*total/done)
    if 'RUNNING' in entry['status']:
        remaining[job]={'processed_shards':done,'total_shards':total,
                        'rough_remaining_minutes':round(last['seconds']*(total-done)/done/60)}
result={'source':'cloud_catalog_r1 and other_sample_progress_r7',
        'bank_bytes_measured':sum(b['bytes'] for b in banks),'raw_bytes_measured':raw_bytes,
        'contexts':sum(b['contexts'] for b in banks),'cells':sum(b['cells'] for b in banks),
        'banks':banks,'cd4_sample_bytes_measured':sum(e['samples'].get('bytes',0) for e in catalog['units'].values()),
        'new_sample_bytes_estimated':{unit:round(sum(values)/len(values)*next(r['parameters']['parts'] for r in launches.values() if r['parameters']['unit']==unit)) for unit,values in estimated.items()},
        'rough_remaining_minutes':remaining,'estimate_caveat':'Linear extrapolation; shard density, startup, provider and IO may vary. Not a training start ETA.'}
out=HERE/'sizes_current_r1.json'
with out.open('x') as f:f.write(json.dumps(result,indent=1))
print(json.dumps({k:v for k,v in result.items() if k!='banks'}))
