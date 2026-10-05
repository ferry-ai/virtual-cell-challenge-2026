import json
from datetime import datetime,timezone
from pipeline_state import HERE,REPO,sha
p=HERE/'cloud_catalog_r10/manifest.json'
s=HERE/'archive_completion_k562_gwps_r1/state.json'
c=json.loads(p.read_text());v=json.loads(s.read_text())
ref='davidmaisterx/rlab-k562-gwps-r3'
raw=c['raw_archives'][ref]
for unit,value in v['units'].items():
    assert unit in raw['units']
    c['units'][unit]={**value,'raw':raw,'raw_dataset_refs':[ref]}
c['raw_archives'][ref]['derivatives']={'state':'bank_and_samples_verified','units':list(v['units'])}
c.update(created_utc=datetime.now(timezone.utc).isoformat(),training_ready=False,
         previous_manifest={'path':p.relative_to(REPO).as_posix(),'sha256':sha(p)})
c['execution']['current_supervision']['open_jobs_snapshot']=None
c['execution']['current_supervision']['storage_producers_complete']=True
c['sources'].append({'path':s.relative_to(REPO).as_posix(),'sha256':sha(s)})
out=HERE/'cloud_catalog_r11';out.mkdir(exist_ok=False)
m=out/'manifest.json';m.write_text(json.dumps(c,indent=1)+'\n',encoding='utf-8',newline='\n')
(out/'README.md').write_text('# Archivio dati r11\n\nManifest immutabile, SHA256 `'+sha(m)+'`.\nEntrambi i blocchi K562 GWPS banca/campioni verificati; altri input r10 conservati.\n'+str(len(c['units']))+' unità storage, non contesti né fonti consumate nel fit.\n395,75GB grezzi già comprendono K562/HIPSCI. Indice storage, non release ammessa.\nStato operativo solo R-LEAD; fonte archive_completion_k562_gwps_r1/state.json.\n',encoding='utf-8')
print(json.dumps({'units':len(c['units']),'sha256':sha(m)}))
