"""Prepare production-only successors; original estimator, usable-gene mask and panel."""
import ast,base64,hashlib,json
from pathlib import Path
R=Path(__file__).resolve().parents[3];S=R/'reports/modelli/percorso_riusabile_2026-10-05'
OUT=S/'adapter_successors_r1'
def sha(b):return hashlib.sha256(b).hexdigest()
def write(p,obj):p.write_text(json.dumps(obj,indent=2)+'\n',encoding='utf-8')
EXPORT='''
import numpy as np
params=json.loads(Path('params.json').read_text())
receipts=[]
for unit in params['units']:
 root=Path('/kaggle/working/effects')/unit['unit']
 status=json.loads((root/'status.json').read_text());assert status['status']=='derived',status
 effects=json.loads((root/'effects.json').read_text())
 stats=[x for x in effects['statistics'] if x.get('file')]
 assert len(stats)==1 and len(stats[0]['tables'])==1,'BIO must not be collapsed after shrink'
 stat=stats[0];table=stat['tables'][0]
 arrays=np.load(root/stat['file'],allow_pickle=False)
 out=Path('/kaggle/working/cache');out.mkdir(exist_ok=True)
 target=out/(unit['transfer_source_id']+'.npz')
 data={key:arrays['0_'+key] for key in ('raw','shrunk','se','n_cells')}
 assert np.array_equal(np.isfinite(data['raw']),np.isfinite(data['shrunk']))
 assert np.isfinite(data['se'][np.isfinite(data['raw'])]).all(),'measured pair without finite SE'
 np.savez_compressed(target,targets=np.asarray(table['targets']),meta=json.dumps(table['meta']),**data)
 receipts.append({'unit':unit['unit'],'source':unit['transfer_source_id'],'path':'cache/'+target.name,
 'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'bytes':target.stat().st_size,
 'axis_sha256':params['axis']['sha256'],'target_panel':params['panel_sha256'],
 'count_sum_sha256':unit['count_sum_sha256'],'code_sha256':params['code_sha256'],
 'targets':len(table['targets']),'shape':list(data['raw'].shape),'scope':'production only, not C/J validation'})
Path('/kaggle/working/cache_receipt.json').write_text(json.dumps(receipts,indent=2))
print(json.dumps(receipts),flush=True)
'''
def main():
 OUT.mkdir(exist_ok=False)
 panel_file=Path('C:/Users/ferra/vcc2026-data/raw/controls/pert_counts.csv')
 import sys;sys.path.insert(0,str(R/'src'));from vcc2026.panel import read_panel,panel_sha256
 panel=read_panel(panel_file);assert len(panel)==300
 assert panel_sha256(panel)=='c9c4c9a69f76afd4507e9a7619fe9925c19ff34e5878c7854493683b23bea5ca'
 refs=['orion-hct116','orion-hek293t','kolf-chromatin','kolf-metabolic-r4-retry1','kolf-strong-r4-retry1','kolf-pan-genome-r4-access1']
 ready=[]
 for ref in refs:
  old='vcc-effects-'+ref+( '' if '-r4-' in ref else '-r4')
  src=S/'sourcefits_launch_r1'/old
  text=(src/'run.py').read_text(encoding='utf-8');tree=ast.parse(text)
  node=next(n for n in tree.body if isinstance(n,ast.Assign) and any(isinstance(a,ast.Name) and a.id=='P' for a in n.targets))
  payload=ast.literal_eval(node.value)
  files={k:base64.b64decode(v['base64']) for k,v in payload.items()}
  assert all(sha(files[k])==v['sha256'] for k,v in payload.items())
  params=json.loads(files['params.json']);core=files['estimator_core.py'].decode();cloud=files['cloud_job.py'].decode()
  old_scatter='out[key][:, columns] = np.array(result[key], dtype=np.float32, copy=True)'
  assert core.count(old_scatter)==1
  core=core.replace(old_scatter,"usable = np.asarray(result['control_mean']) >= CALL['min_control_frac']\n            out[key][:, columns[usable]] = np.asarray(result[key], dtype=np.float32)[:, usable]")
  wanted="wanted = sorted(set(part['target'].map(_label)) - {'non-targeting'})"
  assert core.count(wanted)==1
  core=core.replace(wanted,wanted+"\n        from pathlib import Path\n        panel = set(json.loads(Path('params.json').read_text())['target_panel'])\n        wanted = [target for target in wanted if target in panel]")
  core=core.replace('Low-control zeros stay zeros.','Low-control genes are NaN as in AxisTable.from_source.')
  assert cloud.count('return frozen_splits()')==1
  cloud=cloud.replace('return frozen_splits()',"return [split for split in frozen_splits() if split.name == 'C:A549']")
  cloud=cloud.replace('projected = len(key) * len(genes) * 4',"projected = len(job['target_panel']) * len(genes) * 4")
  files['estimator_core.py']=core.encode();files['cloud_job.py']=cloud.encode()
  params['code_sha256']={k:sha(files[k]) for k in params['code_sha256']}
  params.update(target_panel=panel,panel_sha256=panel_sha256(panel),production_only=True,output_budget_bytes=256*1024**2)
  files['params.json']=(json.dumps(params,indent=2)+'\n').encode()
  meta=json.loads((src/'kernel-metadata.json').read_text());name='vcc-prod-'+params['units'][0]['unit'].replace('_','-')+'-mask-r1'
  meta.update(id=meta['id'].split('/')[0]+'/'+name,title=name)
  pkg=OUT/name;pkg.mkdir()
  for k,b in files.items():
   if k.endswith('.py'):compile(b,k,'exec')
   (pkg/k).write_bytes(b)
  new_payload={k:{'base64':base64.b64encode(b).decode(),'sha256':sha(b)} for k,b in files.items()}
  lines=text.splitlines(keepends=True)
  rebuilt=''.join(lines[:node.lineno-1])+'P = '+repr(new_payload)+'\n'+''.join(lines[node.end_lineno:])
  rebuilt += '\n'+EXPORT
  compile(rebuilt,'run.py','exec');(pkg/'run.py').write_text(rebuilt,encoding='utf-8');write(pkg/'kernel-metadata.json',meta)
  item={'unit':params['units'][0]['unit'],'owner':meta['id'].split('/')[0],'slug':meta['id'],'package':str(pkg),'metadata':meta,
   'code_sha256':sha((pkg/'run.py').read_bytes()),'params_sha256':sha(files['params.json']),
   'supersedes_adapter':old,'scientific_change':'restore original usable-control gene mask only','production_only':True}
  write(pkg/'ready.json',item);ready.append(item)
 write(OUT/'ready.json',ready);print(json.dumps({'packages':len(ready),'ready':str(OUT/'ready.json')}))
if __name__=='__main__':main()
