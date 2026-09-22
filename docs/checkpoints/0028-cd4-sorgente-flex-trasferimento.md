# CP-0028 — CD4 adottato come sorgente; la gara è 10x Flex; fra contesti il trasferimento per gene è debole e la discriminazione satura

- **Data:** 2026-09-22
- **Tipo:** esperimento
- **Redatto da:** agente (Claude Opus 5.5)
- **Revisione umana:** no. Mandato del proprietario del 22 settembre: «inizia ad implementare».
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Tre domande:
- CD4 (GSE314342), rinviato da D-031, si può usare come sorgente per i 300 bersagli del
  pannello?
- Quanto trasferisce la risposta dello stesso bersaglio da un tipo cellulare all'altro?
- Con quale saggio sono misurati i dati della gara?

## 2. Cosa è stato fatto

- **Stadio 99** (`scripts/99_context_fingerprints.py`): asse genico ufficiale, confronto di
  piattaforma con i profili NTC di Replogle, impronte genetiche dei controlli A/B/C.
- **Stadio 97** (`scripts/97_extract_cd4_rows.py`, modulo `src/vcc2026/remote_csr.py` con
  test): righe del pseudobulk CD4 da S3 pubblico, lette per intervalli esatti di byte. Il
  file da 44,6 GB ha blocchi non compressi.
- **Stadio 98** (`scripts/98_multisource_effects.py`, modulo `src/vcc2026/multisource.py`
  con test): effetti per bersaglio di K562 genome-wide e delle tre condizioni CD4
  sull'asse ufficiale, poi confronti fra sorgenti. Tre esecuzioni:
  - la prima difettosa, conservata;
  - r2 corretta;
  - r3, che riproduce r2 e salva anche la miscela CD4 grezza.
- **Stadio 101** (`scripts/101_transfer_diagnostics.py`): accordo di segno, ampiezze che
  minimizzano l'errore quadratico, effetto del mescolare le sorgenti.
- **Ricetta t08** (`configs/recipes/t08.json`, stadio 100) con la regola e i due emendamenti
  datati in `reports/multisource_2026-09-22/PRIMA_DEI_RISULTATI.md`. Generazione con lo
  stadio 45, trial `trial-ext-profile`: il generatore di trial-01 invariato.
- **Fonti esterne** lette il 22 settembre:
  - l'annuncio di Arc Institute sulla gara 2026 («CRISPR-interference, 10x Flex single-cell
    profiling»);
  - la scheda 10x del Chromium Human Transcriptome Probe Set v1.0.1: 18.532 geni.

## 3. Cosa si è osservato

**Misurato — il saggio** (`reports/context_fingerprints_2026-09-22/fingerprints.json`).
- L'asse ufficiale ha 18.533 geni; il pannello di sonde Flex v1.0.1 ne ha 18.532.
- Mancano del tutto:
  - i geni RPL/RPS e HLA;
  - XIST, MALAT1 e NEAT1.
- Ci sono 4 LINC, 12 geni MT e 43 simboli istonici di vecchia nomenclatura (H2AFY,
  HIST1H1D).

**Misurato — lo scarto di piattaforma** (stesso file). Pearson su log2(CPM+1), 6.700 geni
in comune:

| coppia | r |
|---|---|
| A–B | 0,622 |
| B–C | 0,662 |
| A–C | 0,429 |
| K562–RPE1 | 0,779 |
| A–K562 | 0,335 |
| B–RPE1 | 0,300 |
| C–RPE1 | 0,355 |

**Misurato — impronte genetiche** (stesso file):
- **A:** maschile; CDKN2A, CDKN2B e MTAP a zero su 18.400 cellule.
- **C:** maschile; 3q +0,26 log2 rispetto alla mediana dei tre contesti.
- **B:**
  - femminile;
  - CDKN2A a 2.437 CPM;
  - 5p +0,95, Xq +0,51, 20p −0,49;
  - 10q distale 0,00;
  - LIN28B assente.

**Misurato — CD4** (`reports/cd4_rows_2026-09-22/manifest.json`, `per_target.csv`):
- 297 bersagli su 300: mancano EEF1A2, EPHB2 e FZD2;
- mediana di 1.478 cellule per bersaglio, decimo percentile 448, 291 bersagli sopra le 100
  cellule;
- 6.477 righe del pannello e 2.400 NTC, 1,33 GiB letti in 880 s;
- ogni riga somma al proprio `total_counts`.

**Misurato — primo run dello stadio 98, difettoso** (`reports/multisource_2026-09-22/`,
radice):
- gli effetti CD4 ristretti valgono zero ovunque (q99 = 0,000). Causa: pavimento
  dell'errore standard sui conteggi sommati;
- la proxy di discriminazione vale 0,500 in molte direzioni, perché venivano confrontati
  bersagli assenti dal predittore.

Nello stesso run il prior normale unico (`sc_effects.eb_shrink`) riduce il knockdown di
HDAC1 in K562 da ln −2,46 a −0,35 (cache del primo run, `processed/multisource_2026-09-22/k562.npz` sotto la radice dati).

**Misurato — run corretto r3** (`reports/multisource_2026-09-22/r3/transfer.json` e
`coverage.json`), bersagli del pannello, geni del pannello esclusi:

| confronto | proxy di discriminazione | correlazione per bersaglio (mediana) |
|---|---|---|
| K562 → CD4 (tre condizioni) | 0,649–0,684 | 0,011–0,014 |
| CD4 miscela → K562 | 0,683–0,691 | 0,013–0,016 |
| CD4 fra condizioni (stessi donatori) | 0,99–1,00 | 0,22–0,47 |
| CD4 fra metà di donatori (Stim48hr) | 0,686–0,698 | 0,04–0,11 |

**Misurato — diagnostiche** (`reports/multisource_2026-09-22/r3_diagnostics/diagnostics.json`):
- **Accordo di segno.** Sui 11.239 geni-bersaglio con |z| > 3 in K562 (268 bersagli), CD4
  ha lo stesso segno nel 55,5% dei casi.
- **Ampiezza che minimizza l'errore quadratico.** Il predittore passa dalla sorgente a una
  verità grezza.
  - Da effetti grezzi: 0,011 (K562 → CD4) e 0,042 (CD4 → K562).
  - Dalla miscela di effetti ristretti: 0,107, con peso K562 0,35.
- **Mescolare non alza la discriminazione.** Metà A → metà B: 0,699; K562 + metà A →
  metà B: 0,694. Metà A → K562: 0,694; metà A + metà B → K562: 0,684.

**Misurato — la regola del t08** (`PRIMA_DEI_RISULTATI.md`, secondo emendamento):
- γ = 1, perché le tre proxy stanno entro 0,005;
- pesi K562 0,433 e CD4 0,567;
- l'ampiezza della regola (0,058) è sostituita da quella di trial-01 (0,197 su effetti grezzi).

Gli effetti costruiti (`processed/effects_t08_2026-09-22/manifest.json`, radice dati):
- 297 bersagli su 300 per contesto;
- mediana di 11.583 geni mossi per bersaglio;
- q99 di |ln fc| pari a 0,115; trial-01 aveva 0,12.

## 4. Interpretazione e incertezza

**Interpretazione, fortemente sostenuta:**
- **I dati della gara sono 10x Flex**: lo dichiara l'organizzatore e l'asse lo conferma.
- **A/B/C si raggruppano per piattaforma, non per lignaggio**: A (T-ALL) somiglia a C
  (squamoso) più che a K562 (leucemia).

Conseguenze pratiche:
- le sorgenti in 3' (Replogle, Nadig) misurano circa 8.000 dei geni dell'asse;
- un banco costruito in 3' misura un regime diverso da quello ufficiale.

**Interpretazione:** per i bersagli del pannello il trasferimento fra tipi cellulari è debole
**gene per gene** (55% di segni concordi sui geni confidenti) ma porta **discriminazione**
(~0,68). Questa satura: aggiungere una sorgente indipendente non la alza. Coerente con un
pannello in cui una parte dei bersagli ha una firma riconoscibile ovunque, e il resto no in
nessun contesto misurato. Il fatto che il PDS ufficiale di trial-01 (0,687) coincida con la
proxy è una coincidenza da non leggere come conferma: sono misure diverse.

**Ipotesi, non misura:**
- la differenza fra condizioni CD4 (0,99, stessi donatori) e metà di donatori (0,70) viene
  da struttura condivisa dai donatori, oppure da effetti specifici del donatore;
- i PDS 0,82–0,87 e le MSE 0,65–0,85 delle prime dieci squadre del 16 settembre richiedono
  sorgenti molto più vicine ai contesti di validazione di K562 e CD4. Candidato ovvio: Orion
  (HCT116, HEK293T, genome-wide, cellule fissate);
- le identità di linea di A/B/C.

**Incertezza:**
- le proxy stanno nello spazio degli effetti del pseudobulk, su geni misurati da entrambe
  le sorgenti;
- la «verità» è una sorgente rumorosa, non un contesto ufficiale;
- il bootstrap non è stato calcolato: differenze di 0,01 nella proxy vanno lette come
  rumore.

## 5. Spiegazione semplice

Abbiamo scaricato, da un grande esperimento su linfociti T umani, la risposta ai knockdown
dei nostri 300 geni. Poi abbiamo chiesto quanto somiglia alla risposta degli stessi geni in
cellule di leucemia (K562).

Riconoscere quale gene è stato spento funziona due volte su tre meglio del caso. Prevedere,
gene per gene, se un altro gene sale o scende funziona appena meglio di una moneta. Mettere
insieme le due fonti non rende il riconoscimento più facile.

In più, i dati della gara sono letti con una tecnologia diversa (sonde su cellule fissate):
somigliano fra loro più di quanto somiglino alle fonti pubbliche che usavamo.

## 6. Conseguenze

- **CD4 è adottato come sorgente per bersaglio, nel pseudobulk.** Per il pannello finale del
  22 ottobre la stessa estrazione richiede circa 15 minuti: non serve scaricare il genoma.
  Registrato come D-039.
- **Il t08 è generato come prova a un solo fattore contro trial-01**: stesso generatore,
  stessa ampiezza, sorgenti K562 + CD4. L'invio aspetta il via del proprietario.
- **Orion (HCT116, HEK293T) è la prossima sorgente da misurare**, con la stessa batteria
  (stadi 98 e 101). Serve una decisione del proprietario sulla licenza CC-BY-NC-SA-4.0
  (D-004 (d)).
- **Lo shrinkage a prior normale unico schiaccia gli effetti forti.** `sc_effects.eb_shrink`
  è quello usato dal termine di trasferimento dello stadio 76 (t02, t03). Da non riusare
  senza misurarne il costo.
- Le ampiezze che minimizzano l'MSE (0,01–0,1) sono molto sotto quella di trial-01 (0,197).
  L'MSE ufficiale è comunque tosata a 0 per noi: l'ampiezza si sceglie sulle metriche di
  direzione e di chiamata, non sull'MSE.

## 7. Cosa corregge

- **Supera la ragione di D-031** per rinviare CD4: gli 1,7 TB sono le cellule singole. Il
  pseudobulk si legge per righe (1,33 GiB per il pannello).
- **Completa** la lettura dei contesti di PROGETTO.md §3 (marcatori) e dello stadio 85 con
  saggio, piattaforma e impronte genetiche. Non la contraddice.
- **Non riproduce** l'errore di import `cell_eval2.config` riportato in
  `reports/direzione_2026-09-19/VERIFICHE.md`. Il 22 settembre l'import funziona e
  `test_components_reproduce_the_scored_fidelity` passa. Il documento resta com'è: vale per
  il giorno in cui è stato scritto.
- Nessun checkpoint precedente è corretto.

## 8. Domanda di comprensione

Perché due fonti che danno il segno giusto solo nel 55% dei geni possono comunque
riconoscere quale gene è stato spento due volte su tre meglio del caso? E perché mediarle non
aiuta a riconoscerlo meglio?
