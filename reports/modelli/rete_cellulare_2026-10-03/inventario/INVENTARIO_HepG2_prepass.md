# Inventario delle cellule: linea esclusa HepG2

Prepass: 5603629 cellule lette in 365 shard, 3970762 ammesse per il training, 2439 gruppi di valutazione, serbatoio di 56727 controlli.

| Chiave (studio\|contesto) | Gruppo | Esclusa | Controlli | Rifiutate (regola: cellule) | Training dell'unità | Peso | Offerte | Viste |
|---|---|---|---:|---|---:|---:|---:|---:|
| `a549_liu_hillsley2026\|A549` | A549 |  | 45320 | mito_above_ceiling: 8 | 504189 | 1.1251 |  |  |
| `h1_vcc2025\|H1` | H1 |  | 76352 | duplicate_cell: 38176, mito_above_ceiling: 1 | 238818 | 2.3752 |  |  |
| `hepg2_nadig\|HepG2` | HepG2 | sì | 4976 | genes_below_floor: 8, counts_below_floor: 1 |  |  |  |  |
| `hipsci_targeted_19\|MISSING` | iPSC |  | 0 | no_controls_in_key: 1 | 508726 | 0.2788 |  |  |
| `hipsci_targeted_19\|eipl_1` | iPSC |  | 496 | — | 508726 | 0.2788 |  |  |
| `hipsci_targeted_19\|eipl_3` | iPSC |  | 501 | — | 508726 | 0.2788 |  |  |
| `hipsci_targeted_19\|fiaj_1` | iPSC |  | 549 | — | 508726 | 0.2788 |  |  |
| `hipsci_targeted_19\|fiaj_3` | iPSC |  | 86 | — | 508726 | 0.2788 |  |  |
| `hipsci_targeted_19\|iudw_1` | iPSC |  | 575 | — | 508726 | 0.2788 |  |  |
| `hipsci_targeted_19\|iudw_4` | iPSC |  | 433 | — | 508726 | 0.2788 |  |  |
| `hipsci_targeted_19\|jejf_2` | iPSC |  | 605 | — | 508726 | 0.2788 |  |  |
| `hipsci_targeted_19\|jejf_3` | iPSC |  | 484 | — | 508726 | 0.2788 |  |  |
| `hipsci_targeted_19\|kolf_2` | iPSC |  | 520 | — | 508726 | 0.2788 |  |  |
| `hipsci_targeted_19\|kolf_3` | iPSC |  | 455 | — | 508726 | 0.2788 |  |  |
| `hipsci_targeted_19\|oikd_2` | iPSC |  | 177 | — | 508726 | 0.2788 |  |  |
| `hipsci_targeted_19\|oikd_5` | iPSC |  | 668 | — | 508726 | 0.2788 |  |  |
| `hipsci_targeted_19\|paab_3` | iPSC |  | 397 | — | 508726 | 0.2788 |  |  |
| `hipsci_targeted_19\|paab_4` | iPSC |  | 543 | — | 508726 | 0.2788 |  |  |
| `hipsci_targeted_19\|pipw_4` | iPSC |  | 488 | — | 508726 | 0.2788 |  |  |
| `hipsci_targeted_19\|pipw_5` | iPSC |  | 92 | counts_below_floor: 62 | 508726 | 0.2788 |  |  |
| `hipsci_targeted_19\|tolg_4` | iPSC |  | 182 | — | 508726 | 0.2788 |  |  |
| `hipsci_targeted_19\|tolg_6` | iPSC |  | 368 | — | 508726 | 0.2788 |  |  |
| `hipsci_targeted_19\|zapk_3` | iPSC |  | 622 | — | 508726 | 0.2788 |  |  |
| `jurkat_nadig\|Jurkat` | Jurkat |  | 12013 | counts_below_floor: 85, genes_below_floor: 6 | 215180 | 2.6362 |  |  |
| `kolf_chromatin_modifiers\|KOLF2.1J iPSC` | iPSC |  | 7161 | — | 36508 | 3.8844 |  |  |
| `kolf_metabolic_enzymes\|KOLF2.1J iPSC` | iPSC |  | 18651 | — | 100413 | 1.4123 |  |  |
| `kolf_strong_perturbations\|KOLF2.1J iPSC` | iPSC |  | 35424 | mito_above_ceiling: 55, counts_below_floor: 39, genes_below_floor: 6 | 193473 | 0.733 |  |  |
| `norman2019_crispra\|K562` | K562 |  | 11855 | mito_above_ceiling: 19 | 60117 | 3.1453 |  |  |
| `replogle_k562_essential\|K562` | K562 |  | 10691 | counts_below_floor: 155, genes_below_floor: 10 | 253297 | 0.7465 |  |  |
| `replogle_k562_gwps\|K562` | K562 |  | 75328 | counts_below_floor: 1310, genes_below_floor: 18, counts_far_below_controls: 1 | 1616514 | 0.117 |  |  |
| `replogle_rpe1\|RPE1` | RPE1 |  | 11485 | counts_below_floor: 70, genes_below_floor: 15 | 201857 | 2.8102 |  |  |
| `tian2021_crispra\|iPSC-induced neuron` | Neuron |  | 434 | counts_below_floor: 83 | 15452 | 18.3553 |  |  |
| `tian2021_crispri\|iPSC-induced neuron` | Neuron |  | 437 | mito_above_ceiling: 5 | 26218 | 10.818 |  |  |

Classi dopo il QC: {}; simboli addestrati 8388 (prima del QC 8388).
