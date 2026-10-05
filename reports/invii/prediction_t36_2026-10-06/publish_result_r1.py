"""Publish the measured result and its limitations without rewriting frozen records."""
from pathlib import Path
HERE=Path(__file__).resolve().parent;REPO=HERE.parents[2]
study=REPO/'reports/modelli/percorso_riusabile_2026-10-05'
cp='0067-t36-banca-estesa-punteggio-ufficiale.md'
for path in (study/'README.md',REPO/'docs/piani/strategia-scientifica.md'):
 t=path.read_text(encoding='utf-8').replace('ESECUZIONE_r18.md','ESECUZIONE_r19.md')
 if path.name=='strategia-scientifica.md':
  t=t.replace('t36 ricevuto da VCC','t36 pubblicato')
  start=t.index('- **Prossimo passo:**');end=t.index('\n',start)
  t=t[:start]+f'- **Prossimo passo:** t36 pubblicato, nuovo massimo osservato e confronto descrittivo; [CP-0067](../checkpoints/{cp}). Non pollare entry terminale o reinviare. Proseguire copertura del catalogo, adapter/QC e consumo delle fonti non ancora collegate; nessun worker attivo. [Stato r19](../../reports/modelli/percorso_riusabile_2026-10-05/ESECUZIONE_r19.md).'+t[end:]
 else:t=t.replace('**Rifit/invio conclusi, valutazione in corso:**','**Rifit, invio e valutazione della release parziale conclusi:**')
 path.write_text(t,encoding='utf-8')
path=REPO/'reports/invii/README.md';t=path.read_text(encoding='utf-8')
start=t.index('**In valutazione:**');end=t.index('\n\n',start)
t=t[:start]+f'**Ultimo esito:** [t36](prediction_t36_2026-10-06/comparison.json), nuovo massimo osservato **0,147249**, +0,002404 contro t28; confronto descrittivo, stabilità non dimostrata ([CP-0067](../../docs/checkpoints/{cp})). Bozza locale t31 mai inviata.'+t[end:]
marker='|---|---|---|---|\n';pos=t.index(marker,t.index('## I punteggi ufficiali'))+len(marker)
t=t[:pos]+f'| **t36** | **+0,147249** | 432 | Transfer t25/emitter t28, banca estesa parziale; +0,002404 contro t28, nuovo massimo osservato. Nessuna soglia numerica preregistrata; confronto descrittivo, nessuna promozione robusta ([CP-0067](../../docs/checkpoints/{cp})) |\n'+t[pos:]
path.write_text(t,encoding='utf-8')
path=REPO/'docs/PROGETTO.md';t=path.read_text(encoding='utf-8').replace('ESECUZIONE_r18.md','ESECUZIONE_r19.md')
start=t.index('**Riferimento ufficiale:**');end=t.index('\n\n',start)
t=t[:start]+f'**Massimo ufficiale osservato:** t36 **0,147249**, +0,002404 contro t28; confronto descrittivo su singolo invio, stabilità non dimostrata ([CP-0067](checkpoints/{cp})). Algoritmo di confronto: transfer t25 con emitter t28; unica variabile banca. Nessuna promozione automatica a riferimento robusto. Stato e assegnazioni in [R-LEAD](piani/strategia-scientifica.md).'+t[end:]
start=t.index('**Consegna:**');end=t.index('\n\n',start)
t=t[:start]+f'**Consegna:** t36 ricevuto alle00:56 del6ottobre e pubblicato al controllo01:38. Checksum e sei membri ufficiali verificati; [risultato e limiti](../reports/modelli/percorso_riusabile_2026-10-05/ESECUZIONE_r19.md). Rifit/generazione/invio della release parziale conclusi, percorso completo D-053 ancora aperto.'+t[end:]
path.write_text(t,encoding='utf-8')
path=REPO/'docs/AMBITI.md';t=path.read_text(encoding='utf-8')
start=t.index('- **Misurato.** Massimo osservato:',t.index('### 2.'));end=t.index('\n- **Misurato.** Il t28',start)
t=t[:start]+f'- **Misurato, 6/10.** Massimo osservato t36 **0,147249**, +0,002404 da t28 sulla banca estesa parziale. Sei membri ufficiali verificati; PDS/NMAE salgono, reach/fedeltà/Jaccard scendono, MSE scalata0. Confronto descrittivo senza soglia numerica preregistrata; nessuna stabilità dimostrata o promozione automatica ([CP-0067](checkpoints/{cp})). Tutti i punteggi: [invii](../reports/invii/README.md).'+t[end:]
path.write_text(t,encoding='utf-8')
path=REPO/'docs/STRADE.md';t=path.read_text(encoding='utf-8')
start=t.index('| S-010 |');end=t.index('\n',start)
t=t[:start]+'| S-010 | Fonti del transfer: tabelle aggregate in più contro le fonti della ricetta t22/t25 | Banco storico positivo ma non ammesso; t36 ufficiale +0,002404 da t28, nuovo massimo descrittivo (CP-0067), stabilità non dimostrata | ipotizzato | 2026-10-06 |'+t[end:]
start=t.index('### S-010');pos=t.index('\n\n',start)+2
t=t[:pos]+f'''- **Aggiornamento 6/10:** [CP-0067](checkpoints/{cp}), [comparison t36](../reports/invii/prediction_t36_2026-10-06/comparison.json): transfer t25/emitter t28 su banca estesa parziale,0,147249 e +0,002404 da t28. Invio diretto autorizzato dal proprietario, senza banco comparativo o soglia numerica preregistrata. Nuovo massimo osservato, non prova stabile o attribuibile a una fonte. Meccanismo ancora **ipotizzato**. Il banco storico e il suo criterio qui sotto mantengono il loro perimetro; «nessun invio finora» si riferisce al4ottobre, non allo stato attuale. La lettura eseguibile read_t36_score.py vincola entry/pannello/ancore/media e vieta soglie inventate, non misura robustezza.

'''+t[pos:]
path.write_text(t,encoding='utf-8')
path=REPO/'docs/REGISTRO.md';t=path.read_text(encoding='utf-8')
pos=t.index('| `docs/checkpoints/0065-')
t=t[:pos]+f'| `docs/checkpoints/{cp}` | attuale | — | t36 pubblicato0,147249, +0,002404 da t28, nuovo massimo tra riferimenti registrati; confronto descrittivo senza banda numerica, copertura parziale e robustezza aperta | — |\n'+t[pos:]
t=t.replace('ESECUZIONE_r18 e R-LEAD seguono t36 ricevuto e valutazione','ESECUZIONE_r19 e R-LEAD seguono t36 pubblicato e copertura residua')
t=t.replace('corpus completo e valutazione ancora aperti','corpus completo e conferma della robustezza ancora aperti')
t=t.replace('nessuna banda numerica inventata e nessun miglioramento presunto','nessuna banda numerica inventata; t36 pubblicato, confronto descrittivo in comparison.json')
path.write_text(t,encoding='utf-8')
print('Official table, CP-0067, S-010 and live routes updated; frozen records preserved.')
