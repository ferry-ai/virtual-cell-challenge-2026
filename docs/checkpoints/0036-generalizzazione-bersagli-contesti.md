# CP-0036 — La ricerca valuta bersagli e contesti nuovi senza richiedere overlap col pannello

- **Data:** 2026-09-24
- **Tipo:** cambio-di-strategia
- **Redatto da:** Codex
- **Revisione umana:** no
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Come scegliere dati e modelli per il set finale senza limitarsi ai bersagli
attuali, distinguendo trasferimento dello stesso bersaglio e previsione di nuovi?

## 2. Cosa è stato fatto

Su richiesta del proprietario, registrata D-044 e scritta la guida
`docs/GENERALIZZAZIONE.md`. Aggiornati accordo degli agenti, mappa, guida operativa
e README. Precisato il docstring di `src/vcc2026/multisource.py`: il requisito
dello stesso bersaglio appartiene a quel metodo, non a ogni modello zero-shot.
Riletti CP-0026 e CP-0035 per distinguere risultati passati e nuova ipotesi.

## 3. Cosa si è osservato

**Nessuna nuova misura biologica o prestazione di modello.** CP-0035 aveva
misurato nove bersagli attuali nell'archivio Mixscale, che ne contiene 218:
`reports/dld1_audit_2026-09-24/mixscale_r1/measurements.json`.
Quell'overlap descrive l'uso immediato nella baseline, non il valore per il training.
CP-0026 aveva già distinto regimi C/T/J; lo scarto di quella rete rimane valido
per quell'esperimento, senza costituire un divieto generale di modelli appresi.

## 4. Interpretazione e incertezza

**Decisione:** ammettere sorgenti anche senza overlap col pannello e dare priorità
alla valutazione congiunta su bersagli e contesti nuovi. **Ipotesi aperta:** una
maggiore diversità di contesti può migliorare la generalizzazione. Non basta
contarli: studio, chimica e stimolo possono essere confusi con il contesto.

## 5. Spiegazione semplice

Imparare dagli effetti di altri geni può aiutare a prevedere un gene mai osservato.
Per dimostrarlo bisogna nascondere davvero quel gene durante l'addestramento,
anche nei dataset di altre linee: nascondere soltanto una coppia gene-linea non basta.

## 6. Conseguenze

D-044 attiva. Conservare tutti i bersagli delle sorgenti; usare Mixscale come
primo candidato per progettare separazioni fra linee, dopo aver verificato come
sono state stimate le risposte. Richiedere descrittori utilizzabili per bersagli
nuovi, validation distinta dal test e confronti semplici prima della rete.
Nessuna modifica numerica alla produzione, nessun training o invio eseguito.

## 7. Cosa corregge

Precisa l'ambito di CP-0035: le coperture sul pannello non sono criteri di
ammissione alla ricerca; il suo confronto fra linee non è un test su bersagli
mai osservati. Non corregge i numeri né richiede di riscrivere quel checkpoint.

## 8. Domanda di comprensione

Perché togliere un gene dalla sola linea di test non basta a valutarlo come
bersaglio mai visto, se la sua risposta rimane in altre sorgenti di training?
