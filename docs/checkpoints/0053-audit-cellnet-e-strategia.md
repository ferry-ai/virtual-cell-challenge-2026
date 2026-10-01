# CP-0053 — Audit cellnet e strategia per un modello competitivo

- **Data:** 2026-10-01
- **Tipo:** cambio-di-strategia
- **Redatto da:** Codex, lead su mandato del proprietario
- **Revisione umana:** no
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Quali bias e difetti stanno limitando il progetto e il training cellulare attuale?
Quale programma può produrre un modello competitivo con evidenza interpretabile?

## 2. Cosa è stato fatto

Revisionati codice e output r2, prepass r5/r7, storico degli invii e fonti primarie.
Sei script nuovi, con output e hash in
[`reports/analisi/lead_audit_2026-10-01/`](../../reports/analisi/lead_audit_2026-10-01/README.md):
analisi degli eval, replay integrale del campionatore, controesempi col codice originale,
lettura in blocchi del file locale HepG2, ricostruzione del pool controlli.
Comandi e verifiche in [VERIFICHE](../../reports/analisi/lead_audit_2026-10-01/VERIFICHE.md).
Nessuna modifica al training concorrente, nessuna apertura di H1 test, nuovo job o invio.

## 3. Cosa si è osservato

- Solo 128 target nascosti comuni fra 1.100 di r5 e 1.142 di r7. Lettura di 145.473 cellule
  HepG2: metà/metà trans mediano 0,373 in C e 0,148 in J; rispettivamente 103,5 e 50,5 cellule
  mediane ([data_r1](../../reports/analisi/lead_audit_2026-10-01/data_r1/data_diagnostics.json)).
- Replay di 50.172 batch con esposizioni esattamente uguali al log: K562 GW riceve il 32,61%
  del coefficiente medio della loss, contro 16,67% a chiavi attive uguali
  ([sampler_r1](../../reports/analisi/lead_audit_2026-10-01/sampler_r1/replay.json)).
- 52 librerie HepG2 hanno almeno 64 controlli nativi, nessuna dopo il cap; tutte le perturbate
  ricorrono quindi al pool fra librerie. Oracolo rete/transfer 0,42862 contro transfer 0,38995,
  non un ensemble ottenibile ([design_r1](../../reports/analisi/lead_audit_2026-10-01/design_r1/design.json)).
- Su C il coseno diagnostico della rete è 0,26565 contro transfer 0,38995; vince nel 38,25%
  dei target. In T, 315/400 gruppi vengono da K562 GW e 268/400 hanno likelihood migliore
  di unknown ma coseno negativo ([r1](../../reports/analisi/lead_audit_2026-10-01/r1/diagnostics.json)).
- Riprodotti unknown senza gradiente, gradiente del basale da sole perturbate e ruolo C
  falso dopo esclusione QC della sorgente del target
  ([controesempi](../../reports/analisi/lead_audit_2026-10-01/counterexamples_r1/counterexamples.json)).
- R3 concluso durante l'audit: solo 20 J valutati in comune con r2; identity collassato.
  Il nuovo controesempio prova che il clamp dei pesi della miscela può spingere il gate
  ulteriormente verso zero anche quando il componente perturbato è migliore
  ([aggiornamento](../../reports/analisi/lead_audit_2026-10-01/AGGIORNAMENTO_R3.md)); non prova
  la causa iniziale del collasso.

## 4. Interpretazione e incertezza

I difetti del disegno sono verificati; quanto ciascuno cambi il punteggio non è misurato.
Le statistiche HepG2 sono post hoc, su asse nativo e con un solo split cellulare, non repliche
biologiche o score VCC. Il rumore differente fra C/J confonde la loro difficoltà; il vantaggio
oracolare motiva un residuo appreso out-of-fold ma non ne dimostra la fattibilità.
R3 rispetto a r2 non identifica l'effetto dei soli dati aggiunti, perché cambia anche il test.

## 5. Spiegazione semplice

Prima di dire che più libri migliorano uno studente, bisogna dargli lo stesso esame.
Qui, aggiungendo dati, cambiano le domande escluse dal training. Inoltre alcune materie
pesano nella loss il doppio di quanto previsto. Correggere esame e pesi rende utile misurare
se una rete più ricca impara davvero biologia trasferibile.

## 6. Conseguenze

D-050 precisa D-044: J per rivendicare generalizzazione congiunta; C e J separati per adottare
un modello competitivo secondo il supporto. Nessuna soglia precedente cambia.
[R-LEAD](../piani/strategia-scientifica.md): correggere banco e controlli, confronti semplici,
transfer con residuo biologico, dati ponte, distribuzioni e conferma indipendente.
[Nota tecnica](../../reports/analisi/lead_audit_2026-10-01/NOTA_TRAINING.md) per il prossimo training;
l'assegnazione R-LAB resta all'agente già attivo.

## 7. Cosa corregge

Nessun punteggio o esito di checkpoint precedente viene corretto. Si precisa per i nuovi
programmi la portata del criterio J di D-044/GENERALIZZAZIONE, mantenendo la dichiarazione
scientifica originale. Si aggiorna AMBITI: HIPSCI è ora entrata nel nuovo training cellulare,
mentre la copertura del 29/09 descriveva il modello precedente. I report storici restano intatti.

## 8. Domanda di comprensione

Perché stesso seme e più dati non bastano a rendere r3 un confronto causale con r2?
