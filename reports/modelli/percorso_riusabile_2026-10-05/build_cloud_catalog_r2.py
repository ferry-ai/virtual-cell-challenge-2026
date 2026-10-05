"""Extend the immutable cloud index with closed partitions and prior raw archives."""
import json
from datetime import datetime,timezone
from pathlib import Path
from pipeline_state import HERE,REPO,sha

def main():
 out=HERE/'cloud_catalog_r2';out.mkdir(exist_ok=False)
 previous=HERE/'cloud_catalog_r1/manifest.json';parts_path=HERE/'snapshot_parts_r4/state.json'
 archive_path=HERE/'archive_followup_r2/state.json';assignment_path=HERE/'parallel_archives_r1/assignments.json'
 catalog=json.loads(previous.read_text());parts=json.loads(parts_path.read_text());archive=json.loads(archive_path.read_text())
 assignments=json.loads(assignment_path.read_text())['assignments']
 for unit,entry in parts['units'].items():
  records=[v for v in parts['parts'].values() if any(
   r['slug']==v['kernel'] and r['parameters']['unit']==unit for r in map(json.loads,(HERE/'other_sample_launches.jsonl').read_text().splitlines()))]
  for r in records:
   if r['state']=='remote_complete_manifest_checked' and sha(REPO/r['receipt'])!=r['receipt_sha256']:raise ValueError('partition receipt changed')
  catalog['units'][unit]['samples']={**entry,'parts':records,
   'mount_selection':'explicit saved kernel version for each part; global source indices retained; union receipt required'}
 raw_index={}
 for r in archive['archives']:
  if sha(REPO/r['files_receipt'])!=r['files_sha256']:raise ValueError('archive manifest changed')
  assignment=next((v for v in assignments if v['slug']==r['dataset'].split('/')[1]),None)
  launch=next((v for v in archive['launches'] if v['source']==r['dataset'].split('/')[1]),None)
  raw_index[r['dataset']]={**r,'version_ref':r['dataset']+'/'+str(r['version']),
   'url':'https://www.kaggle.com/datasets/'+r['dataset']+'/versions/'+str(r['version']),
   'derivatives':{'state':'cloud_job_running' if launch else 'owner_start_required' if assignment else 'not_integrated',
    'kernel':launch['slug'] if launch else None,'assignment':assignment},
   'fit_eligibility':'not yet reconciled; raw storage does not certify QC, controls or split admission',
   'fallback_allowed':False}
 catalog.update(created_utc=datetime.now(timezone.utc).isoformat(),scope='Current verified branch plus 17 explicitly versioned existing raw archives; full catalogue and training remain open',
  raw_archives=raw_index,previous_manifest={'path':str(previous.relative_to(REPO)).replace('\\','/'),'sha256':sha(previous)},
  consumer_policy='Pin this manifest SHA. Verify raw/derivative receipt then consumed file hashes. Reject unresolved parts and fit eligibility; retain same identity after resume.',
  storage_policy='Saved Kaggle versions and verified Drive archives are persistent. Local matrices optional. Repo contains index and receipts, not the raw matrices.')
 catalog['sources'] += [{'path':str(p.relative_to(REPO)).replace('\\','/'),'sha256':sha(p)} for p in [parts_path,archive_path,assignment_path]]
 manifest=out/'manifest.json';manifest.write_text(json.dumps(catalog,indent=1)+'\n',encoding='utf-8',newline='\n')
 lines=['# ARCHIVIO DATI — indice corrente, non reingerire','',
  '**Archivio → banca pronta e campioni → training esteso** è il percorso principale.',
  'Manifest immutabile: `manifest.json`; SHA256 `'+sha(manifest)+'`.',
  'Contiene account, versioni, percorsi interni, ricevute e hash. Non usare il vecchio cubo del pilot come fallback.',
  '', '[Tutti i dataset, dimensioni e diversità](../DATI_DISPONIBILI_r1.md) · [Avvio dei quattro Colab e job Kaggle](../PARALLELISMO_r1.md)',
  '', '| Unità della nuova ingestione | Banca salvata | Campioni |','|---|---|---|']
 for unit,e in catalog['units'].items():
  b=e['bank'];s=e['samples'];status='completi, unione verificata' if s['state']=='remote_complete_union_checked' else 'completi' if s['state']=='remote_complete_manifest_checked' else 'parti '+str(s.get('verified_parts',0))+'/'+str(s.get('expected_parts','?'))+' verificate'
  lines.append('| '+unit+' | ['+b['kernel']+']('+b['url']+') | '+status+' |')
 lines+=['','## Archivi precedenti persistenti','',
  '17 dataset grezzi nominati nel manifest, 69,58 GB: conservarli e riusarli. Età del dato non è motivo di esclusione; identità e ruolo vanno verificati.',
  'I nuovi job preparano solo pseudobulk e campioni da questi shard. Includono tutte le loro chiavi biologiche; QC e ammissibilità al trainer restano da riconciliare.',
  '', '## Aggiunte incrementali','',
  'Aggiungere sorgente/versione e manifest con hash; eseguire soltanto i derivati mancanti. Se input, asse, QC, codice e parametri coincidono, montare i derivati esistenti.',
  'Una nuova versione del manifest mantiene la precedente. Cambi di QC/asse/normalizzazione rigenerano soltanto i dipendenti.',
  '', '**Il training esteso non è ancora avviato.** Integrare lettori e guardie nel trainer, con split e ricevute di uso/loss anche dopo resume. Il catalogo contiene ancora lacune aperte.']
 (out/'README.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
 print(json.dumps({'sha256':sha(manifest),'raw_archives':len(raw_index),'training_ready':False}))

if __name__=='__main__':main()
