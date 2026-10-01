# Catalogo del corpus cellulare (R-LAB)

Generato da `catalogo.py` il 1/10 dalle misure remote (`p1_r4/remote/`), dai `complete.json` dei job e dalle ricevute di pubblicazione. Stato: **misurato** dove c'è un file di prova, **scritto a mano con la sua evidenza** negli altri casi. Le cellule che entrano davvero nel training (dopo QC e identità) sono nel pre-passo di [cellnet_tecnico_2026-10-01](../../../modelli/cellnet_tecnico_2026-10-01/README.md).

## 1. Ingeriti (shard nel contratto, su Drive e su Kaggle)

| Dataset | Job e dataset Kaggle | Cellule | Stato |
|---|---|---|---|
| hepg2_nadig | J01 (job 086), pubblicato come rlab-hepg2-nadig | 145473 | nei due training, come contesto tenuto fuori (classi C e J) |
| jurkat_nadig | J05 (job 103), rlab-jurkat-nadig | 262956 | nei due training |
| h1_vcc2025_trainval | J04 (job 108), rlab-h1-vcc2025-trainval | 320200 | nei due training, train e validation letti come un esperimento: 38.176 controlli sono gli stessi nei due file e contano una volta (il test è la riserva) |
| hipsci_targeted_19 | J02 (job 088), rlab-hipsci-targeted19 | 1161865 | nei due training (526.843 cellule senza guida assegnata restano fuori dalla supervisione) |
| hipsci_gw_fitness | J02 (job 088), rlab-hipsci-gwfit | 322746 | fuori dal training: 36 NTC in tutto, da 1 a 5 per linea, sotto il minimo di 30 per chiave; rientra solo con controlli dichiarati (le cellule non assegnate come controlli chiedono prima un'analisi) |
| hipsci_gw_nonfitness | J02 (job 088), rlab-hipsci-gwnonfit | 396458 | fuori dal training: 12 NTC in tutto, come per il fitness |
| replogle_k562_gwps | J06 r2 (job 115), rlab-k562-gwps-r2 | 1989578 | nel secondo training; il dataset del 30/09, rlab-k562-gwps, ha codici al posto dei bersagli (E-20260930-003) e non entra in nessun training |
| replogle_k562_essential | J07 r7 (job 114), rlab-k562-essential | 310385 | nel secondo training |
| replogle_rpe1 | J07 r7 (job 114), rlab-rpe1 | 247914 | nel secondo training |
| jurkat_gse249595 | J03 (job 087), rlab-jurkat-gse249595 | n.d. | fuori: nessuna chiamata delle guide nel rilascio; si supervisiona dopo un'assegnazione provata |

Nel primo training: **1.890.494 cellule** prima di QC e identità; nel secondo **4.438.371**. Le cellule di training ammesse e quelle viste stanno nel pre-passo e nella copertura di ciascun training.

## 2. Misurati in remoto, non ancora ingeriti

| File | Modalità | Cellule | Formato | Adattatore | Stato e motivo |
|---|---|---|---|---|---|
| a549_GSE345058_SC_raw_normalized_counts | KO (Cas9) | 606075 | csr_matrix | h5rows, layer raw_counts | da ingerire: X non è di conteggi, i conteggi interi sono nel layer raw_counts |
| cd4_D1_Rest | CRISPRi | 3074496 | csr_matrix | h5rows | da ingerire: l'adattatore esiste (righe CSR o dense, anche via HTTP) |
| cd4_D1_Stim48hr | CRISPRi | 2805354 | csr_matrix | h5rows | da ingerire: l'adattatore esiste (righe CSR o dense, anche via HTTP) |
| cd4_D1_Stim8hr | CRISPRi | 2789727 | csr_matrix | h5rows | da ingerire: l'adattatore esiste (righe CSR o dense, anche via HTTP) |
| cd4_D2_Rest | CRISPRi | 2940194 | csr_matrix | h5rows | da ingerire: l'adattatore esiste (righe CSR o dense, anche via HTTP) |
| cd4_D2_Stim48hr | CRISPRi | 2863571 | csr_matrix | h5rows | da ingerire: l'adattatore esiste (righe CSR o dense, anche via HTTP) |
| cd4_D2_Stim8hr | CRISPRi | 3032848 | csr_matrix | h5rows | da ingerire: l'adattatore esiste (righe CSR o dense, anche via HTTP) |
| cd4_D3_Rest | CRISPRi | 2778524 | csr_matrix | h5rows | da ingerire: l'adattatore esiste (righe CSR o dense, anche via HTTP) |
| cd4_D3_Stim48hr | CRISPRi | 2607532 | csr_matrix | h5rows | da ingerire: l'adattatore esiste (righe CSR o dense, anche via HTTP) |
| cd4_D3_Stim8hr | CRISPRi | 2481284 | csr_matrix | h5rows | da ingerire: l'adattatore esiste (righe CSR o dense, anche via HTTP) |
| cd4_D4_Rest | CRISPRi | 2693903 | csr_matrix | h5rows | da ingerire: l'adattatore esiste (righe CSR o dense, anche via HTTP) |
| cd4_D4_Stim48hr | CRISPRi | 2815784 | csr_matrix | h5rows | da ingerire: l'adattatore esiste (righe CSR o dense, anche via HTTP) |
| cd4_D4_Stim8hr | CRISPRi | 2727254 | csr_matrix | h5rows | da ingerire: l'adattatore esiste (righe CSR o dense, anche via HTTP) |
| h1_train | CRISPRi | 221273 | csr_matrix | h5rows | ingerito (J04) |
| h1_val | CRISPRi | 98927 | csr_matrix | h5rows | ingerito (J04) |
| kolf_KOLF_Chromatin_Modifiers_QC_Filtered | CRISPRi | 44039 | csc_matrix | CSC da scrivere | da ingerire: serve l'adattatore per matrici ordinate per gene |
| kolf_KOLF_Metabolic_Enzymes_QC_Filtered | CRISPRi | 117768 | csc_matrix | CSC da scrivere | da ingerire: serve l'adattatore per matrici ordinate per gene |
| kolf_KOLF_Pan_Genome_QC_Filtered | CRISPRi | 2659209 | csc_matrix | CSC da scrivere | da ingerire: serve l'adattatore per matrici ordinate per gene |
| kolf_KOLF_Strong_Perturbations | CRISPRi | 232438 | dense | CSC da scrivere, layer counts | da ingerire: X non è di conteggi, i conteggi interi sono nel layer counts |
| scp_AdamsonWeissman2016_GSM2406675_10X001 | CRISPR | 5768 | csc_matrix | CSC da scrivere | da ingerire: serve l'adattatore per matrici ordinate per gene |
| scp_AdamsonWeissman2016_GSM2406677_10X005 | CRISPR | 15006 | csc_matrix | CSC da scrivere | da ingerire: serve l'adattatore per matrici ordinate per gene |
| scp_AdamsonWeissman2016_GSM2406681_10X010 | CRISPR | 65337 | csc_matrix | CSC da scrivere | da ingerire: serve l'adattatore per matrici ordinate per gene |
| scp_AissaBenevolenskaya2021 | drug | 119071 | csr_matrix | h5rows | da ingerire con testa separata; i farmaci non prevalgono sulle perturbazioni genetiche (proprietario) |
| scp_ChangYe2021 | drug | 42277 | csr_matrix | h5rows | da ingerire con testa separata; i farmaci non prevalgono sulle perturbazioni genetiche (proprietario) |
| scp_CuiHacohen2023 | cytokines | 96034 | csr_matrix | h5rows | da ingerire con testa separata; i farmaci non prevalgono sulle perturbazioni genetiche (proprietario) |
| scp_DatlingerBock2017 | CRISPR | 5905 | csr_matrix | h5rows | da ingerire: l'adattatore esiste (righe CSR o dense, anche via HTTP) |
| scp_DatlingerBock2021 | CRISPR | 39194 | csr_matrix | h5rows | da ingerire: l'adattatore esiste (righe CSR o dense, anche via HTTP) |
| scp_DixitRegev2016_K562_TFs_13_days | CRISPR | 19268 | csc_matrix | CSC da scrivere | da ingerire: serve l'adattatore per matrici ordinate per gene |
| scp_DixitRegev2016_K562_TFs_7_days | CRISPR | 33013 | csc_matrix | CSC da scrivere | da ingerire: serve l'adattatore per matrici ordinate per gene |
| scp_DixitRegev2016_K562_TFs_High_MOI | CRISPR | 51898 | csc_matrix | CSC da scrivere | da ingerire: serve l'adattatore per matrici ordinate per gene |
| scp_FrangiehIzar2021_protein | proteine (ADT) | 218331 | csc_matrix | — | fuori dalla supervisione RNA: matrice di proteine di superficie (24 feature), altro saggio; vista ausiliaria possibile |
| scp_FrangiehIzar2021_RNA | CRISPR | 218331 | csc_matrix | CSC da scrivere | da ingerire: serve l'adattatore per matrici ordinate per gene |
| scp_GasperiniShendure2019_atscale | CRISPR | 207324 | csc_matrix | CSC da scrivere | da ingerire: serve l'adattatore per matrici ordinate per gene |
| scp_GasperiniShendure2019_highMOI | CRISPR | 47650 | csc_matrix | CSC da scrivere | da ingerire: serve l'adattatore per matrici ordinate per gene |
| scp_GasperiniShendure2019_lowMOI | CRISPR | 41284 | csc_matrix | CSC da scrivere | da ingerire: serve l'adattatore per matrici ordinate per gene |
| scp_GehringPachter2019 | drug | 20382 | csr_matrix | — | fuori dalla supervisione dei conteggi: X non intero e nessun layer di conteggi grezzi |
| scp_JoungZhang2023_atlas | ORF overexpression | 1145823 | csr_matrix | — | fuori dalla supervisione dei conteggi: X non intero e nessun layer di conteggi grezzi |
| scp_JoungZhang2023_combinatorial | ORF overexpression | 167947 | csr_matrix | — | fuori dalla supervisione dei conteggi: X non intero e nessun layer di conteggi grezzi |
| scp_LaraAstiasoHuntly2023_exvivo | CRISPR-cas9 | 146793 | csr_matrix | h5rows | da ingerire: l'adattatore esiste (righe CSR o dense, anche via HTTP) |
| scp_LaraAstiasoHuntly2023_invivo | CRISPR-cas9 | 135836 | csr_matrix | h5rows | da ingerire: l'adattatore esiste (righe CSR o dense, anche via HTTP) |
| scp_LaraAstiasoHuntly2023_leukemia | CRISPR-cas9 | 182949 | csr_matrix | h5rows | da ingerire: l'adattatore esiste (righe CSR o dense, anche via HTTP) |
| scp_LiangWang2023 | CRISPR-cas9 | 41383 | csr_matrix | h5rows | da ingerire: l'adattatore esiste (righe CSR o dense, anche via HTTP) |
| scp_LotfollahiTheis2023 | drug | 63430 | csc_matrix | CSC da scrivere | da ingerire con testa separata; i farmaci non prevalgono sulle perturbazioni genetiche (proprietario) |
| scp_McFarlandTsherniak2020 | CRISPR, drug | 182875 | csc_matrix | CSC da scrivere | da ingerire: serve l'adattatore per matrici ordinate per gene |
| scp_NadigOConner2024_hepg2 | CRISPR | 145473 | dense | — | fuori: ripubblicazione scPerturb di hepg2_nadig, ingerito dal rilascio originale |
| scp_NadigOConner2024_jurkat | CRISPR | 262956 | dense | — | fuori: ripubblicazione scPerturb di jurkat_nadig, ingerito dal rilascio originale |
| scp_NormanWeissman2019_filtered | CRISPR | 111445 | csc_matrix | CSC da scrivere | da ingerire: serve l'adattatore per matrici ordinate per gene |
| scp_PapalexiSatija2021_eccite_arrayed_protein | proteine (ADT) | 8984 | csc_matrix | — | fuori dalla supervisione RNA: matrice di proteine di superficie (4 feature), altro saggio; vista ausiliaria possibile |
| scp_PapalexiSatija2021_eccite_arrayed_RNA | CRISPR | 8984 | csc_matrix | CSC da scrivere | da ingerire: serve l'adattatore per matrici ordinate per gene |
| scp_PapalexiSatija2021_eccite_protein | proteine (ADT) | 20729 | csc_matrix | — | fuori dalla supervisione RNA: matrice di proteine di superficie (4 feature), altro saggio; vista ausiliaria possibile |
| scp_PapalexiSatija2021_eccite_RNA | CRISPR | 20729 | csc_matrix | CSC da scrivere | da ingerire: serve l'adattatore per matrici ordinate per gene |
| scp_ReplogleWeissman2022_K562_essential | CRISPR | 310385 | dense | — | fuori: ripubblicazione scPerturb di replogle_k562_essential, ingerito dal rilascio originale |
| scp_ReplogleWeissman2022_K562_gwps | CRISPR | 1989578 | dense | — | fuori: ripubblicazione scPerturb di replogle_k562_gwps, ingerito dal rilascio originale |
| scp_ReplogleWeissman2022_rpe1 | CRISPR | 247914 | dense | — | fuori: ripubblicazione scPerturb di replogle_rpe1, ingerito dal rilascio originale |
| scp_SantinhaPlatt2023 | CRISPR-cas9 | 100134 | csc_matrix | CSC da scrivere | da ingerire: serve l'adattatore per matrici ordinate per gene |
| scp_SchiebingerLander2019_GSE106340 | drug | 68339 | csr_matrix | h5rows | da ingerire con testa separata; i farmaci non prevalgono sulle perturbazioni genetiche (proprietario) |
| scp_SchiebingerLander2019_GSE115943 | drug | 259155 | csr_matrix | h5rows | da ingerire con testa separata; i farmaci non prevalgono sulle perturbazioni genetiche (proprietario) |
| scp_SchraivogelSteinmetz2020_TAP_SCREEN__chromosome_11_screen | CRISPR | 120310 | csr_matrix | h5rows | da ingerire: l'adattatore esiste (righe CSR o dense, anche via HTTP) |
| scp_SchraivogelSteinmetz2020_TAP_SCREEN__chromosome_8_screen | CRISPR | 112260 | csr_matrix | h5rows | da ingerire: l'adattatore esiste (righe CSR o dense, anche via HTTP) |
| scp_ShifrutMarson2018 | CRISPR | 52236 | csr_matrix | h5rows | da ingerire: l'adattatore esiste (righe CSR o dense, anche via HTTP) |
| scp_SrivatsanTrapnell2020_sciplex2 | drug | 24262 | csr_matrix | h5rows | da ingerire con testa separata; i farmaci non prevalgono sulle perturbazioni genetiche (proprietario) |
| scp_SrivatsanTrapnell2020_sciplex3 | drug | 799317 | csr_matrix | h5rows | da ingerire con testa separata; i farmaci non prevalgono sulle perturbazioni genetiche (proprietario) |
| scp_SrivatsanTrapnell2020_sciplex4 | drug | 98437 | csr_matrix | h5rows | da ingerire con testa separata; i farmaci non prevalgono sulle perturbazioni genetiche (proprietario) |
| scp_SunshineHein2023 | CRISPR-cas9 | 90380 | csc_matrix | CSC da scrivere | da ingerire: serve l'adattatore per matrici ordinate per gene |
| scp_TianKampmann2019_day7neuron | CRISPR | 182790 | csc_matrix | CSC da scrivere | da ingerire: serve l'adattatore per matrici ordinate per gene |
| scp_TianKampmann2019_iPSC | CRISPR | 275708 | csc_matrix | CSC da scrivere | da ingerire: serve l'adattatore per matrici ordinate per gene |
| scp_TianKampmann2021_CRISPRa | CRISPR | 21193 | csc_matrix | CSC da scrivere | da ingerire: serve l'adattatore per matrici ordinate per gene |
| scp_TianKampmann2021_CRISPRi | CRISPR | 32300 | csc_matrix | CSC da scrivere | da ingerire: serve l'adattatore per matrici ordinate per gene |
| scp_WeinrebKlein2020 | cytokine | 65075 | csr_matrix | — | fuori dalla supervisione dei conteggi: X non intero e nessun layer di conteggi grezzi |
| scp_WesselsSatija2023 | CRISPR-cas13 | 30707 | csr_matrix | h5rows | da ingerire: l'adattatore esiste (righe CSR o dense, anche via HTTP) |
| scp_XieHon2017 | CRISPR | 13283 | dense | h5rows | da ingerire: l'adattatore esiste (righe CSR o dense, anche via HTTP) |
| scp_XuCao2023 | CRISPRi | 98315 | csc_matrix | CSC da scrivere | da ingerire: serve l'adattatore per matrici ordinate per gene |
| scp_ZhaoSims2021 | drug | 165748 | csr_matrix | h5rows | da ingerire con testa separata; i farmaci non prevalgono sulle perturbazioni genetiche (proprietario) |
| southard_fibroblast_CRISPRa_final_pop | CRISPRa | 447301 | csr_matrix | h5rows | da ingerire: l'adattatore esiste (righe CSR o dense, anche via HTTP) |
| southard_fibroblast_CRISPRa_mean_pop | CRISPRa | 10916 | dense | — | solo aggregati: medie per popolazione (vedi sorgenti solo aggregate) |
| southard_RPE1_CRISPRa_final_population | CRISPRa | 850225 | csr_matrix | h5rows | da ingerire: l'adattatore esiste (righe CSR o dense, anche via HTTP) |
| southard_RPE1_CRISPRa_mean_pop | CRISPRa | 10912 | dense | — | solo aggregati: medie per popolazione (vedi sorgenti solo aggregate) |

Per stato: da ingerire: 51; da ingerire con testa separata; i farmaci non prevalgono sulle perturbazioni genetiche (proprietario): 10; fuori: 5; fuori dalla supervisione RNA: 3; fuori dalla supervisione dei conteggi: 4; ingerito (J04): 2; solo aggregati: 2.

## 3. Sorgenti solo aggregate (dichiarate a parte)

| Sorgente | Studio | Che cosa c'è | Nota |
|---|---|---|---|
| dld1_gse337988 | DLD-1, GSE337988 | effetti (LFC e SE su un pannello di risposte) | file per cellula da verificare |
| mixscale (parte DE) | Mixscale, Zenodo 14518762 | espressione differenziale per linea e stimolo | le cellule esistono come oggetti Seurat (IFNG, IFNB, INS, TGFB, TNFA): servono R e un adattatore |
| southard_*_mean_pop | Southard 2025, medie per popolazione | medie con p e p aggiustati (matrici dense non intere) | le cellule sono nei file final_pop dello stesso studio |
| depmap_24q4 | DepMap 24Q4 | bulk basale (espressione e dipendenza) | covariate ausiliarie, mai supervisione |
| catalogo_accessioni | 77 accessioni del catalogo del 26/09 | solo menzioni | da riconciliare una per una |

## 4. Sorgenti note senza misura remota

Orion (HCT116, HEK293T: parquet su Hugging Face, licenza non commerciale), Tahoe-100M (parquet; farmaci, con la cautela del proprietario), VIPerturb-seq (RDS prefiltrato: serve R), microglia GSE335887 e PerturbFate GSE291147 (non acquisiti), scBaseCount (a pagamento per chi legge): i loro dati per cellula esistono ma serve un lettore o un via, come scritto in `sources.yaml`.
