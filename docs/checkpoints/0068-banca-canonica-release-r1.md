# CP-0068 — Banca canonica: registro, release r1 a 17 fonti e fit con ricevuta di consumo

- **Data:** 2026-10-07
- **Tipo:** esperimento
- **Redatto da:** Claude Code
- **Revisione umana:** no
- **Stato:** immutabile
- **Strade:** S-010

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Dalla banca persistente già verificata si arriva a un fit reale del transfer, con un solo
ingresso, senza reingestione, e con la prova di quali fonti il fit ha davvero letto? E quali fonti
della banca passano la regola di ammissione scritta prima di guardarle?

## 2. Cosa è stato fatto

Tutto in [banca_canonica_2026-10-07](../../reports/modelli/banca_canonica_2026-10-07/README.md),
ingresso `percorso.py`. Orari letti con `date`, Europe/Rome.

1. Scaricate e verificate contro le ricevute di banca le 67 tabelle `rows.csv` delle 45 unità
   ([manifest](../../reports/modelli/banca_canonica_2026-10-07/rows_r1/state.json)); piano dei
   metadati senza leggere conteggi ([piano](../../reports/modelli/banca_canonica_2026-10-07/piano_r1.json)).
2. [Protocollo](../../reports/modelli/banca_canonica_2026-10-07/PROTOCOLLO.md) con ruoli e regola di
   ammissione, scritto alle 01:35, prima dei lanci.
3. Consumer generale `count_sum → effetti`: adapter e stimatore byte-identici a quelli del consumer
   HIPSCI già verificato, otto prove su banche sintetiche. Dodici derivazioni su Kaggle CPU, sui tre
   account, lanciate dalle 01:39: nessuna ingestione, nessuna matrice scaricata.
4. Regola applicata dal codice alle ricevute
   ([ammissione](../../reports/modelli/banca_canonica_2026-10-07/ammissione_r1.json)); release congelata
   ([release r1](../../reports/modelli/banca_canonica_2026-10-07/fit/release_r1.json)).
5. Fit `davideferrante11/vcc-fit-banca-canonica-r1` (01:57–02:00) e secondo avvio `-r2` sulla
   stessa release: pacchetto del t36 con un driver nuovo, solo stage 100, nessuna generazione.
6. Raccolta la diagnostica HIPSCI lanciata dalla sessione precedente
   ([ricevuta](../../reports/modelli/percorso_riusabile_2026-10-05/hipsci_qc_r1/completion_r1/verification.json)).

## 3. Cosa si è osservato

Tutto **misurato**; i valori stanno nei file citati.

- **Derivazioni.** Dodici job COMPLETE con codice salvato uguale al pacchetto e hash di banca, asse e
  pannello verificati nel runtime. Due primi tentativi (`tian2019_ipsc` r1, `norman2019` r1) fermati
  dalla guardia d'identità prima di ogni stima: banche in copie montabili con altri nomi di file;
  rilanciati cercando i file per contenuto.
- **Ammissione** (mediana del log-rapporto grezzo sul proprio gene, `ammissione_r1.json`):
  Xu 2023 −1,434 (5 bersagli); Tian 2021 CRISPRi −0,478 (6); Tian 2019 neuroni −0,0014 (1, RFK);
  Tian 2019 iPSC +0,049 (1, RFK): non ammessa. HIPSCI mirato: mediana negativa in 19 cloni su 19,
  mediana fra i cloni −1,468 (5 bersagli).
- **K562.** Banca a singola cellula (a+b sommati) contro tabella storica BULK: 272 bersagli comuni,
  coseno mediano degli effetti shrunk 0,994, decimo percentile 0,984 (ricevuta di `k562_gwps_sc`).
- **A549.** Gli otto pool della stima del 27/09 sono il codice di una colonna di lotto modulo 8,
  non donatori; stesse cellule per bersaglio nelle due derivazioni, coseno mediano grezzo 0,940
  ([prova](../../reports/modelli/banca_canonica_2026-10-07/a549_identita_r1.json)).
- **Fit.** 17 fonti attese = verificate per sha256 = lette dallo stage 100; ricetta del t36
  ricostruita con l'hash registrato `3109a6d9…`; effetti diversi dal riferimento su 17 bersagli,
  tutti con un voto nuovo, e su nessun altro; 300 bersagli coperti su 300
  ([consumo](../../reports/modelli/banca_canonica_2026-10-07/fit/r1/completion/consumo.json)).
  Voti per bersaglio: da 2 a 9, 183 bersagli con 5.
- **Riuso.** Secondo fit: stessa release, stesso driver, stesse tabelle, stessi effetti
  (`d7a8cb14…`), nessuna derivazione lanciata fra i due
  ([prova](../../reports/modelli/banca_canonica_2026-10-07/fit/riuso_r2.json)).
- **Registro** ([pagina](../../reports/modelli/banca_canonica_2026-10-07/REGISTRO_FONTI_r1.md)):
  45 unità, 31 studi, 39.973.948 cellule in banca, 395,75 GB grezzi, 38,12 GB di banca e 189,20 GB
  di campioni; 28 unità dietro le fonti lette dal fit, 2.367.170 cellule nelle righe lette.

## 4. Interpretazione e incertezza

**Misura:** il percorso banca → derivazione → release → fit gira da un ingresso e si ripete
identico senza toccare i grezzi; il fit dichiara e verifica ciò che legge.

**Interpretazione:** la banca è riusabile per il transfer. Non è «completa»: 17 unità non arrivano
a nessun trainer. Sette sono KO e due CRISPRa, derivate e tenute fuori dal voto per scelta
dichiarata prima; due sono lo stesso esperimento del K562 che già vota; una non è ammessa; cinque
non sono derivabili con lo stimatore originale (controlli, cellule, etichette).

**Limite della regola.** Tian 2019 neuroni passa alla lettera con −0,0014, che non è evidenza di
knockdown; lo stesso bersaglio nell'altro file di Tian 2019 è a +0,049. Una regola di solo segno
non distingue un effetto nullo quando il bersaglio è uno. Non l'ho spostata dopo la lettura: la
fonte è nella release r1, segnalata, e toglierla è una decisione del proprietario.

**Non misurato:** nessun punteggio, nessuna validazione a linee escluse, nessun confronto di
qualità fra release e t36. I 44 record del catalogo senza banca portano il motivo del catalogo,
non riverificato.

## 5. Spiegazione semplice

Avevamo un magazzino ordinato ma nessuna prova di che cosa la ricetta prendesse dagli scaffali.
Ora la ricetta elenca ogni ingrediente con la sua etichetta, controlla che sia proprio quello,
e alla fine scrive che cosa ha usato. Rifatta una seconda volta senza tornare al mercato, dà lo
stesso piatto. Alcuni scaffali restano chiusi, e c'è scritto perché.

## 6. Conseguenze

L'ingresso operativo per il riuso passa a `banca_canonica_2026-10-07`; RIUSO r3 resta la prova
della release t36. D-053 resta aperto. Nessuna nuova decisione D-NNN e nessun invio: la release r1
non è stata generata né valutata. Decisioni del proprietario: braccio KO nel transfer o no;
Tian 2019 neuroni dentro o fuori; riferimento per HIPSCI genome-wide.

## 7. Cosa corregge

Nessuna misura precedente. Risolve con evidenza due questioni lasciate aperte in
`ESECUZIONE_r14.md`: gli «otto pool donatore» di A549 non sono donatori; HIPSCI mirato, già
corretto da R-026 per `p2`, passa ora anche il controllo del knockdown per clone.

## 8. Domanda di comprensione

Perché la tabella K562 a singola cellula, quasi identica a quella storica, non vota?
