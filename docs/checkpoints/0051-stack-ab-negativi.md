# CP-0051 — Stack A e B non superano il transfer; il ricontrollo numerico chiude la selezione senza candidati

- **Data:** 2026-09-29
- **Tipo:** osservazione
- **Redatto da:** Codex, audit scientifico lead 29 settembre
- **Revisione umana:** no
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Stack migliora il transfer K562 congelato su dodici target development? Conservare
gli input misurati propri di ciascun contesto rende ammissibile la variante B?

## 2. Cosa è stato fatto

Applicato il protocollo prospettico A/B agli stessi prompt, controlli, modelli e
cellule finali. A usa supporto comune negli input, B gli assi propri; entrambi
conservano lo stesso supporto comune in uscita e fallback transfer. Il primo
selettore si è fermato per una differenza numerica nella baseline. Il job085,
congelato da un emendamento operativo, ha ripetuto sequenzialmente i due scoring
con codice e dati identici e thread1; nessuna nuova inferenza o nuova truth.
Il selettore originale è stato rieseguito senza cambiarne le tolleranze.

Procedura, hash e report:
[RISULTATI_STACK_AB.md](../../reports/analisi/lead_scientist_2026-09-29/neural/RISULTATI_STACK_AB.md).

## 3. Cosa si è osservato

**Misurato, indice locale e non VCC:** A delta proiezione −0,1583214825 e delta
PDS −0,3333333333; B rispettivamente −0,1285121072 e −0,2348484848. Entrambi
falliscono D > 0 e PDS >= 0. Tutti i cinque contributi della primaria peggiorano.
MSE migliora (transfer1,448774; A1,303689; B1,333849) ed è riportata separatamente.
Fonti: [A](../../reports/analisi/lead_scientist_2026-09-29/neural/stack_paired_scoring_results_r1/A/pilot_comparison.json),
[B](../../reports/analisi/lead_scientist_2026-09-29/neural/stack_paired_scoring_results_r1/B/pilot_comparison.json).

Il ricontrollo085 termina rc0 alle21:52:28UTC. La baseline A/B è ora identica
byte per byte; D e delta PDS sono esattamente invariati rispetto agli originali.
Il [manifest del selettore](../../reports/analisi/lead_scientist_2026-09-29/neural/stack_ab_selection_r2/selection_manifest.json)
attesta tutte le guardie superate e `selected_variant=null`.

## 4. Interpretazione e incertezza

**Interpretazione:** questa implementazione ibrida non supera il suo riferimento.
B recupera parte del PDS rispetto ad A ma perde ulteriormente NMAE e reach. Non
è una dimostrazione che Stack o tutti i modelli pretrained siano inutili.
Dodici target esplorativi, controlli condivisi, una inferenza per candidato e
pretraining HepG2 non escluso limitano la portata. Le pendenze globali definiscono
un indice, non una conversione esatta in punti VCC. Nessun confronto con t25/t28.

## 5. Spiegazione semplice

Il programma funziona, ma le sue previsioni perdono il confronto fissato. Un
piccolissimo disaccordo numerico aveva bloccato il controllo di identità: risolto
quello, la conclusione scientifica resta la stessa e non passa nessun candidato.

## 6. Conseguenze

Nessuna conferma Stack sulla riserva e nessuna promozione. Il bundle080 pronto
non viene usato per concedere una seconda chance. Nessun nuovo job dopo085
in questa linea. Il registro errori conserva distintamente successo tecnico e
risultato negativo: [E006 r002](../../reports/analisi/lead_scientist_2026-09-29/learning/incidents/E-20260929-006.r002.json).
La riparazione è verificata; l'origine esatta dei11ULP non è attribuita.

## 7. Cosa corregge

Nessuna conclusione scientifica precedente viene ribaltata. Chiude l'attesa della
linea Stack citata in CP-0049 e distingue il fallimento numerico del selettore
dal risultato negativo dei due candidati. I protocolli e i risultati originali
restano immutati.

## 8. Domanda di comprensione

Perché correggere un errore di riproducibilità non costituisce una prova che il
modello migliori, anche quando entrambi gli scoring terminano correttamente?
