# Tabella comparativa del pilot modulare

Generata dai JSON di risultato, non a mano. Metrica primaria: `pooled_mse_vs_null` (più basso è meglio), spazio pseudobulk log2FC, **non** un punteggio VCC. Nessuna variante è scelta sul test esterno: la colonna `eleggibile sul test` è sempre no.

| modello | usa contesto | protocollo | direzione | seed | MSE/nullo | Pearson med. | copertura bersagli | parametri tot. | parametri addestrabili | train s | infer s | picco RSS | artefatto B | ampiezza | contesto identificabile | eleggibile sul test |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| lowrank_linear__with_ctx | sì | new_context_seen_target | k562_rpe1_to_hepg2 | 2026 | 1.4846 | 0.1689 | 1.0000 | 58824 | 531 | 0.8190 | 0.0718 | 389951488 | 450039 | cross_context_within_training | sì | no |
| lowrank_linear__no_ctx | no | new_context_seen_target | k562_rpe1_to_hepg2 | 2026 | 1.3309 | 0.1386 | 1.0000 | 58491 | 198 | 0.6446 | 0.1072 | 389951488 | 447531 | cross_context_within_training | sì | no |
| modular_frozen__with_ctx | sì | new_context_seen_target | k562_rpe1_to_hepg2 | 2026 | 1.0505 | 0.1563 | 1.0000 | 58845 | 552 | 1.2503 | 0.1162 | 389951488 | 451791 | cross_context_within_training | sì | no |
| modular_frozen__no_ctx | no | new_context_seen_target | k562_rpe1_to_hepg2 | 2026 | 1.2173 | 0.1321 | 1.0000 | 58549 | 256 | 1.5604 | 0.1346 | 389951488 | 448918 | cross_context_within_training | sì | no |
| lowrank_linear__with_ctx | sì | new_context_seen_target | k562_rpe1_to_hepg2 | 2027 | 1.4806 | 0.1667 | 1.0000 | 58824 | 531 | 1.6515 | 0.1321 | 476979200 | 450126 | cross_context_within_training | sì | no |
| lowrank_linear__no_ctx | no | new_context_seen_target | k562_rpe1_to_hepg2 | 2027 | 1.3279 | 0.1389 | 1.0000 | 58491 | 198 | 0.9619 | 0.0889 | 476979200 | 447623 | cross_context_within_training | sì | no |
| modular_frozen__with_ctx | sì | new_context_seen_target | k562_rpe1_to_hepg2 | 2027 | 1.0695 | 0.1608 | 1.0000 | 110733 | 624 | 1.5266 | 0.1268 | 476979200 | 849645 | cross_context_within_training | sì | no |
| modular_frozen__no_ctx | no | new_context_seen_target | k562_rpe1_to_hepg2 | 2027 | 1.1985 | 0.1778 | 1.0000 | 110437 | 328 | 1.9205 | 0.1310 | 476979200 | 846784 | cross_context_within_training | sì | no |
| lowrank_linear__with_ctx | sì | new_context_seen_target | k562_hepg2_to_rpe1 | 2026 | 0.8719 | 0.2589 | 1.0000 | 58824 | 531 | 1.1481 | 0.0980 | 477700096 | 449342 | cross_context_within_training | sì | no |
| lowrank_linear__no_ctx | no | new_context_seen_target | k562_hepg2_to_rpe1 | 2026 | 0.8935 | 0.2323 | 1.0000 | 58491 | 198 | 0.5696 | 0.0613 | 477700096 | 446836 | cross_context_within_training | sì | no |
| modular_frozen__with_ctx | sì | new_context_seen_target | k562_hepg2_to_rpe1 | 2026 | 0.8890 | 0.3028 | 1.0000 | 110733 | 624 | 1.4839 | 0.0955 | 477700096 | 848986 | cross_context_within_training | sì | no |
| modular_frozen__no_ctx | no | new_context_seen_target | k562_hepg2_to_rpe1 | 2026 | 0.8767 | 0.2253 | 1.0000 | 58549 | 256 | 1.0510 | 0.1020 | 477700096 | 448210 | cross_context_within_training | sì | no |
| lowrank_linear__with_ctx | sì | new_context_seen_target | k562_hepg2_to_rpe1 | 2027 | 0.8730 | 0.2541 | 1.0000 | 58824 | 531 | 0.9788 | 0.0942 | 477700096 | 449471 | cross_context_within_training | sì | no |
| lowrank_linear__no_ctx | no | new_context_seen_target | k562_hepg2_to_rpe1 | 2027 | 0.8948 | 0.2299 | 1.0000 | 58491 | 198 | 0.7367 | 0.0852 | 477700096 | 446961 | cross_context_within_training | sì | no |
| modular_frozen__with_ctx | sì | new_context_seen_target | k562_hepg2_to_rpe1 | 2027 | 0.8608 | 0.3534 | 1.0000 | 58845 | 552 | 1.0898 | 0.1028 | 477700096 | 451213 | cross_context_within_training | sì | no |
| modular_frozen__no_ctx | no | new_context_seen_target | k562_hepg2_to_rpe1 | 2027 | 0.8759 | 0.2683 | 1.0000 | 58549 | 256 | 1.0591 | 0.0674 | 477700096 | 448335 | cross_context_within_training | sì | no |
| lowrank_linear__with_ctx | sì | new_context_seen_target | rpe1_hepg2_to_k562 | 2026 | 1.1648 | 0.0899 | 1.0000 | 58824 | 531 | 1.0534 | 0.1544 | 478801920 | 450113 | cross_context_within_training | sì | no |
| lowrank_linear__no_ctx | no | new_context_seen_target | rpe1_hepg2_to_k562 | 2026 | 1.2792 | 0.0879 | 1.0000 | 58491 | 198 | 0.8909 | 0.0949 | 478801920 | 447615 | cross_context_within_training | sì | no |
| modular_frozen__with_ctx | sì | new_context_seen_target | rpe1_hepg2_to_k562 | 2026 | 1.0949 | 0.0847 | 1.0000 | 58845 | 552 | 1.8100 | 0.1050 | 478801920 | 451858 | cross_context_within_training | sì | no |
| modular_frozen__no_ctx | no | new_context_seen_target | rpe1_hepg2_to_k562 | 2026 | 1.2504 | 0.0830 | 1.0000 | 58549 | 256 | 1.1842 | 0.1023 | 478801920 | 449004 | cross_context_within_training | sì | no |
| lowrank_linear__with_ctx | sì | new_context_seen_target | rpe1_hepg2_to_k562 | 2027 | 1.1653 | 0.0882 | 1.0000 | 58824 | 531 | 0.8138 | 0.0908 | 479330304 | 450083 | cross_context_within_training | sì | no |
| lowrank_linear__no_ctx | no | new_context_seen_target | rpe1_hepg2_to_k562 | 2027 | 1.2775 | 0.0874 | 1.0000 | 58491 | 198 | 0.7740 | 0.0923 | 479330304 | 447581 | cross_context_within_training | sì | no |
| modular_frozen__with_ctx | sì | new_context_seen_target | rpe1_hepg2_to_k562 | 2027 | 1.0831 | 0.0757 | 1.0000 | 110733 | 624 | 1.5695 | 0.0974 | 479330304 | 849686 | cross_context_within_training | sì | no |
| modular_frozen__no_ctx | no | new_context_seen_target | rpe1_hepg2_to_k562 | 2027 | 1.2949 | 0.0922 | 1.0000 | 58549 | 256 | 1.4671 | 0.2224 | 479330304 | 448969 | cross_context_within_training | sì | no |
| lowrank_linear__with_ctx | sì | new_context_unseen_target | k562_rpe1_to_hepg2 | 2026 | 1.3196 | 0.1511 | 1.0000 | 58680 | 387 | 0.7466 | 0.0219 | 479330304 | 448413 | cross_context_within_training | sì | no |
| lowrank_linear__no_ctx | no | new_context_unseen_target | k562_rpe1_to_hepg2 | 2026 | 1.1072 | 0.1507 | 1.0000 | 58347 | 54 | 0.6732 | 0.0322 | 479330304 | 445887 | cross_context_within_training | sì | no |
| modular_frozen__with_ctx | sì | new_context_unseen_target | k562_rpe1_to_hepg2 | 2026 | 1.1074 | 0.1538 | 1.0000 | 58717 | 424 | 0.7195 | 0.0210 | 479330304 | 450029 | cross_context_within_training | sì | no |
| modular_frozen__no_ctx | no | new_context_unseen_target | k562_rpe1_to_hepg2 | 2026 | 1.0736 | 0.1551 | 1.0000 | 110309 | 200 | 0.7125 | 0.0222 | 479330304 | 844917 | cross_context_within_training | sì | no |
| lowrank_linear__with_ctx | sì | new_context_unseen_target | k562_rpe1_to_hepg2 | 2027 | 1.3040 | 0.1720 | 1.0000 | 58680 | 387 | 1.1399 | 0.0440 | 479330304 | 448434 | cross_context_within_training | sì | no |
| lowrank_linear__no_ctx | no | new_context_unseen_target | k562_rpe1_to_hepg2 | 2027 | 1.0639 | 0.1739 | 1.0000 | 58347 | 54 | 0.7944 | 0.0447 | 479330304 | 445910 | cross_context_within_training | sì | no |
| modular_frozen__with_ctx | sì | new_context_unseen_target | k562_rpe1_to_hepg2 | 2027 | 1.0700 | 0.1719 | 1.0000 | 110605 | 496 | 1.6168 | 0.0390 | 479330304 | 847953 | cross_context_within_training | sì | no |
| modular_frozen__no_ctx | no | new_context_unseen_target | k562_rpe1_to_hepg2 | 2027 | 1.0591 | 0.1746 | 1.0000 | 58421 | 128 | 1.3263 | 0.0593 | 479330304 | 447168 | cross_context_within_training | sì | no |
| lowrank_linear__with_ctx | sì | new_context_unseen_target | k562_hepg2_to_rpe1 | 2026 | 0.8855 | 0.3382 | 1.0000 | 58680 | 387 | 0.6905 | 0.0322 | 479330304 | 447809 | cross_context_within_training | sì | no |
| lowrank_linear__no_ctx | no | new_context_unseen_target | k562_hepg2_to_rpe1 | 2026 | 0.8942 | 0.3346 | 1.0000 | 58347 | 54 | 0.8652 | 0.0402 | 479330304 | 445281 | cross_context_within_training | sì | no |
| modular_frozen__with_ctx | sì | new_context_unseen_target | k562_hepg2_to_rpe1 | 2026 | 0.8723 | 0.3412 | 1.0000 | 110605 | 496 | 1.7104 | 0.0456 | 479330304 | 847213 | cross_context_within_training | sì | no |
| modular_frozen__no_ctx | no | new_context_unseen_target | k562_hepg2_to_rpe1 | 2026 | 0.8926 | 0.3320 | 1.0000 | 110309 | 200 | 1.3512 | 0.0350 | 479330304 | 844325 | cross_context_within_training | sì | no |
| lowrank_linear__with_ctx | sì | new_context_unseen_target | k562_hepg2_to_rpe1 | 2027 | 0.8796 | 0.3615 | 1.0000 | 58680 | 387 | 1.1642 | 0.0385 | 479330304 | 447741 | cross_context_within_training | sì | no |
| lowrank_linear__no_ctx | no | new_context_unseen_target | k562_hepg2_to_rpe1 | 2027 | 0.8885 | 0.3425 | 1.0000 | 58347 | 54 | 0.8749 | 0.0377 | 479330304 | 445220 | cross_context_within_training | sì | no |
| modular_frozen__with_ctx | sì | new_context_unseen_target | k562_hepg2_to_rpe1 | 2027 | 0.8730 | 0.3523 | 1.0000 | 58717 | 424 | 1.3723 | 0.0379 | 479330304 | 449351 | cross_context_within_training | sì | no |
| modular_frozen__no_ctx | no | new_context_unseen_target | k562_hepg2_to_rpe1 | 2027 | 0.8855 | 0.3467 | 1.0000 | 58421 | 128 | 0.9441 | 0.0312 | 479330304 | 446458 | cross_context_within_training | sì | no |
| lowrank_linear__with_ctx | sì | new_context_unseen_target | rpe1_hepg2_to_k562 | 2026 | 1.0780 | 0.1022 | 1.0000 | 58680 | 387 | 0.6955 | 0.0350 | 479330304 | 448416 | cross_context_within_training | sì | no |
| lowrank_linear__no_ctx | no | new_context_unseen_target | rpe1_hepg2_to_k562 | 2026 | 1.2108 | 0.1012 | 1.0000 | 58347 | 54 | 0.8357 | 0.0431 | 479330304 | 445889 | cross_context_within_training | sì | no |
| modular_frozen__with_ctx | sì | new_context_unseen_target | rpe1_hepg2_to_k562 | 2026 | 1.1896 | 0.1010 | 1.0000 | 110605 | 496 | 1.4610 | 0.0399 | 479330304 | 847828 | cross_context_within_training | sì | no |
| modular_frozen__no_ctx | no | new_context_unseen_target | rpe1_hepg2_to_k562 | 2026 | 1.2264 | 0.0975 | 1.0000 | 58421 | 128 | 1.1554 | 0.0395 | 479330304 | 447146 | cross_context_within_training | sì | no |
| lowrank_linear__with_ctx | sì | new_context_unseen_target | rpe1_hepg2_to_k562 | 2027 | 1.0480 | 0.0988 | 1.0000 | 58680 | 387 | 0.7222 | 0.0295 | 479330304 | 448398 | cross_context_within_training | sì | no |
| lowrank_linear__no_ctx | no | new_context_unseen_target | rpe1_hepg2_to_k562 | 2027 | 1.1401 | 0.0999 | 1.0000 | 58347 | 54 | 0.8288 | 0.0388 | 479330304 | 445871 | cross_context_within_training | sì | no |
| modular_frozen__with_ctx | sì | new_context_unseen_target | rpe1_hepg2_to_k562 | 2027 | 1.1124 | 0.0931 | 1.0000 | 58717 | 424 | 1.3900 | 0.0382 | 479330304 | 450016 | cross_context_within_training | sì | no |
| modular_frozen__no_ctx | no | new_context_unseen_target | rpe1_hepg2_to_k562 | 2027 | 1.1503 | 0.0947 | 1.0000 | 110309 | 200 | 1.4102 | 0.0472 | 479330304 | 844913 | cross_context_within_training | sì | no |
