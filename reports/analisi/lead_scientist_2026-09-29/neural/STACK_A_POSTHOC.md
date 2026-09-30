# Stack A: perdita di specificità nel pilot di sviluppo

**Stato: misurato, analisi post hoc del 29 settembre 2026.** Il risultato non cambia il protocollo A/B, la soglia di promozione o la conferma riservata. Non sono stati letti nuovi outcome HepG2, né i dodici target di riserva. Sono stati letti i CSV già prodotti dallo scorer, le due predizioni A, i controlli pubblici congelati e la lista geni del modello.

Il pilot A fallisce la regola registrata: la proiezione dei cinque membri peggiora di **−0,158321**, con delta PDS **−0,333333**. La componente PDS spiega −0,124179, cioè circa il **78,4%** della perdita nella proiezione. Anche gli altri quattro contributi sono negativi. La MSE ufficiale locale, calcolata come rapporto delle somme, migliora da 1,448774 a 1,303689; rimane sopra 1 e non compensa il fallimento della regola. Questi numeri sono un benchmark locale sui dodici target, non uno score VCC.

La PDS peggiora in otto target, è pari in tre e migliora soltanto per HAUS8 (+0,0909). Le cadute maggiori sono RPL36A (1 → 0), EEF2 (1 → 0,1818), CCDC130 (1 → 0,4545) e DCTN1 (0,6364 → 0,0909). La direction fidelity peggiora in nove target su dodici; la direction reach peggiora in sette, migliora in due, è pari in due e non è eleggibile in uno. La NMAE peggiora in sei dei nove target eleggibili.

## Che cosa mostrano le cellule generate

Per ogni target sono state aggregate le 400 cellule finali e confrontate con gli stessi 2000 controlli reali. L'asse osservato ha **9624 geni**; la parte modificata da Stack, S, ha **5179 geni**. La misura principale qui è la media per gene di `log1p(CPM)` delle singole cellule, meno la stessa media dei controlli. È una diagnostica geometrica, non una ricostruzione dello scorer: non applica tutti i suoi filtri e non usa le espressioni vere dei target.

La componente comune è la media dei dodici vettori risposta; la componente specifica è ogni risposta meno tale media. RMS ed energia sono calcolati uniformemente sui geni indicati, senza scegliere geni dopo gli esiti.

| Diagnostica sui 5179 geni S | Trasferimento | Stack A |
|---|---:|---:|
| RMS della componente comune | 0,15709 | 0,15482 |
| RMS della componente specifica dei target | 0,18128 | 0,12212 |
| Frazione dell'energia nella componente comune | 42,89% | 61,64% |
| Coseno medio fra coppie di risposte | 0,40406 | 0,58540 |
| RMS di rumore stimato dalla differenza fra due metà, riportato alla media di 400 cellule | 0,09180 | 0,09181 |

**Misura:** la componente specifica scende del **32,6%**; la componente comune resta quasi invariata. La somiglianza fra le risposte aumenta mentre il livello di rumore da campionamento resta molto simile. Togliendo i dodici geni bersaglio dalla geometria, il rapporto fra RMS specifici resta 0,6753, contro 0,6737 includendoli. Il fenomeno non è spiegato soltanto dai geni bersaglio stessi.

La stessa direzione emerge da un'altra trasformazione: con `log1p(CPM pooled)`, sui geni S il RMS specifico scende da 0,13934 a 0,09150 (rapporto 0,6567). Fuori da S il RMS specifico resta praticamente uguale: rapporto Stack/trasferimento 0,9967 nella media di `log1p(CPM)` e 0,99993 nel profilo pooled. Questo è coerente con il fallback conservato fuori S; non è un test di uguaglianza delle cellule, perché il campionamento finale può produrre conteggi diversi.

## Interpretazione e limiti

**Interpretazione supportata:** A perde specificità rispetto al trasferimento sui geni che sostituisce. Non osserviamo principalmente una nuova componente comune molto più grande: osserviamo soprattutto una riduzione della componente che distingue i target. Questo è coerente con il peggioramento della PDS e della direction reach, ma non dimostra da solo quale operazione a monte lo causi.

**Ipotesi non dimostrata:** chiamare la componente comune «stress biologico» sarebbe prematuro. Una componente molto simile compare già nel trasferimento. Inoltre, il suo RMS passa da circa 0,155 nella media cellulare logaritmica a 0,054 nel profilo pooled di Stack; pooling, profondità cellulare e trasformazione logaritmica influiscono quindi sulla descrizione. La diversa variabilità fra cellule reali e campionamento Poisson potrebbe contribuire. Non abbiamo isolato causalmente questi fattori o assegnato un programma biologico con annotazioni esterne. I nomi dei trenta geni più grandi sono riportati nel JSON come descrizione, non come arricchimento o etichetta di pathway.

**Ipotesi testata separatamente da B, già congelata prima degli score:** limitare anche i controlli HepG2 all'intersezione con K562 può eliminare informazione di contesto. Questo audit di A non stabilisce se B recupererà specificità. Gli esiti di B e la successiva selezione devono essere letti con la regola A/B invariata. Il fatto che Stack riduca l'errore MSE non autorizza a cambiare ora tale regola o a scegliere un'ampiezza usando questi dodici target.

Il rumore split-half è una stima descrittiva della variabilità delle cellule finali, condizionata al modello, ai prompt, al seed del decoder e ai controlli congelati. Non misura l'incertezza del modello o la variabilità fra seed Stack. Non sono disponibili in A i profili esatti precedenti al campionamento: tutte le nuove misure sono sulle cellule finali. Non si rivendica che HepG2 sia assente dal pretraining.

## Riproducibilità

- Codice: `diagnose_stack_a_failure.py`; test: `test_diagnose_stack_a_failure.py`, **2 PASS**, con righe non contigue, library size diverse e decomposizione comune/specifica.
- Evidenza numerica: `stack_a_failure_r1/analysis.json`, SHA256 `1285cdaa236fd93ca5ac07e1b843eaddfa64e2587c69cbc4e65ab1739e404cb2`; `stack_a_failure_r1/per_target.csv` contiene tutti i membri e le differenze per target.
- Il JSON registra gli SHA effettivamente riletti delle due predizioni, del bundle, della lista geni, dei CSV, della ricevuta finale e del codice. Gli SHA delle predizioni coincidono con quelli usati dallo scorer A: Stack `4baa9e71…`, trasferimento `0210a9ff…`.
- Lettura CSR in blocchi di **64 cellule**; nessuna predizione caricata come AnnData completa. Matrici aggregate 12×9624. `psutil` non è installato: il picco RSS non è stato misurato, quindi non viene dichiarato come verificato.
- Il primo avvio si è fermato sulla lettura sandbox della sola lista geni Drive; il secondo, autorizzato per lettura, è terminato correttamente. Nessun training, inferenza, scoring aggiuntivo, invio o modifica dei candidati è stato eseguito.
