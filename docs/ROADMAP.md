# Roadmap — ordinata per valore informativo diviso costo

Aggiornata il 2026-09-15, dopo
[CP-0003](checkpoints/0003-prima-pipeline-e-calibrazione-ampiezza.md),
[CP-0004](checkpoints/0004-primo-trial-locale-e-pacchetti.md),
[CP-0005](checkpoints/0005-packaging-streaming-trial01.md) e
[CP-0006](checkpoints/0006-prima-sottomissione-e-punteggio.md).

> **L'ordine è cambiato il 15 settembre**, dopo il primo punteggio. La sezione
> «Priorità dal 15 settembre» qui sotto è quella operativa: R-8, R-9 e R-10 sono
> **proposte**, non decisioni, e nessuna richiede un'acquisizione o una sottomissione.
> R-1..R-7 restano validi e non sono stati riscritti.

> **R-0 — chiuso il 13 settembre.** Era: impacchettare le previsioni già generate,
> bloccato perché `vcc prep` chiede 33,5 GiB contro i 7,81 della macchina. Risolto
> senza una macchina più grande: `trial-01-transfer` è un `.vcc` da 3,91 GiB, prodotto
> qui con 0,52 GiB di picco e tutte le convalide attive
> ([CP-0005](checkpoints/0005-packaging-streaming-trial01.md), D-018).
>
> Chiuso anche il resto, il 13 settembre: la sottomissione è stata autorizzata,
> inviata e valutata. **Primo punteggio ufficiale del progetto: 0,045929, rango 446 su
> 920** ([CP-0006](checkpoints/0006-prima-sottomissione-e-punteggio.md)). Solo `pds`
> batte la media del contesto; `fid` è negativa. Il collo di bottiglia torna a essere
> quello di sempre — il **segnale**, non la meccanica — che è ciò di cui si occupano
> R-1 e R-3. `trial-00-controls` resta non inviabile (D-017).

L'ordine non è per dimensione del dataset né per eleganza del modello. È per quanto
ciascun passo **riduce l'incertezza che blocca una decisione**, diviso per quanto costa.
Le incertezze numerate sono quelle di [PROGETTO.md](PROGETTO.md) §4.

Ogni voce dichiara: ipotesi, input, implementazione, dipendenze, risorse, criterio di
successo, artefatto atteso. Un passo senza criterio di successo non è un passo, è un
desiderio.

---

## Priorità dal 15 settembre, dopo il primo punteggio

Il punteggio misurato (0,045929: `pds` 0,413, `mse` 0 al pavimento, `fid` −0,182,
le altre tre indistinguibili da zero — [CP-0006](checkpoints/0006-prima-sottomissione-e-punteggio.md) §3.2)
dice una cosa precisa: **il modello distingue le perturbazioni ma sbaglia ampiezza e
direzione sui singoli geni**. Le tre voci nuove attaccano quella frase, e nessuna delle
tre richiede di scaricare dati nuovi o di consumare quota.

| Ordine | Voce | Costo | Che cosa sblocca |
|---|---|---|---|
| 1 | R-10 ancore `b` e `r` | ore, nessun dato | converte ogni metrica grezza locale in punti di gara |
| 2 | R-9 nullo **generato** | ore di DE, solo dati locali | separa l'artefatto del generatore dal segnale trasferito |
| 3 | R-8 ricentratura sulla baseline | minuti, firme già costruite | spiega perché `mse` e `fid` stanno sotto la baseline |
| 4 | R-1 bundle di valutazione | ~0,9 GB | le sei metriche VCC su effetti **veri** |
| 5 | R-2 calibrazione sulle sei metriche | ore di DE | chiude la metà aperta di D-006 |
| 6 | R-3 CD4, poi R-4 ablation | GB e banda | l'unica copertura del pannello |

## R-8 — Ricentrare la previsione sulla baseline del punteggio

**Perché.** Le nostre calibrazioni misurano l'errore rispetto a «non prevedere nulla»,
cioè al profilo NTC: `pooled_mse_null_zero_response` in
[`calibration_c002.json`](../reports/trial_2026-09-12/calibration_c002.json) è
letteralmente `mean(truth²)`. Lo zero della gara è un'altra cosa — secondo la
specifica ufficiale citata in `README.md` è la **media dei costrutti perturbati**, non
la media dei controlli — e la differenza fra le due origini è la risposta *comune* a
ogni perturbazione. Le nostre firme la contengono (Δ è calcolato contro l'NTC della
sorgente, quindi Δ = comune + specifico) e α = 0,197 la comprime insieme al resto.

**Ipotesi, non misura.** Che comprimere anche la componente comune sia ciò che porta
`mse` sotto la baseline (grezzo 1,231 contro `b` ≈ 0,996 stimato) e `fid` a −0,182, e
che due ampiezze separate — una per la componente comune, una per quella specifica —
battano l'ampiezza unica a parità di tutto il resto.

- **Dipendenza bloccante, e va fatta prima:** verificare la definizione di `b` sulla
  specifica ufficiale e nel codice di `cell-eval2` installato. Se `b` non è la media
  dei costrutti perturbati, questa voce decade. **Oggi è una lettura del README, non
  una nostra misura.**
- **Input:** le firme di `e001` già costruite; nessuna acquisizione.
- **Implementazione:** decomporre per sorgente Δ = c + s con c = media sui bersagli;
  estendere `ShrunkTransfer` con `alpha_common` e `alpha_specific`; in
  `44_calibrate_transfer.py` la griglia resta in forma chiusa, perché l'MSE è
  quadratica in entrambe. Valutare **anche** contro l'origine giusta: l'errore rispetto
  al predittore «c per tutti», non rispetto a zero.
- **Risorse:** lo stadio 44 costa 27,6 s. Due parametri invece di uno non cambiano
  l'ordine di grandezza.
- **Criterio di successo:** su bersagli tenuti fuori, (α_c, α_s) scelti in CV annidata
  battono il predittore «c per tutti» con intervallo bootstrap su bersagli disgiunto.
  **Se non lo battono si registra e si tiene l'ampiezza unica**: vorrà dire che la
  componente comune non trasferisce, che è un risultato.
- **Artefatto:** `reports/pipeline/recentering_<run>.json` + checkpoint.

## R-9 — Il nullo generato: quanto del punteggio è artefatto del generatore

**Perché.** [CP-0004](checkpoints/0004-primo-trial-locale-e-pacchetti.md) §3.8 ha
misurato che le cellule generate rilevano il 4–6% di geni in più dei controlli reali
**a effetto previsto zero**, e il log2FC efficace mediano dopo calibrazione è 0,0246.
Sono quantità dello stesso ordine, e `fid` guarda proprio i geni che la previsione
chiama significativi: se quelle chiamate nascono dal campionamento e non dal segnale,
la loro direzione è casuale e `fid` scende sotto la baseline. È l'incertezza 12 di
[PROGETTO.md](PROGETTO.md) §4, ed è misurabile **senza dati nuovi**.

- **Ipotesi:** che un bundle generato a effetto previsto **zero**, passato allo scorer
  contro i controlli reali, produca già `fid` e `jac` sotto la baseline. Se sì,
  l'artefatto è la causa principale e si corregge nel generatore.
- **Input:** i controlli ufficiali di un contesto; nessuna acquisizione.
- **Implementazione:** variante di `42_null_calibration.py` che, invece di
  ricampionare cellule reali, usa `45_generate_prediction.py` con effetto nullo. Poi
  ripetere con dispersione aumentata e con effetto **sparsificato** (solo i geni con
  |Δ|/SE sopra soglia si muovono), per vedere quale riduce le chiamate spurie.
- **Risorse:** il DE domina — 392 s per 6 perturbazioni con `scanpy`. **Installare
  `pdex` prima** (D-014), è l'intervento con il rapporto beneficio/costo più alto di
  tutta la roadmap.
- **Criterio di successo:** il numero di geni chiamati significativi da un bundle
  generato a effetto zero, misurato, con il confronto contro il nullo reale già in
  [`null_calibration_A.json`](../reports/pipeline/null_calibration_A.json) (Jaccard
  0,000, 5 perturbazioni su 6 escluse per «empty gate»). Una differenza netta fra i due
  è la misura che serve.
- **Artefatto:** `reports/pipeline/generated_null_<run>.json` + checkpoint.

## R-10 — Ancore `b` e `r` dalla classifica pubblica

**Perché.** Senza `b` e `r` ogni misura locale resta in unità che non si confrontano
con la gara. [CP-0006](checkpoints/0006-prima-sottomissione-e-punteggio.md) §3.5 mostra
che la classifica pubblica espone grezzo **e** scalato per ogni squadra e metrica: due
righe con grezzi diversi determinano `b` e `r`. La derivazione preliminare su due righe
per `mse` (`b` ≈ 0,996, `r` ≈ 0,022) riproduce il nostro 1,231 → 0. **Non è una
misura**: è aritmetica su due righe.

- **Ipotesi:** che la formula sia esattamente `(u − b) / (r − b)` con `b` e `r`
  costanti per metrica dentro una partizione.
- **Implementazione:** raccogliere molte righe, stimare (`b`, `r`) per ognuna delle sei
  metriche ai minimi quadrati, e **validare su righe tenute fuori**.
- **Criterio di successo:** su righe non usate per la stima, lo scalato previsto cade
  entro la precisione con cui la pagina mostra i numeri, per tutte e sei le metriche.
  Se una metrica non torna, si registra come non risolta invece di forzarla.
- **Artefatto:** `reports/leaderboard_<data>/anchors.json` + riga di registro. Il file
  **non si sovrascrive**: una classifica è una fotografia datata.
- **Attenzione:** i valori valgono per la partizione `val` e per questo pannello. Sul
  set finale le ancore sono altre.

## Calendario proposto fino al 5 novembre

Proposta, non decisione. Le date fisse sono due: **22 ottobre** (rilascio del set
finale D/E/F) e **5 novembre** (chiusura). La classifica finale dipende **solo** dal
set finale, quindi ogni sottomissione di validazione va trattata come uno strumento di
misura, non come un risultato.

| Finestra | Lavoro | Perché lì |
|---|---|---|
| 15–19 set | R-10, R-9, R-8 | tutto locale: nessun download, nessuna quota |
| 20 set – 1 ott | R-1 e R-2, con `pdex` installato per primo | prima misura sulle metriche vere |
| 2–12 ott | R-3 (CD4), poi R-4 | l'unica copertura del pannello, e l'ablation che la giudica |
| 13–21 ott | congelamento del candidato e **prova cronometrata** del runbook completo | il set finale non è il momento per scoprire un collo di bottiglia |
| 22 ott | esecuzione del runbook su D/E/F | il rilascio |
| 23 ott – 5 nov | iterazioni sul set finale, con budget di quota dichiarato | è l'unica partizione che conta per la classifica |

**Regola di quota, proposta.** Due sottomissioni al giorno, una sola in volo
([SOTTOMISSIONE.md](SOTTOMISSIONE.md) §1). Nessun invio senza (a) una domanda scritta
prima, (b) che cosa cambierebbe nel piano ciascun esito possibile, (c) l'autorizzazione
esplicita del proprietario. La prima sottomissione ha rispettato le tre condizioni;
vanno mantenute anche quando la quota sembra abbondante.

---

## R-1 — Bundle di valutazione a singola cellula (sblocca D-003)

**Perché è primo.** È l'unico passo che trasforma ogni scelta futura da "metrica proxy"
a "metrica VCC". Finché manca, la calibrazione dell'ampiezza è misurata su log2FC
pseudobulk (CP-0003 §3.4) e non sulle sei metriche che assegnano i punti. Costa meno di
un giga.

- **Ipotesi da verificare:** che un sottoinsieme limitato di cellule perturbate reali
  più i loro NTC, in un contesto qualunque, basti a produrre tutte e sei le metriche
  VCC con effetti veri, e a ordinare le baseline fra loro.
- **Input:** mirror scPerturb di Nadig HepG2 (0,851 GB compressi, il più piccolo
  dataset perturbato completo con NTC espliciti: 145.473 × 9.624, 4.976 NTC) oppure
  RPE1 (1,237 GB, 247.914 × 8.749, 11.485 NTC).
- **Implementazione:** estendere `pseudobulk.py` con un lettore a singola cellula
  *backed*; nuovo `48_build_eval_bundle.py` che seleziona bersagli e NTC appaiati per
  batch, scrive il bundle reale con `SubmissionWriter` e riusa `score_bundle`.
- **Dipendenze:** nessuna oltre a quanto esiste. Lo stadio 3 dimostra già che il
  percorso scorer funziona end-to-end.
- **Risorse:** circa 0,9 GB di download; **non** caricare la matrice densa intera
  (HepG2 densa è circa 5,6 GB, RPE1 circa 8,7 GB) — lettura a blocchi obbligatoria.
  Disco locale sufficiente (31,1 GB liberi). Nessuna spesa.
- **Criterio di successo:** tutte e sei le metriche VCC calcolate e **aggregabili** su
  perturbazioni reali (nel nullo l'aggregazione dell'MSE è stata rifiutata: §3.5), con
  almeno 20 bersagli che superano il gate DE. Le baseline si ordinano in modo stabile
  fra fold.
- **Artefatto:** `reports/pipeline/eval_bundle_<sorgente>.json` + checkpoint.
- **Rischio noto:** 0/300 copertura del pannello in entrambe le fonti. Questo bundle
  misura *calibrazione e ordinamento delle baseline*, non copertura del pannello. Non
  va raccontato come benchmark del pannello 2026.

## R-2 — Rifare la calibrazione dell'ampiezza sulle sei metriche VCC

**Perché.** Chiude la metà ancora aperta di D-006. L'α ottimo per l'MSE pseudobulk non
è necessariamente l'α ottimo per un punteggio che pesa anche direzione, Jaccard e PDS.

- **Ipotesi:** che l'α ottimo sulle sei metriche stia nello stesso ordine di grandezza
  di quello misurato in spazio log2FC (0,22–0,47).
- **Input:** il bundle di R-1; le firme già costruite.
- **Implementazione:** griglia α × `prior_sd` valutata con `score_bundle`, con split per
  bersaglio; riusare `41_transfer_experiment.py` sostituendo la funzione obiettivo.
- **Risorse:** dominato dal DE. Con `scanpy` lo stadio 3 ha impiegato circa 6 minuti per
  6 perturbazioni; una griglia da 30 punti su 30 bersagli è dell'ordine delle ore.
  **Installare `pdex` prima** (vedi D-014: cambia i numeri, quindi va fatto una volta
  sola e dichiarato).
- **Criterio di successo:** un α scelto su bersagli tenuti fuori batte α = 1 e α = 0 sul
  punteggio medio delle sei metriche, con un intervallo bootstrap che non contiene
  l'altro.
- **Artefatto:** aggiornamento di D-006 con il numero misurato sulle metriche vere.

## R-3 — CD4: firme di pseudobulk per i bersagli del pannello

**Perché.** È l'unica sorgente con copertura del pannello (297/300 in libreria, 293
osservati) e lignaggio vicino al contesto A. Senza, nessun modello può dire qualcosa
sui 300 bersagli che non venga da K562.

- **Ipotesi:** che le firme CD4 per i bersagli del pannello siano stimabili con
  incertezza utile, e che l'α calibrato da CD4 differisca da quello di K562 — è
  l'incertezza 11 di PROGETTO.md.
- **Input:** righe di pseudobulk CD4 per i bersagli del pannello più gli NTC appaiati
  **per donatore e condizione**; resting e stimulated **mai mescolati**.
- **Implementazione:** `44_ingest_cd4_pseudobulk.py` sul modello di
  `25_ingest_cd4_pilot.py`, con tetto di byte esplicito e manifesto.
- **Dipendenze:** audit delle guide escluse (525.722 righe targeting senza mappatura
  curata, 792.766 senza tipo di guida) **prima** di scalare. Un'esclusione non
  spiegata è una selezione non dichiarata.
- **Risorse:** il file di pseudobulk è 44,57 GB; si estraggono righe selezionate. Il
  pilot ha trasferito 92,5 MB per 64 cellule, cioè circa 1,4 MB per cellula: **non**
  assumere che una frazione piccola implichi un trasferimento piccolo. Stimare con un
  probe prima di fissare il tetto.
- **Criterio di successo:** almeno 239 bersagli del pannello con ≥30 cellule e un
  rapporto |Δ|/SE mediano confrontabile o migliore di K562 (0,795).
- **Artefatto:** `<artifact_root>/<run>/signatures/cd4_*.npz` + riga di registry
  promossa da `pilot_ingested` a `usable`.

## R-4 — Ablation delle sorgenti e pesi misurati

**Perché.** D-007 tiene K562 come ablazione; ora il suo contributo marginale è
quantificato (1,0% di MSE cross-lineage). La domanda vera è se CD4 + K562 batta CD4.

- **Ipotesi:** che pesare le sorgenti per affidabilità misurata batta sceglierne una.
- **Indizio preliminare, da non citare come misura.** Uno smoke test del 2026-09-12 su
  2.013 bersagli comuni a K562 genome-wide, K562 essential e RPE1 dà una Pearson
  mediana di 0,1102 combinando le due sorgenti K562 a peso uguale, contro 0,0919 e
  0,0788 prese singolarmente; l'MSE aggregato resta praticamente invariato (0,3361
  contro 0,3359 e 0,3363, con nullo a 0,3614). **Non è un esperimento calibrato**: α
  era fissato a 0,25, non c'è stato alcuno split per bersaglio e i pesi non sono stati
  scelti su dati tenuti fuori. Serve solo a dire che il meccanismo di combinazione
  gira su dati veri e che l'ipotesi merita l'esperimento vero.
- **Input:** firme CD4 (R-3) e K562; `WeightedTransfer` è già implementato e ha girato
  su dati reali; `LowRankRidge` è implementato e coperto da test, ma **non è ancora
  stato misurato** su dati reali.
- **Criterio di successo:** il modello pesato batte la migliore sorgente singola su
  bersagli tenuti fuori, con intervallo bootstrap disgiunto. **Se non lo batte, si
  registra e si tiene la sorgente singola** — è un esito informativo, non un
  fallimento.
- **Artefatto:** tabella di ablation + aggiornamento di D-007.

## R-5 — Orion HCT116, proiezione dei metadati e acquisizione limitata

**Perché.** 300/300 in libreria, 18.106 geni di output in comune: la copertura di
pannello più ampia dopo CD4. Ma 168 bersagli osservati nel solo Batch1, tutti sotto le
30 cellule: **un solo shard non è copertura**.

- **Dipendenza bloccante:** la licenza CC-BY-NC-SA-4.0 va verificata contro le regole
  della gara **prima** di usarla in una sottomissione (D-004, riapertura d). Registrata,
  non verificata. Questo è un controllo da fare a monte, non a valle.
- **Attenzione tecnica:** `batch_size` non è un tetto di I/O — un row group può forzare
  la lettura di gran parte di uno shard.
- **Criterio di successo:** numero di bersagli del pannello con ≥30 cellule aggregando
  più shard, e costo di traffico per bersaglio misurato.

## R-6 — MCF-7, promotori (controllo indipendente)

Valore: verificare se la specificità di promotore rompe l'assunzione "una guida = un
knockdown di gene". Candidati del pannello RC3H2, SRSF5, UPF3B, da confermare con un
join al disegno originale — l'attuale è parsing provvisorio dei nomi delle guide.
Conservare promotore principale e alternativo distinti. Priorità bassa finché R-1..R-4
non sono chiusi.

## R-7 — Song Jurkat (deconvoluzione high-MOI)

Readout TAP-seq su 374 geni, al massimo ~2,02% degli output VCC; mediana 13 guide per
cellula. Progetto di deconvoluzione a sé, non un corpus a singola perturbazione. Utile
come evidenza ausiliaria sui programmi T, con maschera esplicita sugli altri geni.
Priorità bassa.

---

## Non in roadmap, e perché

| Fonte | Motivo |
|---|---|
| Pisces | Solo `.gitattributes`, LICENSE, README (24.308 byte). "Coming Soon" non è un dataset. |
| Multiome RPE1 (Zenodo) | L'archivio è software; i dati sono FASTQ su SRA. Serve un budget di ricostruzione, non un download. |
| GSE281860 (keratinociti) | Espone conteggi di guide, non la matrice RNA. È l'unica pista squamosa: resta come lead, non come sorgente. |
| Calu-3 | Stato d'infezione è un confondente da modellare; bystander e spike-in WT non sono NTC CRISPRi. Ausiliario a bassa priorità. |
| Atlanti completi in locale | 1,736 TB per CD4 single-cell. D-005. |

## Regola di promozione e scarto

Una fonte sale di livello nel registry solo con l'evidenza che quel livello richiede, e
`src/vcc2026/registry.py` lo verifica. Una fonte entra nel training solo a
`pilot_ingested` o oltre, con `enabled: true`.

Un modello si adotta solo se batte la baseline precedente su **bersagli tenuti fuori**,
con intervallo bootstrap su bersagli disgiunto. Un modello che non batte il nullo si
registra come non adottato e si conserva il risultato: sapere che una strada non porta
da nessuna parte vale quanto sapere che ce ne porta.
