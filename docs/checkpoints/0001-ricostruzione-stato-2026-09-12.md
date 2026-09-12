# CP-0001 — Ricostruzione dello stato al 12 settembre 2026

- **Data:** 2026-09-12
- **Tipo:** ricostruzione-retrospettiva
- **Redatto da:** agente (Claude Opus 5)
- **Revisione umana:** no
- **Stato:** immutabile

> **Attenzione al tipo.** Fino a oggi il progetto non teneva checkpoint. Questo
> checkpoint non registra un esperimento nuovo: ricostruisce, leggendo gli artefatti
> già presenti nel repository, dove siamo arrivati e quali conclusioni sono state
> corrette lungo il percorso. Le date delle tre fasi vengono dai titoli dei documenti
> e dalla data di modifica dei file, non da un diario tenuto sul momento. Nessun
> risultato scientifico nuovo è stato prodotto qui.

## 1. Domanda

Qual è lo stato reale del progetto, quali affermazioni sono sostenute da misure, e
quali conclusioni precedenti sono state corrette dalle analisi successive?

## 2. Cosa è stato fatto

Lettura e verifica incrociata di tutto il materiale presente: `README.md`, i tre
documenti in `docs/`, i report in `reports/`, i 20 script di analisi in `scripts/`,
`configs/config.yaml`, `configs/candidate_ingestion.json`, e il contenuto della
cartella dati esterna `C:/Users/ferra/vcc2026-data`.

Controlli rifatti in questa sessione, tutti in sola lettura:

- ricalcolo delle coperture da `reports/candidate_verification/panel_coverage.csv`
  (300 righe): 297 in libreria CD4, 293 osservati, 239 con almeno 30 cellule; 300 in
  libreria Orion, 168 osservati nel solo Batch1; 25 bersagli in comune con H1 2025
  (13 Training, 4 Validation, 8 Test);
- elenco diretto di `C:/Users/ferra/vcc2026-data/external/vcc2025/`;
- confronto fra il testo attuale di `scripts/17_extract_scorer_contract.py` e il JSON
  che quello script aveva prodotto, `reports/scorer/vcc2026_contract.json`;
- lettura di `reports/transfer_ceiling/transfer_ceiling.json` per confrontare i numeri
  salvati con quelli citati nei documenti (mediana Pearson K562 genome-wide verso
  RPE1: 0,0905 grezza — coincide).

Nessun dato è stato scaricato, spostato o modificato.

## 3. Cosa si è osservato

**Il compito.** Nessun dato di addestramento fornito. Si ricevono solo i profili
basali di tre contesti anonimi e si devono simulare 300 knockdown CRISPRi in ciascuno.
Costanti in `configs/config.yaml`, formato in `README.md`.

**I controlli ufficiali.** 18.400 cellule × 18.533 geni per contesto, conteggi interi
non negativi, UMI mediani 20.109 / 19.946 / 20.034 per A / B / C. Evidenza:
`reports/data_audit/audit.json`, `reports/candidate_verification/coverage_summary.json`.

**Il pannello dei 300 bersagli è "espresso ovunque, non essenziale".** 288/300
superano 5 CPM in tutti e tre i contesti; i pannelli essential di K562 e di RPE1
contengono 0/300 bersagli, con matching sia per simbolo sia per ENSG. Con 300 geni
estratti a caso fra quelli espressi ci si aspetterebbero circa 33 sovrapposizioni: lo
zero è una scelta di disegno. Evidenza: `docs/revisione_analisi_2026-09-11.md` §2,
`reports/candidate_verification/coverage_summary.json`.

**Chi sono A, B e C.** A è di lignaggio linfoide T (CD3D 939, CD3E 760 CPM medi,
ZAP70, DNTT, RAG1; maschile). B è un ibrido epiteliale-mesenchimale (CLU 7.857,
VIM 6.052, KRT7/8/18; femminile). C è epitelio squamoso (TP63 854, KRT5/13/14/15,
SOX2; maschile). Evidenza: `reports/context_identity/markers.csv`,
`reports/context_identity/context_identity.json`.

**Quanto vale K562, l'unica sorgente locale con copertura del pannello.** Copre
272/300 bersagli e 7.681/18.533 geni di output; il knockdown funziona (270/280 righe
oltre il 50% di abbattimento); ma la risposta trascrizionale stimabile è povera:
**mediana 5 geni differenzialmente espressi per riga**, 37 righe a zero. Evidenza:
`docs/revisione_analisi_2026-09-11.md` §4.

**Il punteggio.** Sei metriche, quattro delle quali misurano direzione o ordinamento.
La MSE normalizzata è bloccata a 0 verso il basso, la NMAE a −6. Verifica numerica
eseguita contro il `cell-eval2 0.16.0` installato:
`reports/candidate_verification/scorer_clamp_check.json`.

**I candidati esterni, misurati e non soltanto citati.**

| Sorgente | In libreria | Osservati | Con almeno 30 cellule | Geni di output in comune |
|---|---:|---:|---:|---:|
| CD4 Zhu/Dann/Marson, D1 Rest | 297/300 | 293 | 239 | 17.772/18.533 |
| Orion HCT116, solo Batch1 | 300/300 | 168 | 0 | 18.106 |
| Nadig Jurkat / HepG2 | — | 0 | 0 | 8.284 / 9.024 |
| Replogle RPE1 | — | 0 | 0 | 8.260 |

Evidenza: `reports/candidate_verification/coverage_summary.json`,
`reports/candidate_verification/panel_coverage.csv`.

**H1 2025 non è in casa.** `C:/Users/ferra/vcc2026-data/external/vcc2025/` contiene
quattro CSV di metadati e nessuna matrice RNA. Verificato in questa sessione.

**La macchina.** 8.384.401.408 byte di RAM totale, circa 28,1 GB di disco libero.
Evidenza: `reports/candidate_verification/hardware.json`. Il solo pseudobulk CD4 pesa
44,6 GB; i dodici oggetti single-cell CD4 sommano 1,736 TB.

**L'unica ingestione realmente eseguita** è un pilota di 64 cellule (32 non-targeting,
16 STAT6, 16 VIM) estratto da remoto: 92.475.050 byte trasferiti per produrre un file
da 1.630.799 byte. Evidenza:
`reports/candidate_verification/pilot/cd4_D1_Rest_64.manifest.json`.

**Nessun modello è stato allenato, nessun punteggio di leaderboard esiste, nessuna
sottomissione è stata inviata.** Gli script esistono e i documenti dichiarano che sono
stati eseguiti, ma eseguire una sonda non è addestrare un modello.

## 4. Interpretazione e incertezza

La forma del problema, come emerge dalle misure, è questa: il pannello sembra scelto
per essere difficile nel modo che rende inutili le scorciatoie. I bersagli sono
espressi ovunque (non si possono ignorare) e non essenziali (gli effetti sono piccoli
per costruzione). La sorgente che copre più bersagli, K562, è del lignaggio sbagliato
per tutti e tre i contesti e contiene pochissimo segnale stimabile. Le sorgenti di
lignaggio più vicino coprono bene la libreria ma hanno poche cellule per bersaglio.

Quanto è solida questa lettura: le coperture e i conteggi di cellule sono **misure**.
L'attribuzione di lignaggio ad A, B e C è un'**interpretazione** basata su marcatori e
su un test di contrasto, non su un riferimento esterno appaiato: identifica un
lignaggio, non una linea cellulare. Che il CD4 primario trasferisca ad A — che porta
anche marcatori T immaturi, DNTT e RAG1 — è un'**ipotesi non testata**.

Resta ignoto il valore dell'ancora di replicato `r` per nmae, mse e jaccard: si
ottiene solo costruendo un bundle di valutazione con dati perturbati reali, che oggi
non abbiamo.

## 5. Spiegazione semplice

Immagina di dover prevedere come cambia il comportamento di tre persone che non hai
mai incontrato, quando togli loro una delle 300 abitudini che hanno. Ti danno solo un
video di come vivono normalmente, senza nessuna perturbazione. Hai un archivio di
esperimenti simili, ma fatti su persone molto diverse da loro.

Le tre scoperte principali finora sono: (1) le 300 abitudini scelte sono quelle che
tutti hanno ma che nessuno considera vitali, quindi toglierle cambia poco e il
cambiamento è difficile da distinguere dal rumore; (2) l'archivio più grande che
possediamo riguarda persone del gruppo sbagliato; (3) il punteggio premia soprattutto
l'azzeccare la **direzione** del cambiamento (sale o scende) più che la sua dimensione
esatta.

Un esempio del punto (3): se dici "questo gene scende un po'" e in realtà scende
molto, perdi poco. Se dici "sale" e invece scende, perdi molto. Questo orienta la
strategia verso decisioni prudenti sull'ampiezza e decise sul segno.

## 6. Conseguenze

- La priorità di acquisizione attuale è CD4 come prima sorgente e Orion HCT116 come
  seconda, con K562 conservato come ablazione: `docs/DECISIONI.md`, D-004 e D-007.
- Il collo di bottiglia dichiarato in `README.md` (fase 1, valutazione locale) è
  **ancora aperto, e ora si sa perché**: manca un bundle di valutazione con dati
  perturbati reali, e H1 2025 non è stato scaricato. Vedi D-003.
- Il vincolo hardware è una decisione registrata, non un dettaglio: nessun atlante
  completo su questa macchina. Vedi D-005.
- La postura di sottomissione "decidere sulla direzione, comprimere l'ampiezza" resta
  **da verificare**, non stabilita. Vedi D-006.

## 7. Cosa corregge

Questo checkpoint non corregge un checkpoint precedente: non ce ne sono. Registra le
correzioni già avvenute fra i tre documenti di strategia, che oggi si possono
ricostruire solo leggendoli tutti e tre nell'ordine giusto.

| Conclusione iniziale | Dove | Correzione successiva | Dove |
|---|---|---|---|
| Priorità di acquisizione: H1, poi KOLF2.1J, poi HIPSCI | `docs/data_strategy_2026-09-11.md` §3 | Sono tutti contesti iPSC/ESC: nessuno corrisponde al lignaggio di A, B o C | `docs/revisione_analisi_2026-09-11.md` §3 |
| Priorità riordinata verso sorgenti di lignaggio affine | `docs/revisione_analisi_2026-09-11.md` §6 | Priorità operativa misurata sulla copertura reale: CD4 (GSE314342) prima, Orion HCT116 seconda | `docs/candidate_adversarial_review_2026-09-12.md` §5 |
| I pseudobulk Replogle non sono usabili a livello di conteggi | `docs/data_strategy_2026-09-11.md` §1 | `X * num_cells_filtered` è intero entro l'1%: i conteggi sono ricostruibili, pur non essendo singole cellule | `docs/revisione_analisi_2026-09-11.md` §2 |
| Lo 0/300 nei pannelli essential potrebbe essere un artefatto di parsing | `docs/data_strategy_2026-09-11.md` §1 | È disegno del pannello, confermato per simbolo e per ENSG | `docs/revisione_analisi_2026-09-11.md` §2 |
| La MSE normalizzata è "downside-free": restringere non costa | `reports/scorer/vcc2026_contract.json`, campo `floor_note` | Il pavimento sta sullo score normalizzato, non sull'errore: restringere può azzerare tutti i punti positivi | `docs/candidate_adversarial_review_2026-09-12.md` §3, e `scripts/17_extract_scorer_contract.py` corretto nel codice |
| H1 2025 è il banco di prova su cui costruire subito P0 | `docs/revisione_analisi_2026-09-11.md` §6 | La cartella locale contiene solo metadati: l'RNA è da acquisire, P0 non parte così | `docs/candidate_adversarial_review_2026-09-12.md` §2 |
| L'intorno di co-espressione negli NTC è una previsione a costo zero della direzione | `docs/revisione_analisi_2026-09-11.md` §6, punto P1 | La co-espressione non è uno stimatore causale del segno: resta un priore debole da testare a parte | `docs/candidate_adversarial_review_2026-09-12.md` §4 |
| Pisces è disponibile; Nadig è un componente di Replogle; il DOI 20022944 è la raccolta processata | `reports/candidate_pdf_extracted.txt` (PDF esterno, non nostro) | Pisces è "Coming Soon"; Nadig è uno studio a sé; il record processato è 20029387 | `docs/candidate_adversarial_review_2026-09-12.md` §1 |

Una contraddizione **non è risolta**: se l'asse genico ufficiale sia ricostruibile in
identificatori Ensembl. Vedi `docs/REGISTRO.md`, scheda R-004.

## 8. Domanda di comprensione

CD4 copre 293 dei 300 bersagli. Perché questo non significa che possiamo stimare 293
effetti? *(Suggerimento: 239 e 147.)*
