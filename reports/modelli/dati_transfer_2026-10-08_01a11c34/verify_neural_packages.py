"""Audit prepared cloud payloads without executing bootstrap, network or RNA."""
import ast
import argparse
import base64
import csv
import hashlib
import io
import json
from pathlib import Path
import zlib
from percorso import HERE, read, pin, sha, now, write_new


def main():
    parser=argparse.ArgumentParser(__doc__)
    parser.add_argument('--prepared',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    prepared=read(args.prepared);out=[]
    for job in prepared['jobs']:
        path=Path(job['code']['path'])
        if sha(path)!=job['code']['sha256']:raise ValueError('package changed')
        if sha(job['metadata']['path'])!=job['metadata']['sha256']:raise ValueError('metadata changed')
        tree=ast.parse(path.read_text())
        assignments=[n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='P' for t in n.targets)]
        if len(assignments)!=1:raise ValueError('ambiguous bootstrap payload')
        payload=ast.literal_eval(assignments[0].value)
        members={}
        for name,spec in payload.items():
            if Path(name).is_absolute() or '..' in Path(name).parts:raise ValueError('unsafe member')
            data=zlib.decompress(base64.b64decode(spec['data']))
            if hashlib.sha256(data).hexdigest()!=spec['sha256']:raise ValueError('embedded hash mismatch')
            if name.endswith('.py'):ast.parse(data,filename=name)
            members[name]=data
        if set(members)!=set(job['payload_files']):raise ValueError('payload inventory mismatch')
        count=0
        if 'official_contract.json' in members:
            contract=json.loads(members['official_contract.json'])
            for plan in contract['plans']:
                value=dict(plan);expected=value.pop('plan_sha256')
                if hashlib.sha256(json.dumps(value,sort_keys=True,separators=(',',':')).encode()).hexdigest()!=expected:
                    raise ValueError('official plan changed')
                if plan['cells_per_stratum']!=64 or plan['denominator_policy']!='full_provided_official_X_before_alignment':
                    raise ValueError('official denominator or selection differs')
                if len(plan['genes'])!=18533 or plan['part_role']!='destination':raise ValueError('official axis or role differs')
                count+=1
        elif 'job.json' in members:
            config=json.loads(members['job.json'])
            for part in config['parts']:
                data=members[part['plan']]
                if hashlib.sha256(data).hexdigest()!=part['plan_sha256']:raise ValueError('part pin changed')
                plan=json.loads(data);original=read(plan['original_plan']['path'])
                if sha(plan['original_plan']['path'])!=plan['original_plan']['sha256']:raise ValueError('original plan changed')
                genes=members['plans/'+plan['genes_file']]
                if hashlib.sha256(genes).hexdigest()!=plan['genes_sha256'] or json.loads(genes)!=original['genes']:
                    raise ValueError('gene axis changed')
                rows=members[part['rows']]
                if hashlib.sha256(rows).hexdigest()!=plan['rows']['sha256']:raise ValueError('row cutout pin differs')
                records=list(csv.DictReader(io.StringIO(rows.decode())))
                with Path(original['rows']['path']).open(newline='',encoding='utf-8') as f:
                    old_rows=list(csv.DictReader(f))
                if len(records)!=len(plan['controls']):raise ValueError('control cutout coverage differs')
                for new,old in zip(plan['controls'],original['controls']):
                    if records[new['bank_row']]!=old_rows[old['bank_row']] or records[new['bank_row']]['target']!='NTC':
                        raise ValueError('wrong control cutout')
                    if new['context_id']!=old['context_id'] or new['expected_cells']!=old['expected_cells']:
                        raise ValueError('control assignment changed')
                if plan['sources']!=original['sources']:raise ValueError('source inventory changed')
                count+=1
        else:
            contract=json.loads(members['anchor_requests.json'])
            for req in contract['parity_requests']+contract['requests']:
                recipe=members['recipes/'+req['id']+'.json']
                if hashlib.sha256(recipe).hexdigest()!=req['recipe']['sha256']:raise ValueError('anchor recipe changed')
                value=json.loads(recipe)
                if value['common']!='panel' or set(value['contexts'][req['id']]['weights'])!=set(req['sources']):
                    raise ValueError('anchor definition changed')
                if any(contract['source_lineages'][s] in req['excluded_lineages'] for s in req['sources']):
                    raise ValueError('held lineage admitted')
                count+=1
        metadata=read(job['metadata']['path'])
        if not metadata['is_private'] or metadata['enable_gpu']:raise ValueError('wrong privacy or accelerator')
        out.append(dict(slug=job['slug'],status='PASS',units_or_anchor_requests=count,code_bytes=path.stat().st_size))
    result=dict(utc=now(),status='PASS',jobs=out,
        checked='decoded payload SHA, Python syntax, exact NTC cutout equality, gene/source identity, anchor exclusions, private CPU metadata',
        actual_remote_input_access_verified=False,real_numeric_extraction_executed=False)
    result['prepared']=pin(args.prepared)
    write_new(args.out,result)
    print(json.dumps(result))


if __name__=='__main__':main()
