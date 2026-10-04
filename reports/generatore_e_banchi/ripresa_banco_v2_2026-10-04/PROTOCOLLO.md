# D-056 sul banco v2, emissione t28

Tipo: protocollo diagnostico, scritto prima dei nuovi risultati. Reti e selettori restano congelati.
Scopo: misurare il contributo della correzione D-056 con 400 cellule previste per bersaglio,
cinque semi appaiati e l'emissione t28, sulle cinque linee H1, HepG2, RPE1, Jurkat, K562.
Nessun training, scelta del fold da inviare o promozione automatica.

## Precedenti

- **S-009, CP-0064 e CP-0065:** il banco originario usava una baseline diversa dall'invio,
  pochi campioni e un flusso casuale globale. Si confrontano `prod_wR:prod` e `all_wR:all`
  separatamente, con il banco v2 a 400 cellule e cinque semi. La rete resta quella del pilot:
  l'esperimento non corregge retroattivamente la baseline di training.
- **S-006:** una correzione comune può coprire il segnale dei bersagli. Nessuna media
  autorizza a ignorare il PDS della singola linea; si leggono tutti i membri e i grezzi.
- **S-010:** il confronto fra fonti del transfer resta distinto dal contributo neurale:
  i due confronti principali sono appaiati contro la propria baseline.

**Segnale precoce e arresto:** un input diverso dagli hash archiviati, bersagli duplicati,
un target senza geni osservati, un target non C, o mancata parità con correzione zero
invalidano il job prima dello scoring. Un PDS significativamente negativo esclude quella
linea dall'insieme diagnostico favorevole anche se la media dei sei membri aumenta.

## Disegno congelato

Usare `bench_v2.py` del 4/10 senza modificarlo; scorer `cell-eval2==0.16.0`.
400 cellule per target, cinque semi (seme generatore 20260912, indici 0–4), verità e replicato
al seme 2026. Emissione `t28`: effetti ×1,5 e dispersione per gene stimata dai soli controlli.
Quattro bracci: `all`, `all_wR`, `prod`, `prod_wR`. Gli effetti sono quelli delle corsie C
precedenti, esportati in NPZ sull'asse reale; R e w non sono riottimizzati.
La formula, le esclusioni J nelle medie e i pesi sono importati dal codice archiviato.

## Lettura prima dei numeri

Per ogni linea e confronto: media e deviazione standard del delta appaiato sui sei membri,
sui cinque senza JAC e su ciascun membro, grezzi e denominatori compresi. «Risolto» conserva
la convenzione CP-0065: `abs(media) > 2 * sd / sqrt(5)`. È rumore del generatore condizionato
a verità, modello e controlli fissi, non un intervallo sull'incertezza biologica o di training.

Una linea è **favorevole sul banco** solo se il guadagno dei sei membri è risolto positivo,
anche quello senza JAC è risolto positivo, e il PDS non è risolto negativo. Negli altri casi
si specifica quale condizione manca. Si riportano tutte e cinque le linee, comprese le perdite.
Le cinque linee sono già state lette: nessuna nuova conferma indipendente. Non si sceglie il
«miglior fold» come prova di validità sul sito; prima di un invio servono candidato esatto,
guardie all'esportazione, regola propria e autorizzazione del proprietario.

## Esecuzione e copertura

CPU cloud; portatile solo per preparazione e test piccoli. Output distinti per linea.
Nessuna risposta della linea esclusa nel fit, nessuna apertura della riserva H1 test.
Questo è un riesame del pilot a otto gruppi, non il corpus principale completo D-053.
CD4 prosegue separatamente: archivio verificato, aggregati, campioni e uso effettivo nel
training sono requisiti diversi e non si dichiarano soddisfatti da un job concluso.
