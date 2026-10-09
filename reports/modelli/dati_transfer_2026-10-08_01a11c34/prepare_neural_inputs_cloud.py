"""Prepare private CPU jobs only. Does not push, download, launch or share."""
import ast
import argparse
import base64
from collections import defaultdict
import copy
import csv
import hashlib
import io
import json
from pathlib import Path
import re
import zipfile
import zlib
from percorso import HERE, DATA, ROOT, read, pin, sha, now, write_new


def encode(members, entry, install=False):
    payload={n:dict(data=base64.b64encode(zlib.compress(b)).decode(),sha256=hashlib.sha256(b).hexdigest())
             for n,b in members.items()}
    code='import os,sys,json,base64,zlib,hashlib,runpy\nfrom pathlib import Path\nos.chdir("/kaggle/working")\nsys.path.insert(0,"/kaggle/working")\n'
    code+='P='+repr(payload)+'\n'
    code+='for n,p in P.items():\n b=zlib.decompress(base64.b64decode(p["data"]));assert hashlib.sha256(b).hexdigest()==p["sha256"];q=Path(n);q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(b)\n'
    if install:
        code+='import subprocess,importlib.metadata as md\ncore={n:md.version(n) for n in ("numpy","scipy","pandas","h5py")}\n'
        code+='Path("core_constraints.txt").write_text("".join(n+"=="+v+"\\n" for n,v in core.items()))\n'
        code+='subprocess.check_call([sys.executable,"-m","pip","install","--disable-pip-version-check","--constraint","core_constraints.txt","anndata==0.13.3.post0","zstandard==0.25.0"])\nassert {n:md.version(n) for n in core}==core\n'
    code+='runpy.run_path('+repr(entry)+',run_name="__main__")\n'
    ast.parse(code)
    if len(code.encode())>900000:raise ValueError('Kaggle source exceeds conservative size limit')
    return code


def save_job(slug, members, entry, mounts, revision, install=False):
    stage=DATA/('processed/dati_transfer_2026-10-08_01a11c34/neural_inputs_cloud_'+revision)/slug
    code=encode(members,entry,install)
    stage.mkdir(parents=True,exist_ok=False)
    (stage/'run.py').write_text(code,encoding='utf-8',newline='\n')
    metadata=dict(id=slug,title=slug.split('/')[1],code_file='run.py',language='python',kernel_type='script',
        is_private=True,enable_gpu=False,enable_tpu=False,enable_internet=install,
        dataset_sources=sorted({m['ref'] for m in mounts if m['kind']=='dataset'}),
        kernel_sources=sorted({m['ref'] for m in mounts if m['kind']=='kernel'}),competition_sources=[])
    write_new(stage/'kernel-metadata.json',metadata)
    return dict(slug=slug,stage=str(stage),code=pin(stage/'run.py'),metadata=pin(stage/'kernel-metadata.json'),
        payload_files={n:dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest()) for n,b in members.items()},
        compute_authorized=False,current_source_access_verified=False,launched=False)


def main():
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('--revision',required=True);args=parser.parse_args()
    inventory=read(HERE/'ntc_extraction_plans_r2.json'); by_owner=defaultdict(list)
    for item in inventory['plans']:
        plan=read(item['plan']['path'])
        if sha(item['plan']['path'])!=item['plan']['sha256']:raise ValueError('NTC plan changed')
        owners={m['ref'].split('/')[0] for m in plan['mount_hints']}
        if len(owners)!=1:raise ValueError('native account assignment ambiguous: '+plan['part_id'])
        by_owner[next(iter(owners))].append((item,plan))
    jobs=[]
    for owner,items in sorted(by_owner.items()):
        members={n:(HERE/n).read_bytes() for n in ('ntc_cells.py','run_ntc_extraction.py','ntc_campaign_worker.py')}
        genes=json.dumps(items[0][1]['genes']).encode();members['plans/genes.json']=genes
        config=dict(parts=[]);mounts=[]
        for item,original in items:
            plan=copy.deepcopy(original);plan.pop('genes')
            plan.update(genes_file='genes.json',genes_sha256=hashlib.sha256(genes).hexdigest(),
                        original_plan=item['plan'])
            rows_name='rows/'+plan['part_id']+'.csv';row_path=Path(plan['rows']['path'])
            if sha(row_path)!=plan['rows']['sha256']:raise ValueError('NTC rows changed')
            with row_path.open(encoding='utf-8',newline='') as src:
                reader=csv.DictReader(src);fieldnames=reader.fieldnames;all_rows=list(reader)
            stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fieldnames);writer.writeheader()
            for new_index,record in enumerate(plan['controls']):
                old_index=record['bank_row'];row=all_rows[old_index]
                if row['target']!='NTC':raise ValueError('non-NTC cutout')
                writer.writerow(row);record.update(bank_row=new_index,original_bank_row=old_index)
            members[rows_name]=stream.getvalue().encode()
            plan['original_rows']=plan['rows'];plan['rows']=dict(bytes=len(members[rows_name]),
                sha256=hashlib.sha256(members[rows_name]).hexdigest())
            name='plans/'+plan['part_id']+'.json';members[name]=(json.dumps(plan)+'\n').encode()
            mounts.extend(plan['mount_hints'])
            config['parts'].append(dict(plan=name,plan_sha256=hashlib.sha256(members[name]).hexdigest(),rows=rows_name))
        members['job.json']=json.dumps(config).encode()
        job=save_job(owner+'/dt-ntc-inputs-01a11c34-'+args.revision,members,'ntc_campaign_worker.py',mounts,args.revision)
        job.update(parts=len(items),contexts=sorted({c for item,p in items for c in item['contexts']}))
        jobs.append(job)
    # Reuse only verified code/configuration/axis members of the previous package.
    base=HERE/'fit/dt1-01a11c34-r1/package'
    code=(base/'run.py').read_text()
    encoded=re.search(r"b64decode\('([A-Za-z0-9+/=]+)'\)",code).group(1)
    with zipfile.ZipFile(io.BytesIO(base64.b64decode(encoded))) as archive:
        old={name:archive.read(name) for name in archive.namelist() if not name.endswith('/')}
    params=json.loads(old['params.json'])
    for name,digest in params['embedded_sha256'].items():
        if hashlib.sha256(old[name]).hexdigest()!=digest:raise ValueError('base embedded member changed')
    members={n:b for n,b in old.items() if n.startswith(('repo/','data/raw/controls/'))}
    members.update({n:(HERE/n).read_bytes() for n in ('ntc_cells.py','run_ntc_extraction.py','panel_anchor_worker.py')})
    contract=read(HERE/'panel_anchor_requests_r1.json')
    if hashlib.sha256(members['repo/scripts/100_build_context_effects.py']).hexdigest()!=contract['stage100']['sha256']:
        raise ValueError('stage100 differs from frozen request')
    contract['coordinates']=read(ROOT/'reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/banco/r1/package/params.json')['coords']
    contract['parity_requests']=[]
    canonical=read(contract['canonical_release']['path'])
    production=read(contract['production_recipe']['path'])
    for lineage,tag in [('K562','k562'),('iPSC','ipsc')]:
        ident='parity_'+tag
        names=sorted(s for s,l in contract['source_lineages'].items() if l!=lineage)
        recipe=copy.deepcopy(production);one=next(iter(recipe['contexts'].values()))
        recipe['contexts']={ident:dict(amplitude=one['amplitude'],weights={s:1. for s in names})}
        data=json.dumps(recipe).encode();members['recipes/'+ident+'.json']=data
        reference=read(ROOT/('reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/banco/livello_b_'+tag+'_r1/effetti.json'))
        contract['parity_requests'].append(dict(id=ident,excluded_lineages=[lineage],sources=names,
            recipe=dict(bytes=len(data),sha256=hashlib.sha256(data).hexdigest()),
            expected_effects_sha256=reference['files']['T0']['sha256'],
            source_pins={s:canonical['voted'][s] for s in names},
            expected_cache_sha256={s+'.npz':canonical['voted'][s]['sha256'] for s in names}))
    for request in contract['requests']:
        path=Path(request['recipe']['path'])
        if sha(path)!=request['recipe']['sha256']:raise ValueError('anchor recipe changed')
        members['recipes/'+path.name]=path.read_bytes()
    members['anchor_requests.json']=json.dumps(contract).encode()
    meta=read(base/'kernel-metadata.json')
    mounts=[dict(kind='kernel',ref=r) for r in meta['kernel_sources']]
    mounts += [dict(kind='dataset',ref=r) for r in meta['dataset_sources']]
    jobs.append(save_job('davideferrante11/dt-ammi-anchors-01a11c34-'+args.revision,members,'panel_anchor_worker.py',mounts,args.revision,True))
    report=dict(utc=now(),jobs=jobs,cloud_jobs_prepared=len(jobs),cloud_jobs_launched=0,
        visibility='all private; no change to source sharing',quota_authorized=False,
        control_extraction_parts=30,control_contexts=47,new_anchor_requests=17,parity_checks=2,
        private_cross_account_output_transfer_authorized=False,
        before_launch=['fresh per-job input access and resource checks','explicit consent for new cloud quota'],
        tests=pin(HERE/'ntc_cells_tests_r5.txt'))
    write_new(HERE/('neural_inputs_cloud_prepared_'+args.revision+'.json'),report)
    print(json.dumps(dict(jobs=[dict(slug=j['slug'],code_bytes=j['code']['bytes'],parts=j.get('parts')) for j in jobs])))


if __name__=='__main__':main()
