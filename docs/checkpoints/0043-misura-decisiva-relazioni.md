# CP-0043 — La misura decisiva per la rete relazionale: inconclusiva per W1, e la via delle relazioni non prevede nulla nemmeno nella stessa linea

- **Data:** 2026-09-29
- **Tipo:** osservazione
- **Redatto da:** Claude (Opus 5.5, sessione f2abd9a6)
- **Revisione umana:** no
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Chi si muove con chi (la correlazione fra geni delle risposte su molti bersagli) è più conservato fra linee
dell'effetto del singolo bersaglio? E serve a prevedere la risposta di una linea nuova a un knockdown? È l'azione 6
della scheda [R-REV](../piani/revisione-critica.md) e la prova da cui dipendeva la rete relazionale della scheda
[R-V2](../piani/modello-v2.md), voluta dal proprietario: «spengo x, y si muove perché è legato a x».

## 2. Cosa è stato fatto

- **Protocollo e regola** fissati alle 19:56 del 28/09, prima di qualunque calcolo sugli effetti, e committati in
  `b8ccdef` ([RISULTATI](../../reports/modelli/covariazione_2026-09-28/RISULTATI.md)).
- **Codice** di un sottoagente della sessione, con 21 prove sintetiche.
- **Dove è girato:**
  - la parte A (M1, M2, M3a sulle coppie di linee) su Kaggle CPU, dal dataset della rete r2, fra le 22:51 UTC del
    28/09 e le 00:14 UTC del 29/09;
  - la parte B (calibrazione degli SE, controlli W3–W5, coppie HIPSCI) sul portatile;
  - la combinazione con la regola il 29/09.
- Uscite in [`r1/`](../../reports/modelli/covariazione_2026-09-28/r1/).

## 3. Cosa si è osservato

Tutto in `r1/verdict.json` e `r1/parte_a/`.

- **Verdetto per la regola: inconclusivo.**
  - W1 lascia 3 contesti su 5: CD4 ha una quota di segnale per bersaglio di 0,17, sotto il minimo di 0,20;
    VIPerturb ha troppi pochi bersagli rispondenti.
  - W2 e W4 non si calcolano: le coppie che li servono hanno 8–143 bersagli rispondenti comuni, contro 200.
- **Lettura «uso»: no.** La via delle relazioni (la pendenza di ogni gene sul gene x attraverso gli altri knockdown)
  ha l'intervallo sullo zero:
  - fra linee: K562 +0,003, HCT116 −0,002, KOLF2.1J −0,003;
  - nella stessa linea: −0,004, −0,010, −0,007.
- **L'effetto dello stesso bersaglio** misurato altrove vale +0,090, +0,076 e +0,009. Sommarci le relazioni lo
  peggiora (−0,034 su K562).
- **Lettura «mappa»: inconclusiva.** Mediana di D +0,086 su tre coppie, positiva su due; il segno non regge togliendo
  un contesto.

## 4. Interpretazione e incertezza

- **Misurato:** nei dati pubblici che abbiamo, la forma lineare di «y si muove perché è legato a x» non prevede la
  risposta a un knockdown, nemmeno nella linea in cui si è imparata. Quello che si trasferisce è l'effetto del bersaglio
  stesso.
- **Interpretazione:** la covariazione esiste ed è in parte conservata (ρ_cov 0,16–0,37 fra linee e laboratori
  diversi, 0,55 fra le due Orion), ma non codifica chi muove chi. Co-regolazione non è causalità.
- **Limiti:**
  - la prova è sulla forma lineare più semplice;
  - due contesti su cinque sono usciti per W1;
  - le soglie sono proposte scritte prima, non calibrate;
  - una forma diversa, o molti più dati, potrebbero dire altro, e questa prova non lo esclude.

## 5. Spiegazione semplice

L'idea era: se due geni salgono e scendono insieme in migliaia di esperimenti, allora spegnendo il primo si muoverà
anche il secondo. Si è provato a prevedere così che cosa succede spegnendo un gene, e non funziona, nemmeno nella stessa
linea cellulare. Funziona invece guardare che cosa è successo spegnendo lo stesso gene in un'altra linea.

## 6. Conseguenze

- **Per la regola registrata alle 19:58** la rete relazionale non parte
  ([rete_relazionale](../../reports/modelli/rete_relazionale_2026-09-28/RISULTATI.md)). Codice e autoverifica restano
  nella sua cartella.
- **Il proprietario**, alle 11:25 del 29/09, ha scelto di puntare sulla prova generale del 22 ottobre e sul banco con
  lo scorer vero (azioni 3 e 4 di R-REV).
- La direzione «usare tutti i dati» resta, ma sul canale dello stesso bersaglio: più sorgenti e sorgenti migliori
  per il trasferimento, non relazioni fra geni.

## 7. Cosa corregge

Nessun checkpoint precedente. Toglie la base misurata alla «Proposta per quando si riparte» della scheda R-V2 (punto 2,
disegno della rete relazionale), che resta scritta com'era.

## 8. Domanda di comprensione

Perché un tetto «nella stessa linea» vicino a zero pesa più di un risultato negativo fra linee diverse?
