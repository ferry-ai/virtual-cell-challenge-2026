# Archivi persistenti: dati e dataset, 5 ottobre 2026

**Percorso principale: archivio verificato → banca e campioni → training esteso.**
Indice dei dati conservati; non è una dichiarazione di training completo.

## Nuova ingestione conservata su Kaggle

CD4: 12 unità (4 donatori × Rest/Stim8hr/Stim48hr), 21.980.517 cellule, 206,00 GB grezzi.
KOLF2.1J: 2.659.209 cellule, 18,39 GB. HCT116: 3.409.169 cellule, 38,66 GB.
HEK293T: 4.534.299 cellule, 63,12 GB. Totale: **326,17 GB**, 32.583.194 righe cellulari, 15 unità biologiche.
Notebook, versioni, percorsi e hash: [manifest corrente](cloud_catalog_r2/README.md).

## Archivi precedenti da riusare, non da reingerire

Versioni osservate via API e manifest recuperati in `archive_followup_r2/state.json`.
Tutti i dataset della tabella appartengono a `davidmaisterx`; le unità non coincidono con i contesti biologici.

| Dataset | Versione | GB grezzi | Righe cellulari | Unità di sorgente |
|---|---:|---:|---:|---|
| [rlab-a549](https://www.kaggle.com/datasets/davidmaisterx/rlab-a549/versions/1) | 1 | 7.652 | 606.075 | a549_ko |
| [rlab-h1-vcc2025-trainval](https://www.kaggle.com/datasets/davidmaisterx/rlab-h1-vcc2025-trainval/versions/1) | 1 | 6.384 | 320.200 | h1_train, h1_val |
| [rlab-hepg2-nadig](https://www.kaggle.com/datasets/davidmaisterx/rlab-hepg2-nadig/versions/1) | 1 | 1.332 | 145.473 | hepg2_nadig |
| [rlab-hipsci-targeted19](https://www.kaggle.com/datasets/davidmaisterx/rlab-hipsci-targeted19/versions/1) | 1 | 13.030 | 1.161.865 | hipsci_gw_fitness, hipsci_gw_nonfitness, hipsci_targeted_19 |
| [rlab-jurkat-nadig](https://www.kaggle.com/datasets/davidmaisterx/rlab-jurkat-nadig/versions/1) | 1 | 2.040 | 262.956 | jurkat_nadig |
| [rlab-k562-essential-r2](https://www.kaggle.com/datasets/davidmaisterx/rlab-k562-essential-r2/versions/1) | 1 | 2.472 | 310.385 | k562_essential, rpe1 |
| [rlab-k562-gwps-r3](https://www.kaggle.com/datasets/davidmaisterx/rlab-k562-gwps-r3/versions/1) | 1 | 13.973 | 1.989.578 | k562_gwps_a, k562_gwps_b |
| [rlab-rpe1-r2](https://www.kaggle.com/datasets/davidmaisterx/rlab-rpe1-r2/versions/1) | 1 | 1.947 | 247.914 | k562_essential, rpe1 |
| [rlab-scp-k562-hek](https://www.kaggle.com/datasets/davidmaisterx/rlab-scp-k562-hek/versions/1) | 1 | 1.105 | 202.494 | dixit2016_d7, dixit2016_d13, dixit2016_high_moi, xu2023 |
| [rlab-scp-ko](https://www.kaggle.com/datasets/davidmaisterx/rlab-scp-ko/versions/1) | 1 | 2.488 | 317.695 | frangieh2021, sunshine2023, papalexi2021_arrayed |
| [rlab-scp-tcells](https://www.kaggle.com/datasets/davidmaisterx/rlab-scp-tcells/versions/1) | 1 | 0.343 | 97.335 | shifrut2018, datlinger2017, datlinger2021 |
| [rlab-tian-norman](https://www.kaggle.com/datasets/davidmaisterx/rlab-tian-norman/versions/1) | 1 | 2.091 | 623.436 | tian2021_crispri, tian2021_crispra, tian2019_ipsc, tian2019_neuron, norman2019 |
| [rlab-hipsci-gwfit](https://www.kaggle.com/datasets/davidmaisterx/rlab-hipsci-gwfit/versions/1) | 1 | 4.163 | 322.746 | hipsci_gw_fitness, hipsci_gw_nonfitness, hipsci_targeted_19 |
| [rlab-hipsci-gwnonfit](https://www.kaggle.com/datasets/davidmaisterx/rlab-hipsci-gwnonfit/versions/1) | 1 | 4.987 | 396.458 | hipsci_gw_fitness, hipsci_gw_nonfitness, hipsci_targeted_19 |
| [rlab-jurkat-gse249595](https://www.kaggle.com/datasets/davidmaisterx/rlab-jurkat-gse249595/versions/1) | 1 | 2.411 | 1.783.158 | GSM7951413_channel1, GSM7951414_channel2, GSM7951415_channel3, GSM7951416_channel4, GSM7951417_channel5, GSM7951418_channel6, GSM7951419_channel7, GSM7951420_channel8, GSM7951421_channel9, GSM7951422_channel10, GSM7951423_channel11, GSM7951424_channel12, GSM7951425_channel13, GSM7951426_channel14, GSM7951427_channel15, GSM7951428_channel16 |
| [rlab-kolf-small](https://www.kaggle.com/datasets/davidmaisterx/rlab-kolf-small/versions/1) | 1 | 1.592 | 161.807 | kolf_chromatin, kolf_metabolic |
| [rlab-kolf-strong](https://www.kaggle.com/datasets/davidmaisterx/rlab-kolf-strong/versions/1) | 1 | 1.573 | 232.438 | kolf_strong |

**17 archivi precedenti: 69.58 GB di shard distinti per SHA256.**
Con il nuovo ramo: **395.75 GB di grezzi perturbazionali conservati**.
Le 41.765.207 righe sommate fra i rilasci non sono una stima di cellule biologiche uniche: deduplicazione e sovrapposizioni di schermi restano da riconciliare.

## Diversità e limiti di copertura

Sono rappresentati K562, RPE1, HepG2, Jurkat, H1, iPSC/KOLF/HIPSCI, neuroni, A549, CD4/T primarie, melanoma, Calu-3, THP-1, HCT116, HEK293T e HEK293.
HIPSCI comprende 19 linee nel rilascio mirato. CD4 comprende 4 donatori × 3 stati; Frangieh 3 stati; Shifrut 4 combinazioni donatore/stimolo; Dixit 3 esperimenti; Datlinger stimolato/non stimolato. CRISPRi, CRISPRa e KO restano metadati distinti.
Il numero totale delle chiavi biologiche `(studio, contesto, donatore/clone, condizione, modalità, chimica)` va letto dai nuovi `rows.csv`: non sostituirlo con il numero di dataset o delle unità.
Tian 2019 richiede ancora la decisione QC sui droplet; Jurkat GSE249595 non ha chiamate delle guide; HIPSCI genome-wide ha controlli scarsi; gli UNASSIGNED non diventano etichette perturbazionali. Archiviazione completa non implica ammissibilità al fit.
Il catalogo completo mantiene anche sorgenti non ancora convertite/ingerite: queste non entrano nei GB dichiarati e non sono escluse per comodità.

## Basali, aggregati e ingestione parziale

L’audit Kaggle del 2 ottobre conserva anche `vcc-corpus-basale-r1`, `vcc-corpus-tahoe-r1`, aggregati e pacchetti dei modelli: 85,67 GB complessivi di file storici riletti, **comprensivi** dei 69,58 GB sopra. Non sommare i due valori.
Fonte: `reports/sorgenti/archivio_cloud_2026-10-02/kaggle_verify/esito_r2.json`. Basali e Tahoe richiedono un ruolo e un adapter espliciti; non sono pseudobulk perturbazionali.
Southard: output parziali persistenti in `Drive/vcc2026/data/processed/corpus_cellulare_2026-09-30/j09_southard_r3`; job 132 senza battito recente. Preservare shard e ricevute; un eventuale resume deve usare `--reuse`, senza ripartire da zero.

## Riutilizzo e trainer

Non usare nomi simili o “latest” come fallback: selezionare dataset/versione, manifest e hash. Montare i dati cloud; il passaggio sul portatile è facoltativo.
Un nuovo dataset aggiunge solo adattatore e derivati propri, poi una nuova versione dell’indice. Riutilizzare i derivati se input, asse, QC, codice e parametri coincidono.
Per un teammate: l’indice Git non conferisce accesso ai dataset privati. Concedere accesso ai riferimenti nominati e fornire il manifest; non condividere token.
Il trainer esteso deve integrare lettori, split D-053, hash nel runtime e ricevute di esposizione/loss anche dopo resume. I 18 fit precedenti restano un pilot aggregato. **Training esteso non ancora avviato.**
