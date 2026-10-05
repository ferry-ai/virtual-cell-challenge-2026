"""Record closed HIPSCI unions and unchanged mountable Norman/iPSC copies."""
import json
from datetime import datetime, timezone
from pipeline_state import HERE, REPO, sha


def main():
    previous = HERE/'cloud_catalog_r8/manifest.json'
    c = json.loads(previous.read_text())
    part = HERE/'hipsci_verified_r5/state.json'
    h = json.loads(part.read_text())
    for unit, value in h['units'].items():
        if value['state'] != 'remote_complete_union_checked':
            raise ValueError('HIPSCI union not verified')
        c['units'][unit]['partition_union'] = value
        c['units'][unit]['verified_parts'] = {k:v for k,v in h['jobs'].items() if v.get('unit') == unit}
    norman = HERE/'norman_rehouse_private_r1.json'
    n = json.loads(norman.read_text())
    publication = HERE/'public_norman_r1/publication.jsonl'
    public = json.loads(publication.read_text().strip())
    if not public['public'] or public['version']['current_version_number'] != 1:
        raise ValueError('Norman publication not verified')
    for role in ('bank', 'samples'):
        c['units']['norman2019'][role]['mountable_copy'] = {
            'dataset': n['dataset'], 'version': 1, 'private': False,
            'layout_sha256': n['layout_sha256'],
            'access_adapter': (HERE/'restore_bank_aliases_v1.py').relative_to(REPO).as_posix(),
            'files': n['files'], 'original_producer_retained': True,
            'consumer_runtime_hashes_verified': False}
    access = HERE/'public_ipsc_input_r1/verified_after_response_error.json'
    a = json.loads(access.read_text())
    if not a['public'] or a['version']['current_version_number'] != 3:
        raise ValueError('iPSC publication not verified')
    c['units']['tian2019_ipsc']['bank']['mountable_copy']['private'] = False
    c['execution']['current_supervision'] = {
        'open_jobs_snapshot': (HERE/'remaining_open_progress_r6.json').relative_to(REPO).as_posix(),
        'grok_session': '613a1b58-0807-4abe-8dff-be9b67204552',
        'grok_scope': 'agenti/grok_transfer_esteso_r2',
        'previous_delivery_review': 'GROK_REVIEW_r1.md',
        'full_fit_launched': False}
    c.update(created_utc=datetime.now(timezone.utc).isoformat(), training_ready=False,
             previous_manifest={'path':previous.relative_to(REPO).as_posix(),'sha256':sha(previous)})
    sources = (part, norman, publication, access, HERE/'GROK_REVIEW_r1.md',
               HERE/'remaining_open_progress_r6.json', HERE/'restore_bank_aliases_v1.py')
    c['sources'] += [{'path':p.relative_to(REPO).as_posix(),'sha256':sha(p)} for p in sources]
    out = HERE/'cloud_catalog_r9'
    out.mkdir(exist_ok=False)
    manifest = out/'manifest.json'
    manifest.write_text(json.dumps(c,indent=1)+'\n',encoding='utf-8',newline='\n')
    (out/'README.md').write_text('''# ARCHIVIO DATI — indice corrente r9

Manifest immutabile `manifest.json`, SHA256 `DIGEST`. Versioni precedenti conservate.
Account/versioni/percorsi/hash identificano i dati: nessun fallback ai dataset storici.
È un indice di storage, non una release ammessa al fit.

- Grezzi 395,75 GB, HIPSCI inclusa: [fonti e GB](../DATI_DISPONIBILI_r2.md).
- HIPSCI genome-wide: **24/24 parti e entrambe le unioni verificate** in hipsci_verified_r5.
- Norman banca e campioni: `davideferante/vcc-norman-bank-samples-r1`, versione 1 pubblica.
  Byte originali verificati prima del salvataggio; layout e alias espliciti nel manifest.
- iPSC statistiche originali: `davideferante/vcc-tian-ipsc-sample-input-r1`, versione 3 pubblica.
  Pubblicazione verificata dopo una risposta API non valida; nessuna versione dati nuova.
- K562 GWPS e HIPSCI mirato19 ancora aperti nell'ultimo snapshot remaining_open_progress_r6.
- **Copertura dell'intero catalogo e collegamento al trainer ancora aperti.** Verificare
  accessi, hash, assi, maschere, split e consumo effettivo nel runtime prima della chiusura.
  Grok prosegue nella stessa sessione, cartella r2; r1 non adottata dopo difetto BIO riprodotto.
  Nessun fit esteso ancora lanciato. [Verifica r1](../GROK_REVIEW_r1.md).

Riutilizzare i derivati a parità di input, asse, QC, codice e parametri. Un nuovo dataset
aggiunge il proprio adattatore/banca/campioni e una nuova release, senza rifare gli altri.
'''.replace('DIGEST',sha(manifest)),encoding='utf-8')
    print(json.dumps({'manifest_sha256':sha(manifest),'indexed_units':len(c['units'])}))


if __name__ == '__main__':
    main()
