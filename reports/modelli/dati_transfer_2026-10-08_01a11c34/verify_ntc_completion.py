"""Verify terminal NTC receipts against frozen plans, without local RNA download."""
import argparse
from collections import Counter
import json
from pathlib import Path
import subprocess
import sys
from build_ammi_runtime_contract import payload
from percorso import HERE, now, read, pin, sha, write_new


def main():
    p=argparse.ArgumentParser(__doc__);p.add_argument('--prepared',type=Path,required=True)
    p.add_argument('--slug',required=True);p.add_argument('--metadata',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--allow-partial',action='store_true');a=p.parse_args()
    job=next(j for j in read(a.prepared)['jobs'] if j['slug']==a.slug)
    remote=subprocess.run([sys.executable,str(HERE/'remote_identity.py'),a.slug.split('/')[0],a.slug],
        capture_output=True,text=True,timeout=120)
    if remote.returncode:raise RuntimeError('saved code lookup failed')
    identity=json.loads(remote.stdout)
    if identity!={'source_sha256':job['code']['sha256'],'version':1,'is_private':True}:
        raise ValueError('saved code identity differs')
    members=payload(job);config=json.loads(members['job.json'])
    completions=list(a.metadata.rglob('campaign_complete.json'))
    expected={json.loads(members[x['plan']])['part_id'] for x in config['parts']}
    if len(completions)>1 or (not completions and not a.allow_partial):
        raise ValueError('unique campaign completion required')
    if completions:
        done=read(completions[0]);entries=done['parts']
        if done['status']!='COMPLETE':raise ValueError('campaign not complete')
        summary=completions[0]
    else:
        summary=a.metadata/'progress.json';entries=read(summary)
    listed={x['part_id']:x for x in entries}
    if not listed or not set(listed)<=expected or len(entries)!=len(listed):
        raise ValueError('invalid completed parts')
    if not a.allow_partial and set(listed)!=expected:
        raise ValueError('campaign parts incomplete')
    parts={};total=Counter()
    for item in config['parts']:
        plan=json.loads(members[item['plan']]);part=plan['part_id']
        if part not in listed:continue
        hits=[x for x in a.metadata.rglob('complete.json') if x.parent.name==part]
        if len(hits)!=1:raise ValueError('part completion missing')
        path=hits[0];doc=read(path)
        if doc['status']!='COMPLETE' or doc['part_id']!=part or doc['plan_sha256']!=item['plan_sha256']:
            raise ValueError('part plan differs')
        import hashlib
        codes={n:hashlib.sha256(members[n]).hexdigest() for n in ('run_ntc_extraction.py','ntc_cells.py')}
        if doc['code']!=codes:raise ValueError('runtime reader differs')
        population=Counter()
        for control in plan['controls']:population[control['context_id']]+=control['expected_cells']
        if set(population)!=set(doc['contexts']) or any(not 0<n<=population[c] for c,n in doc['contexts'].items()):
            raise ValueError('NTC context coverage/population differs')
        if doc['NTC_cells_read']!=sum(doc['contexts'].values()) or doc['arrays_shape']!=[doc['NTC_cells_read'],18533]:
            raise ValueError('NTC counts/axes differ')
        if doc['perturbed_RNA_rows_read']!=0 or doc['cells_consumed_by_trainer']!=0 or doc['complete_D053']:
            raise ValueError('invalid NTC-only consumption claim')
        raw=doc['raw_sizes_measured']
        if set(raw)!={s['sha256'] for s in plan['sources']} or doc['source_files_verified']!=len(raw):
            raise ValueError('missing raw source verification')
        for source in plan['sources']:
            if raw[source['sha256']]<=0 or (source.get('bytes') is not None and raw[source['sha256']]!=source['bytes']):
                raise ValueError('raw source size differs')
        if set(doc['files'])!={'counts.npz','axes_depth_mask.npz','cells.json'}:raise ValueError('output files differ')
        if any(x['bytes']<=0 or len(x['sha256'])!=64 for x in doc['files'].values()):raise ValueError('invalid output pin')
        if listed[part]['contexts']!=doc['contexts'] or listed[part]['cells']!=doc['NTC_cells_read']:
            raise ValueError('campaign and part counts disagree')
        total.update(doc['contexts'])
        parts[part]=dict(completion=pin(path),plan_sha256=item['plan_sha256'],contexts=doc['contexts'],
            files={name:{**v,'remote_path':'ntc/'+part+'/'+name} for name,v in doc['files'].items()},
            resources=doc['resources'],raw_sources=len(raw))
    report=dict(utc=now(),status='PASS_METADATA_AND_CODE',slug=a.slug,remote_identity=identity,
        prepared=pin(a.prepared),completion_summary=pin(summary),parts=parts,
        campaign_complete=set(listed)==expected,missing_parts=sorted(expected-set(listed)),
        contexts=dict(total),NTC_candidates_before_global_merge=sum(total.values()),
        raw_RNA_downloaded=False,numeric_output_arrays_independently_rehashed=False,
        runtime_consumer_must_verify_output_hashes=True,training_executed=False,complete_D053=False)
    write_new(a.out,report)
    print(json.dumps(dict(status=report['status'],parts=len(parts),contexts=len(total),cells=sum(total.values()))))


if __name__=='__main__':main()
