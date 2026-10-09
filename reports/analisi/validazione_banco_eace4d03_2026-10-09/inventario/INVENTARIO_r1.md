# Inventario della banca per la valutazione

Scritto da `inventario/inventario.py` dai metadati committati (registro canonico del 7/10, registro d'uso di T3, manifest dei fold v2); nessun dato letto e nessuna ingestione rifatta. **«In banca» non vuol dire «verità utilizzabile»**: la colonna del ruolo applica una regola ai numeri dell'unità, e ogni lacuna è nominata. Donatori, condizioni e librerie della stessa linea non sono lignaggi. Tutti i lignaggi sono **sviluppo**.

Regole: fold a sei membri sul pannello con almeno 30 bersagli del pannello, 10 cellule per bersaglio e 100 controlli; lettura descrittiva da 3 bersagli; CRISPRi, KO e CRISPRa separati.

## 1. Per lignaggio

| Lignaggio | Studi | Modalità | Cellule in banca | Verità oggi: spazio degli effetti | Verità oggi: sei membri | Pronto per i sei membri (cellule in banca) | Altre letture possibili | Da quando è fonte, e dove è già entrato |
|---|---|---|---:|---|---|---|---|---|
| **K562** | 4 | CRISPRa, CRISPRi, KO | 2.515.587 | C-K562 (`k562`) | 272 bersagli, 7.679 geni | `k562_gwps_a` (272 bersagli), `k562_gwps_b` (272 bersagli) | fuori pannello: `k562_essential` (2.057 bersagli) | dal primo transfer inviato (t02, 17/09). testa cis stimata su coppie di K562 genome-wide; ampiezza 1,576 ed emissione ×1,5 nate anche su banchi di K562; linea di conferma del cubo r2 (D-056); fold C-K562 di livello A e B dall'8/10; l'ipotesi «senza KOLF» nasce su questo fold; validazione interna del fit AMMI C-iPSC |
| **CD4T** | 2 | CRISPRi, KO | 22.032.753 | C-CD4T (`cd4_Rest`, `cd4_Stim8hr`, `cd4_Stim48hr`) | — | `D1_Rest` (293 bersagli), `D2_Rest` (293 bersagli), `D3_Rest` (289 bersagli), `D1_Stim8hr` (293 bersagli), `D2_Stim8hr` (293 bersagli), `D3_Stim8hr` (292 bersagli), `D1_Stim48hr` (293 bersagli), `D2_Stim48hr` (290 bersagli), `D3_Stim48hr` (287 bersagli), `D4_Rest` (294 bersagli), `D4_Stim8hr` (297 bersagli), `D4_Stim48hr` (294 bersagli) | — | t08, 22/09. fold C-CD4T di livello A dall'8/10; validazione interna del fit AMMI C-K562 |
| **HCT116** | 1 | CRISPRi | 3.409.169 | C-HCT116 (`orion_hct116`) | — | `orion_hct116` (300 bersagli) | — | t11, 23/09. fold C-HCT116 di livello A dall'8/10 |
| **HEK293** | 2 | CRISPRi | 4.632.614 | C-HEK293 (`orion_hek293t`) | — | `orion_hek293t` (300 bersagli) | descrittive: `xu2023` CRISPRi, 5 | t17 (24/09) e, nella ricetta di riferimento, t22 (26/09); Xu 2023 dal fit T1 (8/10). fold C-HEK293 di livello A dall'8/10 |
| **iPSC** | 8 | CRISPRi | 5.205.746 | C-iPSC (`kolf_pan_genome`, `kolf_strong`) | 55 bersagli, 18.106 geni | `kolf_pan_genome` (282 bersagli), `kolf_strong` (55 bersagli) | descrittive: `kolf_chromatin` CRISPRi, 8, `kolf_metabolic` CRISPRi, 4, `hipsci_targeted_19` CRISPRi, 5; fuori pannello: `tian2019_ipsc` (39.161 bersagli) | t36, 5/10 (quattro tabelle KOLF2.1J); HIPSCI mirato dal fit T1 (8/10). fold C-iPSC di livello A e B dall'8/10; il ridge ESM2 senza contesto mostra segnale nel regime T solo contro questa verità |
| **H1** | 2 | CRISPRi | 320.200 | C-H1 (`h1`) | — | — | descrittive: `h1_train` CRISPRi, 13, `h1_val` CRISPRi, 4 | t36, 5/10 (train e val insieme). linea di sviluppo del cubo r2 (D-056); fold C-H1 di livello A, 17 bersagli; H1 test: protetta, mai letta |
| **neuron** | 3 | CRISPRa, CRISPRi | 232.667 | — | — | — | descrittive: `tian2021_crispri` CRISPRi, 6; fuori pannello: `tian2019_neuron` (41.357 bersagli) | fit T1, 8/10 (Tian 2021 CRISPRi, sei bersagli); nel t38 dal 9/10. nessun fold lo tiene fuori |
| **HepG2** | 1 | CRISPRi | 145.473 | — | — | — | fuori pannello: `hepg2_nadig` (2.393 bersagli) | mai fonte del pannello (zero bersagli del pannello). banco HepG2 v2: su questo banco è stato scelto il generatore del t28; linea di sviluppo del cubo r2; la rete esportata nel t30 è quella del fold HepG2; ampiezza nata anche su banchi K562 → HepG2 |
| **Jurkat** | 3 | CRISPRi, KO | 308.055 | — | — | — | fuori pannello: `jurkat_nadig` (2.393 bersagli) | mai fonte del pannello (zero bersagli del pannello). linea di conferma del cubo r2 (D-056) |
| **RPE1** | 1 | CRISPRi | 247.914 | — | — | — | fuori pannello: `rpe1` (2.393 bersagli) | mai fonte del pannello (zero bersagli del pannello). linea di sviluppo del cubo r2 (D-056) |
| **A549** | 1 | KO | 606.075 | — | — | — | descrittive: `a549_ko` KO, 21 | t38, 9/10: voto KO a peso 0,25. nessun banco lo ha valutato |
| **Calu3** | 1 | KO | 90.380 | — | — | — | descrittive: `sunshine2023` KO, 6 | t38, 9/10: voto KO a peso 0,25. nessun banco lo ha valutato |
| **melanoma** | 1 | KO | 218.331 | — | — | — | descrittive: `frangieh2021` KO, 5 | t38, 9/10: voto KO a peso 0,25. nessun banco lo ha valutato |
| **THP1** | 1 | KO | 8.984 | — | — | — | — | mai: in banca, non derivata. nessun uso |

45 unità in 14 lignaggi. Con un fold nello spazio degli effetti: 6. Con un fold a sei membri oggi: 2. Con cellule in banca sufficienti per un fold a sei membri: CD4T, HCT116, HEK293, K562, iPSC.

## 2. Per unità di banca

| Unità | Lignaggio | Studio | Modalità | Chimica | Contesti; donatori o cloni; condizioni | Cellule: tutte / controlli / bersagli del pannello | Bersagli: nativi / pannello | Cellule per bersaglio del pannello | Tabella di effetti | Uso nel t38 | Ruolo possibile nella valutazione | Lacune |
|---|---|---|---|---|---|---|---|---:|---|---|---|---|
| `D1_Rest` | CD4T | cd4_marson2025 | CRISPRi | 10x Flex | 1; 1; Rest | 1.750.820 / 76.543 / 35.180 | 12.091 / 293 | 120 | `cd4_mix` | voto CRISPRi | fold del pannello a sei membri (livello B) | — |
| `D2_Rest` | CD4T | cd4_marson2025 | CRISPRi | 10x Flex | 1; 1; Rest | 1.981.060 / 83.987 / 45.657 | 12.062 / 293 | 156 | `cd4_mix` | voto CRISPRi | fold del pannello a sei membri (livello B) | — |
| `D3_Rest` | CD4T | cd4_marson2025 | CRISPRi | 10x Flex | 1; 1; Rest | 1.901.024 / 76.823 / 45.239 | 11.941 / 289 | 157 | `cd4_mix` | voto CRISPRi | fold del pannello a sei membri (livello B) | — |
| `D1_Stim8hr` | CD4T | cd4_marson2025 | CRISPRi | 10x Flex | 1; 1; Stim8hr | 1.605.685 / 69.632 / 32.870 | 12.176 / 293 | 112 | `cd4_mix` | voto CRISPRi | fold del pannello a sei membri (livello B) | — |
| `D2_Stim8hr` | CD4T | cd4_marson2025 | CRISPRi | 10x Flex | 1; 1; Stim8hr | 2.086.574 / 88.354 / 49.777 | 12.228 / 293 | 170 | `cd4_mix` | voto CRISPRi | fold del pannello a sei membri (livello B) | — |
| `D3_Stim8hr` | CD4T | cd4_marson2025 | CRISPRi | 10x Flex | 1; 1; Stim8hr | 1.691.290 / 68.441 / 40.100 | 12.032 / 292 | 137 | `cd4_mix` | voto CRISPRi | fold del pannello a sei membri (livello B) | — |
| `D1_Stim48hr` | CD4T | cd4_marson2025 | CRISPRi | 10x Flex | 1; 1; Stim48hr | 1.646.772 / 73.534 / 34.489 | 12.161 / 293 | 118 | `cd4_mix` | voto CRISPRi | fold del pannello a sei membri (livello B) | — |
| `D2_Stim48hr` | CD4T | cd4_marson2025 | CRISPRi | 10x Flex | 1; 1; Stim48hr | 2.050.788 / 87.747 / 47.842 | 12.070 / 290 | 165 | `cd4_mix` | voto CRISPRi | fold del pannello a sei membri (livello B) | — |
| `D3_Stim48hr` | CD4T | cd4_marson2025 | CRISPRi | 10x Flex | 1; 1; Stim48hr | 1.885.549 / 77.334 / 43.893 | 11.830 / 287 | 153 | `cd4_mix` | voto CRISPRi | fold del pannello a sei membri (livello B) | — |
| `D4_Rest` | CD4T | cd4_marson2025 | CRISPRi | 10x Flex | 1; 1; Rest | 1.747.709 / 76.636 / 40.135 | 12.407 / 294 | 137 | `cd4_mix` | voto CRISPRi | fold del pannello a sei membri (livello B) | — |
| `D4_Stim8hr` | CD4T | cd4_marson2025 | CRISPRi | 10x Flex | 1; 1; Stim8hr | 1.755.121 / 77.030 / 39.801 | 12.456 / 297 | 134 | `cd4_mix` | voto CRISPRi | fold del pannello a sei membri (livello B) | — |
| `D4_Stim48hr` | CD4T | cd4_marson2025 | CRISPRi | 10x Flex | 1; 1; Stim48hr | 1.878.125 / 83.474 / 42.049 | 12.414 / 294 | 143 | `cd4_mix` | voto CRISPRi | fold del pannello a sei membri (livello B) | — |
| `kolf_pan_genome` | iPSC | kolf_pan_genome | CRISPRi | MISSING | 1; 0 | 2.659.209 / 146.747 / 67.607 | 11.687 / 282 | 240 | `kolf_pan_genome` | voto CRISPRi | fold del pannello a sei membri (livello B) | chimica non riportata nel registro |
| `orion_hct116` | HCT116 | orion_hct116 | CRISPRi | MISSING | 1; 0 | 3.409.169 / 165.777 / 49.542 | 18.293 / 300 | 165 | `orion_hct116` | voto CRISPRi | fold del pannello a sei membri (livello B) | chimica non riportata nel registro |
| `orion_hek293t` | HEK293 | orion_hek293t | CRISPRi | MISSING | 1; 0 | 4.534.299 / 218.838 / 66.289 | 18.311 / 300 | 221 | `orion_hek293t` | voto CRISPRi | fold del pannello a sei membri (livello B) | chimica non riportata nel registro |
| `hepg2_nadig` | HepG2 | hepg2_nadig | CRISPRi | 10x 3' | 1; 0 | 145.473 / 4.976 / — | 2.393 / 0 | — | `hepg2_nadig` | tabella letta, nessun voto sul pannello | ricerca su bersagli fuori pannello (T, J, C fuori pannello) | — |
| `jurkat_nadig` | Jurkat | jurkat_nadig | CRISPRi | 10x 3' | 1; 0 | 262.956 / 12.013 / — | 2.393 / 0 | — | `jurkat_nadig` | tabella letta, nessun voto sul pannello | ricerca su bersagli fuori pannello (T, J, C fuori pannello) | — |
| `h1_train` | H1 | h1_vcc2025_train | CRISPRi | 10x Flex | 1; 0 | 221.273 / 38.176 / 15.130 | 150 / 13 | 1164 | `h1` | voto CRISPRi | lettura descrittiva sul pannello (pochi bersagli) | — |
| `h1_val` | H1 | h1_vcc2025_val | CRISPRi | 10x Flex | 1; 0 | 98.927 / 38.176 / 5.156 | 50 / 4 | 1289 | `h1` | voto CRISPRi | lettura descrittiva sul pannello (pochi bersagli) | — |
| `rpe1` | RPE1 | replogle_rpe1 | CRISPRi | 10x 3' v3 | 1; 0 | 247.914 / 11.485 / — | 2.393 / 0 | — | `rpe1` | tabella letta, nessun voto sul pannello | ricerca su bersagli fuori pannello (T, J, C fuori pannello) | — |
| `k562_essential` | K562 | replogle_k562_essential | CRISPRi | 10x 3' v3 | 1; 0 | 310.385 / 10.691 / — | 2.057 / 0 | — | `k562_essential` | tabella letta, nessun voto sul pannello | ricerca su bersagli fuori pannello (T, J, C fuori pannello) | — |
| `datlinger2017` | Jurkat | datlinger2017_jurkat_ko | KO | CROP-seq | 2; 0 | 5.905 / 1.320 / — | 96 / 0 | — | — | in banca, non derivata | nessuno oggi | condizione o stimolo non riportati per i contesti; in banca, non derivata: native labels are guide names with library prefix and guide number; no exact panel symbol, a declared guide-to-gene map is required |
| `datlinger2021` | Jurkat | datlinger2021_jurkat_ko | KO | scifi-RNA-seq | 2; 0 | 39.194 / 4.497 / — | 40 / 0 | — | — | in banca, non derivata | nessuno oggi | condizione o stimolo non riportati per i contesti; in banca, non derivata: native labels are guide names with guide number; no exact panel symbol, a declared guide-to-gene map is required |
| `shifrut2018` | CD4T | shifrut2018_tcells_ko | KO | 10x | 4; 2 | 52.236 / 3.541 / 572 | 20 / 1 | 572 | `shifrut2018` | voto KO a peso 0,25 | nessuno oggi | condizione o stimolo non riportati per i contesti |
| `dixit2016_d13` | K562 | dixit2016_k562_ko | KO | 10x (Perturb-seq) | 1; 0 | 19.268 / 3.491 / 2.347 | 10 / 2 | 1174 | `dixit2016` | voto KO a peso 0,25 | nessuno oggi | — |
| `dixit2016_d7` | K562 | dixit2016_k562_ko | KO | 10x (Perturb-seq) | 1; 0 | 33.013 / 5.381 / 4.429 | 10 / 2 | 2214 | `dixit2016` | voto KO a peso 0,25 | nessuno oggi | — |
| `dixit2016_high_moi` | K562 | dixit2016_k562_ko | KO | 10x (Perturb-seq) | 1; 0 | 51.898 / 10.492 / 7.107 | 10 / 2 | 3554 | `dixit2016` | voto KO a peso 0,25 | nessuno oggi | — |
| `xu2023` | HEK293 | xu2023_hek293_crispri | CRISPRi | 10x 3' | 1; 0 | 98.315 / 2.758 / 4.293 | 203 / 5 | 859 | `xu2023` | voto CRISPRi | lettura descrittiva sul pannello (pochi bersagli) | — |
| `kolf_chromatin` | iPSC | kolf_chromatin_modifiers | CRISPRi | MISSING | 1; 0 | 44.039 / 7.161 / 2.577 | 107 / 8 | 322 | `kolf_chromatin` | voto CRISPRi | lettura descrittiva sul pannello (pochi bersagli) | chimica non riportata nel registro |
| `kolf_metabolic` | iPSC | kolf_metabolic_enzymes | CRISPRi | MISSING | 1; 0 | 117.768 / 18.651 / 4.361 | 97 / 4 | 1090 | `kolf_metabolic` | voto CRISPRi | lettura descrittiva sul pannello (pochi bersagli) | chimica non riportata nel registro |
| `kolf_strong` | iPSC | kolf_strong_perturbations | CRISPRi | MISSING | 1; 0 | 232.438 / 35.424 / 7.433 | 1.655 / 55 | 135 | `kolf_strong` | voto CRISPRi | fold del pannello a sei membri (livello B) | chimica non riportata nel registro |
| `norman2019` | K562 | norman2019_crispra | CRISPRa | 10x 3' | 1; 0 | 111.445 / 11.855 / 972 | 236 / 3 | 324 | `norman2019` | CRISPRa, fuori dal transfer | solo ramo CRISPRa separato | — |
| `tian2019_ipsc` | iPSC | tian2019_ipsc | CRISPRi | 10x 3' | 1; 0 | 271.223 / 10.401 / 2.028 | 39.161 / 1 | 2028 | `tian2019_ipsc` | derivata, non ammessa al voto | ricerca su bersagli fuori pannello (T, J, C fuori pannello) | più etichette native che geni (39.161): guide o combinazioni da riconciliare prima di usarle come bersagli |
| `tian2019_neuron` | neuron | tian2019_neuron_day7 | CRISPRi | 10x 3' | 1; 0 | 179.174 / 15.083 / 3.190 | 41.357 / 1 | 3190 | `tian2019_neuron` | derivata, non ammessa al voto | ricerca su bersagli fuori pannello (T, J, C fuori pannello) | più etichette native che geni (41.357): guide o combinazioni da riconciliare prima di usarle come bersagli |
| `tian2021_crispra` | neuron | tian2021_crispra | CRISPRa | 10x 3' | 1; 0 | 21.193 / 434 / 1.235 | 100 / 4 | 309 | `tian2021_crispra` | CRISPRa, fuori dal transfer | solo ramo CRISPRa separato | — |
| `tian2021_crispri` | neuron | tian2021_crispri | CRISPRi | 10x 3' | 1; 0 | 32.300 / 437 / 984 | 184 / 6 | 164 | `tian2021_crispri` | voto CRISPRi | lettura descrittiva sul pannello (pochi bersagli) | — |
| `a549_ko` | A549 | a549_liu_hillsley2026 | KO | MISSING | 1; 0 | 606.075 / 45.320 / 13.945 | 1.000 / 21 | 664 | `a549_ko` | voto KO a peso 0,25 | lettura KO separata, descrittiva | chimica non riportata nel registro |
| `hipsci_gw_fitness` | iPSC | hipsci_gw_fitness | CRISPRi | MISSING | 60; 24; day3, day4, day5 | 322.746 / 36 / 1.539 | 2.252 / 31 | 50 | — | in banca, non derivata | nessuno oggi | chimica non riportata nel registro; solo 36 controlli non perturbati; in banca, non derivata: controls: see piano; non-targeting cells are too few to give every clone matched controls with the original estimator |
| `hipsci_gw_nonfitness` | iPSC | hipsci_gw_nonfitness | CRISPRi | MISSING | 40; 34; day3, day6 | 396.458 / 12 / 3.930 | 4.954 / 166 | 24 | — | in banca, non derivata | nessuno oggi | chimica non riportata nel registro; solo 12 controlli non perturbati; in banca, non derivata: controls: see piano; non-targeting cells are too few to give every clone matched controls with the original estimator |
| `frangieh2021` | melanoma | frangieh2021_melanoma_ko | KO | 10x 3' v3 | 3; 0 | 218.331 / 57.605 / 3.256 | 248 / 5 | 651 | `frangieh2021` | voto KO a peso 0,25 | lettura KO separata, descrittiva | condizione o stimolo non riportati per i contesti |
| `papalexi2021_arrayed` | THP1 | papalexi2021_thp1_arrayed_ko | KO | 10x 3' (ECCITE) | 1; 0 | 8.984 / 2.009 / 4 | 10 / 1 | 4 | — | in banca, non derivata | nessuno oggi | 4 cellule per bersaglio del pannello; in banca, non derivata: one panel symbol with 4 cells, below min_cells 10 of the original recipe |
| `sunshine2023` | Calu3 | sunshine2023_calu3_ko | KO | 10x 3' | 1; 0 | 90.380 / 3.536 / 1.704 | 24.194 / 6 | 284 | `sunshine2023` | voto KO a peso 0,25 | lettura KO separata, descrittiva | più etichette native che geni (24.194): guide o combinazioni da riconciliare prima di usarle come bersagli |
| `hipsci_targeted_19` | iPSC | hipsci_targeted_19 | CRISPRi | MISSING | 19; 19; day3 | 1.161.865 / 8.241 / 7.583 | 444 / 5 | 1517 | `hipsci_targeted_19` | voto CRISPRi | lettura descrittiva sul pannello (pochi bersagli) | chimica non riportata nel registro |
| `k562_gwps_a` | K562 | replogle_k562_gwps | CRISPRi | 10x 3' v3 | 1; 0 | 1.000.000 / 37.785 / 25.201 | 9.864 / 272 | 93 | `k562_gwps_sc` | stesso esperimento della tabella K562 BULK: non vota due volte | fold del pannello a sei membri (livello B) | — |
| `k562_gwps_b` | K562 | replogle_k562_gwps | CRISPRi | 10x 3' v3 | 1; 0 | 989.578 / 37.543 / 24.927 | 9.866 / 272 | 92 | `k562_gwps_sc` | stesso esperimento della tabella K562 BULK: non vota due volte | fold del pannello a sei membri (livello B) | — |

Tutte le 45 unità hanno campioni di singole cellule in banca (livelli 32, 64, 128 per contesto e bersaglio); la tabella di effetti è l'aggregato che il transfer legge. Le cellule «per bersaglio» sono la media delle cellule con un bersaglio del pannello divise per i bersagli del pannello dell'unità.

## 3. Quali checkpoint si possono leggere come contesto nuovo, e dove

| Checkpoint o candidato | Si legge come regime C su | Nota |
|---|---|---|
| transfer rifatto dal banco (stadio 100) senza le tabelle del lignaggio | ogni lignaggio con una tabella di verità | è l'unico modello che il banco ricalcola con l'esclusione; vale per T0, T1, R1, P4 e i bracci d'analisi |
| T3 (t38), effetti di produzione | nessuno | contiene le risposte di tutti i lignaggi dei fold e i voti KO; non è una ricetta dello stadio 100 e non esistono suoi effetti a lignaggio escluso |
| ridge ESM2, fit C-K562 e J-K562 | K562 | gli altri lignaggi sono nel training: su di loro la lettura è «visto», o T per i bersagli nascosti del fit J |
| ridge ESM2, fit C-iPSC e J-iPSC | iPSC | come sopra |
| ridge ESM2, fit T e di produzione | nessuno | tutti i lignaggi nel training; il fit T nasconde i 66 bersagli del gruppo di test |
| AMMI none, fit C-K562 (seme 17) | K562 | CD4T è escluso dal training ma serve alle guardie interne: una lettura su CD4T non è un test pulito |
| AMMI none, fit C-iPSC (seme 17) | iPSC | K562 è escluso dal training ma serve alle guardie interne |
