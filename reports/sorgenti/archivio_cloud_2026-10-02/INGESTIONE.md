# Ingestione dei dati mancanti nel cloud: flusso, riconciliazione, campionamenti, ruoli, download

2–3 ottobre 2026, Claude Code, sessione `096065`. **Tipo: proposta**, con le misure dei report citati.
Nessun download, nessun job d'ingestione e nessun training sono partiti da questo documento: i nuovi
download (§5) aspettano il via del proprietario. Il flusso del §1 esiste già come codice (corpus R-LAB);
qui diventa la regola per tutto ciò che manca.

## 1. Il flusso: sorgente → runtime cloud → shard verificati → Drive e Kaggle

Nessun byte pesante passa dal portatile. Il codice è quello del corpus
([corpus_cellulare_2026-09-30](../corpus_cellulare_2026-09-30/README.md)): adattatori `h5rows` e
`h5csc_shards` (letture a intervalli di byte con controllo dell'ETag), contratto dello shard, `rlab_job.py`,
`publish_kaggle.py`. I passi:

1. **Spec e preflight sul portatile** (solo metadati): locatore, byte e checksum pubblicati dall'host
   (md5 di Zenodo e Figshare, crc32c del bucket Arc, ETag di S3), licenza, citazione, ruolo del §4. Il
   preflight di [ERRORI](../../../docs/ERRORI.md) gira in locale e poi sul runtime.
2. **Lettura sul runtime Colab** (CPU, la destinazione per questo lavoro secondo `CLAUDE.md`): dallo host
   direttamente al disco del runtime, a intervalli di byte quando il formato lo consente.
3. **Originali immutabili**: quando il file sorgente va conservato, il job lo copia in
   `MyDrive/vcc2026/data/raw/<sorgente>_<data>/` verificando il checksum dell'host sul runtime, con la
   licenza e il record di provenienza accanto. Gli shard non sostituiscono mai l'originale.
4. **Shard nel contratto**, ricevuta per shard, `complete.json` scritto per ultimo, su
   `MyDrive/vcc2026/data/processed/corpus_cellulare_<data>/<job>/`.
5. **Verifica indipendente**: un job Colab su un altro runtime rilegge gli shard da Drive (`verify_drive.py`
   di questa cartella): uno sha256 calcolato dallo stesso runtime che ha scritto può venire dalla sua cache
   (E-20260929-005). Poi `publish_kaggle.py` pubblica un dataset privato per sorgente, in shard, e un
   kernel CPU Kaggle ricalcola gli sha256 sul server (come `kaggle_verify/`).
6. **Catalogo** aggiornato da `complete.json`, ricevute e verifiche, mai dai piani.

Tre stati restano distinti: **acquisito** (shard verificati), **integrato nel banco** (effetti in una
tabella del banco R-LEAD con un ruolo di split), **usato nel training** (righe ammesse nel pre-passo di un
training preciso, dopo QC).

## 2. Riconciliazione del catalogo con i manifest

Fonti: [catalogo r4](../corpus_cellulare_2026-09-30/catalogo_r4/CATALOGO.md) (1/10 16:00),
`complete.json` dei job su Drive, ricevute di pubblicazione, verifica Kaggle del 2/10 (`kaggle_verify/`,
sha256 calcolati sul server Kaggle), fattibilità R-LEAD
([RISULTATI §1](../../analisi/generalizzazione_contesti_2026-10-02/RISULTATI.md)), esiti dei training r1–r3.

| Sorgente | Acquisizione (misurato) | Banco R-LEAD | Training cellulari | Che cosa manca davvero |
|---|---|---|---|---|
| HepG2, Nadig 2025 | J01, `rlab-hepg2-nadig`: 8/8 shard verificati su Kaggle | gruppo HepG2 (development) | r1–r3 | — |
| **Jurkat, Nadig 2025** (GSE264667) | J05, 262.956 cellule, `rlab-jurkat-nadig`: 14/14 | no: nessuna tabella di effetti locale | r1–r3 | gli effetti (somme dagli shard, nel cloud) se il banco li vuole |
| Jurkat GSE249595 | J03, `rlab-jurkat-gse249595`: 97/97 | no | no: il rilascio non ha chiamate delle guide | un'assegnazione delle guide provata |
| H1 2025, train e validation | J04, 320.200 cellule, `rlab-h1-vcc2025-trainval`: 65/65 | no | r1–r3 | il test è la riserva chiusa: non si scarica |
| HIPSCI mirato, 19 linee | J02, 59/59 | gruppo iPSC | r1–r3 | — |
| HIPSCI genome-wide (fitness, non-fitness) | J02, 17/17 e 20/20 | fuori (36 e 12 NTC) | fuori | controlli dichiarati |
| Replogle K562 GWPS | J06 r3, 100/100 | gruppo K562 | r2–r3 | — |
| Replogle K562 essential, RPE1 | J07 r8, 32/32 e 25/25 | gruppi K562 e RPE1 | r2–r3 | — |
| A549 (KO) | J10, 31/31 | fuori (altra modalità) | r3 | — |
| **Tian 2019 e 2021, Norman 2019** | J11, 623.436 cellule, 34/34 | no | r3 | gli effetti, se il banco li vuole |
| KOLF2.1J piccoli e forte | J08 (9/9), J12 (12/12) | KOLF2.1J nel gruppo iPSC, dagli effetti delle somme | r3 | lo schermo pan-genome (2.659.209 cellule) a livello di cellula |
| **scPerturb, terza ondata** | J13–J15: 317.695 + 97.335 + 202.494 = **617.524 cellule**, 17/17, 6/6, 11/11 | no | nessuno | effetti e ruoli (§4) prima di qualunque uso |
| Southard RPE1 e Hs27 (CRISPRa) | **incompleta**: job 125 interrotto con il runtime il 1/10 dopo le 06:29 UTC; su Drive 48 file (3,0 GiB) di RPE1, nessuno di Hs27, nessun `complete.json`, niente su Kaggle | Hs27 solo come effetti dalle somme, fuori (CRISPRa) | no | completare l'ingestione: nuova lettura da Zenodo (§5) |
| CD4, Marson 2025 | effetti dal pseudobulk (`universe_cd4_2026-09-27_me1`) | gruppo CD4T | no | cellule: campione esplicito (§3) |
| Orion HCT116, HEK293T | effetti (`universe_orion_*_me1`) | gruppi HCT116, HEK293T | no | cellule: campione esplicito (§3) |
| VIPerturb (K562, Flex) | effetti dai pool | gruppo K562 | no | cellule da RDS (serve R) |
| **Jiang 2025 = Mixscale** | DE in locale (`external/mixscale_zenodo14518762/`); cellule mai lette | no | no | cellule: oggetti Seurat (§5) |
| DLD-1 GSE337988 | solo effetti (LFC, SE) | no | no | file per cellula da verificare |
| microglia GSE335887, PerturbFate GSE291147 | non acquisiti | no | no | elenco dei file da leggere (solo metadati) |
| Tahoe-100M | controlli DMSO a sottocampione; bracci farmacologici su Kaggle | no | no | i farmaci non prevalgono (decisione del proprietario) |

Tre correzioni al quadro di partenza:
- **Jurkat di Nadig e Tian non sono «acquisiti in parte»**: sono ingeriti per intero, con parità nei
  `complete.json` e copie verificate su Kaggle; mancano solo come tabelle di effetti del banco.
- **La terza ondata scPerturb** è pubblicata con 617.524 cellule (somma verificata dei tre job) e non è in
  nessun training né nel banco.
- **«Jiang 2025, sei linee» e «Mixscale» sono la stessa sorgente**: il probe del 15/09
  (`reports/storico/jiang_2026-09-15/jiang_probe.json`) e la scheda Mixscale puntano allo stesso record
  Zenodo 14518762 (CRISPRi, linee A549, MCF7, HT29, HAP1, BxPC3 e K562, stimoli IFNG, IFNB, INS, TGFB,
  TNFA). Nel catalogo compaiono due volte; le cellule non sono mai state lette.

## 3. Campionamento esplicito di CD4 e Orion

Regola comune: il campione si decide **prima** di leggere i conteggi, solo da metadati e da un hash
deterministico dell'identificativo della cellula (mai dall'esito); per ogni cellula si registra la
probabilità di inclusione π; il manifest del campione (cellule, strati, π, sale) si scrive e si hasha
prima della lettura delle matrici. Le cellule escluse restano contate per strato.

### CD4 (Marson 2025, CRISPRi, Flex)

- **Popolazione misurata** (struttura remota, `../corpus_cellulare_2026-09-30/p1_r4/remote/cd4_*.json`):
  12 file `D{1..4}_{Rest,Stim8hr,Stim48hr}.assigned_guide.h5ad`, 33,6 milioni di cellule, 1.735,8 GB
  (HEAD su S3). In `D1_Rest`: 3.074.496 cellule × 18.130 geni, conteggi interi in CSR; `guide_group` =
  targeting single sgRNA 1.754.014, no sgRNA 794.379, multi sgRNA 526.103; `guide_type` non-targeting
  76.634; 23.256 guide e 12.100 geni bersaglio; 23 `lane_id`; colonna `low_quality`.
- **Strati:** donatore × condizione (il file) × corsia (`lane_id`), con il bersaglio per ID Ensembl.
- **Idonee:** `low_quality == False`; bersagliate con `guide_group == "targeting single sgRNA"`; controlli
  con `guide_type == "non-targeting"` e guida singola. «no sgRNA» e «multi sgRNA» restano fuori dalla
  supervisione, contate.
- **Controlli:** tutti, π = 1, in ogni corsia.
- **Bersagliate:** per (file, guida) le prime `k` cellule nell'ordine di `sha256(sale + barcode)`;
  π = min(1, k / n). Proposta `k = 10`: circa 20 cellule per bersaglio per donatore e condizione,
  ≤ 240 per bersaglio in tutto; stima 3,5–4 milioni di cellule, una ventina di GB di shard (stima di
  2,5 byte per valore non nullo del pilota HepG2; da misurare sul primo file).
- **Costo di lettura (stima):** prima i soli `obs` dei 12 file (pochi GB); poi le righe scelte, che su
  CSR con blocchi da 6.958 valori costano circa 15–20 GB letti per file. È un download (§5).
- **Licenza:** non registrata nella repo per il bucket `genome-scale-tcell-perturb-seq`: da verificare
  prima del via.

### Orion (Xaira X-Atlas, CRISPRi, CC-BY-NC-SA-4.0)

- **Popolazione misurata** ([ORION.md](../universo_2026-09-26/ORION.md)): HCT116 109 file parquet
  (46,6 GB), 3.409.169 cellule con `pass_guide_filter == 1`, 165.777 controlli, 18.293 bersagli; HEK293T
  223 file (79,7 GB), 4.534.299 cellule, 218.838 controlli, 18.311 bersagli. Un file per lotto GEM;
  38.606 token genici, 18.533 sull'asse ufficiale.
- **Strati:** linea × lotto GEM (il file) × bersaglio.
- **Idonee:** `pass_guide_filter == 1`, un solo bersaglio.
- **Controlli:** tutti, π = 1, in ogni lotto.
- **Bersagliate:** tetto `k = 40` cellule per (linea, bersaglio), ripartite fra i lotti in proporzione e
  scelte con l'hash del barcode; π registrata. Stima ≤ 1,5 milioni di bersagliate più 385 mila controlli
  (la mediana è 164 e 211 cellule per bersaglio, quindi il tetto morde quasi ovunque).
- **Costo:** i parquet non sono indicizzati per bersaglio: si legge tutto, 126,3 GB (download, §5).
  Asse nativo conservato, con la mappatura all'asse ufficiale come nello stadio 102.
- **Cautele:** saggio GEM-X 5′ da riverificare sul protocollo primario (AMBITI §4); licenza non
  commerciale ammessa negli invii per decisione del proprietario, verifica esterna ancora aperta
  (PROGETTO §0).

## 4. Ruoli prima dell'integrazione: training, sviluppo, riserva

L'unità d'indipendenza è il **gruppo di linea** (tutti gli studi, stati, donatori, cloni), come nel P1 di
R-LEAD ([split_manifest](../../analisi/generalizzazione_contesti_2026-10-02/p1_r1/split_manifest.json));
una riserva è un insieme di esiti mai letti, letto una volta sola
([reserve_manifest](../../analisi/generalizzazione_contesti_2026-10-02/p1_r1/reserve_manifest.json)).
**Proposta**, da adottare in R-LEAD (proprietaria di P1 e P5) prima di qualunque integrazione:

| Ruolo proposto | Sorgenti | Motivo |
|---|---|---|
| **Training, nei fold congelati del proprio gruppo** | cellule di CD4 (CD4T), Orion (HCT116, HEK293T), KOLF pan-genome (iPSC), Southard RPE1 CRISPRa (RPE1, come modalità separata) | gruppi già nel banco: nuove cellule dello stesso gruppo restano nello stesso ruolo e negli stessi fold per bersaglio; non creano indipendenza |
| **Development** | Jurkat Nadig, H1 train/val, Tian/Norman, A549, terza ondata scPerturb, Southard Hs27 | già visti dai training r1–r3 o di modalità diversa (KO, CRISPRa); utili a P2–P4, non a una conferma |
| **Riserva candidata (da dichiarare)** | MCF7, HT29, HAP1, BxPC3 di Jiang/Mixscale (CRISPRi); microglia GSE335887 | linee mai entrate in un banco né in un training. Per Mixscale i riassunti DE sono stati letti il 24/09 (`pattern_mixscale_2026-09-24`): la riserva vale solo se R-LEAD dichiara quella lettura e la giudica non selettiva |
| **Riserva chiusa** | H1 2025 test; gara D/E/F | il test H1 dopo un fit su H1 train/val **non** è una prova su un contesto nuovo |

Le linee correlate non diventano indipendenti: Xu 2023 HEK293 (terza ondata) appartiene alla famiglia
di HEK293T; Dixit e Norman sono K562 (catalogo r4); Datlinger 2017 usa cellule Jurkat secondo la
pubblicazione (CROP-seq), per il 2021 il contesto va letto negli shard prima di assegnare il ruolo. Il file dei ruoli si scrive con hash e sale
prima del primo job d'integrazione (proposta di nome: `ruoli_ingestione_r1.json` in questa cartella).

## 5. Nuovi download: elenco separato, ciascuno aspetta il via

| Sorgente | File | Byte (metadati pubblici) | Licenza | Che cosa sblocca |
|---|---|---|---|---|
| Southard 2025, completamento | `RPE1_CRISPRa_final_population.h5ad` (Zenodo 15213619), `fibroblast_CRISPRa_final_pop.h5ad` (Zenodo 15200179) | 29,75 GB + 9,72 GB | CC BY 4.0 | finire J09 (RPE1 850.225 e Hs27 447.301 cellule), oggi interrotto |
| KOLF2.1J pan-genome | `KOLF_Pan_Genome_QC_Filtered.h5ad` (Figshare+ 27261219) | 189,39 GB | CC BY 4.0 | 2.659.209 cellule CRISPRi del gruppo iPSC |
| CD4 Marson 2025, campione §3 | `obs` dei 12 `*.assigned_guide.h5ad`, poi le righe scelte | pochi GB, poi circa 15–20 GB letti per file | da verificare | cellule CD4 Flex con donatori e stati |
| Orion, campione §3 | 109 + 223 parquet (Hugging Face `Xaira-Therapeutics/X-Atlas-Orion`) | 126,3 GB letti | CC-BY-NC-SA-4.0 | cellule HCT116 e HEK293T |
| Jiang/Mixscale, cellule | 5 `Seurat_object_*_Perturb_seq.rds` (Zenodo 14518762, md5 pubblicati) | 20,14 GB | CC BY 4.0 | sei linee CRISPRi, quattro mai viste; serve R sul runtime |
| VIPerturb, cellule | `genome_wide_filtered.rds` (+ tre bin) (Zenodo 18460279) | 3,61 GB (+ 10,23 GB) | CC BY 4.0 | cellule K562 in Flex; serve R |
| CD4, pseudobulk originale | `GWCD4i.pseudobulk_merged.h5ad` (S3) | 44,57 GB | da verificare | solo se si sceglie di archiviarlo su Drive rileggendolo da S3 invece di caricarlo dal portatile |
| microglia GSE335887, PerturbFate GSE291147 | elenco dei file GEO | solo metadati | GEO | dimensioni e formato, per decidere |

Non si scarica: **H1 2025 test** (riserva). Su Kaggle i dataset nuovi vanno sull'account con GPU,
`davidmaisterx`, che usa circa 108 GB dei 200 GB di quota privata (dichiarati da Kaggle); quattro dataset
superati da incidenti occupano 30,8 GB e potrebbero liberarsi solo col via del proprietario.
