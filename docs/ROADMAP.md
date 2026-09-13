# Roadmap — ordinata per valore informativo diviso costo

Aggiornata il 2026-09-13, dopo
[CP-0003](checkpoints/0003-prima-pipeline-e-calibrazione-ampiezza.md),
[CP-0004](checkpoints/0004-primo-trial-locale-e-pacchetti.md) e
[CP-0005](checkpoints/0005-packaging-streaming-trial01.md).

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
