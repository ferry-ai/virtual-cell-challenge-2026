# Tabella comparativa del pilot modulare

Generata dai JSON di risultato, non a mano. Metrica primaria: `pooled_mse_vs_null` (più basso è meglio), spazio pseudobulk log2FC, **non** un punteggio VCC. Nessuna variante è scelta sul test esterno: la colonna `eleggibile sul test` è sempre no.

| modello | usa contesto | protocollo | direzione | seed | MSE/nullo | Pearson med. | copertura bersagli | parametri tot. | parametri addestrabili | train s | infer s | picco RSS | artefatto B | ampiezza | contesto identificabile | eleggibile sul test |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| lowrank_linear__B0 | sì | new_context_unseen_target | k562_rpe1_to_hepg2 | 2026 | 1.3198 | 0.1511 | 1.0000 | 58680 | 387 | 4.8565 | 0.0235 | 361832448 | 447355 | cross_context_within_training | sì | no |
| lowrank_linear__B1 | sì | new_context_unseen_target | k562_rpe1_to_hepg2 | 2026 | 1.6214 | 0.1491 | 1.0000 | 59949 | 1656 | 5.7526 | 0.0322 | 361832448 | 454197 | cross_context_within_training | sì | no |
| lowrank_linear__B2 | no | new_context_unseen_target | k562_rpe1_to_hepg2 | 2026 | 1.4274 | 0.1358 | 1.0000 | 59616 | 1323 | 6.5673 | 0.0276 | 361832448 | 451689 | cross_context_within_training | sì | no |
| lowrank_linear__B3 | sì | new_context_unseen_target | k562_rpe1_to_hepg2 | 2026 | 1.3501 | 0.1411 | 1.0000 | 59949 | 1656 | 4.9391 | 0.0195 | 361832448 | 454226 | cross_context_within_training | sì | no |
| modular_frozen__B0 | sì | new_context_unseen_target | k562_rpe1_to_hepg2 | 2026 | 1.1012 | 0.1483 | 1.0000 | 110605 | 496 | 2.5464 | 0.0246 | 361832448 | 846687 | cross_context_within_training | sì | no |
| modular_frozen__B1 | sì | new_context_unseen_target | k562_rpe1_to_hepg2 | 2026 | 1.1163 | 0.1545 | 1.0000 | 59845 | 1552 | 1.9169 | 0.0163 | 361832448 | 458261 | cross_context_within_training | sì | no |
| modular_frozen__B2 | no | new_context_unseen_target | k562_rpe1_to_hepg2 | 2026 | 1.4802 | 0.1178 | 1.0000 | 111437 | 1328 | 5.4767 | 0.0193 | 361832448 | 853215 | cross_context_within_training | sì | no |
| modular_frozen__B3 | sì | new_context_unseen_target | k562_rpe1_to_hepg2 | 2026 | 1.1165 | 0.1544 | 1.0000 | 59845 | 1552 | 2.2400 | 0.0181 | 361832448 | 458289 | cross_context_within_training | sì | no |
| lowrank_linear__B0 | sì | new_context_unseen_target | k562_rpe1_to_hepg2 | 2027 | 1.3037 | 0.1716 | 1.0000 | 58680 | 387 | 6.4531 | 0.0312 | 361832448 | 447473 | cross_context_within_training | sì | no |
| lowrank_linear__B1 | sì | new_context_unseen_target | k562_rpe1_to_hepg2 | 2027 | 1.3375 | 0.1609 | 1.0000 | 59949 | 1656 | 3.3699 | 0.0198 | 361832448 | 453984 | cross_context_within_training | sì | no |
| lowrank_linear__B2 | no | new_context_unseen_target | k562_rpe1_to_hepg2 | 2027 | 1.1861 | 0.1593 | 1.0000 | 59616 | 1323 | 4.2890 | 0.0271 | 361832448 | 451453 | cross_context_within_training | sì | no |
| lowrank_linear__B3 | sì | new_context_unseen_target | k562_rpe1_to_hepg2 | 2027 | 1.4345 | 0.1641 | 1.0000 | 59949 | 1656 | 5.4260 | 0.0794 | 361832448 | 453915 | cross_context_within_training | sì | no |
| modular_frozen__B0 | sì | new_context_unseen_target | k562_rpe1_to_hepg2 | 2027 | 1.0524 | 0.1694 | 1.0000 | 58717 | 424 | 5.0159 | 0.0187 | 361832448 | 449097 | cross_context_within_training | sì | no |
| modular_frozen__B1 | sì | new_context_unseen_target | k562_rpe1_to_hepg2 | 2027 | 1.0480 | 0.1736 | 1.0000 | 111733 | 1624 | 2.8640 | 0.0209 | 361832448 | 856148 | cross_context_within_training | sì | no |
| modular_frozen__B2 | no | new_context_unseen_target | k562_rpe1_to_hepg2 | 2027 | 1.2427 | 0.1376 | 1.0000 | 111437 | 1328 | 3.1088 | 0.0330 | 361832448 | 853380 | cross_context_within_training | sì | no |
| modular_frozen__B3 | sì | new_context_unseen_target | k562_rpe1_to_hepg2 | 2027 | 1.0632 | 0.1723 | 1.0000 | 111733 | 1624 | 3.4486 | 0.0278 | 361832448 | 856167 | cross_context_within_training | sì | no |
| lowrank_linear__B0 | sì | new_context_unseen_target | k562_hepg2_to_rpe1 | 2026 | 0.8825 | 0.3465 | 1.0000 | 58680 | 387 | 3.6747 | 0.0243 | 361832448 | 446870 | cross_context_within_training | sì | no |
| lowrank_linear__B1 | sì | new_context_unseen_target | k562_hepg2_to_rpe1 | 2026 | 0.9139 | 0.2700 | 1.0000 | 59949 | 1656 | 4.7404 | 0.0179 | 361832448 | 453683 | cross_context_within_training | sì | no |
| lowrank_linear__B2 | no | new_context_unseen_target | k562_hepg2_to_rpe1 | 2026 | 0.9356 | 0.2478 | 1.0000 | 59616 | 1323 | 4.0105 | 0.0373 | 361832448 | 451180 | cross_context_within_training | sì | no |
| lowrank_linear__B3 | sì | new_context_unseen_target | k562_hepg2_to_rpe1 | 2026 | 0.9089 | 0.2799 | 1.0000 | 59949 | 1656 | 4.4469 | 0.0215 | 361832448 | 453724 | cross_context_within_training | sì | no |
| modular_frozen__B0 | sì | new_context_unseen_target | k562_hepg2_to_rpe1 | 2026 | 0.8825 | 0.3146 | 1.0000 | 110605 | 496 | 2.1582 | 0.0348 | 361832448 | 846205 | cross_context_within_training | sì | no |
| modular_frozen__B1 | sì | new_context_unseen_target | k562_hepg2_to_rpe1 | 2026 | 0.8755 | 0.3481 | 1.0000 | 59845 | 1552 | 4.4894 | 0.0243 | 361832448 | 457781 | cross_context_within_training | sì | no |
| modular_frozen__B2 | no | new_context_unseen_target | k562_hepg2_to_rpe1 | 2026 | 0.9393 | 0.2397 | 1.0000 | 59549 | 1256 | 2.8373 | 0.0195 | 361832448 | 455015 | cross_context_within_training | sì | no |
| modular_frozen__B3 | sì | new_context_unseen_target | k562_hepg2_to_rpe1 | 2026 | 0.8781 | 0.3462 | 1.0000 | 59845 | 1552 | 2.2618 | 0.0205 | 361832448 | 457800 | cross_context_within_training | sì | no |
| lowrank_linear__B0 | sì | new_context_unseen_target | k562_hepg2_to_rpe1 | 2027 | 0.8785 | 0.3623 | 1.0000 | 58680 | 387 | 4.0045 | 0.0200 | 361832448 | 446811 | cross_context_within_training | sì | no |
| lowrank_linear__B1 | sì | new_context_unseen_target | k562_hepg2_to_rpe1 | 2027 | 0.9076 | 0.3040 | 1.0000 | 59949 | 1656 | 3.5543 | 0.0235 | 361832448 | 453293 | cross_context_within_training | sì | no |
| lowrank_linear__B2 | no | new_context_unseen_target | k562_hepg2_to_rpe1 | 2027 | 0.9257 | 0.2366 | 1.0000 | 59616 | 1323 | 4.6199 | 0.0234 | 361832448 | 450785 | cross_context_within_training | sì | no |
| lowrank_linear__B3 | sì | new_context_unseen_target | k562_hepg2_to_rpe1 | 2027 | 0.9180 | 0.2988 | 1.0000 | 59949 | 1656 | 3.4780 | 0.0217 | 361832448 | 453252 | cross_context_within_training | sì | no |
| modular_frozen__B0 | sì | new_context_unseen_target | k562_hepg2_to_rpe1 | 2027 | 0.8820 | 0.3366 | 1.0000 | 58717 | 424 | 2.7276 | 0.0364 | 361832448 | 448411 | cross_context_within_training | sì | no |
| modular_frozen__B1 | sì | new_context_unseen_target | k562_hepg2_to_rpe1 | 2027 | 0.8789 | 0.3349 | 1.0000 | 111733 | 1624 | 1.9668 | 0.0206 | 361832448 | 855522 | cross_context_within_training | sì | no |
| modular_frozen__B2 | no | new_context_unseen_target | k562_hepg2_to_rpe1 | 2027 | 0.9395 | 0.2031 | 1.0000 | 111437 | 1328 | 1.6052 | 0.0152 | 361832448 | 852753 | cross_context_within_training | sì | no |
| modular_frozen__B3 | sì | new_context_unseen_target | k562_hepg2_to_rpe1 | 2027 | 0.8752 | 0.3407 | 1.0000 | 111733 | 1624 | 1.4119 | 0.0154 | 361832448 | 855520 | cross_context_within_training | sì | no |
| lowrank_linear__B0 | sì | new_context_unseen_target | rpe1_hepg2_to_k562 | 2026 | 1.0773 | 0.1023 | 1.0000 | 58680 | 387 | 4.2286 | 0.0201 | 361832448 | 447500 | cross_context_within_training | sì | no |
| lowrank_linear__B1 | sì | new_context_unseen_target | rpe1_hepg2_to_k562 | 2026 | 1.2312 | 0.0888 | 1.0000 | 59949 | 1656 | 3.8723 | 0.0222 | 361832448 | 454339 | cross_context_within_training | sì | no |
| lowrank_linear__B2 | no | new_context_unseen_target | rpe1_hepg2_to_k562 | 2026 | 1.4761 | 0.0925 | 1.0000 | 59616 | 1323 | 3.3735 | 0.0252 | 361832448 | 451830 | cross_context_within_training | sì | no |
| lowrank_linear__B3 | sì | new_context_unseen_target | rpe1_hepg2_to_k562 | 2026 | 1.1103 | 0.0708 | 1.0000 | 59949 | 1656 | 3.7205 | 0.0224 | 361832448 | 454373 | cross_context_within_training | sì | no |
| modular_frozen__B0 | sì | new_context_unseen_target | rpe1_hepg2_to_k562 | 2026 | 1.1828 | 0.1026 | 1.0000 | 110605 | 496 | 2.1148 | 0.0161 | 361832448 | 846912 | cross_context_within_training | sì | no |
| modular_frozen__B1 | sì | new_context_unseen_target | rpe1_hepg2_to_k562 | 2026 | 1.1785 | 0.0977 | 1.0000 | 59845 | 1552 | 2.0649 | 0.0340 | 361832448 | 458411 | cross_context_within_training | sì | no |
| modular_frozen__B2 | no | new_context_unseen_target | rpe1_hepg2_to_k562 | 2026 | 1.4642 | 0.0871 | 1.0000 | 59549 | 1256 | 3.3210 | 0.0172 | 361832448 | 455597 | cross_context_within_training | sì | no |
| modular_frozen__B3 | sì | new_context_unseen_target | rpe1_hepg2_to_k562 | 2026 | 1.1801 | 0.0981 | 1.0000 | 59845 | 1552 | 2.2426 | 0.0170 | 361832448 | 458428 | cross_context_within_training | sì | no |
| lowrank_linear__B0 | sì | new_context_unseen_target | rpe1_hepg2_to_k562 | 2027 | 1.0479 | 0.0984 | 1.0000 | 58680 | 387 | 3.9948 | 0.0429 | 361832448 | 447436 | cross_context_within_training | sì | no |
| lowrank_linear__B1 | sì | new_context_unseen_target | rpe1_hepg2_to_k562 | 2027 | 1.0958 | 0.0825 | 1.0000 | 59949 | 1656 | 2.3609 | 0.0178 | 361832448 | 453928 | cross_context_within_training | sì | no |
| lowrank_linear__B2 | no | new_context_unseen_target | rpe1_hepg2_to_k562 | 2027 | 1.2167 | 0.0839 | 1.0000 | 59616 | 1323 | 1.7685 | 0.0249 | 361832448 | 451411 | cross_context_within_training | sì | no |
| lowrank_linear__B3 | sì | new_context_unseen_target | rpe1_hepg2_to_k562 | 2027 | 1.0909 | 0.0936 | 1.0000 | 59949 | 1656 | 2.4182 | 0.0229 | 361832448 | 453883 | cross_context_within_training | sì | no |
| modular_frozen__B0 | sì | new_context_unseen_target | rpe1_hepg2_to_k562 | 2027 | 1.0752 | 0.0886 | 1.0000 | 110605 | 496 | 2.2035 | 0.0201 | 361832448 | 846864 | cross_context_within_training | sì | no |
| modular_frozen__B1 | sì | new_context_unseen_target | rpe1_hepg2_to_k562 | 2027 | 1.1057 | 0.0967 | 1.0000 | 59845 | 1552 | 2.2017 | 0.0167 | 361832448 | 458332 | cross_context_within_training | sì | no |
| modular_frozen__B2 | no | new_context_unseen_target | rpe1_hepg2_to_k562 | 2027 | 1.2578 | 0.0885 | 1.0000 | 111437 | 1328 | 2.2822 | 0.0286 | 361832448 | 853395 | cross_context_within_training | sì | no |
| modular_frozen__B3 | sì | new_context_unseen_target | rpe1_hepg2_to_k562 | 2027 | 1.1082 | 0.0950 | 1.0000 | 59845 | 1552 | 3.2479 | 0.0311 | 361832448 | 458344 | cross_context_within_training | sì | no |
