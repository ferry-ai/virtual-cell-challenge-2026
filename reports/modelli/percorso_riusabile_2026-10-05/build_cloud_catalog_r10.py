"""Pin the verified HIPSCI targeted19 bank and materialized samples."""
import json
from datetime import datetime,timezone
from pipeline_state import HERE,REPO,sha


def main():
    previous=HERE/'cloud_catalog_r9/manifest.json'
    source=HERE/'archive_completion_hipsci_targeted19_r1/state.json'
    c=json.loads(previous.read_text());s=json.loads(source.read_text())
    ref='davidmaisterx/rlab-hipsci-targeted19'
    for unit,value in s['units'].items():
        raw=c['raw_archives'][ref]
        if unit not in raw['units']:raise ValueError('unit absent from pinned raw archive')
        c['units'][unit]={**value,'raw':raw,'raw_dataset_refs':[raw['dataset']]}
    c['raw_archives'][ref]['derivatives']={'state':'bank_and_samples_verified','units':list(s['units'])}
    c.update(created_utc=datetime.now(timezone.utc).isoformat(),training_ready=False,
             previous_manifest={'path':previous.relative_to(REPO).as_posix(),'sha256':sha(previous)})
    snapshot=HERE/'remaining_open_progress_r7.json'
    c['execution']['current_supervision']['open_jobs_snapshot']=snapshot.relative_to(REPO).as_posix()
    c['sources'] += [{'path':p.relative_to(REPO).as_posix(),'sha256':sha(p)} for p in (source,snapshot)]
    out=HERE/'cloud_catalog_r10';out.mkdir(exist_ok=False)
    manifest=out/'manifest.json';manifest.write_text(json.dumps(c,indent=1)+'\n',encoding='utf-8',newline='\n')
    (out/'README.md').write_text('''# ARCHIVIO DATI — indice corrente r10

Manifest immutabile `manifest.json`, SHA256 `DIGEST`; r9 e precedenti conservati.
Account, versioni, hash e lineage identificano gli input. Nessun fallback storico.
Questo è un indice di storage, non una release ammessa al fit.

- HIPSCI mirato19: banca e campioni chiusi e verificati, 20 contesti BIO.
  Campioni: 497.355 / 520.464 / 622.353 cellule ai livelli 32 / 64 / 128.
  Ricevute, codice e versione in archive_completion_hipsci_targeted19_r1/state.json.
- HIPSCI genome-wide: entrambe le unioni verificate, 24/24 parti.
- Norman banca/campioni pubblici v1; iPSC statistiche pubbliche v3, byte originali.
  [Dettagli di accesso e riuso](../cloud_catalog_r9/README.md).
- K562 GWPS resta RUNNING nell'ultimo snapshot remaining_open_progress_r7.json.
  Il 50/50 è il primo blocco prima di salvataggio e campionamento, non la chiusura.
- Copertura dell'intero catalogo, ammissione QC/split, assi e hash nel runtime,
  consumo effettivo nel trainer ancora aperti. Grok stessa sessione r2, nessun fit esteso.
- [Grezzi e GB](../DATI_DISPONIBILI_r2.md): 395,75 GB, HIPSCI già inclusa.

Riutilizzare i derivati se input/asse/QC/codice/parametri coincidono; un nuovo
dataset aggiunge solo i suoi derivati e una nuova release globale.
'''.replace('DIGEST',sha(manifest)),encoding='utf-8')
    print(json.dumps({'manifest_sha256':sha(manifest),'units':len(c['units'])}))


if __name__=='__main__':main()
