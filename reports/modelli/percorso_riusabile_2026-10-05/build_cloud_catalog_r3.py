"""Pin public raw inputs, fallback assignments and the first verified archive reuse."""
import json
from datetime import datetime,timezone
from pathlib import Path
from pipeline_state import HERE,REPO,sha

def main():
 out=HERE/'cloud_catalog_r3';out.mkdir(exist_ok=False)
 parent=HERE/'cloud_catalog_r2/manifest.json';catalog=json.loads(parent.read_text())
 publication=HERE/'public_archives_r2/publication.jsonl';launches=HERE/'archive_launches_r2.jsonl'
 records=[json.loads(x) for x in launches.read_text().splitlines()]
 if len({r['slug'] for r in records})!=len(records):raise ValueError('duplicate jobs')
 public={r['ref'] for r in map(json.loads,publication.read_text().splitlines()) if r['public']}
 for ref,entry in catalog['raw_archives'].items():
  match=next((r for r in records if r.get('source',r.get('spec',{}).get('slug'))==ref.split('/')[1]),None)
  entry['public']=ref in public
  if match:entry['derivatives']={'state':'accepted_cloud_output_not_yet_verified','kernel':match['slug'],'code_sha256':match['code_sha256']}
 done_path=HERE/'archive_completion_hepg2_r1/state.json';done=json.loads(done_path.read_text())
 for unit,value in done['units'].items():
  for artifact in ('bank','samples'):
   r=value[artifact]
   if sha(REPO/r['receipt'])!=r['receipt_sha256']:raise ValueError('completion receipt changed')
  value['raw']={'dataset':'davidmaisterx/rlab-hepg2-nadig',**catalog['raw_archives']['davidmaisterx/rlab-hepg2-nadig']}
  catalog['units'][unit]=value
  catalog['raw_archives']['davidmaisterx/rlab-hepg2-nadig']['derivatives']={'state':'bank_and_samples_verified','kernel':done['kernel'],'units':[unit]}
 catalog.update(created_utc=datetime.now(timezone.utc).isoformat(),scope='Current branch plus 17 pinned raw archives; first archive reuse verified; full catalogue/trainer open',
  previous_manifest={'path':str(parent.relative_to(REPO)).replace('\\','/'),'sha256':sha(parent)},
  execution={'jobs':records,'colab_assignments':'not started; superseded by Kaggle fallback',
   'public_raw_inputs':sorted(public),'new_job_outputs':'private; verify or arrange GPU-account access before trainer consumption'})
 catalog['sources'] += [{'path':str(p.relative_to(REPO)).replace('\\','/'),'sha256':sha(p)} for p in [publication,launches,done_path]]
 manifest=out/'manifest.json';manifest.write_text(json.dumps(catalog,indent=1)+'\n',encoding='utf-8',newline='\n')
 text='''# ARCHIVIO DATI — indice corrente

**Percorso principale: archivio → banca pronta e campioni → training esteso.**

Manifest `manifest.json`, SHA256 `DIGEST`. Selezionare account/versione/percorso/hash;
non usare un dataset precedente per somiglianza del nome o come fallback.

- [Dati disponibili, contesti e dimensioni](../DATI_DISPONIBILI_r1.md): **395,75 GB**
  di grezzi perturbazionali conservati; 17 archivi precedenti nominati e versionati.
- 15 banche della nuova ingestione verificate. Campioni CD4, KOLF e HCT116 chiusi;
  HEK293T 3/6 nell'ultimo snapshot verificato, gli altri job già lanciati.
- **Prima catena riusata verificata su dati veri:** HepG2 Nadig dall'archivio
  esistente produce banca e matrici cellulari persistenti, codice/versione/conteggi/
  lineage/ricevute verificati (`archive_completion_hepg2_r1`). Nessuna reingestione.
- Dodici nuovi job accettati sui tre Kaggle in `archive_launches_r2.jsonl`.
  I Colab non sono partiti e sono sostituiti: non avviarli né duplicare i job.
- Cinque sorgenti esplicitamente autorizzate sono pubbliche: SCP KO, SCP Tcells,
  SCP K562/HEK, Tian/Norman e HIPSCI targeted19. Prove in `public_archives_r2`.
  Gli altri archivi e i nuovi output restano privati; prima del trainer verificare
  gli accessi reali del consumatore, senza ricalcolo per aggirare una permission.

Un teammate può montare le cinque sorgenti pubbliche; per gli altri riferimenti
servono i permessi. Non trasferire credenziali. I manifest di Git sono metadati,
non copie delle matrici né accesso automatico ai dataset privati.

Le aggiunte sono incrementali: adattatore e derivati della sola nuova sorgente,
poi nuova release dell'indice. Riutilizzare i derivati se input, asse, QC, codice
e parametri coincidono; conservare le versioni precedenti.

**Il training esteso non è ancora avviato.** Copertura del catalogo, QC/ruoli,
lettori e ricevute di consumo/loss nel trainer restano da integrare con D-053.
Il cubo `rlead-bench-cube-r2` resta un pilot, non la banca completa.
'''.replace('DIGEST',sha(manifest))
 (out/'README.md').write_text(text,encoding='utf-8')
 print(json.dumps({'manifest_sha256':sha(manifest),'jobs':len(records),'public_inputs':len(public),'verified_reused_units':len(done['units'])}))

if __name__=='__main__':main()
