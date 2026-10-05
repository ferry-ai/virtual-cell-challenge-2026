"""Preserve exact upload evidence and route live state to the received t36 entry."""
import hashlib,json
from pathlib import Path
here=Path(__file__).resolve().parent;repo=here.parents[2]
trial=repo/'reports/invii/trial_2026-10-06'
raw=trial/'submit_t36_raw.json';receipt=json.loads(raw.read_text(encoding='utf-8-sig'))
assert receipt['entry_id']=='JLcMRGExhXKk77XVds7x' and receipt['model_name']=='t36 - transfer t28 banca estesa'
assert receipt['md5_verified'] and receipt['bytes_uploaded']==4163225600
public={k:v for k,v in receipt.items() if k!='file_path'}
public.update(raw_output_preserved_locally='submit_t36_raw.json',raw_output_sha256=hashlib.sha256(raw.read_bytes()).hexdigest(),omitted_private_field='file_path',completed_utc='2026-10-05T22:56:09.997243+00:00')
with (trial/'submit_t36_public_receipt.json').open('x',encoding='utf-8') as f:json.dump(public,f,indent=2,ensure_ascii=False)
for path in (here/'README.md',repo/'docs/piani/strategia-scientifica.md'):
 t=path.read_text(encoding='utf-8').replace('ESECUZIONE_r17.md','ESECUZIONE_r18.md')
 if path.name=='strategia-scientifica.md':
  t=t.replace('**Aggiornato:** 5 ottobre 2026, consolidamento delle prove','**Aggiornato:** 6 ottobre 2026, t36 ricevuto da VCC')
  start=t.index('- **Prossimo passo:**');end=t.index('\n',start)
  t=t[:start]+'- **Prossimo passo:** t36 ricevuto da VCC alle00:56, entry `JLcMRGExhXKk77XVds7x`, stato ufficiale launching. Processo terminato; seguire lo score, nessun altro invio o download. [Stato r18](../../reports/modelli/percorso_riusabile_2026-10-05/ESECUZIONE_r18.md).'+t[end:]
 else:t=t.replace('**Rifit/invio in corso:**','**Rifit/invio conclusi, valutazione in corso:**')
 path.write_text(t,encoding='utf-8')
path=repo/'docs/PROGETTO.md';t=path.read_text(encoding='utf-8').replace('ESECUZIONE_r17.md','ESECUZIONE_r18.md')
start=t.index('**Consegna:**');end=t.index('\n\n',start)
t=t[:start]+'''**Consegna:** t36 ricevuto da VCC alle **00:56 del 6 ottobre**, prima dell'obiettivo02:00; checksum verificato e valutazione avviata, stato launching senza punteggio. 360.000 cellule generate, distinte dalle cellule sperimentali della banca. [Ricevuta e stato](../reports/modelli/percorso_riusabile_2026-10-05/ESECUZIONE_r18.md). Nessun miglioramento ancora dimostrato.'''+t[end:]
path.write_text(t,encoding='utf-8')
path=repo/'reports/invii/README.md';t=path.read_text(encoding='utf-8')
start=t.index('**In corso:**');end=t.index('\n\n',start)
t=t[:start]+'''**In valutazione:** [t36](prediction_t36_2026-10-06/README.md), ricevuto da VCC alle00:56 del6ottobre, entry `JLcMRGExhXKk77XVds7x`, stato launching senza punteggio. La bozza locale t31 non è stata inviata. [Ricevuta e stato](../modelli/percorso_riusabile_2026-10-05/ESECUZIONE_r18.md).'''+t[end:]
path.write_text(t,encoding='utf-8')
path=repo/'docs/REGISTRO.md';t=path.read_text(encoding='utf-8')
t=t.replace('ESECUZIONE_r17 e R-LEAD seguono trasferimento/invio t36','ESECUZIONE_r18 e R-LEAD seguono t36 ricevuto e valutazione')
t=t.replace('Candidato e packaging verificati; testi t36 e output CLI dell\'invio quando disponibile. Non dichiarato score','Candidato e packaging verificati; t36 ricevuto00:56, MD5 verificato, ricevuta pubblicabile e stato completo launching. Originale CLI con percorso personale conservato localmente escluso da Git; nessun score')
path.write_text(t,encoding='utf-8')
print('t36 received; exact entry, bytes and checksum confirmed; no score inferred.')
