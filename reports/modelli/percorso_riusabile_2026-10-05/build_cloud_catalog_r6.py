"""Pin verified Tian closures, shared HIPSCI input privacy and actual partition assignment."""
import json
from datetime import datetime,timezone
from pipeline_state import HERE,REPO,sha


def main():
    out=HERE/'cloud_catalog_r6';out.mkdir(exist_ok=False)
    previous=HERE/'cloud_catalog_r5/manifest.json';c=json.loads(previous.read_text())
    sources=[]
    path=HERE/'tian_resume_verified_r1/state.json';t=json.loads(path.read_text());sources.append(path)
    ref='davidmaisterx/rlab-tian-norman'
    for unit,value in t['units'].items():
        c['units'][unit]={**value,'raw':c['raw_archives'][ref],'raw_dataset_refs':[ref]}
    c['raw_archives'][ref]['derivatives']={'state':'bank_and_samples_verified','units':list(t['units']),
        'producers':'tian_resume_verified_r1/state.json; distinct bank/sample provenance retained'}
    public=HERE/'public_hipsci_r1/publication.jsonl';sources.append(public)
    for r in map(json.loads,public.read_text().splitlines()):
        if not r['public']:raise ValueError('raw input not public')
        c['raw_archives'][r['ref']]['public']=True
    c['execution']['public_raw_inputs']=sorted(set(c['execution']['public_raw_inputs'])|
        {r['ref'] for r in map(json.loads,public.read_text().splitlines())})
    paths=[HERE/'hipsci_partition_r1/launches.jsonl',HERE/'hipsci_shared_r1/launches.jsonl',
           HERE/'tian_resume_r2/launches.jsonl',HERE/'tian_ipsc_r4/launches.jsonl']
    frozen=[]
    for i,p in enumerate(paths):
        dest=out/f'launch_snapshot_{i}.jsonl';dest.open('xb').write(p.read_bytes())
        frozen.append({'path':dest.relative_to(REPO).as_posix(),'sha256':sha(dest)})
    assigned=[r for p in paths[:2] for r in map(json.loads,p.read_text().splitlines()) if r['accepted']]
    if len({(r['unit'],r['partition']['part']) for r in assigned})!=len(assigned):raise ValueError('duplicate HIPSCI assignment')
    part_path=HERE/'hipsci_verified_r1/state.json';h=json.loads(part_path.read_text());sources.append(part_path)
    c['execution']['recovery'].update(hipsci='dispatch_hipsci_shared_v1.py; archive_partition_state_v2.py; both ledgers required',
        tian='all five units bank/samples verified in tian_resume_verified_r1; iPSC bank reused from saved producer',
        frozen_launch_journals=frozen,hipsci_assigned=assigned,hipsci_verified_units=h['units'],
        private_sample_input_version2=json.loads((HERE/'tian_rehouse_version2_r1.json').read_text()))
    c['execution']['publication_authorization']='Owner: publish pipeline inputs/outputs when access limits work; do not publish unrelated models.'
    c.update(created_utc=datetime.now(timezone.utc).isoformat(),training_ready=False,
        scope='Verified closures and cross-account HIPSCI partitions; complete catalogue/consumer/trainer still open',
        previous_manifest={'path':previous.relative_to(REPO).as_posix(),'sha256':sha(previous)})
    c['sources'] += frozen+[{'path':p.relative_to(REPO).as_posix(),'sha256':sha(p)} for p in sources]
    manifest=out/'manifest.json';manifest.write_text(json.dumps(c,indent=1)+'\n',encoding='utf-8',newline='\n')
    (out/'README.md').write_text('''# ARCHIVIO DATI — indice corrente r6

Percorso principale: archivio → banca/campioni persistenti → training esteso.
Manifest `manifest.json`, SHA256 `DIGEST`. Montare account/versioni/percorsi/hash,
mai un dataset storico per somiglianza del nome. R5 e i precedenti sono conservati.

- Grezzi perturbazionali: **395,75 GB**, invariati; [tabella fonti](../DATI_DISPONIBILI_r2.md).
- CD4, KOLF, HCT116 e HEK293T hanno campioni chiusi e unioni verificate.
  HEK293T 6/6, 27,26GB; codice/versioni/ricevute/lineage verificati, nessun nuovo download.
- Otto ulteriori job chiusi oltre a HepG2, in archive_completion_batch_r1.
- **Tian/Norman: tutte le cinque unità banca/campioni verificate**, in
  tian_resume_verified_r1. Norman e banca iPSC già riusciti sono riusati;
  i riferimenti ai diversi produttori restano espliciti. Le statistiche iPSC
  rimangono nel produttore ERROR recuperabile via API: ancora da rendere
  montabili al trainer, senza ripetere il calcolo. Locatori gzip originali
  preservati tramite alias binario nel dataset privato di input versione 2.
- HIPSCI genome-wide: due grezzi ora pubblici senza modifica dei file,
  assegnazioni CPU distribuite sui tre account. [Ledger e prossimi comandi](../PARALLELISMO_r3.md).
  Tre parti già verificate, unioni 12/12 per unità ancora aperte. Gli snapshot
  dei ledger sono congelati qui; i journal operativi possono crescere.
- Sette input grezzi pubblici verificati; gli altri dati e nuovi output
  ancora privati. L'utente autorizza la pubblicazione necessaria a togliere
  limiti di accesso della pipeline; evitare trasferimenti o ricalcolo inutili.

**Training esteso ancora non avviato.** Integrare reader delle parti e ancore,
hash nel runtime, split D-053, QC/ruoli e uso effettivo dei dati/loss anche dopo
resume; completare le altre voci del catalogo. Nessuna promozione dalla loss
dei 18 fit preliminari. Questo indice certifica gli artefatti indicati, non
copertura completa o consumo effettivo da parte del trainer.
'''.replace('DIGEST',sha(manifest)),encoding='utf-8')
    print(json.dumps({'manifest_sha256':sha(manifest),'units_indexed':len(c['units']),
                     'hipsci_assigned':len(assigned),'public_raw_inputs':len(c['execution']['public_raw_inputs'])}))


if __name__=='__main__':main()
