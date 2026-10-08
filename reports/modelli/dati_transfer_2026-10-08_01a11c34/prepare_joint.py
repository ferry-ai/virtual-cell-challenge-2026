"""Prepare six explicit joint source jobs for each production/TJ regime; no launch."""
import argparse
import ast
import base64
import hashlib
import json
from pathlib import Path
import zlib
from joint_rows import UNITS
from percorso import BANK,DATA,HERE,ROOT,now,pin,read,sha,write_new


def main(version='j1',inventory_name='inventory_r1.json'):
    frozen={name:(HERE/name).read_bytes() for name in ('fold_bank.py','alltarget_runtime.py','joint_rows.py','joint_runtime.py')}
    frozen['estimator.py']=(BANK/'consumer/estimator.py').read_bytes()
    frozen['gene_names.csv']=(DATA/'raw/controls/gene_names.csv').read_bytes()
    policies=['cd4_Rest','cd4_Stim8hr','cd4_Stim48hr','h1','k562_gwps','hipsci_targeted_19']
    inventory=[]
    for parent,revision in [('01a11c34-r3','01a11c34-'+version+'p'),('01a11c34-tj1','01a11c34-'+version+'t')]:
        for policy in policies:
            members=dict(frozen);units={};mounts={};split=None;parents=[]
            for unit in sorted(UNITS[policy]):
                proofpath=HERE/'alltargets'/parent/unit/'prepared.json';proof=read(proofpath)
                parameter=ROOT/proof['stage']/'params.json'
                if sha(parameter)!=proof['params']['sha256']:raise ValueError('parent parameter changed')
                p=read(parameter)
                if split is not None and split!=p['split']:raise ValueError('different unit splits')
                split=p['split'];units[unit]={k:p[k] for k in ('bank','resolved_labels','mapping_evidence')}
                mount=p['bank']['mount'];mounts[mount['ref']]=mount['kind'];parents.append(pin(proofpath))
            owner='davideferante' if policy=='hipsci_targeted_19' else 'davideferrante11'
            job='dt-joint-'+policy.lower().replace('_','-')+'-'+revision
            params=dict(job_id=job,policy=policy,units=units,split=split,chunk_targets=128,
                recipe=p['recipe'],embedded={n:dict(bytes=len(b),sha256=hashlib.sha256(b).hexdigest()) for n,b in members.items()},
                claims_complete_corpus=False,pooling='explicit biological identity before shrinkage',
                source_effects_of_T1_unchanged=True)
            members['params.json']=(json.dumps(params,separators=(',',':'))+'\n').encode()
            payload={n:dict(data=base64.b64encode(zlib.compress(b)).decode(),sha256=hashlib.sha256(b).hexdigest()) for n,b in members.items()}
            code='import os,sys,base64,zlib,hashlib,runpy\nfrom pathlib import Path\nos.chdir("/kaggle/working");sys.path.insert(0,"/kaggle/working")\nP='+repr(payload)+'\n'
            code+='for n,p in P.items():\n b=zlib.decompress(base64.b64decode(p["data"]));assert hashlib.sha256(b).hexdigest()==p["sha256"];Path(n).write_bytes(b)\n'
            code+='runpy.run_path("joint_runtime.py",run_name="__main__")\n';ast.parse(code)
            if len(code)>900000:raise ValueError('payload exceeds safe source limit')
            dest=HERE/'joint'/revision/policy/'package';dest.mkdir(parents=True,exist_ok=False)
            (dest/'run.py').write_text(code,encoding='utf-8',newline='\n');(dest/'params.json').write_bytes(members['params.json'])
            meta=dict(id=owner+'/'+job,title=job,code_file='run.py',language='python',kernel_type='script',
                is_private=True,enable_gpu=False,enable_tpu=False,enable_internet=False,
                dataset_sources=sorted(n for n,k in mounts.items() if k=='dataset'),
                kernel_sources=sorted(n for n,k in mounts.items() if k=='kernel'),competition_sources=[])
            write_new(dest/'kernel-metadata.json',meta)
            proof=dict(utc=now(),policy=policy,regime=split['regime'],owner=owner,slug=meta['id'],
                stage=dest.relative_to(ROOT).as_posix(),code=pin(dest/'run.py'),params=pin(dest/'params.json'),
                metadata=pin(dest/'kernel-metadata.json'),parents=parents,compute_started=False,
                cross_account_input_access_verified=not policy.startswith('cd4'))
            write_new(dest.parent/'prepared.json',proof);inventory.append(proof)
    write_new(HERE/'joint'/inventory_name,dict(utc=now(),packages=inventory,
        compute_authorized=False,preflight_required=True,
        missing_before_launch=['measure current slots','check cross-account CD4 bank access','explicit consent for extra cloud jobs'],
        not_a_T2_candidate=True))
    print(json.dumps(dict(packages=len(inventory),regimes=['production','T'],started_jobs=0)))


if __name__=='__main__':
    parser=argparse.ArgumentParser(__doc__);parser.add_argument('--version',default='j1');parser.add_argument('--inventory',default='inventory_r1.json')
    args=parser.parse_args();main(args.version,args.inventory)
