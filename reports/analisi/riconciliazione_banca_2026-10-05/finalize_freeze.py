import json,hashlib
from pathlib import Path
from datetime import datetime,timezone
R=Path(__file__).resolve().parents[3];A=Path(__file__).parent
S=R/'reports/modelli/percorso_riusabile_2026-10-05'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
previous=A/'frozen/expected_r2.json';e=json.loads(previous.read_text())
storage=S/'cloud_catalog_r11/manifest.json';c=json.loads(storage.read_text())
assert set(e['expected_storage_units']) <= set(c['units'])
e.update(utc=datetime.now(timezone.utc).isoformat(),storage_index=storage.relative_to(R).as_posix(),storage_sha256=sha(storage),
         expected_storage_units=c['units'],previous_coverage={'path':previous.relative_to(R).as_posix(),'sha256':sha(previous)})
(A/'frozen/expected_r3.json').open('x',encoding='utf-8').write(json.dumps(e,indent=1)+'\n')
for rel in ('README.md','reports/modelli/percorso_riusabile_2026-10-05/README.md'):
 p=R/rel;s=p.read_text(encoding='utf-8').replace('cloud_catalog_r10/','cloud_catalog_r11/').replace('manifest storage r10','manifest storage r11').replace('storage r10','storage r11')
 s=s.replace('frozen/expected_r2.json','frozen/expected_r3.json').replace('expected r2 congelato','expected r3 congelato')
 s=s.replace('ESECUZIONE_r14.md','ESECUZIONE_r15.md')
 p.write_text(s,encoding='utf-8')
p=R/'docs/piani/strategia-scientifica.md';s=p.read_text(encoding='utf-8').replace('storage r10','storage r11').replace('ESECUZIONE_r14.md','ESECUZIONE_r15.md')
s=s.replace('freeze alle23:30 e lancio del pacchetto generation_successors_r1, poi invio diretto dopo integrità/formato','rifit/generazione generation_successors_r1 accettato alle23:29:37, provider RUNNING; seguire output e invio diretto dopo integrità/formato')
p.write_text(s,encoding='utf-8')
p=R/'docs/PROGETTO.md';s=p.read_text(encoding='utf-8').replace('43 unità storage censite','45 unità storage censite').replace('ESECUZIONE_r13.md','ESECUZIONE_r15.md')
s=s.replace('la correzione degli adapter precede il fit finale','sei cache corrette sono state verificate e montate nel job finale')
s=s.replace('generazione .vcc preparata, non avviata','rifit/generazione .vcc accettato su Kaggle alle23:29:37, provider RUNNING')
p.write_text(s,encoding='utf-8')
# Correct the dated audit's routing without rewriting the frozen evidence it describes.
p=A/'README.md';s=p.read_text(encoding='utf-8')
notice='**Aggiornamento del freeze:** storage [r11](../../modelli/percorso_riusabile_2026-10-05/cloud_catalog_r11/manifest.json), 45 unità; coverage [r3](frozen/expected_r3.json) conserva tutte le voci r2 e aggiunge GWPS. Cache K562 e controlli già caricati; sei adapter corretti verificati. [Lancio finale](../../modelli/percorso_riusabile_2026-10-05/ESECUZIONE_r15.md). Le fotografie r10/r2 sotto sono precedenti, non stato operativo.\n\n'
s=s.replace('## Identità degli ingressi',notice+'## Identità degli ingressi',1);p.write_text(s,encoding='utf-8')
print(json.dumps({'coverage_units':len(e['expected_storage_units']),'coverage_sha256':sha(A/'frozen/expected_r3.json')}))
