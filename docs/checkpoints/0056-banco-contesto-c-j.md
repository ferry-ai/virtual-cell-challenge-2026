# CP-0056 — R-LEAD P3: i controlli di una linea mai vista non migliorano il transfer su sette gruppi di linea

- **Data:** 2026-10-03
- **Corse:** 2 ottobre 2026; regola applicata alle 20:04 CEST per C e alle 22:19 per C e J (`written_utc` dei due `decision.json`)
- **Tipo:** esperimento
- **Redatto da:** Claude Code (Opus 5.5), sessione `22d21f`
- **Revisione umana:** no
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Dai soli controlli di una linea mai vista perturbata si può imparare una correzione della risposta che migliori il
transfer dello stesso bersaglio (regime C), o il riferimento senza memoria per bersagli nuovi (regime J)?
Mandato del proprietario in chat (2/10), programma [R-LEAD](../piani/strategia-scientifica.md), D-052.

## 2. Cosa è stato fatto

- **P0** ([report](../../reports/analisi/generalizzazione_contesti_2026-10-02/README.md), `p0_r1/`): preflight
  (scorer `cell_eval2` 0.16.0 con preset `vcc2026` importabile nel venv), 457 input con sha256, matrice contesto ×
  bersaglio × studio su 33 tabelle locali; universo HepG2 ricostruito dalle cellule locali con lo stimatore del t25.
- **P1** (`p1_r1/`): split per gruppi di linea interi (sette: CD4T, HCT116, HEK293T, HepG2, K562, RPE1, iPSC), fold
  per sha256 della chiave Ensembl riconciliata, regimi ricalcolati dopo il QC, esposizioni r2/r3 dai loro prepass,
  storia delle riserve.
- **P2** ([PROTOCOLLO](../../reports/analisi/generalizzazione_contesti_2026-10-02/PROTOCOLLO.md), commit `e60767c`):
  cubo del banco (4.212 bersagli, 10.821 geni), bracci, metriche, regola congelata prima dei dati reali; controllo
  sintetico positivo e negativo; correzioni d'implementazione prima dei risultati (§10, runner v2 `43a1e23`).
- **P3**: corse `p3_c_r2` (C) e `p3_j_r2` (J) nella radice dati, regola applicata da `decide.py`
  (`p3_decision_c_r1/`, `p3_decision_cj_r1/`).

## 3. Cosa si è osservato

Tutti numeri **misurati** su linee già lette in passato (sviluppo), indici sugli effetti, non punteggi VCC.

- **Esito della regola:** `no_benefit` in C e in J ([decisione](../../reports/analisi/generalizzazione_contesti_2026-10-02/p3_decision_cj_r1/decision.json)).
- **C, contesto:** m1 − tm0 = +0,0010 di coseno pesato (bootstrap sui gruppi −0,0015…+0,0045), positivo in 2 gruppi
  su 7; m2 − m2_0 = +0,0037, 3 su 7, con un nullo permutato a +0,0095.
- **C, catena:** tm0 − transfer = +0,057 di coseno in 7 gruppi su 7, MSE relativo da 1,41 a 1,00, PDS da 0,759 a 0,641:
  la regola boccia la regressione di PDS.
- **C, specificità:** m1 con bersagli permutati perde 0,14 di PDS e 0,11 di coseno specifico.
- **J:** il riferimento senza memoria supera il generico di +0,0075 di PDS (6 gruppi su 7); jm1 − jm1_0 = +0,0017,
  5 su 7: non passa.
- **Parità P2** (`p2_parity/`): adattamenti di HepG2 riprodotti a 4,4e-16; stadio 45 e `trial01_cells` scrivono le
  stesse celle bit per bit dagli effetti esportati.
- **Tetto della verità** (`ceiling_r1/`): coseno pesato fra metà indipendenti 0,134 su HepG2, 0,052 su VIPerturb K562.
- Il banco a sei membri su HepG2 non ha dato numeri: fermato alle 20:39 a 4,2 GB di memoria privata.

## 4. Interpretazione e incertezza

- **Interpretazione.** A parità di righe, descrittori e capacità, l'espressione basale della linea nuova non
  aggiunge informazione utile né come guadagno per gene né come interazione di programma a basso rango. La
  calibrazione senza contesto avvicina le previsioni alla risposta comune e paga in discriminazione: lo schema di
  CP-0026, ora su sette linee.
- **Incertezza.** Sette gruppi, con linea, studio e saggio confusi (HCT116/HEK293T stesso studio; HepG2, RPE1 e K562
  della stessa famiglia 3′); unità d'inferenza piccola. La primaria (coseno) premia per costruzione chi reintroduce la
  risposta comune: limite dichiarato dopo i risultati, regola invariata. Nessuna riserva intatta in locale.
- **Ipotesi.** Il limite è il numero di linee collegate e la loro confusione, non la forma del modello.

## 5. Spiegazione semplice

Abbiamo chiesto a modelli semplici di correggere la previsione per una cellula nuova guardando solo come si presenta
a riposo. Su sette tipi cellulari la correzione non aiuta: indovina altrettanto bene se le diamo la cellula sbagliata.
Rendere la previsione più «media» la fa somigliare di più alla verità, ma rende tutte le perturbazioni simili tra loro,
ed è proprio quello che la gara punisce.

## 6. Conseguenze

- Nessuna adozione: il transfer t22/t25 resta il riferimento (PROGETTO §0 invariato nella sostanza).
- P4 motivato dal limite di dati: banco esteso a Jurkat, H1 train/val e neuroni Tian 2021 (somme su Kaggle), e una
  rete non lineare con protocollo congelato ([p4](../../reports/analisi/generalizzazione_contesti_2026-10-02/p4/hypothesis.md));
  un training cellulare GPU richiede prima le correzioni della nota tecnica dell'audit.
- Un nuovo protocollo dovrebbe usare come primaria la parte specifica o il PDS.

## 7. Cosa corregge

Non corregge checkpoint precedenti. Precisa CP-0026 su più contesti: il risultato negativo sul contesto letto dai
controlli si estende da due a sette linee di training, con gemelli riaddestrati e nulli permutati.

## 8. Domanda di comprensione

Perché un modello che alza il coseno con la verità in tutte le sette linee può comunque essere bocciato dalla regola?
