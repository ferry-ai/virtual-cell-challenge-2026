# Inventario riconciliato del catalogo: che cosa c'è, che cosa usa il pilot, che cosa manca

4 ottobre 2026, 00:03 CEST (ora letta con `date`), Claude Code, sessione `d0100a`, binario dati di
[R-LEAD](../../../docs/piani/strategia-scientifica.md), passo 1 di [R-DATI](../../../docs/piani/dati-affidabilita.md).
Lo chiede il mandato D-053 prima di congelare il prossimo corpus principale
([GENERALIZZAZIONE §2.1](../../../docs/GENERALIZZAZIONE.md#21-copertura-integrale-vincolo-non-negoziabile)).

**Che cosa è.** Una riconciliazione per gruppo di linea fra il catalogo, i manifest di ciò che è stato acquisito e
ciò che il pilot v4 usa davvero. È una sintesi: ogni numero viene dal file citato nella colonna «Fonte» della
legenda, e lo stato dei job è quello letto su Kaggle e su Drive la notte fra il 3 e il 4 ottobre (job che cambiano:
si rilegge prima di agire). **Non è** l'adozione dei gruppi né dei ruoli: la
[mappa a 21 gruppi](../ingestione_completa_2026-10-03/orion/line_groups_expanded_v1.json) e i
[ruoli](../archivio_cloud_2026-10-02/ruoli_ingestione_r1.json) restano proposte finché R-LEAD non le adotta con un
file nuovo nel protocollo del corpus ampliato.

**Risposta breve.** Il pilot v4 addestra sulle cellule di **8 gruppi su 21** (5.603.629 cellule in 365 shard) e
usa gli aggregati di **10 gruppi** come ancore. Nessun training usa ancora le cellule di CD4T, HCT116, HEK293T e
degli altri dieci gruppi; per sei di questi le cellule sono già pubblicate su Kaggle e mai usate.

## Legenda delle fonti

| Sigla | File | Che cosa dà |
|---|---|---|
| CAT | [catalogo r4](../corpus_cellulare_2026-09-30/catalogo_r4/catalogo.json), 1/10 | Cellule per sorgente ingerita, stato e motivo delle voci remote (77) |
| ING | [INGESTIONE §2 e §4](../archivio_cloud_2026-10-02/INGESTIONE.md), 2–3/10 | Riconciliazione precedente, ruoli proposti |
| PRE | `processed/rete_cellulare_2026-10-03/out_prepass_h1_r1/prepass/{prepass_done,splits}.json` nella radice dati | 365 shard, 5.603.629 cellule, 33 chiavi, cellule di training per unità nel fold H1 |
| ANC | [manifest delle ancore](../../modelli/rete_ancorata_v4_2026-10-03/esito/anchors_r1/), regola `all` | 34 tabelle aggregate, 10 gruppi |
| KOLF | [verifica KOLF](../ingestione_completa_2026-10-03/kolf/esito_verifica_r1/source_complete.json) | 2.659.209 cellule, 133 shard, 18,39 GB, sha256 riletti |
| LOG | [lancio_orion_r2.jsonl](../ingestione_completa_2026-10-03/kaggle_cpu/lancio_orion_r2.jsonl), [lancio_cd4_r1.jsonl](../ingestione_completa_2026-10-03/kaggle_cpu/lancio_cd4_r1.jsonl) e stato letto su Kaggle il 3/10 alle 23:59 | Parti spinte e concluse |
| CONS | [consegna dell'ingestione](../ingestione_completa_2026-10-03/HANDOFF_CLAUDE2.md) | Struttura di DLD-1, prova CD4, limiti di Kaggle |

## 1. Gli 8 gruppi del pilot v4

Cellule nel corpus del pilot (PRE) e tabelle aggregate nel cubo (ANC). «Training nel fold H1» sono le cellule di
classe training quando H1 è la linea esclusa; negli altri due fold cambia solo la linea esclusa.

| Gruppo | Sorgente (modalità) | Cellule acquisite (CAT) | Training nel fold H1 (PRE) | Aggregati (ANC) | Fuori dal pilot, e perché |
|---|---|---:|---:|---|---|
| K562 | Replogle GWPS (CRISPRi) | 1.989.578 | 1.616.514 | `k562_gwps` | — |
| K562 | Replogle essential (CRISPRi) | 310.385 | 253.297 | `k562_essential` | — |
| K562 | Norman 2019 (CRISPRa) | 111.445 | 60.117 | nessuna (le ancore sono solo CRISPRi) | — |
| K562 | VIPerturb (CRISPRi, Flex) | cellule non convertite (RDS) | 0 | `k562_viperturb` | manca la conversione da RDS (sonda r2 committata, non lanciata) |
| K562 | Dixit 2016 (CRISPR, tre contesti) | 104.179, pubblicate (`rlab-scp-k562-hek`) | 0 | nessuna | mai inserite in un pre-passo; modalità da confermare negli shard |
| K562 | Adamson 2016 | 86.111, non ingerite | 0 | nessuna | i controlli sono nomi di plasmidi: serve una mappa dichiarata (CAT) |
| RPE1 | Replogle RPE1 (CRISPRi) | 247.914 | 201.857 | `rpe1` | — |
| RPE1 | Southard 2025 (CRISPRa) | 850.225, in ingestione | 0 | nessuna | job Colab 132 vivo alle 23:51 del 3/10 (battito di `dispatcher_q2.log`) |
| HepG2 | Nadig 2025 (CRISPRi) | 145.473 | 119.008 | `hepg2_nadig` | — |
| Jurkat | Nadig 2025 (CRISPRi) | 262.956 | 215.180 | `jurkat_nadig` | — |
| Jurkat | Datlinger 2017 e 2021 | 5.905 + 39.194, pubblicate (`rlab-scp-tcells`) | 0 | nessuna | mai inserite; per il 2021 il contesto va letto negli shard (ING §4) |
| Jurkat | GSE249595 | 97 shard pubblicati | 0 | nessuna | il rilascio non ha chiamate delle guide (CAT) |
| H1 | VCC 2025 train e validation (CRISPRi) | 320.200 | linea esclusa del fold | `h1_train`, `h1_val` | il test resta riserva chiusa, mai scaricato |
| iPSC | HIPSCI mirato, 19 linee (CRISPRi) | 1.161.865 (526.843 senza guida, fuori dalla supervisione) | 508.726 | 19 tabelle `hipsci_*` | — |
| iPSC | KOLF2.1J cromatina, metabolico, forte (CRISPRi) | 44.039 + 117.768 + 232.438 | 36.508 + 100.413 + 193.473 | `kolf21j` | — |
| iPSC | KOLF2.1J pan-genome (CRISPRi) | 2.659.209, verificate (KOLF) | 0 | compresa in `kolf21j` solo se quella tabella viene dallo schermo pan-genome: **da verificare** nel registro del banco | servono gemelli compatti e un pre-passo nuovo |
| iPSC | HIPSCI genome-wide fitness e non-fitness | 322.746 + 396.458 | 0 | nessuna | 36 e 12 controlli in tutto: rientra solo con controlli dichiarati (CAT) |
| iPSC | Tian 2019 iPSC | 275.708, ingerite | 0 | nessuna | droplet non filtrati ([protocollo r3](../../modelli/rete_cellulare_2026-10-03/PROTOCOLLO.md)): serve una regola di QC, non un'esclusione definitiva |
| Neuron | Tian 2021 CRISPRi e CRISPRa | 32.300 + 21.193 | 26.218 + 15.452 | `tian2021_neuron` (CRISPRi) | — |
| Neuron | Tian 2019, neuroni al giorno 7 | 182.790, ingerite | 0 | nessuna | come Tian 2019 iPSC |
| A549 | Liu e Hillsley 2026 (KO) | 606.075 | 504.189 | nessuna (KO: altra modalità) | — |
| A549 | Mixscale, cellule (CRISPRi) | non convertite (RDS) | 0 | nessuna | vedi §3 |

## 2. I tre gruppi che oggi entrano solo come ancore

| Gruppo | Sorgente | Cellule attese | Stato dell'acquisizione (LOG) | Aggregati (ANC) | Che cosa manca per le cellule |
|---|---|---:|---|---|---|
| HCT116 | Orion (CRISPRi) | 3.409.169 | 4 parti su 4 concluse; verifica di linea `vcc-orion-hct116-verify-r1` spinta il 3/10 alle 23:59 | `hct116` | esito della verifica, gemelli, pre-passo |
| HEK293T | Orion (CRISPRi) | 4.534.299 | 8 parti su 8 concluse; verifica `vcc-orion-hek293t-verify-r1` in corsa dalle 23:48 | `hek293t` | come HCT116 |
| HEK293T (famiglia) | Xu 2023, HEK293 (CRISPRi) | 98.315, pubblicate (`rlab-scp-k562-hek`) | — | nessuna | mai inserite in un pre-passo |
| CD4T | Marson 2025 (CRISPRi, Flex), 4 donatori × 3 stati | 33,6 milioni in 12 file | 2 parti su 24 concluse (`D1_Rest`), 2 in corsa (`D1_Stim8hr`), 20 in coda; nessun file ancora verificato | `cd4_rest`, `cd4_stim8hr`, `cd4_stim48hr` | le altre parti, la verifica per file, gemelli, campioni annidati |

## 3. Gli altri dieci gruppi della mappa, e le risorse in ricognizione

| Gruppo | Sorgente (modalità secondo CAT) | Cellule | Stato | Che cosa manca |
|---|---|---:|---|---|
| Melanoma_Frangieh2021 | Frangieh 2021, tre stati (CRISPR) | 218.331 | pubblicate (`rlab-scp-ko`), in nessun training | pre-passo con il gruppo adottato; aggregati |
| Calu-3 | Sunshine 2023 (CRISPR-cas9 nel catalogo) | 90.380 | pubblicate (`rlab-scp-ko`), in nessun training | modalità da confermare; pre-passo; aggregati |
| THP-1 | Papalexi 2021 arrayed (CRISPR) | 8.984 | pubblicate (`rlab-scp-ko`), in nessun training | pre-passo; la parte ECCITE (20.729) chiede una mappa delle etichette |
| PrimaryT_Shifrut2018 | Shifrut 2018, donatore × stimolo (CRISPR) | 52.236 | pubblicate (`rlab-scp-tcells`), in nessun training | pre-passo; famiglia correlata a CD4T: si esclude insieme nei fold severi |
| Hs27 | Southard 2025 (CRISPRa) | 447.301 | in ingestione con RPE1 (job 132) | ricevute, verifica da un altro runtime, pubblicazione |
| MCF7, HT29, HAP1, BxPC3 | Mixscale = Jiang 2025 (CRISPRi), con A549 e K562 | mai lette (5 RDS, 20,14 GB) | solo espressione differenziale in locale | conversione da RDS con R; ruolo proposto: riserva candidata (ING §4) |
| DLD-1 | GSE337988 (CRISPRi) | 1.196.592 a MOI bassa (CONS) | solo effetti in locale; struttura dei file letta | adattatore dalle matrici per canale |
| microglia da iPSC | GSE335887 | da misurare | solo metadati | adattatore (matrici 10x e guide CROP-seq) |
| PerturbFate | GSE291147 | da misurare | solo metadati | decisione dopo i metadati |

## 4. Voci del catalogo fuori dal percorso, con il motivo

Dal catalogo r4 (CAT). I motivi sono quelli ammessi dal §2.1: incompatibilità verificata, duplicazione, integrità.

| Voci | Motivo |
|---|---|
| Lara-Astiaso 2023 (tre), Liang 2023, Santinha 2023 | topo: l'asse è umano |
| Gasperini 2019 (tre), Xie 2017, Schraivogel 2020 (due) | schermi di enhancer: i bersagli non sono geni («fuori per ora») |
| Wessels 2023 | coppie di guide Cas13 per cellula, nessun bersaglio singolo |
| Gehring 2019, Joung 2023 (due), Weinreb 2020 | matrice non intera e nessun layer di conteggi grezzi |
| Frangieh e Papalexi, matrici di proteine (tre) | proteine di superficie, non RNA |
| Nadig (due) e Replogle (tre) da scPerturb | ripubblicazioni di sorgenti già ingerite dal rilascio originale |
| Undici studi con farmaci o citochine, Tahoe-100M | non è un'esclusione di contesti: richiedono una testa separata e, per decisione del proprietario, i farmaci non prevalgono sulle perturbazioni genetiche. Restano una voce aperta |
| DepMap 24Q4 | covariate basali, mai supervisione |

## 5. Lavoro che porta dal pilot al corpus con tutti i gruppi

In ordine di prontezza; ogni voce è una lacuna aperta, non un motivo di esclusione.

1. **HCT116 e HEK293T:** leggere gli esiti delle due verifiche di linea; gemelli compatti dei loro shard.
2. **KOLF pan-genome:** gemelli compatti (già verificato).
3. **Terza ondata scPerturb (617.524 cellule, sei contesti in più):** già nel contratto e su Kaggle; gemelli con il
   launcher esistente; modalità e contesti da leggere negli shard prima di assegnare i gruppi.
4. **CD4:** le 20 parti in coda, la verifica per file, poi gemelli e campioni annidati per donatore e stato.
5. **Southard RPE1 e Hs27:** ricevute del job 132, verifica, pubblicazione.
6. **Tian 2019:** una regola di QC per i droplet non filtrati, scritta prima di guardarne gli effetti.
7. **Conversioni:** Mixscale (sei linee) e VIPerturb da RDS, DLD-1, microglia, PerturbFate.
8. **Voci con etichette da mappare:** Adamson 2016, Papalexi ECCITE, Jurkat GSE249595, HIPSCI genome-wide.
9. **Aggregati per chi non ha una tabella nel cubo:** A549 (KO), Norman e Tian CRISPRa, terza ondata, Southard.
10. **Protocollo del corpus ampliato:** gruppi e ruoli adottati da R-LEAD, pre-passo nuovo, ancore per fold, ricevuta
    dell'uso effettivo. La quota GPU decide quando parte il training: il 3/10 alle 23:58 restavano 11,32 h su
    `davideferrante11` (in consumo dai due training) e 30 h intere su ciascuno degli altri due account configurati.

## Limiti di questa riconciliazione

- I numeri del catalogo sono del 1° ottobre; quelli dei job cambiano di ora in ora.
- Non ho riaperto gli shard: modalità e contesti della terza ondata sono quelli dichiarati dal catalogo e dalla
  proposta dei gruppi, che li segna in parte come non verificati.
- La provenienza della tabella `kolf21j` (schermi piccoli o pan-genome) non è stata controllata qui.
- Le «77 accessioni del catalogo del 26/09» citate dal catalogo r4 come sole menzioni non sono riconciliate una per
  una.
