"""Pin new verified closures, error recovery and complete HEK sample union."""
import json
from datetime import datetime,timezone
from pipeline_state import HERE,REPO,sha


def main():
    out=HERE/'cloud_catalog_r5';out.mkdir(exist_ok=False)
    parent=HERE/'cloud_catalog_r4/manifest.json'; c=json.loads(parent.read_text());sources=[]
    batch=HERE/'archive_completion_batch_r1/state.json'
    for r in json.loads(batch.read_text()):
        if r['state']!='verified':continue
        path=__import__('pathlib').Path(r['receipt']); state=json.loads(path.read_text());sources.append(path)
        for unit,value in state['units'].items():
            rawrefs=[ref for ref,v in c['raw_archives'].items() if unit in v['units']]
            if len(rawrefs)!=1:raise ValueError('ambiguous raw provenance')
            c['units'][unit]={**value,'raw':c['raw_archives'][rawrefs[0]],'raw_dataset_refs':rawrefs}
            c['raw_archives'][rawrefs[0]]['derivatives']={'state':'bank_and_samples_verified','kernel':state['kernel'],
                'units':list(state['units'])}
    partial=HERE/'tian_partial_r1/state.json'; t=json.loads(partial.read_text());sources.append(partial)
    for unit,value in t['units'].items():
        ref='davidmaisterx/rlab-tian-norman'
        c['units'][unit]={**value,'raw':c['raw_archives'][ref],'raw_dataset_refs':[ref]}
    parts_path=HERE/'snapshot_parts_r5/state.json';parts=json.loads(parts_path.read_text());sources.append(parts_path)
    for unit,state in parts['units'].items():
        c['units'][unit]['samples']={**state,'parts':[p for p in parts['parts'].values() if p['kernel'].find(unit.replace('orion_','').replace('kolf_pan_genome','kolf'))>=0],
             'consumer_hashes_verified':False,'training_used':False}
    # Use producer receipts for exact unit membership instead of slug guessing.
    for unit in parts['units']:
        c['units'][unit]['samples']['parts']=[]
        for p in parts['parts'].values():
            if p['state']=='remote_complete_manifest_checked' and json.loads((REPO/p['receipt']).read_text())['unit']==unit:
                c['units'][unit]['samples']['parts'].append(p)
    c['execution']['recovery']={'hipsci':'hipsci_partition_r1/launches.jsonl; 12 disjoint BIO/target parts per unit',
       'tian':'tian_partial_r1/state.json; retain Norman, reuse iPSC bank; tian_resume_r1 and tian_rehouse_r1',
       'completed_job_sample_hashes':'manifest checked; full matrices verified only in runtime consumer'}
    c.update(created_utc=datetime.now(timezone.utc).isoformat(),training_ready=False,
       scope='Current archived sources; new derivative closures verified, HEK complete; full catalogue/trainer open',
       previous_manifest={'path':parent.relative_to(REPO).as_posix(),'sha256':sha(parent)})
    sources += [batch,HERE/'archive_jobs_progress_r3.json',HERE/'remaining_archives_progress_r2.json',
                HERE/'hipsci_partition_r1/launches.jsonl']
    c['sources'] += [{'path':p.relative_to(REPO).as_posix(),'sha256':sha(p)} for p in sources]
    manifest=out/'manifest.json';manifest.write_text(json.dumps(c,indent=1)+'\n',encoding='utf-8',newline='\n')
    (out/'README.md').write_text('''# ARCHIVIO DATI — indice corrente r5

Percorso principale: archivio → banca/campioni → training esteso.
Manifest `manifest.json`, SHA256 `DIGEST`; usare account/versioni/percorsi/hash,
mai un archivio storico per somiglianza del nome o un fallback al pilot r2.

- Grezzi perturbazionali conservati: **395,75 GB**. [Tabella delle fonti](../DATI_DISPONIBILI_r2.md).
- CD4, KOLF, HCT116 e **HEK293T** chiusi nei campioni; HEK ha tutte le sei parti
  e unione verificata, **27,26 GB** (`snapshot_parts_r5`), senza riscaricare matrici.
- Oltre a HepG2, verificate otto chiusure di job: Jurkat, H1 train/val, RPE1,
  K562 essenziale, SCP Tcells (3 unità), SCP K562/HEK (4 unità), KOLF piccoli
  (2 unità) e KOLF forte. Prove in `archive_completion_batch_r1`.
- Norman è già chiuso dentro il job Tian fallito; iPSC ha banca salvata.
  `tian_partial_r1` conserva i riferimenti. Il problema dei campioni sono righe
  con popolazione misurata zero: restano in banca, non generano cellule fittizie.
- HIPSCI genome-wide richiede partizione per capienza output: `hipsci_partition_r1`.
  Le parti conservano gruppi BIO/target interi; momento, maschera e campione
  uguali alla versione non partizionata nella fixture. Unione reale ancora aperta.
- Cinque input pubblici autorizzati, altri archivi e nuovi derivati privati.
  Accesso del trainer da verificare; gli output di un job fallito possono essere
  recuperabili via API e comunque rifiutati come input notebook. Riparare accesso
  salvando solo gli artefatti necessari, non rifacendo ingestion o banca.

**Training esteso non ancora avviato.** Riconciliazione del catalogo, QC/ruoli,
controlli per tutte le parti, reader nel trainer, split D-053 e ricevute effettive
di consumo/loss restano necessari. Questo indice non certifica quei passi.
'''.replace('DIGEST',sha(manifest)),encoding='utf-8')
    print(json.dumps({'manifest_sha256':sha(manifest),'units_indexed':len(c['units']),'training_ready':False}))


if __name__=='__main__':main()
