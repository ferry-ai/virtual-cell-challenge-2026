# Un encoder di contesto pre-addestrato su profili basali, innestato nella rete, con l'ablazione dei dati

28 settembre 2026, notte. Scheda [R-V2](../../docs/piani/modello-v2.md), seguito di F10. Autore: claude2 (agent hub,
esecuzione `20260928-014223-v2-context-encoder`), in modalità modifica e **senza poter eseguire codice**: né
l'autoverifica né le corse sono state eseguite. **Proposta e codice, nessuna misura nuova.**

Etichette: **misurato** (lo riporta un file del progetto, citato), **interpretazione**, **ipotesi** (da provare),
**proposta** (una scelta di disegno). Nessun numero qui è un punteggio VCC.

## 0. In breve

- **Che cosa (proposta).** Un encoder che riassume un profilo basale (i controlli di un contesto) in 32 numeri,
  pre-addestrato a ricostruire geni mascherati su molti profili di controllo, con un termine che avvicina i profili
  dello stesso contesto. La rete di [`../rete_contesti_2026-09-27/`](../rete_contesti_2026-09-27/DISEGNO.md) legge
  l'embedding del contesto al posto del suo vettore globale imparato, attraverso una piccola mappa lineare comune.
- **Il confronto (proposta).** Sei condizioni sugli stessi disegni, bersagli di prova e semi: `none` (la rete di
  oggi), `pca`, `ours`, `ours+tahoe`, `ours+scbasecount`, `ours+both`. Disegni: E1 con K562, Orion (HCT116) e CD4
  tenuti fuori, E2 sulla coppia Orion. Per ogni disegno le linee della famiglia tenuta fuori escono anche dai dati
  esterni del pre-addestramento, con liste esplicite (§8).
- **Che cosa decide (proposta, §10).** Solo le previsioni delle perturbazioni nei contesti tenuti fuori: la rete con
  l'embedding contro `none`, contro la sua versione cieca e con lo scambio, contro sé stessa con l'embedding cieco o
  scambiato, e la prova E2. Una ricostruzione migliore dei profili basali non conta.
- **Che cosa ci si aspetta (interpretazione).** Poco o nulla, e va detto prima: la somiglianza basale fra linee non
  ha predetto il trasferimento su Mixscale (§1, punto 4), e con 5–7 contesti CRISPRi per disegno la mappa
  dall'embedding alla risposta si impara da pochissimi punti. Il valore del lavoro è separare, con gli stessi
  controlli, il contributo della descrizione del contesto e quello di ciascuna fonte di dati.
- **Il codice non tocca** `train.py`, `net.py` e `pool.py`: il comportamento di default della rete e la sua
  autoverifica (14 su 14) restano quelli di prima (§5).

## 1. Perché

| # | Evidenza | Fonte | Che cosa ne segue qui |
|---|---|---|---|
| 1 | Misurato: nella corsa di produzione la perdita sulla famiglia `orion` tenuta fuori è minima alla prima valutazione (passo 250) e sale mentre la perdita di training scende; lo stesso nella variante senza partner (minimo al passo 100) | [RISULTATI della rete](../rete_contesti_2026-09-27/RISULTATI.md) | Quello che la rete impara oltre il trasferimento non si porta su una linea nuova. Un'ipotesi: la descrizione del contesto è povera (caratteristiche per gene dei controlli e un vettore globale imparato di 8 numeri) |
| 2 | Misurato: le previsioni per A, B e C della rete di produzione differiscono fra loro dal 42 al 54 % della norma; nulla dice che le differenze siano giuste | idem | La prova deve dire se le differenze fra contesti sono corrette (E2), non solo se esistono |
| 3 | Misurato (riportato dal disegno della rete): un vettore di contesto adattato su due contesti peggiora; la rete condizionata non usa il contesto | [DISEGNO della rete, §1 punto 2](../rete_contesti_2026-09-27/DISEGNO.md) | Nessun parametro libero per contesto: l'embedding viene da un encoder addestrato altrove, e la rete ha solo una mappa lineare comune (264 parametri, §9) |
| 4 | Riportato dal registro, report non riletto qui: la somiglianza basale DepMap fra linee non predice il trasferimento su Mixscale, e pesare per somiglianza peggiora quattro linee su sei | [contesti_2026-09-26](../contesti_2026-09-26/) | Un embedding basale può non contenere ciò che serve alla risposta: è il motivo dei controlli `emb_blind` ed `emb_swap` (§5) e della condizione `pca` |
| 5 | Richiesta del proprietario, 28/09: pre-addestrare un encoder che ricostruisce geni mascherati da profili di controllo; confrontarlo con un encoder dei soli nostri dati; congelato prima, poi facoltativamente rifinito sul CRISPRi; ablazione delle fonti (le previste, + Tahoe, + scBaseCount, entrambe) con stessa architettura e stessa valutazione; nessuna sovrapposizione con i test, studi e famiglie interi separati, le linee tenute fuori escluse anche dal pre-addestramento esterno | assegnazione di questa esecuzione | Tutto il disegno |

## 2. Il formato del corpus (quello che il codice si aspetta)

Un corpus è una fonte o un gruppo di fonti; una condizione di dati è una lista di corpora. Ogni corpus è:

- **`profiles.npz`**
  - `counts`: float32, N × 18.533, conteggi sui geni dell'asse ufficiale nell'ordine di `axis.csv` del dataset
    della rete; **NaN dove la fonte non misura il gene**, mai 0 (D-009);
  - `library`: float64, N, i conteggi totali del profilo su tutti i geni della sua fonte;
  - facoltativi: `profile_id` (controllato contro `meta.csv`), `genes` (controllato contro `--axis`).
- **`meta.csv`**, una riga per profilo nello stesso ordine: `profile_id, source, context, family, study, platform,
  kind, n_cells`, con `kind` in `cells_subset`, `pool`, `donor`, `guide`, `bulk`. Colonne lette se ci sono:
  `cell_line`, `cell_type`, `tissue` (le liste di esclusione le confrontano oltre a `context`), `treatment`
  (registrata, non usata).
- Un argomento `--corpus` è una cartella con i due file, oppure un `.npz` con la tabella accanto (`<nome>.csv`,
  `<nome>_meta.csv`, `<nome>.meta.csv` o `meta.csv`).

Che cosa significano i nomi, e che cosa serve dal lead:
- **`context`** è l'unità che riceve un embedding (la media sui suoi profili) e i cui profili il termine di coerenza
  avvicina. **I contesti della rete e A, B, C devono avere nel corpus lo stesso nome del dataset della rete**
  (`k562`, `cd4_Rest`, `cd4_Stim8hr`, `cd4_Stim48hr`, `orion_hct116`, `orion_hek293t`, `kolf`, `A`, `B`, `C`),
  oppure una tabella `--emb-map` (colonne `network, embedding`). Due fonti descrivono lo stesso contesto solo se
  usano lo stesso nome, maiuscole comprese.
- **`family`** e **`study`**: unità che escono insieme (esclusioni; validazione con `--val-unit study`).
- **`platform`**: l'ingresso di disturbo del decoder (per esempio `flex`, `3prime`, `bulk`, `tahoe`).
- Per le fonti esterne (DepMap, Tahoe, scBaseCount) **`cell_line`, `cell_type` o `tissue` servono** perché le liste
  di esclusione trovino una linea con un nome di contesto diverso dal suo.
- Solo profili di controllo: un profilo `guide` è una guida non mirante; Tahoe solo DMSO (linea e piastra
  conservate); scBaseCount solo campioni umani non trattati, con provenienza verificabile.

## 3. L'encoder (`encoder.py`)

- **Ingresso (proposta).** Per ogni profilo, sui geni del modello (§4): log1p CPM calcolato sui geni che il profilo
  misura (oppure, con `--norm rank`, il rango del gene dentro il profilo: l'opzione robusta alla piattaforma),
  meno la media del gene sui profili di training, diviso la sua deviazione standard (con un minimo), troncato a ±10.
  I geni non misurati o mascherati entrano come 0, cioè la media di training.
- **Architettura (proposta).** MLP 4.096 → 512 → 512 → 32 con LayerNorm, GELU e dropout; un decoder 32 (+ 8 della
  piattaforma) → 512 → 4.096 ricostruisce tutti i geni del modello. La piattaforma entra solo nel decoder, così z
  non ha bisogno di portarla per ricostruire.
- **Obiettivo (proposta).**
  1. ricostruzione dei geni mascherati: si nasconde il 30 % dei geni misurati, e con probabilità 0,3 anche i geni
     che un altro profilo di training non misura (lo schema di un'altra piattaforma); l'errore quadratico conta solo
     sui geni nascosti;
  2. coerenza: un termine contrastivo supervisionato (Khosla et al. 2020) su z normalizzato, peso 0,1,
     temperatura 0,2, che avvicina due profili dello stesso contesto (sottoinsiemi di cellule, pool, piastre, o due
     viste aumentate dello stesso profilo) e allontana gli altri contesti del batch;
  3. sugli ingressi di training, non sui bersagli della ricostruzione, uno scarto per gene log-normale (DS 0,3),
     come `platform_jitter` della rete.
- **Che cosa impara (interpretazione).** Gli assi lungo cui i profili basali covariano nel corpus (linea, proliferazione,
  stress, interferone, p53, per quanto il corpus vari lungo di essi), in una forma stabile fra campioni dello stesso
  contesto.
- **Che cosa non può imparare (interpretazione).**
  - Niente sulle perturbazioni: nessuna risposta entra nell'obiettivo. Se l'embedding aiuta a prevedere le risposte
    lo dicono solo le corse della rete (§10).
  - Effetti di piattaforma o di studio confusi con il contesto: un contesto visto su una sola piattaforma non si
    distingue dalla sua piattaforma.
  - Stati assenti dal corpus: un tipo cellulare nuovo riceve un embedding estrapolato, senza garanzia di senso.
  - L'eterogeneità dentro un contesto: uno pseudobulk non ha struttura per cellula, e l'embedding è la media.
  - Quali differenze basali contano: la ricostruzione pesa gli assi dominanti (dimensione della cellula, carico
    ribosomiale e mitocondriale) qualunque sia il loro legame con le risposte.
  - A valle, la rete impara la mappa dall'embedding al suo vettore di contesto da 5–7 contesti CRISPRi: un embedding
    ricco può fare da identificatore del contesto (il difetto di CP-0013). I controlli lo rivelano, non lo impediscono.

## 4. Il pre-addestramento (`pretrain.py`) e la base PCA (`pca_baseline.py`)

Le due usano la stessa preparazione (`corpus.prepare`), quindi differiscono solo per la mappa dal profilo
all'embedding. In ordine:
1. si leggono le tabelle; si tolgono i profili di altri tipi (`--kinds`) o con meno cellule di `--min-cells`;
2. **si applicano le esclusioni** (contesti, famiglie, studi, nomi di linea; `--exclude-preset` espande le liste
   esplicite del §8) prima di calcolare qualunque cosa;
3. `--require`: i contesti di cui la rete avrà bisogno devono esserci; `--expect-excluded`: i contesti tenuti fuori
   dal disegno devono esserci **e** uscire per intero. Entrambi falliscono in modo esplicito: un nome sbagliato non
   può spegnere un'esclusione in silenzio;
4. validazione: il 10 % dei contesti né esclusi né richiesti, estratti con il seme (interi contesti, o studi con
   `--val-unit study`);
5. **geni**: sui corpora di riferimento (i primi `--reference-corpora`, cioè i nostri), dopo le esclusioni: misurati
   in almeno il 90 % del peso, CPM medio ≥ 1, poi i 4.096 con la varianza pesata di log1p CPM più alta. Ogni
   condizione di dati dello stesso disegno riceve gli **stessi geni**: il confronto fra fonti non cambia il supporto;
6. CPM, log1p (o ranghi), medie e deviazioni per gene **dai soli profili di training**, ciascuno pesato con la
   probabilità del suo contesto; i contesti sono estratti con massa uguale per studio (`--balance study`), uguale
   dentro lo studio, così una fonte grande (DepMap, scBaseCount) non schiaccia le altre.

L'encoder si addestra a batch di 64 contesti diversi × 2 viste, AdamW 1e-3, al più 20.000 passi, arresto dopo 10
valutazioni senza miglioramento della ricostruzione sui contesti di validazione (maschere fisse). Poi **ogni** profilo
è incorporato, anche gli esclusi (un contesto tenuto fuori ha bisogno del suo embedding: è inferenza, come in gara), e
l'embedding di un contesto è la media sui suoi profili.

La base PCA: le prime 32 componenti dei profili di training standardizzati (pesati come sopra; un gene non misurato
vale la media); le coordinate di ogni profilo per minimi quadrati sui geni che misura.

Uscite (cartella nuova): `context_embeddings.npz` (`contexts`, `embeddings`, `n_profiles`, `status` = train, val,
excluded o partial, e gli embedding dei singoli profili), `encoder.pt` (o `pca_model.npz`), `manifest.json` (corpora
con byte e sha256, esclusioni con ciò che ciascun nome ha tolto, geni, curve di perdita, ricostruzione sui profili
tenuti fuori contro la media, geometria degli embedding), `history.csv`, `genes.txt`, `log.txt`. La ricostruzione
sui contesti esclusi è riportata e non entra in nessuna scelta.

## 5. L'innesto nella rete (`train_emb.py`, congelato)

- **Nessun file della rete è modificato.** `train_emb.py` sostituisce, solo quando riceve `--context-embeddings` o
  `--finetune-encoder`, i costruttori che `train.py` chiama (`pool.Phase`, `net.PerturbNet`, `train.net_config`) con
  sottoclassi, e avvolge `predict_arms` e `write_predictions`. Disegno, addestramento, validazione, previsione e
  diagnostica restano il codice di `train.py`. Senza i due flag è `train.py` (chiama `run_design` e basta). La
  condizione `none` gira con `train.py` stesso.
- **Il vettore di contesto (proposta).** In `net.py` il tronco di ogni riga legge u_c = MLP(media degli embedding
  dei geni pesata da `drank`). Qui u_c = tanh(W e_c + b), con e_c l'embedding del contesto standardizzato e W una
  mappa lineare comune 32 → 8 (264 parametri). Con `--emb-mode add` il vettore imparato resta e i due si
  concatenano. Tutto il resto è la rete: caratteristiche per gene dei controlli, cancelli, percorso del trasferimento.
  All'inizio la testa è a zero, quindi la rete parte comunque dal trasferimento calibrato.
- **Standardizzazione dai soli contesti visibili della fase:** e_c = (x_c − x_ref)/s, con x_ref la media degli
  embedding dei contesti visibili di training (`--emb-blind families`: media sulle famiglie delle medie di famiglia)
  e s la radice dello scarto quadratico medio attorno a x_ref. L'embedding cieco è quindi esattamente 0, e nulla dei
  contesti tenuti fuori entra nelle costanti (lo controlla l'autoverifica, punto 9).
- **Controlli dallo stesso modello:**
  - `blind`: caratteristiche del profilo medio di training ed embedding cieco (il cieco di `train.py`, ora completo);
  - `swap`: caratteristiche ed embedding di un altro contesto (lo scambio di `train.py`);
  - `emb_blind`: le caratteristiche vere della riga con l'embedding cieco: **quanto aggiunge l'embedding**;
  - `emb_swap`: le caratteristiche vere con l'embedding del contesto di scambio: **se serve l'embedding giusto**.
  I due nuovi entrano in `metrics.json` (contrasti `net-emb_blind`, `net-emb_swap`, ed E2) e in
  `predemb_<contesto>.npz` accanto a `pred_<contesto>.npz`.
- **Contesti assenti: errore esplicito.** Prima di addestrare, per ogni contesto che il disegno legge (visibili,
  verità, scambio, `--predict-contexts`); nel passaggio in avanti, per ogni riga senza embedding. Se il manifest
  dell'encoder elenca i contesti esclusi dal pre-addestramento, ogni contesto tenuto fuori dal disegno deve esserci;
  altrimenti la corsa si rifiuta (`--allow-seen-contexts` solo per usi trasduttivi dichiarati, come la produzione).

## 6. Fine-tuning (facoltativo, secondo passo)

`--finetune-encoder DIR --finetune-corpus C …`: l'encoder di `pretrain.py` con la sua normalizzazione; l'embedding di
un contesto è la media dell'encoder sui suoi profili di controllo (al più 32, nell'ordine del corpus), ricalcolata a
ogni passo con i gradienti della perdita CRISPRi. I pesi pre-addestrati restano congelati; scostamenti addestrabili
partono da 0 ed entrano come w0 + 0,1 × δ (`--finetune-scale`): con Adam l'encoder si muove dieci volte più piano
della rete, e il decadimento dei pesi lo riporta verso w0. Le costanti di standardizzazione vengono dall'encoder
pre-addestrato sui contesti visibili. Parametri addestrabili: 2.828.130 (§9). Rischio (interpretazione): con 5–7
contesti di training un encoder addestrabile impara ancora più facilmente a riconoscere il contesto; è una variante
da leggere solo se l'encoder congelato passa.

## 7. Regole contro le fughe

1. **Nessun esito perturbativo** entra nel pre-addestramento: solo profili di controllo (§2).
2. **La famiglia tenuta fuori esce dal pre-addestramento, da tutte le fonti**: per nome di famiglia e per le liste
   di linee del §8, applicate a ogni corpus, nostri compresi (i controlli K562 di Replogle, il K562 di VIPerturb-seq
   in Flex, il K562 di DepMap, di Tahoe o di scBaseCount escono tutti dal disegno K562).
3. **Prima di tutto:** gli esclusi non entrano nella scelta dei geni, nelle statistiche di normalizzazione, nella
   validazione né nell'addestramento. L'autoverifica lo prova sovrascrivendoli con rumore: pesi, geni, statistiche e
   embedding degli altri profili restano identici al bit (punto 3).
4. **I controlli del contesto tenuto fuori sono un ingresso**, come in gara (GENERALIZZAZIONE §3, punto 3):
   l'encoder addestrato senza di loro li incorpora solo alla fine.
5. **Studi e famiglie interi:** la validazione dell'encoder estrae contesti interi (o studi interi); la rete tiene
   fuori famiglie intere (`--hold-out-mode family`).
6. **La rete** standardizza gli embedding sui soli contesti visibili; il cieco è la loro media.
7. **Controllo incrociato:** `train_emb.py` rifiuta un encoder che non abbia escluso i contesti tenuti fuori dal
   disegno (dal suo `manifest.json`); `pretrain.py --expect-excluded` rifiuta esclusioni che non trovano il contesto.
8. **A, B, C** restano nel pre-addestramento dei disegni E1/E2: sono controlli dati dalla gara e non sono contesti di
   prova di questi disegni. Nella produzione (previsione di A, B, C) l'encoder può usare tutti i dati: è un uso
   trasduttivo, e questi disegni non lo misurano (§13).
9. **Stessi bersagli di prova e stessi semi** in ogni condizione: gli argomenti di `train.py` sono identici fra le
   condizioni di un disegno; `compare.py` si ferma se i bersagli di prova differiscono.

## 8. Le liste di esclusione esplicite (`corpus.PRESETS`)

Un nome è confrontato in maiuscolo, ridotto a lettere e cifre, con i campi `context`, `cell_line`, `cell_type`,
`tissue`; un modello di quattro o più caratteri vale anche dentro un campo (`HCT116` trova `orion_hct116` e
`HCT 116`), uno più corto solo come campo intero o come parola (`CD4` trova `cd4_Rest` e `CD4-positive, alpha-beta T
cell`, non `CD40LG`). Le liste sono larghe di proposito: un falso positivo toglie dati, un falso negativo è una
fuga. Il manifest elenca, per ogni modello, i contesti che ha tolto (`pattern_hits`): va letto (per esempio `TCELL`
toglie anche `mast cell` e `fat cell`).

| Gruppo | Disegni | Famiglie | Nomi |
|---|---|---|---|
| `k562` | `e1_k562` | `k562` | K562 |
| `orion` | `e1_orion`, `e2_orion` | `orion` | HCT116; HEK293, 293T, 293FT, HEKTE, HEK (HEK293T e derivati) |
| `cd4` | `e1_cd4` (e `e2_cd4`) | `cd4` | CD4, CD4POSITIVE, TCELL, THELPER, TREG, TH1, TH2, TH17; PBMC, PERIPHERALBLOODMONONUCLEAR, WHOLEBLOOD, LYMPHOCYTE, LYMPHNODE, THYMUS, THYMOCYTE, SPLEEN, TONSIL; linee T: JURKAT, HUT78, HUT102, MOLT4, MOLT3, CCRFCEM, CEM, SUPT1, HPBALL, CUTLL1, LOUCY, DND41, KOPTK1, RPMI8402, ALLSIL, KARPAS45, MYLA, HH |
| `ipsc` | `e1_kolf` (facoltativo) | `kolf`, `hipsci` | KOLF, HIPSCI, HPSI, IPSC, IPS, HIPS, ESC, HESC, EMBRYONICSTEM, PLURIPOTENT, H1, H9, WTC11, WA01, WA09 |

Scelte da confermare (proposta): per CD4 escono tutte le cellule T, i campioni di sangue e di tessuto linfoide che
le contengono e le linee di leucemia T; per le iPSC escono anche le staminali embrionali. Sono le versioni strette
della richiesta «per dichiarare la generalizzazione a linee mai viste»; allentarle è una decisione del lead.

## 9. Il confronto, le corse e il budget

**Condizioni** (`make_runs.py`): `none` (la rete di oggi, `train.py`), `pca` (PCA dei nostri), `ours` (encoder sui
nostri: controlli degli universi CRISPRi, A/B/C, DepMap), `ours+tahoe`, `ours+scbasecount`, `ours+both`; facoltative
`pca+both` e `ours-ft` (fine-tuning dell'encoder `ours`). **Disegni:** `e1_k562`, `e1_orion` (verità HCT116,
famiglia Orion fuori), `e1_cd4` (verità `cd4_Rest`, famiglia CD4 fuori), `e2_orion` (HCT116 e HEK293T fuori
insieme); facoltativi `e1_kolf` ed `e2_cd4`. **Semi:** 0, 1, 2; un encoder per seme (seme dell'encoder = seme della
rete), così i tre semi portano entrambe le varianze. `e1_orion` ed `e2_orion` condividono gli encoder (stessa
famiglia fuori). Gli argomenti della rete sono quelli di default di r1.

**Corse** (calcolato su `make_runs.py` con i default):

| | Sessione 0 (gruppo `orion`) | Sessione 1 (gruppi `k562`, `cd4`) | Totale |
|---|---|---|---|
| PCA (CPU, numpy) | 1 | 2 | 3 |
| encoder (`pretrain.py`, GPU) | 12 | 24 | 36 |
| rete (`train.py` / `train_emb.py`, GPU) | 36 | 36 | 72 |
| confronto (`compare.py`, CPU) | 1 | 1 | 2 |

Le sessioni non condividono il disco: ognuna pre-addestra ciò che le sue corse leggono. Dentro una sessione l'ordine
è PCA, poi seme per seme encoder e reti (`none` prima): una sessione interrotta lascia confronti completi per i primi
semi, e `run_list.py` riprende da dove si era fermato (una corsa fatta ha il suo file `done`; una fallita resta come
`<cartella>.failed<n>`).

**Passi.** Rete: al più 20.000 per fase, con arresto dopo 8 valutazioni ogni 250 passi senza miglioramento (la corsa
di produzione si è fermata al passo 2.250, misurato). Encoder: al più 20.000, arresto dopo 10 valutazioni ogni 250.
Il costo misurato di riferimento è quello di [RISULTATI](../rete_contesti_2026-09-27/RISULTATI.md) (0,22 s per passo
della rete su GPU); `run_list.py` scrive i secondi di ogni corsa in `status.jsonl` per il budget successivo.

**Parametri** (calcolato sul codice con i default; la rete con la configurazione di r1, 12.477 geni conservati):

| Modello | Parametri addestrabili | Byte in float32 |
|---|---|---|
| encoder (4.096 geni, 512, 32; 5 piattaforme) | 4.501.072 (encoder 2.378.784, decoder 2.122.240, piattaforme 48) | 18.004.288 |
| rete `none` | 450.402 (misurato, `prod_r1/config.json`) | 1.801.608 |
| rete con embedding, `replace` | 449.346 (−1.320 del vettore imparato, +264 della mappa) | 1.797.384 |
| rete con embedding, `add` | 451.706 | 1.806.824 |
| rete con fine-tuning | 2.828.130 (+ 4.501.072 congelati nel checkpoint) | 11.312.520 addestrabili |

**Memoria e disco** (calcolato; «prima della compressione» dove c'è):
- dataset della rete `rete_contesti_r1`: 6.883.277.418 byte (misurato, `prod_r1/config.json`);
- corpus: 74.140 byte per profilo (conteggi float32 su 18.533 geni + la libreria), 741.400.000 byte ogni 10.000
  profili; in memoria durante il pre-addestramento 36.864 byte per profilo (4.096 geni: CPM, valori standardizzati,
  maschera);
- GPU della rete: i profili di famiglia e dei partner in float16, 2.216.963.268 byte nella fase 2 di produzione
  (50.496 + 38.346 righe × 12.477 geni × 2 byte, righe misurate nel job 053); i disegni E1 ne hanno meno. L'encoder
  in addestramento con AdamW: circa 72 MB. T4 e P100 hanno 16 GB (il T4 del job 053: 15.360 MiB, misurato);
- uscite di una corsa di rete per contesto di verità: `pred_*.npz` 370.660.000 byte e `predemb_*.npz` 148.264.000
  byte prima della compressione (1.000 bersagli × 18.533 geni × 4 byte per braccio); in tutto 26.687.520.000 byte per
  la sessione 0 e 17.791.680.000 per la sessione 1. Per questo le cartelle delle corse vanno su un disco di lavoro
  (`--work`) e nella cartella conservata (`--keep`) finiscono solo i file piccoli e le previsioni mediate sui semi
  di `compare.py` (8.895.840.000 byte per la sessione 0, 5.930.560.000 per la 1; la metà con `--averaged-dtype
  float16`). Il limite di 20 GB dell'uscita di Kaggle è un ricordo, non verificato.

## 10. Che cosa conta come successo o fallimento (regola proposta, da registrare prima delle corse)

**Misura.** `compare.py`, nello spazio degli effetti, con le formule di `train.py` (verificate contro `metrics.json`
dall'autoverifica): skill = 1 − Σ MSE pesato / Σ MSE del predire 0; contrasto a − b = media sui bersagli di
(MSE_b − MSE_a)/MSE_0 medio, intervallo bootstrap appaiato al 95 %, su tutti i bersagli e sullo strato forte. Le
previsioni sono **mediate sui tre semi** come in r1. Il proxy di r1 (`score_pred.py`, Δ combinato) si calcola sulle
cartelle mediate per la condizione migliore, come conferma; da solo non decide qui.

**Regola, per ogni condizione X contro `none`** (e, per attribuire il merito, `ours` contro `pca` e ogni `ours+…`
contro `ours`):
1. **E1:** X − `none` positivo su almeno 2 delle 3 verità (K562, HCT116, CD4 a riposo), con l'intervallo sopra zero
   su almeno una, e nessun intervallo interamente sotto −0,002;
2. **l'embedding è ciò che aiuta:** rete − `emb_blind` positivo su almeno 2 verità su 3, con l'intervallo sopra zero
   su almeno una; lo stesso per rete − `emb_swap` (serve l'embedding del contesto giusto, non uno qualunque);
3. **E2 (Orion):** la correlazione media della rete X fra differenza prevista e osservata ha l'intervallo sopra zero
   e supera il 97,5° percentile delle permutazioni, e la differenza appaiata con `none` è positiva;
4. **semi:** il segno di X − `none` è lo stesso nei tre semi su almeno 2 verità su 3.
`compare.py` legge la regola in modo meccanico (`readout.csv`); vincola solo quando il lead la registra, con l'ora,
prima delle corse.

**Letture.**
- Passano 1–4 per `ours`: prima prova interna che una descrizione del contesto pre-addestrata su controlli migliora
  le previsioni su linee nuove, e che il guadagno passa dall'embedding giusto. Candidato per il banco del pannello
  e per HepG2 con lo scorer vero, ciascuno con una regola sua.
- Passa 1 ma non 2: il guadagno non viene dall'embedding (inizializzazione, ottimizzazione, caso); niente merito
  all'encoder.
- Passano 1 e 2 ma non 3: l'embedding sposta l'ampiezza media, non le differenze fra contesti.
- `ours+tahoe`, `ours+scbasecount` o `ours+both` passano contro `ours`: i dati aggiunti portano qualcosa alla rete, non
  solo alla ricostruzione. Se passa solo `ours+both`, è un'ipotesi da replicare, non l'attribuzione a una fonte.
- `ours` non batte `pca`: l'encoder non vale più di una proiezione lineare dello stesso corpus.

**Falsificherebbe il valore dell'encoder** (proposta):
1. X − `none` ≤ 0, o con l'intervallo che contiene zero, su almeno due verità E1;
2. rete − `emb_blind` ≈ 0: la rete non usa l'embedding;
3. rete − `emb_blind` > 0 ma rete − `emb_swap` ≈ 0: conta la forma, non il contesto;
4. E2 alla pari con le permutazioni;
5. segni diversi fra i semi;
6. un vantaggio solo nello strato forte: ipotesi da replicare, non adozione;
7. una ricostruzione dei profili migliore senza nessuno dei punti 1–4: non è un risultato per la rete.

Descrittivo, non decide: la curva di validazione (la perdita sulla famiglia di validazione sale ancora dalla prima
valutazione? `per_run.csv`, colonna `best_at_first`).

## 11. Autoverifica (`train_emb.py --selftest`, CPU, nessun file tenuto)

Un mondo sintetico dove ogni contesto ha uno stato latente in due dimensioni che forma i suoi profili basali
(attraverso molti geni, con rumore per gene, due piattaforme con scarti per gene) e, nel mondo «piantato», l'ampiezza
della risposta: exp(0,7 s₁ + 0,7 a_t s₂) θ_t, con a_t = ±1 una proprietà del bersaglio visibile come prior. Nel mondo
nullo l'ampiezza è 1. La coppia tenuta fuori (c12, c13, stessa famiglia, stati lontani) ha due alias esterni con altri
nomi. Controlli, una riga ciascuno, uscita 1 se uno fallisce:
1. il corpus si rilegge identico nelle due forme di argomento;
2. escono esattamente la coppia tenuta fuori e i suoi due alias; `--require` e `--expect-excluded` sbagliati
   falliscono;
3. **canarino del pre-addestramento:** con i profili esclusi sovrascritti da rumore, geni, statistiche, validazione,
   pesi addestrati ed embedding degli altri profili restano identici al bit (un thread);
4. l'encoder ritrova lo stato latente sui contesti di validazione ed esclusi (R² medio ≥ 0,5 di una mappa lineare
   adattata sui contesti di training);
5. la PCA scrive lo stesso formato e ritrova anch'essa lo stato (R² medio ≥ 0,5);
6. i profili di uno stesso contesto stanno insieme (dispersione interna / fra contesti < 0,3);
7. le classi sostituite, senza embedding, addestrano e prevedono come quelle di `train.py`, al bit;
8. un file senza c13 e un encoder che ha visto la coppia tenuta fuori sono rifiutati prima di addestrare;
9. la riga cieca è 0 ed è la media pesata dei visibili; cambiare gli embedding dei tenuti fuori cambia le loro righe,
   non le costanti;
10–11. mondo piantato, per ciascuna linea tenuta fuori: la rete batte `blind`, `swap`, `emb_blind` ed `emb_swap`
   (guadagno appaiato con l'intervallo sopra zero e ≥ 0,02 ciascuno);
12. E2 piantato: correlazione media > 0,1, intervallo sopra zero, sopra il 97,5° percentile delle permutazioni;
   cieco e trasferimento prevedono differenza zero;
13. cieco e scambio con l'embedding fanno quello che dicono;
14–15. mondo nullo: nessun guadagno su `blind` né su `emb_blind` oltre il rumore (≤ 2,5 DS bootstrap + 0,005), e al
   più 0,05 di skill persa sul trasferimento;
16. il fine-tuning addestra gli scostamenti, lascia intatti i pesi pre-addestrati, prevede valori finiti e tiene
   identico il cieco delle due linee;
17. `compare.py` ricalcola i contrasti di `train.py` dalle previsioni salvate, a meno di 1e-6.
Il mondo piantato è costruito perché l'embedding *possa* aiutare: se fallisce lì, il codice o l'ottimizzazione sono
sbagliati. Il mondo nullo controlla che non aiuti per un difetto.

## 12. Comandi

Autoverifica, dove c'è torch (Kaggle CPU), con le due cartelle `reports/rete_contesti_2026-09-27/` ed
`reports/encoder_contesto_2026-09-28/` una accanto all'altra (oppure `RETE_CONTESTI_CODE` che punta alla prima):

    python reports/encoder_contesto_2026-09-28/train_emb.py --selftest
    python reports/rete_contesti_2026-09-27/train.py --selftest          (invariato: deve dare ancora 14 su 14)

Controllo del corpus per ogni gruppo di esclusione, prima di spendere GPU (non scrive nulla):

    python pretrain.py --dry-run --corpus <nostri 1> --corpus <nostri 2> ... --reference-corpora <quanti nostri> \
        --exclude-preset orion --require k562,cd4_Rest,cd4_Stim8hr,cd4_Stim48hr,orion_hct116,orion_hek293t,kolf,A,B,C \
        --expect-excluded orion_hct116,orion_hek293t

Pre-addestramento di una condizione (quello che `make_runs.py` scrive; la PCA con gli stessi argomenti di dati):

    python pretrain.py --out <work>/pre/orion/ours+tahoe/seed0 --seed 0 --corpus <nostri> ... --corpus <tahoe> \
        --reference-corpora <quanti nostri> --exclude-preset orion --require ... --expect-excluded orion_hct116,orion_hek293t
    python pca_baseline.py --out <work>/pre/orion/pca --seed 0 --corpus <nostri> ... (stessi argomenti di dati)

Corse di rete di un disegno (stessi argomenti in ogni condizione):

    python rete_contesti_2026-09-27/train.py --data <dati> --out <work>/net/e1_orion/none/seed0 --hold-out orion_hct116 --seed 0
    python encoder_contesto_2026-09-28/train_emb.py --data <dati> --out <work>/net/e1_orion/ours/seed0 \
        --hold-out orion_hct116 --seed 0 --context-embeddings <work>/pre/orion/ours/seed0/context_embeddings.npz
    (fine-tuning: --finetune-encoder <work>/pre/orion/ours/seed0 --finetune-corpus <nostri 1> --finetune-corpus ...)

Tutto il confronto, due sessioni Kaggle:

    python make_runs.py --out runs.json --code <codice>/encoder_contesto_2026-09-28 --data <dati> \
        --work /tmp/enc --keep /kaggle/working/enc --corpus-ours <c1> --corpus-ours <c2> --corpus-ours <c3> \
        --corpus-tahoe <tahoe> --corpus-scbasecount <scbc>
    python run_list.py --runs runs.json --shard 0 --keep-small       (sessione 0)
    python run_list.py --runs runs.json --shard 1 --keep-small       (sessione 1)
    (compare.py gira in fondo a ogni sessione; a mano:)
    python compare.py --runs-json runs.json --data <dati> --out <nuova> --write-averaged <nuova2>

Proxy di r1 sulle cartelle mediate, sul portatile (come per r1):

    scripts\py.cmd reports\rete_contesti_2026-09-27\score_pred.py --run <averaged>/e1_orion/ours --out <nuova> --universe ...

## 13. Limiti, cose non verificate, domande aperte

- **Nulla è stato eseguito.** Il codice è stato scritto e riletto, non fatto girare, e sul portatile non c'è torch:
  il primo passo è l'autoverifica; se fallisce, il resto non si esegue. Le soglie dei controlli 4, 5, 10–12 sono
  scelte senza averle viste girare: un fallimento lì va letto (dettagli nella riga) prima di cambiarle.
- **Il formato del corpus è quello dell'assegnazione**, non ancora un file reale: nomi dei contesti, colonne
  `cell_line`/`cell_type`/`tissue` delle fonti esterne e unità di DepMap (TPM trattati come conteggi, con la libreria
  come somma) sono da confermare sui primi file con `--dry-run`.
- **Trasduttivo contro induttivo.** Le corse misurano un encoder che non ha mai visto la linea tenuta fuori. In gara
  i controlli di A, B, C sono noti e possono entrare nel pre-addestramento: una variante E1 con i controlli della
  linea tenuta fuori nel pre-addestramento (solo i nostri, `--allow-seen-contexts`) misurerebbe quel caso; non è
  nel piano di default.
- **Poche unità.** Con 5–7 contesti CRISPRi visibili per disegno la mappa embedding → risposta si stima da pochi
  punti; tre verità E1 e una coppia E2 sono poche per una generalizzazione. HIPSCI (34 linee, stesso tipo cellulare)
  darebbe più coppie E2 quando sarà un contesto della rete.
- **Bilanciamento per studio.** Con `--balance study` DepMap (un solo studio, circa mille linee) pesa quanto uno studio
  CRISPRi: scelta da discutere (`--balance none` o per fonte sono disponibili).
- **Righe fuori da questa cartella:** una voce nel registro e una nell'indice di `reports/` (aggiunte con questo
  lavoro); la scheda R-V2 non è stata toccata.

## 14. I file

| File | Che cosa fa |
|---|---|
| `DISEGNO.md` | questo documento |
| `corpus.py` | formato del corpus, lettura, esclusioni con le liste esplicite, geni, normalizzazione, uscite (numpy, pandas) |
| `encoder.py` | l'encoder, le perdite, gli scostamenti per il fine-tuning (PyTorch, nessun import del progetto) |
| `pretrain.py` | pre-addestramento, embedding per contesto, manifest; `--dry-run`, `--selftest` (parte encoder) |
| `pca_baseline.py` | la base PCA con la stessa preparazione e lo stesso formato (numpy) |
| `train_emb.py` | l'innesto nella rete senza modificarne i file: congelato o con fine-tuning; `--selftest` |
| `selftest_emb.py` | l'autoverifica sintetica (17 controlli) |
| `make_runs.py` | genera `runs.json`: condizioni × disegni × semi, divise in due sessioni |
| `run_list.py` | esegue una sessione di `runs.json`, riprende da dove si era fermato |
| `compare.py` | mette le condizioni a fianco: diagnostica della rete, contrasti fra condizioni, E2, semi, lettura della regola |
