"""Route live documentation to the verified candidate and t36 transport successor."""
from pathlib import Path
here=Path(__file__).resolve().parent
repo=here.parents[2]
p=repo/'docs/piani/strategia-scientifica.md'
t=p.read_text(encoding='utf-8').replace('ESECUZIONE_r16.md','ESECUZIONE_r17.md')
t=t.replace('processo download/invio PID18600, upload_execution_r2/state.json.','nome t36 richiesto dal proprietario; processo download/invio PID7228, upload_execution_r5_t36/state.json.')
t=t.replace('Stato r16','Stato r17')
p.write_text(t,encoding='utf-8')
p=here/'README.md';t=p.read_text(encoding='utf-8').replace('ESECUZIONE_r16.md','ESECUZIONE_r17.md')
t=t.replace('[cache K562, guardia maschere e freeze]','[candidato completo e invio t36]')
p.write_text(t,encoding='utf-8')
p=repo/'docs/PROGETTO.md';t=p.read_text(encoding='utf-8')
start=t.index('**Rifit:**');end=t.index('**Esiti precedenti:**',start)
t=t[:start]+'''**Rifit:** concluso il transfer originale t25 con emitter t28 sulla release estesa parziale. Sei cache corrette, K562 storico BULK e controlli montati; 13 nomi registrati, 9 con target sul pannello. Sono fonti, non 9 linee distinte. HIPSCI e altre fonti archiviate non sono ancora tutte collegate. Nessun miglioramento dimostrato. [Prove e limiti](../reports/modelli/percorso_riusabile_2026-10-05/ESECUZIONE_r17.md).

**Consegna:** candidato completo, packaging PASS: 360.000 cellule generate, distinte dalle cellule sperimentali della banca. Download a blocchi ripreso dopo interruzione; nome **t36** richiesto dal proprietario, invio del file esatto autorizzato. Stato e processo solo in R-LEAD. Non ancora dichiarato inviato; upload entro le 02:00 resta obiettivo, non promessa.

'''+t[end:]
t=t.replace('## 0. Oggi — 5 ottobre 2026','## 0. Oggi — 6 ottobre 2026')
p.write_text(t,encoding='utf-8')
p=repo/'reports/invii/README.md';t=p.read_text(encoding='utf-8')
t=t.replace('## I punteggi ufficiali in una tabella','**In corso:** [t36](prediction_t36_2026-10-06/README.md), candidato completo, download/invio; nessun punteggio dichiarato. La bozza locale t31 non è stata inviata. [Stato operativo](../modelli/percorso_riusabile_2026-10-05/ESECUZIONE_r17.md).\n\n## I punteggi ufficiali in una tabella',1)
marker='| Data | Cartella | Nocciolo | Vale? | Peso oggi |'
start=t.index(marker);pos=t.index('\n',t.index('\n',start)+1)+1
rows='''| 2026-10-06 | [prediction_t36](prediction_t36_2026-10-06/) | Record runtime originale e correzione nome richiesta dall'utente; nessuna banda numerica inventata | attuale | Invio esplorativo della release estesa parziale |
| 2026-10-06 | [trial](trial_2026-10-06/) | Manifest packaging, testi e trasferimento del candidato; output CLI quando disponibile | attuale | Nessun score ancora dichiarato |
| 2026-10-06 | [prediction_t31](prediction_t31_2026-10-06/) | Bozza locale con record runtime, mai inviata | storico | Sostituita solo l'etichetta da t36; stessi byte |
'''
t=t[:pos]+rows+t[pos:];p.write_text(t,encoding='utf-8')
p=repo/'docs/REGISTRO.md';t=p.read_text(encoding='utf-8')
marker='| `reports/invii/prediction_t30_2026-10-04/`'
pos=t.index(marker)
rows='''| `reports/invii/prediction_t36_2026-10-06/` | attuale | — | Record runtime congelato prima stage100, copia dopo generazione; nome t36 richiesto dall'utente, nessuna banda numerica inventata e nessun miglioramento presunto | — |
| `reports/invii/trial_2026-10-06/` | attuale | — | Candidato e packaging verificati; testi t36 e output CLI dell'invio quando disponibile. Non dichiarato score | — |
| `reports/invii/prediction_t31_2026-10-06/` | storico | `reports/invii/prediction_t36_2026-10-06/` | Bozza locale mai inviata, conservata; correzione del solo nome richiesta dal proprietario prima upload | — |
'''
t=t[:pos]+rows+t[pos:]
start=t.index('| `reports/modelli/percorso_riusabile_2026-10-05/` |');end=t.index('\n',start)
t=t[:start]+"| `reports/modelli/percorso_riusabile_2026-10-05/` | attuale | — | Storage r11 e producer persistenti; rifit/generazione parziale conclusi, candidato formato PASS. ESECUZIONE_r17 e R-LEAD seguono trasferimento/invio t36; corpus completo e valutazione ancora aperti | [R-LEAD](piani/strategia-scientifica.md) |"+t[end:]
p.write_text(t,encoding='utf-8')
print('t36 routes, registry and candidate evidence consolidated.')
