"""Pin SCP KO closures and HIPSCI fitness union without changing old releases."""
import json
from datetime import datetime,timezone
from pipeline_state import HERE,REPO,sha


def main():
    out=HERE/'cloud_catalog_r8';out.mkdir(exist_ok=False)
    previous=HERE/'cloud_catalog_r7/manifest.json';c=json.loads(previous.read_text())
    source=HERE/'archive_completion_scp_ko_r1/state.json';s=json.loads(source.read_text())
    ref='davidmaisterx/rlab-scp-ko'
    for unit,value in s['units'].items():
        c['units'][unit]={**value,'raw':c['raw_archives'][ref],'raw_dataset_refs':[ref]}
    c['raw_archives'][ref]['derivatives']={'state':'bank_and_samples_verified','units':list(s['units'])}
    part=HERE/'hipsci_verified_r4/state.json';h=json.loads(part.read_text())
    for unit,value in h['units'].items():
        raw='davidmaisterx/rlab-hipsci-'+('gwfit' if unit=='hipsci_gw_fitness' else 'gwnonfit')
        c['units'][unit]={'partition_union':value,
            'verified_parts':{k:r for k,r in h['jobs'].items() if r.get('unit')==unit},
            'raw':c['raw_archives'][raw],'raw_dataset_refs':[raw],'training_used':False}
    c['execution']['recovery']['hipsci_verified_units']=h['units']
    c.update(created_utc=datetime.now(timezone.utc).isoformat(),training_ready=False,
        previous_manifest={'path':previous.relative_to(REPO).as_posix(),'sha256':sha(previous)})
    c['sources']+=[{'path':p.relative_to(REPO).as_posix(),'sha256':sha(p)} for p in (source,part)]
    manifest=out/'manifest.json';manifest.write_text(json.dumps(c,indent=1)+'\n',encoding='utf-8',newline='\n')
    (out/'README.md').write_text('''# ARCHIVIO DATI — indice corrente r8

Manifest immutabile `manifest.json`, SHA256 `DIGEST`. R7 e tutte le versioni precedenti conservati.
Account/versioni/percorsi/hash identificano i dati. Indice di storage, non manifest ammesso al fit.

- Grezzi 395,75 GB, HIPSCI inclusa: [fonti e GB](../DATI_DISPONIBILI_r2.md).
- Nuove chiusure SCP KO: Frangieh (3 contesti), Papalexi arrayed (1), Sunshine (1).
  Banche/campioni, versioni/codice/lineage/file verificati in archive_completion_scp_ko_r1.
- HIPSCI fitness: **12/12 parti e unione verificate**, 51.525 righe BIO/target,
  322.746 cellule in ingresso. Nonfitness: **11/12**, unione ancora aperta;
  p8 su davideferrante11 rimane RUNNING. Stato hipsci_verified_r4/state.json.
  Nessuna altra parte da lanciare. Hash delle matrici da verificare nel consumatore.
- K562 GWPS e HIPSCI mirato19 ancora RUNNING; remaining_open_progress_r5.json.
  I 50/50 K562 riguardano il primo blocco; non sono prova di fine job.
- Le chiusure precedenti e la copia iPSC originale versione3 ready sono conservate.
- [Trainer e confronto](../TRAINER_r1.md): preparazione delegata a Grok, worker già
  in lettura delle prove (transcript_snapshot_r1.md). Parent segue chiusure dati.
  Release del fit completa ammessa/congelata; nessuna aggiunta silenziosa in corsa.
  Catalogo/QC, feature/assi, accessi e launcher restano aperti. Training non avviato.
'''.replace('DIGEST',sha(manifest)),encoding='utf-8')
    print(json.dumps({'manifest_sha256':sha(manifest),'indexed_units':len(c['units']),
                     'new_verified_units':list(s['units']),'hipsci_verified':23}))


if __name__=='__main__':main()
