# Tabella comparativa del pilot modulare

Generata dai JSON di risultato, non a mano. Metrica primaria: `pooled_mse_vs_null` (più basso è meglio), spazio pseudobulk log2FC, **non** un punteggio VCC. Nessuna variante è scelta sul test esterno: la colonna `eleggibile sul test` è sempre no.

| modello | usa contesto | protocollo | direzione | seed | MSE/nullo | Pearson med. | copertura bersagli | parametri tot. | parametri addestrabili | train s | infer s | picco RSS | artefatto B | ampiezza | contesto identificabile | eleggibile sul test |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| lowrank_linear__with_ctx | sì | new_context_seen_target | k562_rpe1_to_hepg2 | 2026 | 1.4869 | 0.1675 | 1.0000 | 58824 | 531 | 3.8786 | 0.1102 | 392269824 | 450101 | cross_context_within_training | sì | no |
| lowrank_linear__no_ctx | no | new_context_seen_target | k562_rpe1_to_hepg2 | 2026 | 1.3328 | 0.1402 | 1.0000 | 58491 | 198 | 3.6868 | 0.1072 | 392269824 | 447594 | cross_context_within_training | sì | no |
| modular_frozen__with_ctx | sì | new_context_seen_target | k562_rpe1_to_hepg2 | 2026 | 1.0825 | 0.1581 | 1.0000 | 110733 | 624 | 5.0459 | 0.0996 | 392269824 | 849617 | cross_context_within_training | sì | no |
| modular_frozen__no_ctx | no | new_context_seen_target | k562_rpe1_to_hepg2 | 2026 | 1.2111 | 0.1697 | 1.0000 | 58549 | 256 | 4.6681 | 0.0944 | 392269824 | 448977 | cross_context_within_training | sì | no |
| lowrank_linear__with_ctx | sì | new_context_seen_target | k562_rpe1_to_hepg2 | 2027 | 1.4869 | 0.1675 | 1.0000 | 58824 | 531 | 3.0597 | 0.0702 | 476512256 | 450101 | cross_context_within_training | sì | no |
| lowrank_linear__no_ctx | no | new_context_seen_target | k562_rpe1_to_hepg2 | 2027 | 1.3328 | 0.1402 | 1.0000 | 58491 | 198 | 3.0189 | 0.0982 | 476512256 | 447594 | cross_context_within_training | sì | no |
| modular_frozen__with_ctx | sì | new_context_seen_target | k562_rpe1_to_hepg2 | 2027 | 1.1021 | 0.1550 | 1.0000 | 110733 | 624 | 5.0314 | 0.1499 | 476512256 | 849630 | cross_context_within_training | sì | no |
| modular_frozen__no_ctx | no | new_context_seen_target | k562_rpe1_to_hepg2 | 2027 | 1.1928 | 0.1558 | 1.0000 | 58549 | 256 | 4.7576 | 0.0958 | 476512256 | 448969 | cross_context_within_training | sì | no |
| lowrank_linear__with_ctx | sì | new_context_seen_target | k562_hepg2_to_rpe1 | 2026 | 0.8741 | 0.2574 | 1.0000 | 58824 | 531 | 3.2769 | 0.0870 | 476581888 | 449382 | cross_context_within_training | sì | no |
| lowrank_linear__no_ctx | no | new_context_seen_target | k562_hepg2_to_rpe1 | 2026 | 0.8959 | 0.2231 | 1.0000 | 58491 | 198 | 2.8358 | 0.0688 | 476581888 | 446873 | cross_context_within_training | sì | no |
| modular_frozen__with_ctx | sì | new_context_seen_target | k562_hepg2_to_rpe1 | 2026 | 0.8865 | 0.3228 | 1.0000 | 110733 | 624 | 6.8915 | 0.0730 | 476581888 | 848886 | cross_context_within_training | sì | no |
| modular_frozen__no_ctx | no | new_context_seen_target | k562_hepg2_to_rpe1 | 2026 | 0.8791 | 0.3094 | 1.0000 | 110437 | 328 | 5.3911 | 0.0885 | 476581888 | 846023 | cross_context_within_training | sì | no |
| lowrank_linear__with_ctx | sì | new_context_seen_target | k562_hepg2_to_rpe1 | 2027 | 0.8741 | 0.2574 | 1.0000 | 58824 | 531 | 4.0263 | 0.0998 | 476594176 | 449382 | cross_context_within_training | sì | no |
| lowrank_linear__no_ctx | no | new_context_seen_target | k562_hepg2_to_rpe1 | 2027 | 0.8959 | 0.2231 | 1.0000 | 58491 | 198 | 3.9137 | 0.0851 | 476594176 | 446873 | cross_context_within_training | sì | no |
| modular_frozen__with_ctx | sì | new_context_seen_target | k562_hepg2_to_rpe1 | 2027 | 0.8776 | 0.3322 | 1.0000 | 110733 | 624 | 5.5617 | 0.0891 | 476594176 | 848886 | cross_context_within_training | sì | no |
| modular_frozen__no_ctx | no | new_context_seen_target | k562_hepg2_to_rpe1 | 2027 | 0.8730 | 0.2427 | 1.0000 | 58549 | 256 | 5.6231 | 0.0666 | 476594176 | 448248 | cross_context_within_training | sì | no |
| lowrank_linear__with_ctx | sì | new_context_seen_target | rpe1_hepg2_to_k562 | 2026 | 1.1644 | 0.0858 | 1.0000 | 58824 | 531 | 3.1675 | 0.0919 | 477880320 | 450069 | cross_context_within_training | sì | no |
| lowrank_linear__no_ctx | no | new_context_seen_target | rpe1_hepg2_to_k562 | 2026 | 1.2794 | 0.0862 | 1.0000 | 58491 | 198 | 3.1101 | 0.0700 | 477880320 | 447574 | cross_context_within_training | sì | no |
| modular_frozen__with_ctx | sì | new_context_seen_target | rpe1_hepg2_to_k562 | 2026 | 1.1242 | 0.0855 | 1.0000 | 110733 | 624 | 5.1952 | 0.1098 | 477880320 | 849579 | cross_context_within_training | sì | no |
| modular_frozen__no_ctx | no | new_context_seen_target | rpe1_hepg2_to_k562 | 2026 | 1.2004 | 0.0890 | 1.0000 | 58549 | 256 | 4.5521 | 0.0656 | 477880320 | 448945 | cross_context_within_training | sì | no |
| lowrank_linear__with_ctx | sì | new_context_seen_target | rpe1_hepg2_to_k562 | 2027 | 1.1644 | 0.0858 | 1.0000 | 58824 | 531 | 3.7243 | 0.0750 | 478150656 | 450069 | cross_context_within_training | sì | no |
| lowrank_linear__no_ctx | no | new_context_seen_target | rpe1_hepg2_to_k562 | 2027 | 1.2794 | 0.0862 | 1.0000 | 58491 | 198 | 4.7753 | 0.0980 | 478150656 | 447574 | cross_context_within_training | sì | no |
| modular_frozen__with_ctx | sì | new_context_seen_target | rpe1_hepg2_to_k562 | 2027 | 1.0850 | 0.0791 | 1.0000 | 58845 | 552 | 6.7135 | 0.0859 | 478150656 | 451814 | cross_context_within_training | sì | no |
| modular_frozen__no_ctx | no | new_context_seen_target | rpe1_hepg2_to_k562 | 2027 | 1.2881 | 0.0915 | 1.0000 | 58549 | 256 | 11.6535 | 0.1584 | 478150656 | 448947 | cross_context_within_training | sì | no |
| lowrank_linear__with_ctx | sì | new_context_unseen_target | k562_rpe1_to_hepg2 | 2026 | 1.3198 | 0.1511 | 1.0000 | 58680 | 387 | 2.8415 | 0.0374 | 478150656 | 448239 | cross_context_within_training | sì | no |
| lowrank_linear__no_ctx | no | new_context_unseen_target | k562_rpe1_to_hepg2 | 2026 | 1.1073 | 0.1507 | 1.0000 | 58347 | 54 | 3.3624 | 0.0612 | 478150656 | 445713 | cross_context_within_training | sì | no |
| modular_frozen__with_ctx | sì | new_context_unseen_target | k562_rpe1_to_hepg2 | 2026 | 1.1012 | 0.1483 | 1.0000 | 110605 | 496 | 4.9059 | 0.0354 | 478150656 | 847572 | cross_context_within_training | sì | no |
| modular_frozen__no_ctx | no | new_context_unseen_target | k562_rpe1_to_hepg2 | 2026 | 1.0744 | 0.1553 | 1.0000 | 110309 | 200 | 6.0780 | 0.0293 | 478150656 | 844680 | cross_context_within_training | sì | no |
| lowrank_linear__with_ctx | sì | new_context_unseen_target | k562_rpe1_to_hepg2 | 2027 | 1.3037 | 0.1716 | 1.0000 | 58680 | 387 | 2.5108 | 0.0458 | 478150656 | 448357 | cross_context_within_training | sì | no |
| lowrank_linear__no_ctx | no | new_context_unseen_target | k562_rpe1_to_hepg2 | 2027 | 1.0637 | 0.1732 | 1.0000 | 58347 | 54 | 1.8259 | 0.0215 | 478150656 | 445833 | cross_context_within_training | sì | no |
| modular_frozen__with_ctx | sì | new_context_unseen_target | k562_rpe1_to_hepg2 | 2027 | 1.0524 | 0.1694 | 1.0000 | 58717 | 424 | 3.1022 | 0.0310 | 478150656 | 449982 | cross_context_within_training | sì | no |
| modular_frozen__no_ctx | no | new_context_unseen_target | k562_rpe1_to_hepg2 | 2027 | 1.0563 | 0.1729 | 1.0000 | 58421 | 128 | 3.0292 | 0.0201 | 478150656 | 447089 | cross_context_within_training | sì | no |
| lowrank_linear__with_ctx | sì | new_context_unseen_target | k562_hepg2_to_rpe1 | 2026 | 0.8825 | 0.3465 | 1.0000 | 58680 | 387 | 1.8089 | 0.0231 | 478150656 | 447754 | cross_context_within_training | sì | no |
| lowrank_linear__no_ctx | no | new_context_unseen_target | k562_hepg2_to_rpe1 | 2026 | 0.8931 | 0.3353 | 1.0000 | 58347 | 54 | 1.1875 | 0.0195 | 478150656 | 445227 | cross_context_within_training | sì | no |
| modular_frozen__with_ctx | sì | new_context_unseen_target | k562_hepg2_to_rpe1 | 2026 | 0.8825 | 0.3146 | 1.0000 | 110605 | 496 | 1.7206 | 0.0181 | 478150656 | 847090 | cross_context_within_training | sì | no |
| modular_frozen__no_ctx | no | new_context_unseen_target | k562_hepg2_to_rpe1 | 2026 | 0.8917 | 0.3163 | 1.0000 | 58421 | 128 | 1.8957 | 0.0178 | 478150656 | 446482 | cross_context_within_training | sì | no |
| lowrank_linear__with_ctx | sì | new_context_unseen_target | k562_hepg2_to_rpe1 | 2027 | 0.8785 | 0.3623 | 1.0000 | 58680 | 387 | 2.3119 | 0.0276 | 478150656 | 447695 | cross_context_within_training | sì | no |
| lowrank_linear__no_ctx | no | new_context_unseen_target | k562_hepg2_to_rpe1 | 2027 | 0.8876 | 0.3463 | 1.0000 | 58347 | 54 | 2.3680 | 0.0316 | 478150656 | 445170 | cross_context_within_training | sì | no |
| modular_frozen__with_ctx | sì | new_context_unseen_target | k562_hepg2_to_rpe1 | 2027 | 0.8820 | 0.3366 | 1.0000 | 58717 | 424 | 3.0818 | 0.0420 | 478150656 | 449296 | cross_context_within_training | sì | no |
| modular_frozen__no_ctx | no | new_context_unseen_target | k562_hepg2_to_rpe1 | 2027 | 0.8901 | 0.3403 | 1.0000 | 110309 | 200 | 3.1831 | 0.0334 | 478150656 | 844216 | cross_context_within_training | sì | no |
| lowrank_linear__with_ctx | sì | new_context_unseen_target | rpe1_hepg2_to_k562 | 2026 | 1.0773 | 0.1023 | 1.0000 | 58680 | 387 | 2.1793 | 0.0266 | 478150656 | 448384 | cross_context_within_training | sì | no |
| lowrank_linear__no_ctx | no | new_context_unseen_target | rpe1_hepg2_to_k562 | 2026 | 1.2111 | 0.1013 | 1.0000 | 58347 | 54 | 1.7396 | 0.0372 | 478150656 | 445860 | cross_context_within_training | sì | no |
| modular_frozen__with_ctx | sì | new_context_unseen_target | rpe1_hepg2_to_k562 | 2026 | 1.1828 | 0.1026 | 1.0000 | 110605 | 496 | 2.7496 | 0.0284 | 478150656 | 847797 | cross_context_within_training | sì | no |
| modular_frozen__no_ctx | no | new_context_unseen_target | rpe1_hepg2_to_k562 | 2026 | 1.2221 | 0.0978 | 1.0000 | 58421 | 128 | 3.3260 | 0.0196 | 478150656 | 447115 | cross_context_within_training | sì | no |
| lowrank_linear__with_ctx | sì | new_context_unseen_target | rpe1_hepg2_to_k562 | 2027 | 1.0479 | 0.0984 | 1.0000 | 58680 | 387 | 1.8384 | 0.0300 | 478150656 | 448320 | cross_context_within_training | sì | no |
| lowrank_linear__no_ctx | no | new_context_unseen_target | rpe1_hepg2_to_k562 | 2027 | 1.1404 | 0.0992 | 1.0000 | 58347 | 54 | 1.6956 | 0.0271 | 478150656 | 445784 | cross_context_within_training | sì | no |
| modular_frozen__with_ctx | sì | new_context_unseen_target | rpe1_hepg2_to_k562 | 2027 | 1.0752 | 0.0886 | 1.0000 | 110605 | 496 | 3.1555 | 0.0286 | 478150656 | 847749 | cross_context_within_training | sì | no |
| modular_frozen__no_ctx | no | new_context_unseen_target | rpe1_hepg2_to_k562 | 2027 | 1.1376 | 0.0991 | 1.0000 | 58421 | 128 | 2.3655 | 0.0285 | 478150656 | 447040 | cross_context_within_training | sì | no |
