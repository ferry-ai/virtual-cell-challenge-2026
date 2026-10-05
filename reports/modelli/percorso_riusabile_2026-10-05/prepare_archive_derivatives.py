"""Freeze incremental bank/sample jobs from existing, explicitly pinned raw archives."""
import ast,base64,hashlib,json,zlib
from pathlib import Path
from pipeline_state import HERE,REPO,sha

GROUPS={'frangieh2021':'melanoma','sunshine2023':'Calu3','papalexi2021_arrayed':'THP1',
 'shifrut2018':'CD4T','datlinger2017':'Jurkat','datlinger2021':'Jurkat','xu2023':'HEK293',
 'dixit2016_d7':'K562','dixit2016_d13':'K562','dixit2016_high_moi':'K562',
 'hepg2_nadig':'HepG2','jurkat_nadig':'Jurkat','h1_train':'H1','h1_val':'H1',
 'replogle_rpe1':'RPE1','replogle_k562_essential':'K562','replogle_k562_gwps':'K562',
 'a549':'A549','tian2019':'neuron','tian2021':'neuron','norman2019':'K562',
 'hipsci_targeted19':'iPSC','hipsci_targeted_19':'iPSC','a549_ko':'A549',
 'k562_essential':'K562','k562_gwps_a':'K562','k562_gwps_b':'K562','rpe1':'RPE1',
 'tian2019_ipsc':'iPSC','tian2019_neuron':'neuron','tian2021_crispra':'neuron','tian2021_crispri':'neuron',
 'hipsci_gw_fitness':'iPSC','hipsci_gw_nonfitness':'iPSC','kolf_chromatin':'iPSC',
 'kolf_metabolic':'iPSC','kolf_strong':'iPSC'}

def replace(source,old,new):
 if source.count(old)!=1:raise ValueError('frozen structure differs: '+old[:60])
 return source.replace(old,new)

def modules():
 frozen=ast.literal_eval(next(n.value for n in ast.parse((HERE/'kolf_bank_stage_r1/run.py').read_text()).body
  if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='P' for t in n.targets)))
 bank=base64.b64decode(frozen['bank.py']['data']).decode()
 start=bank.index("    for part in spec['parts']:");end=bank.index('    out.mkdir',start)
 bank=bank[:start]+'''    for s in spec['files']:
        f = root/s['file']
        if s['file'] in seen: raise ValueError('duplicate source')
        seen.add(s['file'])
        if f.stat().st_size != s['bytes'] or sha(f) != s['sha256']: raise ValueError('raw archive changed')
        files.append((f,s['cells']))
'''+bank[end:]
 bank=replace(bank,"    if not spec.get('line_group') or not spec.get('expected_contexts'): raise ValueError('explicit biological identity required')",
  "    if not spec.get('line_group'): raise ValueError('explicit biological identity required')")
 bank=replace(bank,"        if not set(obs.context).issubset(spec['expected_contexts']): raise ValueError('unexpected biological context')",'')
 bank=replace(bank,'            obs = metadata(h); _, mask = mapping(h)',
  '''            obs = metadata(h); oi = col(h['var'],'official_index').astype(int)
            symbols = col(h['var'],'symbol').astype(str)
            axis = np.asarray(spec['axis'],object)
            valid = (oi >= 0) & (oi < G) & (col(h['var'],'mapping') == 'unique')
            if np.any(symbols[valid] != axis[oi[valid]]): raise ValueError('native mapping differs from pinned official axis')
            _, mask = mapping(h)''')
 old='''            # This adapter requires homogeneous shards; never pool or discard mixed contexts.
            bio = set(k[:-1] for k in rkeys)
            if len(bio) != 1: raise ValueError('split multi-context shard before aggregation')
            mask = masks[next(iter(bio))]'''
 bank=replace(bank,old,"            mask = np.ones(G,bool)")
 bank=replace(bank,'                depth = np.asarray(x.sum(1)).ravel(); good = depth > 0',
  '''                cell_masks = np.stack([masks[k[:-1]] for k in rkeys[lo:hi]])
                x = x.multiply(cell_masks).tocsr()
                depth = np.asarray(x.sum(1)).ravel(); good = depth > 0''')
 sample=(HERE/'materialize_samples.py').read_text()
 sample=replace(sample,"    hits = list(root.glob('**/bank/'+p['unit']+'/complete.json'))",
  "    hits = [Path(p['bank_input_path'])/'complete.json']")
 start=sample.index('    source_files = {}');end=sample.index('    if set(source_files)',start)
 sample=sample[:start]+"    source_files = {s['file']:(root/s['file'],s) for s in p['spec']['files']}\n"+sample[end:]
 sample=replace(sample,"            mask = masks[selected_bank_rows[0]]\n            if not np.all(masks[selected_bank_rows] == mask):\n                raise ValueError('source shard mixes measurement masks')",'            mask = np.ones(masks.shape[1],bool)')
 sample=replace(sample,"            x = sp.vstack(matrices, format='csr')","            x = sp.vstack(matrices, format='csr').multiply(masks[selected_bank_rows]).tocsr()")
 return {'bank.py':bank.encode(),'preparation.py':base64.b64decode(frozen['preparation.py']['data']),
  'materialize_samples.py':sample.encode(),'archive_runtime.py':(HERE/'archive_runtime.py').read_bytes()}

def build(slug,owner=None,slot=None):
 origin=HERE/'archive_metadata_r1'/slug
 if not (origin/'files.json').exists():origin=HERE/'archive_followup_r1'/slug
 source=json.loads((origin/'files.json').read_text());done=json.loads((origin/'complete.json').read_text())
 units={r['unit'] for r in source}
 if not units.issubset(done['units']) or not all(done['units'][u]['parity_ok'] for u in units):raise ValueError('raw archive not complete')
 if units-set(GROUPS):raise ValueError('explicit group mapping missing: '+str(units-set(GROUPS)))
 axis_path=Path('C:/Users/ferra/vcc2026-data/processed/ingestione_completa_2026-10-03/kaggle_code_cd4_r1/gene_names.csv')
 axis=[x.strip().split(',')[0] for x in axis_path.read_text().splitlines() if x.strip()]
 if axis[0].lower() in ('gene','gene_name','genes','x'):axis=axis[1:]
 if len(axis)!=18533 or sha(axis_path)!=json.loads((HERE/'axis_binding_r1.json').read_text())['axis_sha256']:raise ValueError('axis differs')
 specs=[]
 for unit in sorted(units):
  files=[r for r in source if r['unit']==unit]
  if sum(r['cells'] for r in files)!=done['units'][unit]['cells']:raise ValueError('raw coverage mismatch')
  specs.append({'name':unit,'line_group':GROUPS[unit],'cells':sum(r['cells'] for r in files),
   'receipt_sha256':sha(origin/'files.json'),'files':files,'axis':axis,'axis_sha256':sha(axis_path)})
 params={'dataset':'davidmaisterx/'+slug,'slug':slug,'job_id':done['job_id'],'slot':slot,
  'source_files_sha256':sha(origin/'files.json'),'units':specs,
  'raw_complete_sha256':sha(origin/'complete.json'),'training_used':False}
 files=modules();files['params.json']=json.dumps(params).encode();files['raw_files.json']=(origin/'files.json').read_bytes()
 files['raw_complete.json']=(origin/'complete.json').read_bytes()
 for name,raw in files.items():
  if name.endswith('.py'):compile(raw,name,'exec')
 payload={n:{'data':base64.b64encode(zlib.compress(b)).decode(),'sha256':hashlib.sha256(b).hexdigest(),'compression':'zlib'} for n,b in files.items()}
 if any(zlib.decompress(base64.b64decode(payload[n]['data']))!=b for n,b in files.items()):raise ValueError('compressed payload differs')
 code='import base64,hashlib,runpy,sys,os,zlib\nfrom pathlib import Path\n'
 code+='os.chdir("/kaggle/working");sys.path.insert(0,"/kaggle/working")\nP='+repr(payload)+'\n'
 code+='for n,v in P.items():\n b=zlib.decompress(base64.b64decode(v["data"]));assert hashlib.sha256(b).hexdigest()==v["sha256"];Path(n).write_bytes(b)\n'
 code+='runpy.run_path("archive_runtime.py",run_name="__main__")\n'
 if len(code.encode())>=1<<20:raise ValueError('code package exceeds conservative API size guard')
 return files,params,code,payload

if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--slug',required=True);p.add_argument('--owner');p.add_argument('--slot',type=int);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 files,params,code,payload=build(a.slug,a.owner,a.slot);a.out.mkdir(parents=True,exist_ok=False)
 for n,b in files.items():(a.out/n).write_bytes(b)
 if a.owner:
  (a.out/'run.py').write_text(code,encoding='utf-8',newline='\n')
  kernel_slug='vcc-derivatives-'+a.slug.removeprefix('rlab-')+'-r1'
  meta={'id':a.owner+'/'+kernel_slug,'title':kernel_slug,
   'code_file':'run.py','language':'python','kernel_type':'script','is_private':True,
   'enable_gpu':False,'enable_tpu':False,'enable_internet':False,
   'dataset_sources':[params['dataset']],'kernel_sources':[],'competition_sources':[]}
  (a.out/'kernel-metadata.json').write_text(json.dumps(meta,indent=1))
  (a.out/'prepared.json').write_text(json.dumps({'code_sha256':hashlib.sha256(code.encode()).hexdigest(),
   'metadata_sha256':sha(a.out/'kernel-metadata.json'),'spec':{k:v for k,v in params.items() if k!='units'},
   'source_units':[{k:v for k,v in u.items() if k!='axis'} for u in params['units']]},indent=1))
 print(json.dumps({'prepared':a.slug,'units':len(params['units']),'cells':sum(u['cells'] for u in params['units'])}))
