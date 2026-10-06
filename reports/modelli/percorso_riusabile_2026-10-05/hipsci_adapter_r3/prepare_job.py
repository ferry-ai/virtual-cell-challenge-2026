import ast
import base64
import hashlib
import json
from pathlib import Path
import zlib

HERE=Path(__file__).resolve().parent
S=HERE.parent
REPO=S.parents[2]
DATA=Path('C:/Users/ferra/vcc2026-data')
def pin(path):
    return dict(bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())

stage=HERE/'package'
stage.mkdir(exist_ok=False)
bank=json.loads((S/'archive_completion_hipsci_targeted19_r1/state.json').read_text())['units']['hipsci_targeted_19']['bank']
receipt_path=REPO/bank['receipt']
assert pin(receipt_path)['sha256']==bank['receipt_sha256']
receipt=json.loads(receipt_path.read_text())
old=json.loads((S/'agenti/grok_transfer_esteso_r7/packages/vcc-effects-h1-joint-r7/params.json').read_text())
axis=DATA/'raw/controls/gene_names.csv'
panel_file=DATA/'raw/controls/pert_counts.csv'
assert pin(axis)['sha256']==old['axis']['sha256']
assert pin(panel_file)['sha256']==old['panel']['file_sha256']
spec=json.loads((S/'fallback_hipsci_r1/params.json').read_text())['units'][0]
params=dict(kind='production_source_fragment',producer=bank['saved_version'],
    bank_files={name:receipt['files'][name] for name in ('count_sum.npz','rows.csv','mask.npz')},
    genes=spec['axis'],panel=old['panel'],
    embedded_inputs={'gene_names.csv':pin(axis),'pert_counts.csv':pin(panel_file)},
    recipe=dict(phi=.2,pseudo=.5,pseudo_scale='constant',min_expected=1.,min_cells=10.,min_control_frac=1e-6),
    claims_complete_catalogue=False,production_hidden_targets=[],
    incident_ids=['E-20260929-005'],guards=['all input hashes before estimates','bounded runtime RAM/disk','no source-marker-only admission'],
    policy=dict(chemistry='unreported; study isolated',unassigned='auxiliary stored, no invented target',
                no_metadata='unresolved; preserved',source_vote='one; joint donors before shrink'))
params['bank_files']['complete.json']=pin(receipt_path)
(stage/'params.json').write_text(json.dumps(params,indent=1)+'\n',encoding='utf-8')
sources={name:(HERE/name).read_bytes() for name in ('adapter.py','policy.py','estimator.py','runtime.py')}
sources.update({'gene_names.csv':axis.read_bytes(),'pert_counts.csv':panel_file.read_bytes(),
                'params.json':(stage/'params.json').read_bytes()})
payload={n:dict(data=base64.b64encode(zlib.compress(b)).decode(),sha256=hashlib.sha256(b).hexdigest())
         for n,b in sources.items()}
code='import os,sys,base64,zlib,hashlib,runpy\nfrom pathlib import Path\n'
code+='os.chdir("/kaggle/working");sys.path.insert(0,"/kaggle/working")\nP='+repr(payload)+'\n'
code+='for n,p in P.items():\n b=zlib.decompress(base64.b64decode(p["data"]));assert hashlib.sha256(b).hexdigest()==p["sha256"];Path(n).write_bytes(b)\n'
code+='runpy.run_path("runtime.py",run_name="__main__")\n'
ast.parse(code)
if len(code.encode())>900000:
    raise ValueError('code size budget exceeded')
(stage/'run.py').write_text(code,encoding='utf-8')
slug='davideferante/vcc-effects-hipsci-targeted19-countsum-r1'
meta=dict(id=slug,title=slug.split('/')[1],code_file='run.py',language='python',kernel_type='script',
          is_private=True,enable_gpu=False,enable_tpu=False,enable_internet=False,
          dataset_sources=[],kernel_sources=[bank['kernel']],competition_sources=[])
(stage/'kernel-metadata.json').write_text(json.dumps(meta,indent=1)+'\n',encoding='utf-8')
proof=dict(slug=slug,stage=str(stage),code=pin(stage/'run.py'),params=pin(stage/'params.json'),
           embedded_files={n:dict(sha256=v['sha256'],bytes=len(sources[n])) for n,v in payload.items()},
           bank=bank['kernel'],producer_version=bank['saved_version']['version'],
           full_training=False,compute_started=False,scope='native five panel targets, all 19 clones and NTC; other labels remain catalogued',
           derivation='count_sum, original constant pseudo .5, joint donors before shrink')
(HERE/'prepared.json').write_text(json.dumps(proof,indent=1)+'\n',encoding='utf-8')
print(json.dumps(dict(slug=slug,code_bytes=len(code.encode()),cloud_compute=False)))
