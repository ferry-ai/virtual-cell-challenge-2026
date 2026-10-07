# Registro canonico delle fonti

Generato da `registro.py` (2026-10-07T00:04). Non si modifica a mano: si rigenera in un file nuovo.
Una riga per unita di banca; i record del catalogo e gli alias stanno nel JSON accanto.

## Fonti operative (un solo ingresso per tabella)

| Fonte | Ruolo | Unita di banca | Bersagli del pannello votati | Letta dal fit | sha256 tabella |
|---|---|---|---:|---|---|
| `cd4_mix` | voto | D1_Rest, D1_Stim8hr, D1_Stim48hr, D2_Rest, D2_Stim8hr, D2_Stim48hr, D3_Rest, D3_Stim8hr, D3_Stim48hr, D4_Rest, D4_Stim8hr, D4_Stim48hr | 293 | si | `ccde53b7546e` |
| `h1` | voto | h1_train, h1_val | 17 | si | `672e36e33006` |
| `hepg2_nadig` | voto | hepg2_nadig | 0 | si | `f0deff3c55e9` |
| `hipsci_targeted_19` | voto (**nuova**) | hipsci_targeted_19 | 5 | si | `150cf45f1b36` |
| `jurkat_nadig` | voto | jurkat_nadig | 0 | si | `6d458e589897` |
| `k562` | voto | nessuna: tabella storica | 272 | si | `a37c78ce1f7c` |
| `k562_essential` | voto | k562_essential | 0 | si | `510dec23350f` |
| `kolf_chromatin` | voto | kolf_chromatin | 8 | si | `f93a45edbb9b` |
| `kolf_metabolic` | voto | kolf_metabolic | 4 | si | `5dcd8a6e726c` |
| `kolf_pan_genome` | voto | kolf_pan_genome | 282 | si | `cdc53d288a4b` |
| `kolf_strong` | voto | kolf_strong | 55 | si | `66b45affac13` |
| `orion_hct116` | voto | orion_hct116 | 293 | si | `e3376fa8532d` |
| `orion_hek293t` | voto | orion_hek293t | 299 | si | `efcf76ac67e0` |
| `rpe1` | voto | rpe1 | 0 | si | `89c0d2405438` |
| `tian2019_neuron` | voto (**nuova**) | tian2019_neuron | 1 | si | `6a550857b838` |
| `tian2021_crispri` | voto (**nuova**) | tian2021_crispri | 6 | si | `aed4a1193382` |
| `xu2023` | voto (**nuova**) | xu2023 | 5 | si | `8599c88644b0` |
| `a549_ko` | braccio KO, non votato | a549_ko |  | no | `b023a3975720` |
| `dixit2016` | braccio KO, non votato | dixit2016_d7, dixit2016_d13, dixit2016_high_moi |  | no | `bc651e8296df` |
| `frangieh2021` | braccio KO, non votato | frangieh2021 |  | no | `32b29f859537` |
| `k562_gwps_sc` | stesso esperimento di k562 BULK: equivalenza, mai secondo voto | k562_gwps_a, k562_gwps_b |  | no | `8c0e2f980fea` |
| `norman2019` | braccio CRISPRa, non votato | norman2019 |  | no | `f42db7cbef90` |
| `shifrut2018` | braccio KO, non votato | shifrut2018 |  | no | `54adc9d4a353` |
| `sunshine2023` | braccio KO, non votato | sunshine2023 |  | no | `d91d811a2d53` |
| `tian2019_ipsc` | derivata, non ammessa al voto (regola del verso) | tian2019_ipsc |  | no | `d06809e44157` |
| `tian2021_crispra` | braccio CRISPRa, non votato | tian2021_crispra |  | no | `3aa3d95ceef5` |

## Unita di banca

| Unita | Studio | Linea | Modalita | Chimica | Contesti | Donatori/cloni | Cellule | Controlli | Bersagli (pannello) | Grezzo GB | Banca+campioni GB | Destinazione |
|---|---|---|---|---|---:|---:|---:|---:|---|---:|---:|---|
| `D1_Rest` | cd4_marson2025 | CD4T | CRISPRi | 10x Flex | 1 | 1 | 1750820 | 76543 | 12091 (293) |  | 9.651 | `cd4_mix`: voto |
| `D2_Rest` | cd4_marson2025 | CD4T | CRISPRi | 10x Flex | 1 | 1 | 1981060 | 83987 | 12062 (293) |  | 8.877 | `cd4_mix`: voto |
| `D3_Rest` | cd4_marson2025 | CD4T | CRISPRi | 10x Flex | 1 | 1 | 1901024 | 76823 | 11941 (289) |  | 9.268 | `cd4_mix`: voto |
| `D1_Stim8hr` | cd4_marson2025 | CD4T | CRISPRi | 10x Flex | 1 | 1 | 1605685 | 69632 | 12176 (293) |  | 11.057 | `cd4_mix`: voto |
| `D2_Stim8hr` | cd4_marson2025 | CD4T | CRISPRi | 10x Flex | 1 | 1 | 2086574 | 88354 | 12228 (293) |  | 10.93 | `cd4_mix`: voto |
| `D3_Stim8hr` | cd4_marson2025 | CD4T | CRISPRi | 10x Flex | 1 | 1 | 1691290 | 68441 | 12032 (292) |  | 10.328 | `cd4_mix`: voto |
| `D1_Stim48hr` | cd4_marson2025 | CD4T | CRISPRi | 10x Flex | 1 | 1 | 1646772 | 73534 | 12161 (293) |  | 11.844 | `cd4_mix`: voto |
| `D2_Stim48hr` | cd4_marson2025 | CD4T | CRISPRi | 10x Flex | 1 | 1 | 2050788 | 87747 | 12070 (290) |  | 9.413 | `cd4_mix`: voto |
| `D3_Stim48hr` | cd4_marson2025 | CD4T | CRISPRi | 10x Flex | 1 | 1 | 1885549 | 77334 | 11830 (287) |  | 9.83 | `cd4_mix`: voto |
| `D4_Rest` | cd4_marson2025 | CD4T | CRISPRi | 10x Flex | 1 | 1 | 1747709 | 76636 | 12407 (294) |  | 10.219 | `cd4_mix`: voto |
| `D4_Stim8hr` | cd4_marson2025 | CD4T | CRISPRi | 10x Flex | 1 | 1 | 1755121 | 77030 | 12456 (297) |  | 11.47 | `cd4_mix`: voto |
| `D4_Stim48hr` | cd4_marson2025 | CD4T | CRISPRi | 10x Flex | 1 | 1 | 1878125 | 83474 | 12414 (294) |  | 13.104 | `cd4_mix`: voto |
| `kolf_pan_genome` | kolf_pan_genome | iPSC | CRISPRi | MISSING | 1 | n.r. | 2659209 | 146747 | 11687 (282) |  | 9.189 | `kolf_pan_genome`: voto |
| `orion_hct116` | orion_hct116 | HCT116 | CRISPRi | MISSING | 1 | n.r. | 3409169 | 165777 | 18293 (300) |  | 21.173 | `orion_hct116`: voto |
| `orion_hek293t` | orion_hek293t | HEK293T | CRISPRi | MISSING | 1 | n.r. | 4534299 | 218838 | 18311 (300) |  | 30.395 | `orion_hek293t`: voto |
| `hepg2_nadig` | hepg2_nadig | HepG2 | CRISPRi | 10x 3' | 1 | n.r. | 145473 | 4976 | 2393 (0) | 1.332 | 1.322 | `hepg2_nadig`: voto |
| `jurkat_nadig` | jurkat_nadig | Jurkat | CRISPRi | 10x 3' | 1 | n.r. | 262956 | 12013 | 2393 (0) | 2.04 | 1.565 | `jurkat_nadig`: voto |
| `h1_train` | h1_vcc2025_train | H1 | CRISPRi | 10x Flex | 1 | n.r. | 221273 | 38176 | 150 (13) | 4.41 | 0.413 | `h1`: voto |
| `h1_val` | h1_vcc2025_val | H1 | CRISPRi | 10x Flex | 1 | n.r. | 98927 | 38176 | 50 (4) | 1.974 | 0.16 | `h1`: voto |
| `rpe1` | replogle_rpe1 | RPE1 | CRISPRi | 10x 3' v3 | 1 | n.r. | 247914 | 11485 | 2393 (0) | 1.947 | 1.463 | `rpe1`: voto |
| `k562_essential` | replogle_k562_essential | K562 | CRISPRi | 10x 3' v3 | 1 | n.r. | 310385 | 10691 | 2057 (0) | 2.472 | 1.601 | `k562_essential`: voto |
| `datlinger2017` | datlinger2017_jurkat_ko | Jurkat | KO | CROP-seq | 2 | n.r. | 5905 | 1320 | 96 (0) | 0.041 | 0.04 | in banca, non derivata: native labels are guide names with library prefix and guide number; no exact panel symbol, a declared guide-to-gene map is required |
| `datlinger2021` | datlinger2021_jurkat_ko | Jurkat | KO | scifi-RNA-seq | 2 | n.r. | 39194 | 4497 | 40 (0) | 0.039 | 0.016 | in banca, non derivata: native labels are guide names with guide number; no exact panel symbol, a declared guide-to-gene map is required |
| `shifrut2018` | shifrut2018_tcells_ko | CD4T | KO | 10x | 4 | 2 | 52236 | 3541 | 20 (1) | 0.263 | 0.052 | `shifrut2018`: braccio KO, non votato |
| `dixit2016_d13` | dixit2016_k562_ko | K562 | KO | 10x (Perturb-seq) | 1 | n.r. | 19268 | 3491 | 10 (2) | 0.128 | 0.009 | `dixit2016`: braccio KO, non votato |
| `dixit2016_d7` | dixit2016_k562_ko | K562 | KO | 10x (Perturb-seq) | 1 | n.r. | 33013 | 5381 | 10 (2) | 0.276 | 0.012 | `dixit2016`: braccio KO, non votato |
| `dixit2016_high_moi` | dixit2016_k562_ko | K562 | KO | 10x (Perturb-seq) | 1 | n.r. | 51898 | 10492 | 10 (2) | 0.359 | 0.014 | `dixit2016`: braccio KO, non votato |
| `xu2023` | xu2023_hek293_crispri | HEK293 | CRISPRi | 10x 3' | 1 | n.r. | 98315 | 2758 | 203 (5) | 0.343 | 0.084 | `xu2023`: voto |
| `kolf_chromatin` | kolf_chromatin_modifiers | iPSC | CRISPRi | MISSING | 1 | n.r. | 44039 | 7161 | 107 (8) | 0.614 | 0.187 | `kolf_chromatin`: voto |
| `kolf_metabolic` | kolf_metabolic_enzymes | iPSC | CRISPRi | MISSING | 1 | n.r. | 117768 | 18651 | 97 (4) | 0.978 | 0.105 | `kolf_metabolic`: voto |
| `kolf_strong` | kolf_strong_perturbations | iPSC | CRISPRi | MISSING | 1 | n.r. | 232438 | 35424 | 1655 (55) | 1.573 | 1.121 | `kolf_strong`: voto |
| `norman2019` | norman2019_crispra | K562 | CRISPRa | 10x 3' | 1 | n.r. | 111445 | 11855 | 236 (3) | 0.837 | 0.196 | `norman2019`: braccio CRISPRa, non votato |
| `tian2019_ipsc` | tian2019_ipsc | iPSC | CRISPRi | 10x 3' | 1 | n.r. | 271223 | 10401 | 39161 (1) | 0.441 | 0.779 | `tian2019_ipsc`: derivata, non ammessa al voto (regola del verso) |
| `tian2019_neuron` | tian2019_neuron_day7 | neuron | CRISPRi | 10x 3' | 1 | n.r. | 179174 | 15083 | 41357 (1) | 0.327 | 0.55 | `tian2019_neuron`: voto |
| `tian2021_crispra` | tian2021_crispra | neuron | CRISPRa | 10x 3' | 1 | n.r. | 21193 | 434 | 100 (4) | 0.171 | 0.098 | `tian2021_crispra`: braccio CRISPRa, non votato |
| `tian2021_crispri` | tian2021_crispri | neuron | CRISPRi | 10x 3' | 1 | n.r. | 32300 | 437 | 184 (6) | 0.316 | 0.226 | `tian2021_crispri`: voto |
| `a549_ko` | a549_liu_hillsley2026 | A549 | KO | MISSING | 1 | n.r. | 606075 | 45320 | 1000 (21) | 7.652 | 1.639 | `a549_ko`: braccio KO, non votato |
| `hipsci_gw_fitness` | hipsci_gw_fitness | iPSC | CRISPRi | MISSING | 60 | 24 | 322746 | 36 | 2252 (31) | 4.163 | 3.328 | in banca, non derivata: controls: see piano; non-targeting cells are too few to give every clone matched controls with the original estimator |
| `hipsci_gw_nonfitness` | hipsci_gw_nonfitness | iPSC | CRISPRi | MISSING | 40 | 34 | 396458 | 12 | 4954 (166) | 4.987 | 3.773 | in banca, non derivata: controls: see piano; non-targeting cells are too few to give every clone matched controls with the original estimator |
| `frangieh2021` | frangieh2021_melanoma_ko | melanoma | KO | 10x 3' v3 | 3 | n.r. | 218331 | 57605 | 248 (5) | 1.644 | 0.831 | `frangieh2021`: braccio KO, non votato |
| `papalexi2021_arrayed` | papalexi2021_thp1_arrayed_ko | THP1 | KO | 10x 3' (ECCITE) | 1 | n.r. | 8984 | 2009 | 10 (1) | 0.054 | 0.008 | in banca, non derivata: one panel symbol with 4 cells, below min_cells 10 of the original recipe |
| `sunshine2023` | sunshine2023_calu3_ko | Calu3 | KO | 10x 3' | 1 | n.r. | 90380 | 3536 | 24194 (6) | 0.791 | 1.146 | `sunshine2023`: braccio KO, non votato |
| `hipsci_targeted_19` | hipsci_targeted_19 | iPSC | CRISPRi | MISSING | 19 | 19 | 1161865 | 8241 | 444 (5) | 13.03 | 7.449 | `hipsci_targeted_19`: voto |
| `k562_gwps_a` | replogle_k562_gwps | K562 | CRISPRi | 10x 3' v3 | 1 | n.r. | 1000000 | 37785 | 9864 (272) | 7.068 | 6.251 | `k562_gwps_sc`: stesso esperimento di k562 BULK: equivalenza, mai secondo voto |
| `k562_gwps_b` | replogle_k562_gwps | K562 | CRISPRi | 10x 3' v3 | 1 | n.r. | 989578 | 37543 | 9866 (272) | 6.905 | 6.127 | `k562_gwps_sc`: stesso esperimento di k562 BULK: equivalenza, mai secondo voto |

## Record del catalogo r4 senza banca

| Record | Stato dichiarato dal catalogo |
|---|---|
| `remote/scp_AdamsonWeissman2016_GSM2406675_10X001` | non in banca: da ingerire: i controlli sono nomi di plasmidi (62(mod)_pBA581, 63(mod)_pBA580): serve una mappa delle etichette dichiarata |
| `remote/scp_AdamsonWeissman2016_GSM2406677_10X005` | non in banca: da ingerire: come l'altro file di Adamson, serve una mappa delle etichette |
| `remote/scp_AdamsonWeissman2016_GSM2406681_10X010` | non in banca: da ingerire: come l'altro file di Adamson, serve una mappa delle etichette |
| `remote/scp_AissaBenevolenskaya2021` | non in banca: da ingerire con testa separata; i farmaci non prevalgono sulle perturbazioni genetiche (proprietario) |
| `remote/scp_ChangYe2021` | non in banca: da ingerire con testa separata; i farmaci non prevalgono sulle perturbazioni genetiche (proprietario) |
| `remote/scp_CuiHacohen2023` | non in banca: da ingerire con testa separata; i farmaci non prevalgono sulle perturbazioni genetiche (proprietario) |
| `remote/scp_FrangiehIzar2021_protein` | non in banca: fuori dalla supervisione RNA: matrice di proteine di superficie (24 feature), altro saggio; vista ausiliaria possibile |
| `remote/scp_GasperiniShendure2019_atscale` | non in banca: fuori per ora: schermo di enhancer, i bersagli non sono geni |
| `remote/scp_GasperiniShendure2019_highMOI` | non in banca: fuori per ora: schermo di enhancer, i bersagli non sono geni |
| `remote/scp_GasperiniShendure2019_lowMOI` | non in banca: fuori per ora: schermo di enhancer, i bersagli non sono geni |
| `remote/scp_GehringPachter2019` | non in banca: fuori dalla supervisione dei conteggi: X non intero e nessun layer di conteggi grezzi |
| `remote/scp_JoungZhang2023_atlas` | non in banca: fuori dalla supervisione dei conteggi: X non intero e nessun layer di conteggi grezzi |
| `remote/scp_JoungZhang2023_combinatorial` | non in banca: fuori dalla supervisione dei conteggi: X non intero e nessun layer di conteggi grezzi |
| `remote/scp_LaraAstiasoHuntly2023_exvivo` | non in banca: fuori: topo (l'asse è umano) |
| `remote/scp_LaraAstiasoHuntly2023_invivo` | non in banca: fuori: topo (l'asse è umano) |
| `remote/scp_LaraAstiasoHuntly2023_leukemia` | non in banca: fuori: topo (l'asse è umano) |
| `remote/scp_LiangWang2023` | non in banca: fuori: topo (l'asse è umano) |
| `remote/scp_LotfollahiTheis2023` | non in banca: da ingerire con testa separata; i farmaci non prevalgono sulle perturbazioni genetiche (proprietario) |
| `remote/scp_McFarlandTsherniak2020` | non in banca: da ingerire con testa separata: farmaci e CRISPR nello stesso file; i farmaci non prevalgono (proprietario) |
| `remote/scp_PapalexiSatija2021_eccite_arrayed_protein` | non in banca: fuori dalla supervisione RNA: matrice di proteine di superficie (4 feature), altro saggio; vista ausiliaria possibile |
| `remote/scp_PapalexiSatija2021_eccite_protein` | non in banca: fuori dalla supervisione RNA: matrice di proteine di superficie (4 feature), altro saggio; vista ausiliaria possibile |
| `remote/scp_PapalexiSatija2021_eccite_RNA` | non in banca: da ingerire: etichette GENEg1 senza separatore, serve una mappa dichiarata; la parte arrayed è in coda |
| `remote/scp_SantinhaPlatt2023` | non in banca: fuori: topo (l'asse è umano) |
| `remote/scp_SchiebingerLander2019_GSE106340` | non in banca: da ingerire con testa separata; i farmaci non prevalgono sulle perturbazioni genetiche (proprietario) |
| `remote/scp_SchiebingerLander2019_GSE115943` | non in banca: da ingerire con testa separata; i farmaci non prevalgono sulle perturbazioni genetiche (proprietario) |
| `remote/scp_SchraivogelSteinmetz2020_TAP_SCREEN__chromosome_11_screen` | non in banca: fuori per ora: enhancer, e TAP-seq misura un pannello di geni |
| `remote/scp_SchraivogelSteinmetz2020_TAP_SCREEN__chromosome_8_screen` | non in banca: fuori per ora: enhancer, e TAP-seq misura un pannello di geni |
| `remote/scp_SrivatsanTrapnell2020_sciplex2` | non in banca: da ingerire con testa separata; i farmaci non prevalgono sulle perturbazioni genetiche (proprietario) |
| `remote/scp_SrivatsanTrapnell2020_sciplex3` | non in banca: da ingerire con testa separata; i farmaci non prevalgono sulle perturbazioni genetiche (proprietario) |
| `remote/scp_SrivatsanTrapnell2020_sciplex4` | non in banca: da ingerire con testa separata; i farmaci non prevalgono sulle perturbazioni genetiche (proprietario) |
| `remote/scp_WeinrebKlein2020` | non in banca: fuori dalla supervisione dei conteggi: X non intero e nessun layer di conteggi grezzi |
| `remote/scp_WesselsSatija2023` | non in banca: fuori per ora: coppie di guide Cas13 per cellula (combinate), nessun gene singolo |
| `remote/scp_XieHon2017` | non in banca: fuori per ora: schermo di enhancer, i bersagli non sono geni |
| `remote/scp_ZhaoSims2021` | non in banca: da ingerire con testa separata; i farmaci non prevalgono sulle perturbazioni genetiche (proprietario) |
| `remote/southard_fibroblast_CRISPRa_final_pop` | non in banca: in ingestione (J09, job 125): vedi §1 |
| `remote/southard_fibroblast_CRISPRa_mean_pop` | non in banca: solo aggregati: medie per popolazione (vedi sorgenti solo aggregate) |
| `remote/southard_RPE1_CRISPRa_final_population` | non in banca: in ingestione (J09, job 125): vedi §1 |
| `remote/southard_RPE1_CRISPRa_mean_pop` | non in banca: solo aggregati: medie per popolazione (vedi sorgenti solo aggregate) |
| `ingested/southard` | non in banca: in ingestione: RPE1 850.225 e Hs27 447.301 cellule (CRISPRa), lette da Zenodo a circa uno shard ogni 9 minuti; fuori dal terzo training perché non pubblicato al lancio del suo pre-passo |
| `ingested/jurkat_gse249595` | solo archivio grezzo (davidmaisterx/rlab-jurkat-gse249595): nessuna banca: fuori: nessuna chiamata delle guide nel rilascio; si supervisiona dopo un'assegnazione provata |
| `aggregate_only/dld1_gse337988` | non in banca: DLD-1, GSE337988 ; effetti (LFC e SE su un pannello di risposte) ; file per cellula da verificare |
| `aggregate_only/mixscale (parte DE)` | non in banca: Mixscale, Zenodo 14518762 ; espressione differenziale per linea e stimolo ; le cellule esistono come oggetti Seurat (IFNG, IFNB, INS, TGFB, TNFA): servono R e un adattatore |
| `aggregate_only/southard_*_mean_pop` | non in banca: Southard 2025, medie per popolazione ; medie con p e p aggiustati (matrici dense non intere) ; le cellule sono nei file final_pop dello stesso studio |
| `aggregate_only/depmap_24q4` | non in banca: DepMap 24Q4 ; bulk basale (espressione e dipendenza) ; covariate ausiliarie, mai supervisione |
| `aggregate_only/catalogo_accessioni` | non in banca: 77 accessioni del catalogo del 26/09 ; solo menzioni ; da riconciliare una per una |
