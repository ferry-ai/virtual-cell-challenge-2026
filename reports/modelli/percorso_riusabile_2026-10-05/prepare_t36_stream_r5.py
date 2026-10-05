"""Apply the owner's t36 label, reusing bytes already downloaded under a historical path."""
import json
from datetime import datetime,timezone
from pathlib import Path
here=Path(__file__).resolve().parent
repo=here.parents[2]
text=(here/'download_submit_frozen_r3.py').read_text(encoding='utf-8')
text=text.replace('upload_execution_r3','upload_execution_r5_t36')
text=text.replace("MODEL='t31 -", "MODEL='t36 -")
text=text.replace("'t31_'+name", "'t36_'+name")
text=text.replace('submit_t31','submit_t36').replace('t31_local_product','t36_local_product')
text=text.replace(" assert (TRIAL/'submission_texts.md')", " (TRIAL/'submission_texts_t36.md').open('x',encoding='utf-8').write(MODEL+'\\n\\n'+DESCRIPTION+'\\n')\n assert (TRIAL/'submission_texts_t36.md')")
assert 't31' not in text.replace('t31_frozen_bank_2026-10-06','')
compile(text,str(here/'download_submit_t36_r5.py'),'exec')
with (here/'download_submit_t36_r5.py').open('x',encoding='utf-8') as f:f.write(text)
report=repo/'reports/invii/prediction_t36_2026-10-06'
report.mkdir(exist_ok=False)
record=json.loads((repo/'reports/invii/prediction_t31_2026-10-06/prediction.json').read_text(encoding='utf-8'))
record.update(submission_name='t36 - transfer t28 banca estesa',owner_label_correction_utc=datetime.now(timezone.utc).isoformat(),supersedes_label_only='t31 local draft; never submitted',candidate_sha256='ea41ddf1ba352911e81442f0e07af999450088a8d5e1738fc66656e1595d4af7')
(report/'prediction.json').write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding='utf-8')
(report/'README.md').write_text('# t36 — transfer t28, banca estesa parziale\n\nNome t36 richiesto dal proprietario prima dell’invio. Sostituisce solo l’etichetta della bozza locale t31, mai inviata; candidato e hash invariati. Il percorso locale di trasporto conserva t31 nel nome per riusare i byte scaricati.\n\nRecord originale congelato nel runtime prima dello stage100, copiato localmente dopo la generazione. Nessuna banda numerica preregistrata: non inventarla dopo lo score. Invio esplorativo autorizzato, nessun miglioramento presunto.\n\n360.000 cellule sono l’output generato (3 contesti × 300 target × 400 cellule), non le cellule sperimentali della banca. Release parziale: non tutti i 395,75 GB archiviati sono consumati.\n',encoding='utf-8')
print('t36 successor ready; same product/hash; partial bytes preserved.')
