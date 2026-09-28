# Tabella comparativa del pilot modulare

Generata dai JSON di risultato, non a mano. Metrica primaria: `pooled_mse_vs_null` (più basso è meglio), spazio pseudobulk log2FC, **non** un punteggio VCC. Nessuna variante è scelta sul test esterno: la colonna `eleggibile sul test` è sempre no.

| modello | usa contesto | protocollo | direzione | seed | MSE/nullo | Pearson med. | copertura bersagli | parametri tot. | parametri addestrabili | train s | infer s | picco RSS | artefatto B | ampiezza | contesto identificabile | eleggibile sul test |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| lowrank_linear__with_ctx | sì | new_context_seen_target | k562_rpe1_to_hepg2 | 2026 | 1.7469 | 0.1453 | 1.0000 | 432120 | 11115 | 4.0321 | 0.0865 | 392306688 | 3310543 | cross_context_within_training | sì | no |
| lowrank_linear__no_ctx | no | new_context_seen_target | k562_rpe1_to_hepg2 | 2026 | 1.6796 | 0.1213 | 1.0000 | 429715 | 8710 | 3.5273 | 0.0791 | 392306688 | 3292549 | cross_context_within_training | sì | no |
| modular_frozen__with_ctx | sì | new_context_seen_target | k562_rpe1_to_hepg2 | 2026 | 1.0510 | 0.1591 | 1.0000 | 838061 | 2528 | 9.0570 | 0.0885 | 392306688 | 6425956 | cross_context_within_training | sì | no |
| modular_frozen__no_ctx | no | new_context_seen_target | k562_rpe1_to_hepg2 | 2026 | 1.1545 | 0.1651 | 1.0000 | 837765 | 2232 | 8.7259 | 0.1282 | 392306688 | 6423125 | cross_context_within_training | sì | no |
| lowrank_linear__with_ctx | sì | new_context_seen_target | k562_hepg2_to_rpe1 | 2026 | 1.0106 | 0.1964 | 1.0000 | 432120 | 11115 | 4.1149 | 0.1103 | 478015488 | 3309849 | cross_context_within_training | sì | no |
| lowrank_linear__no_ctx | no | new_context_seen_target | k562_hepg2_to_rpe1 | 2026 | 1.0392 | 0.1598 | 1.0000 | 429715 | 8710 | 3.6238 | 0.0826 | 478015488 | 3291850 | cross_context_within_training | sì | no |
| modular_frozen__with_ctx | sì | new_context_seen_target | k562_hepg2_to_rpe1 | 2026 | 0.8870 | 0.3262 | 1.0000 | 838061 | 2528 | 8.8260 | 0.0859 | 478015488 | 6425325 | cross_context_within_training | sì | no |
| modular_frozen__no_ctx | no | new_context_seen_target | k562_hepg2_to_rpe1 | 2026 | 0.8882 | 0.2977 | 1.0000 | 111333 | 1224 | 7.6969 | 0.0920 | 478015488 | 854080 | cross_context_within_training | sì | no |
| lowrank_linear__with_ctx | sì | new_context_seen_target | rpe1_hepg2_to_k562 | 2026 | 1.3772 | 0.1039 | 1.0000 | 432120 | 11115 | 4.2554 | 0.0789 | 478773248 | 3310834 | cross_context_within_training | sì | no |
| lowrank_linear__no_ctx | no | new_context_seen_target | rpe1_hepg2_to_k562 | 2026 | 1.5556 | 0.1031 | 1.0000 | 429715 | 8710 | 3.8703 | 0.0715 | 478773248 | 3292833 | cross_context_within_training | sì | no |
| modular_frozen__with_ctx | sì | new_context_seen_target | rpe1_hepg2_to_k562 | 2026 | 1.1083 | 0.0809 | 1.0000 | 215405 | 1664 | 7.6107 | 0.0722 | 478773248 | 1653202 | cross_context_within_training | sì | no |
| modular_frozen__no_ctx | no | new_context_seen_target | rpe1_hepg2_to_k562 | 2026 | 1.2916 | 0.0869 | 1.0000 | 215109 | 1368 | 9.8855 | 0.1148 | 478773248 | 1650378 | cross_context_within_training | sì | no |
| lowrank_linear__with_ctx | sì | new_context_unseen_target | k562_rpe1_to_hepg2 | 2026 | 1.2711 | 0.1508 | 1.0000 | 110840 | 731 | 2.7227 | 0.0391 | 478773248 | 847947 | cross_context_within_training | sì | no |
| lowrank_linear__no_ctx | no | new_context_unseen_target | k562_rpe1_to_hepg2 | 2026 | 1.1079 | 0.1515 | 1.0000 | 110211 | 102 | 4.0691 | 0.0326 | 478773248 | 843252 | cross_context_within_training | sì | no |
| modular_frozen__with_ctx | sì | new_context_unseen_target | k562_rpe1_to_hepg2 | 2026 | 1.1012 | 0.1483 | 1.0000 | 110605 | 496 | 4.7776 | 0.0484 | 478773248 | 847572 | cross_context_within_training | sì | no |
| modular_frozen__no_ctx | no | new_context_unseen_target | k562_rpe1_to_hepg2 | 2026 | 1.0744 | 0.1553 | 1.0000 | 110309 | 200 | 4.8752 | 0.0323 | 478773248 | 844680 | cross_context_within_training | sì | no |
| lowrank_linear__with_ctx | sì | new_context_unseen_target | k562_hepg2_to_rpe1 | 2026 | 0.8900 | 0.3452 | 1.0000 | 110840 | 731 | 1.9539 | 0.0269 | 478773248 | 847468 | cross_context_within_training | sì | no |
| lowrank_linear__no_ctx | no | new_context_unseen_target | k562_hepg2_to_rpe1 | 2026 | 0.8978 | 0.3330 | 1.0000 | 110211 | 102 | 1.8880 | 0.0277 | 478773248 | 842766 | cross_context_within_training | sì | no |
| modular_frozen__with_ctx | sì | new_context_unseen_target | k562_hepg2_to_rpe1 | 2026 | 0.8825 | 0.3146 | 1.0000 | 110605 | 496 | 3.8443 | 0.0302 | 478773248 | 847090 | cross_context_within_training | sì | no |
| modular_frozen__no_ctx | no | new_context_unseen_target | k562_hepg2_to_rpe1 | 2026 | 0.8833 | 0.3448 | 1.0000 | 214085 | 344 | 4.5989 | 0.0275 | 478773248 | 1639634 | cross_context_within_training | sì | no |
| lowrank_linear__with_ctx | sì | new_context_unseen_target | rpe1_hepg2_to_k562 | 2026 | 1.0759 | 0.1028 | 1.0000 | 110840 | 731 | 2.0620 | 0.0204 | 478773248 | 848179 | cross_context_within_training | sì | no |
| lowrank_linear__no_ctx | no | new_context_unseen_target | rpe1_hepg2_to_k562 | 2026 | 1.2125 | 0.1030 | 1.0000 | 110211 | 102 | 1.6550 | 0.0258 | 478773248 | 843480 | cross_context_within_training | sì | no |
| modular_frozen__with_ctx | sì | new_context_unseen_target | rpe1_hepg2_to_k562 | 2026 | 1.1987 | 0.0934 | 1.0000 | 837037 | 1504 | 5.1868 | 0.0271 | 478773248 | 6416220 | cross_context_within_training | sì | no |
| modular_frozen__no_ctx | no | new_context_unseen_target | rpe1_hepg2_to_k562 | 2026 | 1.2494 | 0.0955 | 1.0000 | 836741 | 1208 | 5.1927 | 0.0293 | 478773248 | 6413325 | cross_context_within_training | sì | no |
