"""Pin new closures, all HIPSCI assignments and relocated original iPSC bank."""
import json
from datetime import datetime,timezone
from pipeline_state import HERE,REPO,sha


def main():
    out=HERE/'cloud_catalog_r7';out.mkdir(exist_ok=False)
    previous=HERE/'cloud_catalog_r6/manifest.json';c=json.loads(previous.read_text())
    paths=[HERE/'archive_completion_a549_r1/state.json',HERE/'hipsci_verified_r2/state.json',
           HERE/'tian_population_rehouse_r1.json',HERE/'tian_population_version3_r1.json']
    a=json.loads(paths[0].read_text());ref='davidmaisterx/rlab-a549'
    for unit,value in a['units'].items():
        c['units'][unit]={**value,'raw':c['raw_archives'][ref],'raw_dataset_refs':[ref]}
    c['raw_archives'][ref]['derivatives']={'state':'bank_and_samples_verified','units':list(a['units'])}
    h=json.loads(paths[1].read_text())
    for unit,v in h['units'].items():
        jobs={k:r for k,r in h['jobs'].items() if r.get('unit')==unit}
        c['units'][unit]={'partition_union':v,'verified_parts':jobs,'training_used':False}
    relocated=json.loads(paths[2].read_text());version=json.loads(paths[3].read_text())
    if version!={'status':'ready','current_version_number':3}:raise ValueError('relocated bank not saved')
    c['units']['tian2019_ipsc']['bank']['mountable_copy']={
        'dataset':relocated['dataset'],'version':3,'private':True,
        'receipt_sha256':relocated['bank_receipt_sha256'],'files':relocated['files'],
        'gzip_alias':'samples.jsonl.gz.bin','consumer_runtime_hashes_verified':False,
        'original_producer_retained':True}
    ledgers=[HERE/'hipsci_partition_r1/launches.jsonl',HERE/'hipsci_shared_r1/launches.jsonl']
    frozen=[];assigned=[]
    for i,p in enumerate(ledgers):
        dest=out/f'launch_snapshot_{i}.jsonl';dest.open('xb').write(p.read_bytes())
        frozen.append({'path':dest.relative_to(REPO).as_posix(),'sha256':sha(dest)})
        assigned.extend(r for r in map(json.loads,p.read_text().splitlines()) if r['accepted'])
    if len(assigned)!=24 or len({(r['unit'],r['partition']['part']) for r in assigned})!=24:
        raise ValueError('not all distinct HIPSCI partitions assigned')
    c['execution']['recovery'].update(hipsci_assigned=assigned,hipsci_verified_units=h['units'],
        latest_frozen_launch_journals=frozen,ipsc_population_mountable_version=3)
    c.update(created_utc=datetime.now(timezone.utc).isoformat(),training_ready=False,
        previous_manifest={'path':previous.relative_to(REPO).as_posix(),'sha256':sha(previous)})
    c['sources']+=frozen+[{'path':p.relative_to(REPO).as_posix(),'sha256':sha(p)} for p in paths]
    manifest=out/'manifest.json';manifest.write_text(json.dumps(c,indent=1)+'\n',encoding='utf-8',newline='\n')
    (out/'README.md').write_text('''# ARCHIVIO DATI — indice corrente r7

Manifest immutabile `manifest.json`, SHA256 `DIGEST`. R6 e versioni precedenti conservati.
Account, versioni, percorsi e hash identificano i dati: mai scegliere per somiglianza del nome.

- Grezzi **395,75 GB, HIPSCI già inclusa**; [fonti e GB](../DATI_DISPONIBILI_r2.md).
  Con banca e campioni l'archivio complessivo supera 400 GB; questo non è il volume letto per ogni fit.
- Nuova chiusura A549, banca e campioni verificati: `archive_completion_a549_r1`.
- HIPSCI: tutte **24/24 parti avviate**, **14/24 verificate** (7 per unità);
  unioni ancora aperte. `hipsci_verified_r2/state.json`; entrambi i ledger congelati qui.
- iPSC: statistiche originali rese montabili nel dataset privato
  `davideferante/vcc-tian-ipsc-sample-input-r1`, **versione 3 ready**.
  Riparazione dell'accesso al produttore ERROR; 485,43 MB mancanti trasferiti una volta,
  hash originali verificati, locatori già presenti riusati, nessun ricalcolo.
  Verifica hash nel runtime del trainer e accesso fra account ancora necessari.
- [Collegamento al training e confronto transfer](../TRAINER_r1.md).
  Il nuovo loop esegue ottimizzazione reale sulle fixture, con controlli fra parti e
  ricevute di consumo/resume. Questo NON prova un training esteso su dati reali:
  catalogo/QC, feature di transfer congelate, accessi e launcher restano da completare.
'''.replace('DIGEST',sha(manifest)),encoding='utf-8')
    print(json.dumps({'manifest_sha256':sha(manifest),'hipsci_assigned':24,'hipsci_verified':14}))


if __name__=='__main__':main()
