# Input degli encoder: contesto e bersaglio mai visto

Data: 2026-09-14. Stato: **specifica eseguita il 2026-09-15**, non architettura
adottata.

> **Esito, aggiunto il 2026-09-15.** L'unica estensione proposta qui — il GO slim
> — è stata implementata e misurata secondo la regola del §6, fissata prima del
> run, ed è stata **scartata**: il braccio B1 non batte B0, e il braccio B3 con
> l'annotazione permutata fra i geni va come B1. Vedi
> [CP-0014](checkpoints/0014-go-slim-e-gpu.md), D-028 e
> `reports/go_slim_2026-09-15/`. Il resto di questa pagina resta valido come
> specifica e come inventario verificato dei candidati: la tabella del §2 non è
> stata toccata, e la copertura misurata sul pannello (295/300 dopo propagazione)
> è stata riprodotta da un join scritto separatamente. La riserva (ProtT5, ESM-2,
> gene2vec) **non** si apre: vedi la ragione in D-028.
Il benchmark modulare in corso (`configs/benchmark.yaml`, run `m001`) **non è stato
modificato**. I file di evidenza stanno in `reports/encoder_inputs_2026-09-14/`.
Il probe è `scripts/56_probe_target_descriptors.py`.

Domanda: con quali informazioni prevedere la risposta di un gene **mai perturbato
nel training**, e come distinguere quella modalità da un bersaglio già visto in
altri contesti.

Due modalità, già separate nel protocollo (`src/vcc2026/benchmark/protocol.py`):

| Modo | Cosa è lecito | Cosa è vietato |
|---|---|---|
| A. bersaglio già perturbato in altri contesti di training | firme di risposta di *quel* gene nei contesti di training | risposte perturbate del contesto da predire |
| B. bersaglio mai perturbato nel training | descrittori disponibili senza le sue risposte perturbative | firme, SVD codes, vicini costruiti su *quel* gene escluso |

Questa pagina rende concreta la **B**. La A resta un ramo aggiuntivo già presente
(`train_response_code_*` in `DescriptorBank`), e non va confusa con la
generalizzazione a bersagli nuovi.

## 1. Cosa c'è già (non sostituire)

`src/vcc2026/benchmark/descriptors.py` costruisce già, per ogni coppia
(contesto query, bersaglio):

- **Contesto `z_c`**, indipendente dal bersaglio: 5 statistiche NTC + 32 geni ad
  alta espressione. Gli indici dei 32 sono scelti sul NTC di **training**, mai
  sulla classifica del contesto di test. I NTC del contesto query sono ammessi
  (compito VCC) e dati a tutti i bracci.
- **Bersaglio, parte basale**: `log1p` CPM del gene nei NTC di ogni contesto di
  training e nel NTC query, ciascuno con indicatore «misurato».
- **Bersaglio, parte da risposta (solo modo A)**: codici SVD della risposta di
  training. Nel protocollo `new_context_unseen_target` sono azzerati.

Misurato sul split `new_context_unseen_target` K562→RPE1, seed 2026
(`reports/benchmark_2026-09-14/splits/new_context_unseen_target_k562_to_rpe1_seed2026.json`):

- con contesto: **41** colonne (5 + 32 + 2 + 2)
- senza contesto: **4** colonne (basale training + basale query)
- `context_dependence_identifiable: false` (un solo contesto di training)

Non è un encoder neurale del contesto. Con due contesti perturbati in tutto, un
test che ne esclude uno lascia **un** contesto di training (D-025). Non
identifica una dipendenza generale dal contesto.

## 2. Tabella dei descrittori verificati

Livelli di verifica, come nel registry: **dichiarato** / **verificato nei
metadati** / **verificato su file** / **non verificato**.

| Candidato | Fonte, versione, licenza | File / endpoint | ID e mapping | Copertura misurata | Dimensione | Cosa aggiunge rispetto al basale | Esito |
|---|---|---|---|---|---|---|---|
| Basale NTC del gene (già implementato) | Controlli VCC A/B/C e NTC delle sorgenti di training | Locale | Simbolo sull'asse ufficiale | 300/300 sull'asse; 300/300 con CPM>0 in A; 3/300 sotto 1 CPM in almeno un contesto A/B/C; 272/300 in K562 GWPS | 2 scalari per contesto (valore + maschera) | È il descrittore minimo di modo B, e **dipende dal contesto** | **Base. Tenere.** Verificato su `reports/data_audit/target_inventory.csv` |
| Statistiche NTC di contesto (già implementato) | Stessi NTC | Locale | Universo misurato, non asse intero | n/a (non è un descrittore del gene) | 5 + 32 | Descrive lo stato, non il bersaglio | **Base. Tenere.** Non imparare un ID di dataset |
| Mapping HGNC | [HGNC complete set](https://storage.googleapis.com/public-download-files/hgnc/tsv/tsv/hgnc_complete_set.txt), snapshot 2026-09-14; [CC0](https://www.genenames.org/about/license/) | 16 913 731 byte, sha256 `9e07bb49…b74492` | simbolo approvato, alias, `ensembl_gene_id`, `uniprot_ids` | VCC 300: 299 approvati, 1 alias univoco (`TMEM104`→`SLC38A12`), 0 ambigui, 0 non mappati, 300/300 protein-coding con ENSG e UniProt. K562 GWPS 2659 bersagli unici: 2582 approvati, 72 alias, 4 ambigui, 1 non mappato | 16,9 MB | Non è un descrittore predittivo: è il join | **Infrastruttura. Adottare come autorità di mapping per i 300.** Verificato su file |
| GOA human GAF + GO slim generico | GAF `goa_human.gaf.gz` 2026-07-28, [GO CC-BY-4.0](https://geneontology.org/docs/go-citation-policy/); slim `goslim_generic.obo` 140 termini; `go-basic.obo` per la chiusura | 11,0 + 0,13 + 32,2 MB | UniProt (col. 2 GAF) via HGNC; fallback simbolo col. 3 | VCC 300: 300/300 con almeno un termine GO, 279/300 con processo biologico, 280/300 slim diretto, **295/300 slim dopo propagazione**, 0/300 solo IEA. K562 GWPS: 2641/2659 con GO, 2616/2659 con slim propagato | vettore binario 140 + 1 indicatore mancante | Funzione curata, disponibile senza la risposta perturbativa del gene | **Unica estensione.** Verificato su file |
| STRING v12 fisica (umano) | [9606.protein.info](https://stringdb-downloads.org/download/protein.info.v12.0/9606.protein.info.v12.0.txt.gz) 1,97 MB; [physical.links](https://stringdb-downloads.org/download/protein.physical.links.v12.0/9606.protein.physical.links.v12.0.txt.gz) 8,95 MB; [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/) (NAR 2023) | `preferred_name` ≈ simbolo HGNC | VCC 300/300 come `preferred_name`, 0 ID multipli; 300/300 grado fisico > 0 (mediana 143; il file default include coppie AB e BA, quindi il grado è gonfiato) | 2 + 9 MB | Vicini fisici, non coespressione | **Differita.** Copertura piena, ma il grafo è denso e un descrittore «media dei vicini perturbati in training» è un altro esperimento, non questa estensione |
| STRING rete completa (combined) | 83,2 MB compressi (HEAD) | non scaricata | — | 83,2 MB | Include canale coespressione (STRING v12 usa anche scRNA-seq) | **Non nel confronto rigoroso di modo B.** Dimensione e canale espressione |
| Embedding di sequenza ProtT5 già calcolato | [9606.protein.sequence.embeddings.v12.0.h5](https://stringdb-downloads.org/download/protein.sequence.embeddings.v12.0/9606.protein.sequence.embeddings.v12.0.h5) 38,2 MB (HEAD); CC-BY-4.0 | ENSP via `protein.info` | Copertura attesa = 300/300 STRING info; **vettori non letti** | 38,2 MB | Sequenza proteica, niente RNA | **Riserva.** Pesi/vettori accessibili; scaricare solo se lo slim GO vince l'ablazione |
| ESM-2 t6 8M | [facebook/esm2_t6_8M_UR50D](https://huggingface.co/facebook/esm2_t6_8M_UR50D) `model.safetensors` 31,4 MB (HEAD), MIT; addestrato su UniRef50/D 2021 | sequenza UniProt | copertura = geni con UniProt (300/300 VCC) | 31,4 MB pesi + FASTA | Come ProtT5, da calcolare noi | **Riserva, non prima estensione.** Pesi verificati per HEAD, non scaricati. Serve `torch` |
| gene2vec 200-d | [GitHub autori](https://github.com/jingcheng-du/Gene2vec/blob/master/pre_trained_emb/gene2vec_dim_200_iter_9.txt); paper BMC Genomics 2019, dati dichiarati CC0 | vettori testo | **non misurata**: HEAD 23,6 MB, GET decompresso ha superato 40 MB e lo scarico è stato interrotto | > 40 MB decompressi | Addestrato su coespressione in 984 dataset GEO | **Fuori dal confronto rigoroso.** File esiste; provenienza espressione, non sequenza |
| CORUM complessi | sito CORUM, [CC-BY-NC-4.0](https://mips.helmholtz-muenchen.de/corum/) | HEAD fallito (certificato SSL) | — | — | Subunità di complessi | **Scartata per licenza NC**, stesso tipo di rischio di Orion (D-004) |
| Reactome mapping UniProt | [UniProt2Reactome.txt](https://reactome.org/download/current/UniProt2Reactome.txt), mapping CC0 | HEAD 200, `Content-Length` assente; listing 41 MB non compressi (2026-06-19) | UniProt | non misurata su file | Pathway, sovrapposto a GO | **Differita.** Più grande di GOA; non aggiunge una famiglia nuova rispetto allo slim |
| scGPT gene tokens | checkpoint [whole-human](https://github.com/bowang-lab/scGPT); pretraining CELLxGENE census 2023-05; il paper usa Replogle come task di perturbazione | Google Drive, modello grande | simboli/Ensembl nel `vocab.json` | non scaricato | Embedding addestrato su cellule, non su annotazione | **Fuori dal confronto rigoroso di modo B.** Leakage possibile verso Replogle; non è un file di descrittori piccolo |
| STATE (Arc) | pesi [SE-600M](https://huggingface.co/arcinstitute/SE-600M); ST addestrato su Tahoe-100M, Parse, **Replogle–Nadig**; il Colab VCC usa featurizzazione ESM2 per gene | checkpoint grandi | ESM2 per gene, non un TSV | non scaricato | Modello di transizione, non un descrittore statico | **Non è un descrittore di modo B.** ST ha visto risposte perturbative Replogle. Gli ESM2 che STATE usa sono la stessa famiglia «sequenza» già in riserva |
| GEARS GO-graph | [repo](https://github.com/snap-stanford/GEARS); usa NCBI gene2go, impara embedding sulle perturbazioni | metodo, non vettori da drop-in | Entrez | — | L'idea (GO per geni non visti) è il precedente; i pesi GEARS no | **Non importare i pesi.** Lo slim GO è la versione statica e senza leakage di quella idea |
| Codici SVD della risposta di training | firme e001 | già nel bank | simbolo | solo bersagli nel fold di training | rango 8–16 | Identità effettiva del gene visto | **Solo modo A.** Vietati in B (`allowed_in_unseen_target: false`) |

L'asse ufficiale resta a **simboli** (`gene_names.csv`). La contraddizione aperta
sull'ENSG dei 18 533 output (R-004) **non blocca** questo lavoro: i descrittori
del bersaglio riguardano i 300 + i geni perturbati in training, non tutte le
colonne di output. Per quei geni HGNC dà ENSG e UniProt espliciti.

## 3. Copertura misurata e buchi

Fonte: `reports/encoder_inputs_2026-09-14/coverage.json`,
`hgnc_vcc300_mapping.csv`, `vcc_without_slim.csv`,
`reports/data_audit/target_inventory.csv`.

| Insieme | n | HGNC univoco | UniProt | GO qualsiasi | GO slim propagato |
|---|---:|---:|---:|---:|---:|
| 300 bersagli VCC | 300 | 300 | 300 | 300 | 295 |
| Bersagli unici K562 GWPS (firme e001) | 2659 | 2654 (4 ambigui + 1 non mappato) | 2649 | 2641 | 2616 |

Cinque VCC senza bit slim dopo propagazione, tutti con almeno un termine GO:
`ANKRD52`, `C5orf22`, `TBC1D19`, `TMEM104`, `ZC2HC1A`
(`vcc_without_slim.csv`). Hanno 1–4 termini che non cadono nello slim
generico. Trattamento: vettore slim a zero + indicatore `go_slim_missing=1`.
Il basale resta.

Un solo join non ovvio sui 300: **`TMEM104` è alias / simbolo precedente di
`SLC38A12`** (ENSG00000109066, UniProt Q8NE00). La chiave VCC resta `TMEM104`.
Il GAF si raggiunge via UniProt di `SLC38A12`.

ENSG Replogle vs HGNC sui bersagli K562 con ENSG unico in entrambe: 2572
concordi, 9 discordi, 78 senza ENSG HGNC o simbolo non approvato. I dissensi
sono per lo più aggiornamenti di ID o simboli con trattino che il parser
Replogle marca `nan`. Per i descrittori dei 300 usare **HGNC**. Per i bersagli
di training, il simbolo della firma resta la chiave; HGNC è il join verso GO.

Verifiche **non** fatte, e non necessarie per sbloccare l'implementazione:

- leggere i tensori ProtT5 STRING (38 MB) o calcolare ESM-2
- copertura gene2vec su disco
- Reactome sui 300
- CORUM (licenza + HEAD SSL fallito)
- mapping Ensembl dei 18 533 output (R-004, altro lavoro)

## 4. Encoder del contesto `z_c`

I controlli del contesto da predire sono input ammessi. Le cellule perturbate di
quel contesto no.

### 4.1 Rappresentazione economica (configurazione minima)

Sia `u` l'universo dei geni **misurati in tutte le sorgenti confrontate**
(D-024, D-009: non riempire i non misurati con zero). Dal NTC del contesto,
già allineato all'asse ufficiale come in `extract_control_profile`:

```
stats = [mean(log1p_cpm[u]), std(log1p_cpm[u]),
         log1p(library), log1p(n_cells),
         mean(log1p_cpm[u] > log1p(1))]     # 5
high  = log1p_cpm[u][high_expr_idx]         # 32
z_c   = concat(stats, high)                 # 37
```

`z_c` **non dipende dal bersaglio**. Se il gene da perturbare capita fra i 32,
la sua espressione compare anche in `e_t`: è accettato, non si filtra `z_c` per
`t` (serve per fare batch). Non si duplica in modo implicito: il basale del
bersaglio vive solo in `e_t` come campo nominato.

Normalizzazione: CPM sul totale della libreria del NTC (come ora), poi `log1p`.
Geni non misurati in quel contesto: esclusi da `u` se l'universo lo richiede;
il basale del bersaglio ha la maschera `measured`.

Profondità e batch: `library` e `n_cells` entrano in `stats`. Non si tenta di
correggere il batch con un encoder: con due o tre contesti sarebbe un ID del
dataset.

### 4.2 Cosa si impara solo sul training, cosa si calcola all'inferenza

| Pezzo | Training | Inferenza su un contesto nuovo |
|---|---|---|
| Indici `high_expr` | Dal NTC dei **contesti di training**. Se ce n'è più di uno (es. K562+HepG2), media dei profili NTC di training, poi gli n più abbondanti. Mai dal contesto tenuto fuori | Si riusano gli indici; si leggono i valori sul NTC query |
| Media/std delle colonne di `z_c` per la MLP | Sulle righe di training | Applicata, non ricalcolata |
| PCA / autoencoder sulle cellule NTC | Non in questa configurazione. Due punti-contesto non stimano una PCA di contesto; una PCA sulle cellule *dentro* un contesto cattura ciclo/batch, non il tipo | — |
| `z_c` stesso | Calcolato anche sui NTC di training, per le righe di training | Calcolato sui 18 400 controlli del contesto query |
| One-hot del nome dataset | Vietato | Vietato |

Un grande numero di cellule non è un grande numero di contesti. Con tre
contesti VCC e due di training, `z_c` è un riassunto fisso del basale, non un
lookup.

## 5. Encoder del bersaglio `e_t`

### 5.1 Configurazione minima (modo B) — subito realizzabile

Campi, tutti già nel `DescriptorBank`:

| Campo | Dim | Dipende dal contesto? | Provenienza |
|---|---:|---|---|
| `target_basal_{c}` per ogni contesto di training `c` | 1 | sì, ma su NTC di training | NTC |
| `target_basal_{c}_measured` | 1 | sì | maschera |
| `target_basal_query` | 1 | sì, NTC del contesto da predire | NTC query, lecito |
| `target_basal_query_measured` | 1 | sì | maschera |

Tensore: `e_t_basal ∈ R^{2(C_train+1)}`. Oggi `C_train=1` → 4.

Preprocessing: i CPM sono gli stessi di `extract_control_profile`. Gene assente
dall'asse o non misurato: `(0, 0)` sulla coppia (valore, measured), non uno
zero spacciato per «nessuna espressione» senza maschera.

Nessun parametro addestrabile in questo encoder: è una lookup. La MLP a valle
impara i pesi.

### 5.2 Unica estensione: GO slim

Campi nuovi, **vietato** costruirli dalle firme del bersaglio escluso:

| Campo | Dim | Dipende dal contesto? | Provenienza |
|---|---:|---|---|
| `go_slim_{i}` per i in 1..140 | 140 | no | GAF → chiusura `is_a`/`part_of` su `go-basic.obo` → intersezione slim |
| `go_slim_missing` | 1 | no | 1 se la chiusura non interseca lo slim |

Join, deterministico, congelato negli artefatti:

1. Simbolo VCC / della firma → HGNC (approvato, altrimenti alias univoco;
   alias ambigui o assenti → `go_slim_missing=1`, bit a zero).
2. `uniprot_ids` HGNC (primo ID se ce n'è più d'uno; registrarli tutti nel
   manifesto).
3. Righe GAF `UniProtKB:<id>`, scartando `NOT` in colonna 4.
4. Unione dei GO:ID in P/F/C; chiusura ancestrale; bit slim.

File da congelare (già in cache
`C:/Users/ferra/vcc2026-data/interim/encoder_inputs_2026-09-14/`):

- `hgnc_complete_set` (16 913 731 B)
- `goa_human_gaf` (11 020 779 B, gaf-version 2.2, date-generated 2026-07-28)
- `goslim_generic` (125 864 B, 140 termini)
- `go-basic.obo` (32 227 785 B)
- tabella derivata `symbol → 140 bit + missing` (da scrivere al fit, da
  riusare all'inferenza)

Costo: **misurato** il download (~68,5 MB i file GO+HGNC+STRING usati dal
probe). **Stimato**, non cronometrato come job di training: costruire la
tabella per ~3 000 simboli in meno di un minuto su CPU. Parametri extra della
MLP con `hidden=8`: 141 × 8 = 1 128 pesi in più al primo strato.

Cosa *non* è: non usa le risposte di K562/RPE1/HepG2 del gene. GO include
evidenze IMP (fenotipo mutante) in letteratura; nessuna di queste è la
risposta VCC 2026, che non è pubblica. 0/300 VCC sono annotati *solo* IEA.
Rischio di leakage verso il nostro test: basso. Rischio che GO riassuma
letteratura di knockdown su altri sistemi: dichiarato, è il motivo per cui
serve il controllo a mapping mescolato.

### 5.3 Ramo modo A (non mescolare)

Se e solo se il protocollo è `new_context_seen_target` e il gene ha una riga
di training: `train_response_code_{1..k}` come ora. In modo B: assenti, non
zeri silenziosi senza specifica — il bank già li marca
`derived_from_perturbative_response: true`.

### 5.4 Combinazione `(z_c, e_t)` → coefficienti → delta

Non cambiare il decoder. Resta:

```
x = concat(z_c, e_t_basal[, e_t_go])     # (n_targets, d)
x = (x - mean_train) / std_train         # già in CompactMLP / ModularFrozen
a = MLP(x)                               # (n_targets, k), k ∈ {8,16}
delta[u] = a @ B + mean_y                # B, mean_y da SVD mascherata sul training
delta[¬u] mascherato, non zero-fill
```

Encoder contesto: 0 parametri (lookup). Encoder bersaglio GO: 0 parametri
(lookup). Addestrabili: MLP (e, nel braccio congiunto, B). Calibrazione di
ampiezza: invariata, senza alpha 0,1974, come in `configs/benchmark.yaml`.

## 6. Confronti da far integrare a Claude

Stesso decoder, stessi split, stesso budget di griglia. **Nuovo `run-id`**, non
`m001`. Non scegliere termini GO, rango o hidden sulle risposte del contesto
esterno di test.

Quattro bracci, più le due direzioni e i due protocolli già previsti:

| ID | Descrittori | Scopo |
|---|---|---|
| B0 | basale + `z_c` (stato attuale modo B) | riferimento |
| B1 | B0 + GO slim | valore dell'annotazione |
| B2 | B1 senza `z_c` (come `include_context=false` già esiste) | il contesto NTC serve, sui bersagli nuovi? |
| B3 | B1 con **riga GO permutata** fra i geni (stesso seed, stessa permutazione a train e test) | l'associazione gene↔annotazione conta, o basta «avere 140 bit»? |

Non confrontare B1 con ShrunkTransfer sul protocollo unseen: ShrunkTransfer lì
ha copertura 0 per costruzione. Il confronto sul visto resta quello di m001.

Criterio, fissato prima del run, sulla metrica già dichiarata
`pooled_mse_vs_null` in spazio proxy, protocollo
`new_context_unseen_target`, entrambe le direzioni, due seed:

- **Tenere lo slim** se, sul protocollo unseen, B1 ha MSE/nullo più basso di B0
  con IC bootstrap appaiato per bersaglio che esclude zero **in entrambe** le
  direzioni, oppure in una direzione con effetto stabile sui due seed e non
  peggiore nell'altra.
- **Scartare lo slim** se B1 non batte B0, o se B3 ≈ B1 (l'annotazione vera non
  aggiunge rispetto a un vettore della stessa sparsità assegnato a caso).
- **Non adottare un encoder di contesto più ricco** se B2 ≈ B1: con un contesto
  di training `z_c` è quasi costante e non può essere la causa.
- Nessuna conclusione VCC. Nessuna selezione di feature sul contesto tenuto
  fuori.

HepG2, quando Claude l'avrà nello stesso inventario, entra come terzo contesto
nelle **stesse** quattro etichette, senza cambiare i descrittori.

## 7. Istruzioni operative per Claude

Non toccare `configs/benchmark.yaml` di m001, le firme e001, né
`src/vcc2026/benchmark/` in modo che m001 smetta di essere riproducibile.
Estendere *accanto*:

1. Tabella congelata `symbol → go_slim[140] + missing` a partire dai file in
   `C:/Users/ferra/vcc2026-data/interim/encoder_inputs_2026-09-14/`, scritta in
   un `--out` nuovo (es. `.../artifacts/m002/go_slim_table.npz`). Hash dei
   quattro file sorgente nel manifesto.
2. In `DescriptorBank`, un flag `include_go_slim` (default false). Colonne con
   `derived_from_perturbative_response=False`, `allowed_in_unseen_target=True`.
3. Costruttore della permutazione B3: permutazione dei vettori slim fra i
   simboli della tabella, seed in un yaml **nuovo** (non quello di m001).
4. Runner: stesso protocollo, `run-id` nuovo, `include_response_codes` ancora
   true solo su `new_context_seen_target`.
5. Test: (a) TMEM104 riceve i bit di SLC38A12/Q8NE00; (b) i cinque geni senza
   slim hanno `missing=1` e bit a zero; (c) in modo B nessuna colonna ha
   `derived_from_perturbative_response=True` a true sui valori; (d) B3 con seed
   fisso è deterministico.
6. Non scaricare STRING embeddings, ESM, gene2vec, atlanti. Non usare CORUM.

## 8. Risposta semplice

**Con quali informazioni prevederemo la risposta di un gene mai perturbato nel
training, e perché potrebbero servire?**

Con due cose che si possono leggere senza aver mai spento quel gene. La prima
è quanto è acceso, a riposo, nella cellula di cui ci danno i controlli: un
gene spento di suo non è lo stesso bersaglio di un gene abbondante. La seconda
è un riassunto corto della sua funzione annotata (140 etichette GO di alto
livello: ribosoma, ciclo, mitocondrio, …). Geni della stessa macchina
cellulare, quando li si spegne, tendono a muovere i medesimi programmi; lo
slim è un modo povero di dire «questa macchina» senza copiare la risposta di
qualcun altro. Non usiamo la sua firma perturbativa, né un nome fittizio del
dataset, né un embedding addestrato su Perturb-seq. Se lo slim non batte il
solo basale, o se un'etichetta mescolata a caso fa lo stesso, si butta.
