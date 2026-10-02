# P4 di R-LEAD — l'estensione motivata dal banco: più linee collegate, non una rete più grande

Scritto il 2 ottobre 2026 dopo l'esito del regime C (`p3_decision_c_r1/`) e **prima** di qualunque dato
nuovo; il regime J completa la lettura nel §5. Sessione Claude `22d21f`. Tipi: misurato, interpretazione,
ipotesi, proposta.

## 1. Il limite identificato (misurato e interpretazione)

- **Misurato.** Con sei linee di training per fold, nessuna correzione letta dai controlli batte il suo
  gemello senza contesto: M1 +0,0010 di coseno (2 gruppi positivi su 7), M2 +0,0037 (3 su 7). Un nullo
  con i controlli permutati fa +0,0095, più del contesto vero.
- **Misurato.** I coefficienti di contesto di M1 sono stabili fra i fold: guadagno minore sui geni meno
  espressi nella linea nuova e su quelli più espressi che nelle sorgenti. Il modello impara una
  regolarità, ma questa non migliora le linee tenute fuori.
- **Misurato.** L'unico segno di contesto (M2, +0,026 su HepG2 e RPE1) cade su due schermi essenziali
  della stessa famiglia 3′ di K562. Linea, studio e chimica sono confusi.
- **Interpretazione.** Il limite non è la capacità del modello (M2 sceglie già il rango massimo, e i
  nulli lo eguagliano), ma il numero di linee indipendenti e collegate e la loro confusione con saggio
  e studio. Con sei punti per fold un effetto del contesto non si distingue da un'associazione casuale.

## 2. Ipotesi e contrasto

**H-P4a.** Se esiste una correzione della risposta leggibile dall'espressione basale dei controlli, con
almeno nove gruppi di linea collegati la stessa regola congelata la rileva; se non la rileva, questa
forma di contesto è esclusa con più forza.

- **Contrasto:** banco, cubo, bracci e regola invariati (`PROTOCOLLO.json`), gruppi da 7 a 9–10.
  Si riportano insieme la corsa a 7 gruppi (già decisa, invariata) e quella estesa.
- **Linee da aggiungere**, scelte per collegamento e diversità, non per numero di cellule:
  - **Jurkat** (Nadig 2025, CRISPRi, libreria essenziale come HepG2): linfoblasti T, la prima linea
    tumorale ematologica oltre K562;
  - **neuroni da iPSC** (Tian 2021, CRISPRi): un tipo cellulare assente dal banco;
  - **H1** (gara 2025, train e validation): tutti i suoi 200 bersagli sono già in almeno due gruppi del
    banco (misurato); è la linea più vicina al saggio della gara. Il suo test resta la riserva per P5.
- **Smentita:** la regola fallisce anche con 9–10 gruppi, oppure il nullo permutato eguaglia il
  contesto. **Conferma possibile:** passa → P5 sul test H1, mai letto, con le classi C/J ricalcolate.
- **Che cosa non si cambia insieme:** stimatore (`min_expected` 1), soglia di cellule, geni del cubo
  ricalcolati con la stessa regola, bracci, metriche. Il cubo nuovo si scrive in una cartella nuova.

## 3. Perché non un nuovo training adesso (proposta motivata)

Una rete è giustificata da una domanda che i modelli semplici non possono porre. Qui la domanda
«il contesto serve?» non è limitata dalla forma del modello ma dai dati: una rete su sei linee per
fold ha lo stesso problema di identificabilità, con più parametri per adattarsi all'identità della linea.
Le reti già provate (CP-0026, r1–r3, t29) hanno mostrato proprio il collasso verso la risposta comune
che qui si vede anche nei modelli lineari (PDS da 0,76 a 0,64 quando si aggiunge il termine comune).

**Un training diventa giustificato** se, con le linee aggiunte:
1. il contesto passa la regola con M2 e la selezione interna sceglie sistematicamente la capacità
   massima, oppure i residui di M2 sui gruppi tenuti fuori mostrano una struttura non lineare misurabile
   (per esempio un'interazione a soglia sull'espressione dei geni del programma p53, che una funzione
   bilineare non rappresenta); allora la specifica è una rete di correzione del residuo del transfer,
   con gli stessi fold, gli stessi bracci e la stessa regola;
2. oppure J mostra che il riferimento senza memoria discrimina (§5) ma è limitato dalla linearità.

In entrambi i casi la specifica (ipotesi, architettura, dati, split, loss, confronti, regola di
bocciatura) si scrive prima del job, come chiede R-LEAD P4, e il job GPU si propone con il tuo via.

## 4. Che cosa serve, e che cosa è impedito oggi

| Passo | Input minimo | Dimensione | Stato |
|---|---|---|---|
| Jurkat nel banco | `NadigOConner2024_jurkat.h5ad`, scPerturb, Zenodo 13350497 | 1.293.665.804 byte (misura remota del 30/09) | **impedito: serve il via al download**; licenza del record da verificare |
| Neuroni nel banco | `TianKampmann2021_CRISPRi.h5ad`, stesso record | 289.389.479 byte | **impedito: serve il via al download** |
| H1 nel banco | effetti per bersaglio dagli shard `rlab-h1-vcc2025-trainval` (Kaggle, account `davidmaisterx`) | uscita stimata < 0,5 GB | **impedito: serve il via a un job CPU Kaggle** e al download della sua uscita |
| P5 | test H1 2025, bucket Arc | 11.950.739.168 byte | solo se un candidato passa; chiuso fino ad allora |

Il codice esiste già: `hepg2_universe.py` legge file Nadig densi dello stesso formato; il cubo, gli split e
i runner accettano gruppi nuovi senza cambiare i ruoli esistenti (prova di stabilità di P1).

## 5. Lettura del regime J

Da completare con `p3_decision_cj_r1/` quando la corsa J è finita.
