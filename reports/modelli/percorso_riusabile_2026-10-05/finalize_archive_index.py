"""Publish a corrected immutable index: a dataset holds a subset of its parent job."""
import json,subprocess,sys
from datetime import datetime,timezone
from pipeline_state import HERE,REPO,sha

def main():
 old=HERE/'archive_followup_r2/state.json';state=json.loads(old.read_text())
 for entry in state['archives']:
  files=json.loads((REPO/entry['files_receipt']).read_text());published={f['unit'] for f in files}
  entry['parent_job_units']=entry['units'];entry['units']={u:entry['units'][u] for u in sorted(published)}
  if any(sum(f['cells'] for f in files if f['unit']==u)!=entry['units'][u]['cells'] for u in published):raise ValueError('published source parity differs')
 state['correction']='complete.json can name sibling units absent from this dataset; units now bound to files.json'
 state['previous_state_sha256']=sha(old)
 corrected=HERE/'archive_followup_r3';corrected.mkdir(exist_ok=False)
 (corrected/'state.json').write_text(json.dumps(state,indent=1))
 r=subprocess.run([sys.executable,str(HERE/'archive_summary.py')],capture_output=True,text=True)
 if r.returncode:raise RuntimeError(r.stderr)
 parent=HERE/'cloud_catalog_r3/manifest.json';catalog=json.loads(parent.read_text());all_jobs=[]
 for path in [HERE/'archive_launches_r2.jsonl',HERE/'remaining_archives_r1/launches.jsonl']:
  all_jobs += [r for r in map(json.loads,path.read_text().splitlines()) if r['accepted']]
 if len({r['slug'] for r in all_jobs})!=len(all_jobs):raise ValueError('duplicate work assignment')
 for entry in state['archives']:
  ref=entry['dataset'];target=catalog['raw_archives'][ref]
  target['parent_job_units']=entry['parent_job_units'];target['units']=entry['units']
  launch=next((r for r in all_jobs if r.get('source',r.get('spec',{}).get('slug'))==ref.split('/')[1]),None)
  if launch and target['derivatives']['state']!='bank_and_samples_verified':target['derivatives']={
   'state':'accepted_cloud_output_not_yet_verified','kernel':launch['slug'],'code_sha256':launch['code_sha256']}
 catalog['execution']['jobs']=all_jobs;catalog['previous_manifest']={'path':str(parent.relative_to(REPO)).replace('\\','/'),'sha256':sha(parent)}
 catalog['created_utc']=datetime.now(timezone.utc).isoformat()
 catalog['sources'] += [{'path':str((corrected/'state.json').relative_to(REPO)).replace('\\','/'),'sha256':sha(corrected/'state.json')}]
 out=HERE/'cloud_catalog_r4';out.mkdir(exist_ok=False);manifest=out/'manifest.json'
 manifest.write_text(json.dumps(catalog,indent=1)+'\n',encoding='utf-8',newline='\n')
 readme=(HERE/'cloud_catalog_r3/README.md').read_text().replace(sha(parent),sha(manifest)).replace('DATI_DISPONIBILI_r1.md','DATI_DISPONIBILI_r2.md')
 readme=readme.replace('Dodici nuovi job accettati','Sedici nuovi job accettati').replace('in `archive_launches_r2.jsonl`','in `archive_launches_r2.jsonl` e `remaining_archives_r1/launches.jsonl`')
 readme+='\nLe unità effettivamente pubblicate di ciascun dataset sono legate a `files.json`;\n`complete.json` può descrivere anche unità sorelle dello stesso job che non sono\nin quel dataset. La r2 del resoconto corregge questa sovrapposizione della tabella r1;\nGB e righe totali erano già calcolati dai soli file effettivi e non cambiano.\n'
 (out/'README.md').write_text(readme,encoding='utf-8')
 print(json.dumps({'manifest_sha256':sha(manifest),'accepted_jobs':len(all_jobs),'raw_total_bytes':395749738486}))

if __name__=='__main__':main()
