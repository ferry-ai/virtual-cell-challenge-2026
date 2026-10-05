"""Freeze corrected source-cache successors for the authorized t28 generation."""
import json,sys,shutil,hashlib
from pathlib import Path
R=Path(__file__).resolve().parents[3];S=R/'reports/modelli/percorso_riusabile_2026-10-05'
sys.path.insert(0,str(Path(__file__).parent));from repair_lazy_dependencies import build,sha
def main():
 out=S/sys.argv[1];out.mkdir(exist_ok=False);pkg=out/'package'
 shutil.copytree(S/'generation_parent_r1/package_deps',pkg)
 params=json.loads((pkg/'params.json').read_text());meta=json.loads((pkg/'kernel-metadata.json').read_text())
 overrides={};records=json.loads((S/'adapter_successors_r1/ready.json').read_text())
 extra=S/'additional_sources_r1/ready.json'
 if extra.exists():records+=json.loads(extra.read_text())
 for r in records:
  source=Path(r['package']);receipt=source/'completion_r1/cache_receipt.json'
  if not receipt.exists():raise ValueError('no usable source receipt '+r['unit'])
  entries=json.loads(receipt.read_text());assert len(entries)==1
  entry=entries[0];assert entry['axis_sha256']==params['axis']['sha256'] and entry['target_panel']==params['panel']['panel_sha256']
  assert entry['shape'][1]==params['axis']['genes'] and entry['code_sha256']==json.loads((source/'params.json').read_text())['code_sha256']
  overrides[entry['source']]={**entry,'kernel':r['slug'],'version':1,'receipt_sha256':sha(receipt)}
  meta['kernel_sources'].append(r['slug'])
 params['source_overrides']=overrides;params['kind']='t28_generation_with_original_k562_and_corrected_source_adapters'
 (pkg/'params.json').write_text(json.dumps(params,indent=2))
 driver=pkg/'driver.py';code=driver.read_text()
 code=code.replace("        path = cache / (name + '.npz')", """        path = cache / (name + '.npz')
        override = json.loads((WORKING / 'params.json').read_text()).get('source_overrides', {}).get(name)
        if override:
            receipts = [p for p in INPUTS.rglob('cache_receipt.json') if _sha256(p) == override['receipt_sha256']]
            hits = [p for p in INPUTS.rglob(name + '.npz') if p.stat().st_size == override['bytes'] and _sha256(p) == override['sha256']]
            if len(receipts) != 1 or len(hits) != 1:
                _fail('blocked_corrected_source_identity', source=name, receipts=len(receipts), candidates=len(hits))
            path = hits[0]
""")
 code=code.replace("            context['weights']['k562'] = 1.0", "            context['weights']['k562'] = 1.0\n            for name in params['source_overrides']:\n                context['weights'][name] = 1.0")
 code=code.replace("        origin[name] = {'role': 'voted', 'sha256': _sha256(path), 'bytes': path.stat().st_size}","        origin[name] = {'role': 'voted', 'sha256': _sha256(path), 'bytes': path.stat().st_size, 'successor': override}")
 compile(code,'driver.py','exec');driver.write_text(code)
 meta['kernel_sources']=sorted(set(meta['kernel_sources']));meta.update(id='davideferrante11/vcc-generate-t28-frozen-bank-r1',title='vcc-generate-t28-frozen-bank-r1')
 (pkg/'kernel-metadata.json').write_text(json.dumps(meta,indent=2));build(pkg,True,True)
 ready={'package':str(pkg),'metadata':meta,'slug':meta['id'],'code_sha256':sha(pkg/'run.py'),'params_sha256':sha(pkg/'params.json'),
        'source_overrides':overrides,'bank_complete':False,'only_bank_changes':True,'effects_only':False,'generation_started':False}
 (out/'ready.json').write_text(json.dumps(ready,indent=2));print(json.dumps({'ready':str(out/'ready.json'),'overrides':list(overrides)}))
if __name__=='__main__':main()
