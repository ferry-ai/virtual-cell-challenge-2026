# Gate di espressione: la regola di decisione applicata ai numeri

Run `x001`, protocollo `new_context_seen_target`, statistica `diff`. Generata da `scripts/69_expression_gate_decision.py`, non a mano.

La regola è stata scritta in `configs/benchmark_expression_gate.yaml` **prima** del run (`fixed_before_the_run: True`, `owner_confirmed: False`). Nessun vincitore viene dichiarato: qui si legge solo se le clausole sono soddisfatte.

| variante | promossa a candidato |
| --- | --- |
| gate_G1 | no |
| gate_G2 | no |
| gate_G3 | no |

Gate identità scelto in 30 righe su 54.

## Le clausole, una riga per split

Positivo = il braccio `a` è **peggio** di `b`. La statistica è la differenza appaiata per bersaglio (`diff`), la stessa di CP-0013.

| variante | clausola | a | b | direzione | seed | differenza | IC95 | IC esclude 0 | clausola soddisfatta |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gate_G1 | beats_shrunk_transfer | gate_G1 | shrunk_transfer | k562_rpe1_to_hepg2 | 2026 | 0.0000 | [0.0000, 0.0000] | no | no |
| gate_G1 | beats_shrunk_transfer | gate_G1 | shrunk_transfer | k562_rpe1_to_hepg2 | 2027 | 0.0034 | [0.0022, 0.0046] | sì | no |
| gate_G1 | beats_shrunk_transfer | gate_G1 | shrunk_transfer | k562_hepg2_to_rpe1 | 2026 | 0.0000 | [0.0000, 0.0000] | no | no |
| gate_G1 | beats_shrunk_transfer | gate_G1 | shrunk_transfer | k562_hepg2_to_rpe1 | 2027 | 0.0033 | [0.0019, 0.0048] | sì | no |
| gate_G1 | beats_shrunk_transfer | gate_G1 | shrunk_transfer | rpe1_hepg2_to_k562 | 2026 | 0.0000 | [0.0000, 0.0000] | no | no |
| gate_G1 | beats_shrunk_transfer | gate_G1 | shrunk_transfer | rpe1_hepg2_to_k562 | 2027 | -0.0131 | [-0.0173, -0.0092] | sì | sì |
| gate_G1 | permuted_does_not_beat | gate_G1_perm | gate_G1 | k562_rpe1_to_hepg2 | 2026 | 0.0000 | [0.0000, 0.0000] | no | sì |
| gate_G1 | permuted_does_not_beat | gate_G1_perm | gate_G1 | k562_rpe1_to_hepg2 | 2027 | -0.0005 | [-0.0009, -0.0000] | sì | no |
| gate_G1 | permuted_does_not_beat | gate_G1_perm | gate_G1 | k562_hepg2_to_rpe1 | 2026 | 0.0000 | [0.0000, 0.0000] | no | sì |
| gate_G1 | permuted_does_not_beat | gate_G1_perm | gate_G1 | k562_hepg2_to_rpe1 | 2027 | -0.0017 | [-0.0026, -0.0010] | sì | no |
| gate_G1 | permuted_does_not_beat | gate_G1_perm | gate_G1 | rpe1_hepg2_to_k562 | 2026 | 0.0000 | [0.0000, 0.0000] | no | sì |
| gate_G1 | permuted_does_not_beat | gate_G1_perm | gate_G1 | rpe1_hepg2_to_k562 | 2027 | 0.0029 | [0.0023, 0.0036] | sì | sì |
| gate_G1 | source_measurably_worse | gate_G1_src | gate_G1 | k562_rpe1_to_hepg2 | 2026 | 0.0002 | [0.0000, 0.0003] | sì | sì |
| gate_G1 | source_measurably_worse | gate_G1_src | gate_G1 | k562_rpe1_to_hepg2 | 2027 | -0.0014 | [-0.0017, -0.0011] | sì | no |
| gate_G1 | source_measurably_worse | gate_G1_src | gate_G1 | k562_hepg2_to_rpe1 | 2026 | -0.0000 | [-0.0000, 0.0000] | no | no |
| gate_G1 | source_measurably_worse | gate_G1_src | gate_G1 | k562_hepg2_to_rpe1 | 2027 | -0.0027 | [-0.0033, -0.0021] | sì | no |
| gate_G1 | source_measurably_worse | gate_G1_src | gate_G1 | rpe1_hepg2_to_k562 | 2026 | -0.0045 | [-0.0056, -0.0035] | sì | no |
| gate_G1 | source_measurably_worse | gate_G1_src | gate_G1 | rpe1_hepg2_to_k562 | 2027 | -0.0070 | [-0.0093, -0.0051] | sì | no |
| gate_G2 | beats_shrunk_transfer | gate_G2 | shrunk_transfer | k562_rpe1_to_hepg2 | 2026 | 0.0000 | [0.0000, 0.0000] | no | no |
| gate_G2 | beats_shrunk_transfer | gate_G2 | shrunk_transfer | k562_rpe1_to_hepg2 | 2027 | 0.0000 | [0.0000, 0.0000] | no | no |
| gate_G2 | beats_shrunk_transfer | gate_G2 | shrunk_transfer | k562_hepg2_to_rpe1 | 2026 | 0.0000 | [0.0000, 0.0000] | no | no |
| gate_G2 | beats_shrunk_transfer | gate_G2 | shrunk_transfer | k562_hepg2_to_rpe1 | 2027 | 0.0015 | [0.0010, 0.0021] | sì | no |
| gate_G2 | beats_shrunk_transfer | gate_G2 | shrunk_transfer | rpe1_hepg2_to_k562 | 2026 | 0.0000 | [0.0000, 0.0000] | no | no |
| gate_G2 | beats_shrunk_transfer | gate_G2 | shrunk_transfer | rpe1_hepg2_to_k562 | 2027 | -0.0122 | [-0.0161, -0.0086] | sì | sì |
| gate_G2 | permuted_does_not_beat | gate_G2_perm | gate_G2 | k562_rpe1_to_hepg2 | 2026 | 0.0000 | [0.0000, 0.0000] | no | sì |
| gate_G2 | permuted_does_not_beat | gate_G2_perm | gate_G2 | k562_rpe1_to_hepg2 | 2027 | 0.0000 | [0.0000, 0.0000] | no | sì |
| gate_G2 | permuted_does_not_beat | gate_G2_perm | gate_G2 | k562_hepg2_to_rpe1 | 2026 | 0.0000 | [0.0000, 0.0000] | no | sì |
| gate_G2 | permuted_does_not_beat | gate_G2_perm | gate_G2 | k562_hepg2_to_rpe1 | 2027 | -0.0015 | [-0.0021, -0.0010] | sì | no |
| gate_G2 | permuted_does_not_beat | gate_G2_perm | gate_G2 | rpe1_hepg2_to_k562 | 2026 | 0.0000 | [0.0000, 0.0000] | no | sì |
| gate_G2 | permuted_does_not_beat | gate_G2_perm | gate_G2 | rpe1_hepg2_to_k562 | 2027 | 0.0078 | [0.0057, 0.0103] | sì | sì |
| gate_G2 | source_measurably_worse | gate_G2_src | gate_G2 | k562_rpe1_to_hepg2 | 2026 | 0.0000 | [0.0000, 0.0000] | no | no |
| gate_G2 | source_measurably_worse | gate_G2_src | gate_G2 | k562_rpe1_to_hepg2 | 2027 | 0.0002 | [0.0000, 0.0003] | sì | sì |
| gate_G2 | source_measurably_worse | gate_G2_src | gate_G2 | k562_hepg2_to_rpe1 | 2026 | 0.0000 | [0.0000, 0.0000] | no | no |
| gate_G2 | source_measurably_worse | gate_G2_src | gate_G2 | k562_hepg2_to_rpe1 | 2027 | -0.0002 | [-0.0005, -0.0000] | sì | no |
| gate_G2 | source_measurably_worse | gate_G2_src | gate_G2 | rpe1_hepg2_to_k562 | 2026 | -0.0041 | [-0.0051, -0.0031] | sì | no |
| gate_G2 | source_measurably_worse | gate_G2_src | gate_G2 | rpe1_hepg2_to_k562 | 2027 | -0.0066 | [-0.0088, -0.0048] | sì | no |
| gate_G3 | beats_shrunk_transfer | gate_G3 | shrunk_transfer | k562_rpe1_to_hepg2 | 2026 | 0.0000 | [0.0000, 0.0000] | no | no |
| gate_G3 | beats_shrunk_transfer | gate_G3 | shrunk_transfer | k562_rpe1_to_hepg2 | 2027 | 0.0000 | [0.0000, 0.0000] | no | no |
| gate_G3 | beats_shrunk_transfer | gate_G3 | shrunk_transfer | k562_hepg2_to_rpe1 | 2026 | 0.0000 | [0.0000, 0.0000] | no | no |
| gate_G3 | beats_shrunk_transfer | gate_G3 | shrunk_transfer | k562_hepg2_to_rpe1 | 2027 | 0.0000 | [0.0000, 0.0000] | no | no |
| gate_G3 | beats_shrunk_transfer | gate_G3 | shrunk_transfer | rpe1_hepg2_to_k562 | 2026 | 0.0000 | [0.0000, 0.0000] | no | no |
| gate_G3 | beats_shrunk_transfer | gate_G3 | shrunk_transfer | rpe1_hepg2_to_k562 | 2027 | -0.0028 | [-0.0038, -0.0019] | sì | sì |
| gate_G3 | permuted_does_not_beat | gate_G3_perm | gate_G3 | k562_rpe1_to_hepg2 | 2026 | 0.0000 | [0.0000, 0.0000] | no | sì |
| gate_G3 | permuted_does_not_beat | gate_G3_perm | gate_G3 | k562_rpe1_to_hepg2 | 2027 | 0.0000 | [0.0000, 0.0000] | no | sì |
| gate_G3 | permuted_does_not_beat | gate_G3_perm | gate_G3 | k562_hepg2_to_rpe1 | 2026 | 0.0000 | [0.0000, 0.0000] | no | sì |
| gate_G3 | permuted_does_not_beat | gate_G3_perm | gate_G3 | k562_hepg2_to_rpe1 | 2027 | 0.0027 | [0.0012, 0.0041] | sì | sì |
| gate_G3 | permuted_does_not_beat | gate_G3_perm | gate_G3 | rpe1_hepg2_to_k562 | 2026 | 0.0000 | [0.0000, 0.0000] | no | sì |
| gate_G3 | permuted_does_not_beat | gate_G3_perm | gate_G3 | rpe1_hepg2_to_k562 | 2027 | -0.0084 | [-0.0164, -0.0033] | sì | no |
| gate_G3 | source_measurably_worse | gate_G3_src | gate_G3 | k562_rpe1_to_hepg2 | 2026 | 0.0000 | [0.0000, 0.0000] | no | no |
| gate_G3 | source_measurably_worse | gate_G3_src | gate_G3 | k562_rpe1_to_hepg2 | 2027 | 0.0000 | [0.0000, 0.0000] | no | no |
| gate_G3 | source_measurably_worse | gate_G3_src | gate_G3 | k562_hepg2_to_rpe1 | 2026 | 0.0000 | [0.0000, 0.0000] | no | no |
| gate_G3 | source_measurably_worse | gate_G3_src | gate_G3 | k562_hepg2_to_rpe1 | 2027 | 0.0037 | [0.0025, 0.0048] | sì | sì |
| gate_G3 | source_measurably_worse | gate_G3_src | gate_G3 | rpe1_hepg2_to_k562 | 2026 | 0.0000 | [0.0000, 0.0000] | no | no |
| gate_G3 | source_measurably_worse | gate_G3_src | gate_G3 | rpe1_hepg2_to_k562 | 2027 | -0.0041 | [-0.0057, -0.0026] | sì | no |

## Letture dichiarate prima del run (non promuovono nulla)

| clausola | variante | vale ovunque | split che la rispettano |
| --- | --- | --- | --- |
| permuted_measurably_worse | gate_G1 | no | 1/6 |
| permuted_measurably_worse | gate_G2 | no | 1/6 |
| permuted_measurably_worse | gate_G3 | no | 1/6 |
| asymmetric_beats_symmetric | — | no | 2/6 |

## Che gate è stato scelto, e quanto ha toccato

| braccio | direzione | seed | identità | midpoint CPM | pendenza | attenuazione + | quota di |Δ| rimossa | MSE/nullo |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| gate_G1 | k562_rpe1_to_hepg2 | 2026 | sì | — | — | 1.00 | 0.0000 | 0.9521 |
| gate_G1_perm | k562_rpe1_to_hepg2 | 2026 | sì | — | — | 1.00 | 0.0000 | 0.9521 |
| gate_G1_src | k562_rpe1_to_hepg2 | 2026 | no | 3.0 | 4.0 | 1.00 | 0.0253 | 0.9525 |
| gate_G2 | k562_rpe1_to_hepg2 | 2026 | sì | — | — | 1.00 | 0.0000 | 0.9521 |
| gate_G2_perm | k562_rpe1_to_hepg2 | 2026 | sì | — | — | 1.00 | 0.0000 | 0.9521 |
| gate_G2_src | k562_rpe1_to_hepg2 | 2026 | sì | — | — | 1.00 | 0.0000 | 0.9521 |
| gate_G3 | k562_rpe1_to_hepg2 | 2026 | sì | — | — | 1.00 | 0.0000 | 0.9521 |
| gate_G3_perm | k562_rpe1_to_hepg2 | 2026 | sì | — | — | 1.00 | 0.0000 | 0.9521 |
| gate_G3_src | k562_rpe1_to_hepg2 | 2026 | sì | — | — | 1.00 | 0.0000 | 0.9521 |
| gate_G1 | k562_rpe1_to_hepg2 | 2027 | no | 10.0 | 4.0 | 1.00 | 0.1776 | 0.9547 |
| gate_G1_perm | k562_rpe1_to_hepg2 | 2027 | no | 3.0 | 2.0 | 1.00 | 0.1155 | 0.9535 |
| gate_G1_src | k562_rpe1_to_hepg2 | 2027 | no | 10.0 | 4.0 | 1.00 | 0.1584 | 0.9529 |
| gate_G2 | k562_rpe1_to_hepg2 | 2027 | sì | — | — | 1.00 | 0.0000 | 0.9494 |
| gate_G2_perm | k562_rpe1_to_hepg2 | 2027 | sì | — | — | 1.00 | 0.0000 | 0.9494 |
| gate_G2_src | k562_rpe1_to_hepg2 | 2027 | no | 3.0 | 4.0 | 0.50 | 0.0212 | 0.9498 |
| gate_G3 | k562_rpe1_to_hepg2 | 2027 | sì | — | — | 1.00 | 0.0000 | 0.9494 |
| gate_G3_perm | k562_rpe1_to_hepg2 | 2027 | sì | — | — | 1.00 | 0.0000 | 0.9494 |
| gate_G3_src | k562_rpe1_to_hepg2 | 2027 | sì | — | — | 1.00 | 0.0000 | 0.9494 |
| gate_G1 | k562_hepg2_to_rpe1 | 2026 | sì | — | — | 1.00 | 0.0000 | 0.9709 |
| gate_G1_perm | k562_hepg2_to_rpe1 | 2026 | sì | — | — | 1.00 | 0.0000 | 0.9709 |
| gate_G1_src | k562_hepg2_to_rpe1 | 2026 | no | 1.0 | 4.0 | 1.00 | 0.0040 | 0.9709 |
| gate_G2 | k562_hepg2_to_rpe1 | 2026 | sì | — | — | 1.00 | 0.0000 | 0.9709 |
| gate_G2_perm | k562_hepg2_to_rpe1 | 2026 | sì | — | — | 1.00 | 0.0000 | 0.9709 |
| gate_G2_src | k562_hepg2_to_rpe1 | 2026 | sì | — | — | 1.00 | 0.0000 | 0.9709 |
| gate_G3 | k562_hepg2_to_rpe1 | 2026 | sì | — | — | 1.00 | 0.0000 | 0.9709 |
| gate_G3_perm | k562_hepg2_to_rpe1 | 2026 | sì | — | — | 1.00 | 0.0000 | 0.9709 |
| gate_G3_src | k562_hepg2_to_rpe1 | 2026 | sì | — | — | 1.00 | 0.0000 | 0.9709 |
| gate_G1 | k562_hepg2_to_rpe1 | 2027 | no | 10.0 | 2.0 | 1.00 | 0.2760 | 0.9741 |
| gate_G1_perm | k562_hepg2_to_rpe1 | 2027 | no | 3.0 | 2.0 | 1.00 | 0.1125 | 0.9705 |
| gate_G1_src | k562_hepg2_to_rpe1 | 2027 | no | 10.0 | 4.0 | 1.00 | 0.1700 | 0.9707 |
| gate_G2 | k562_hepg2_to_rpe1 | 2027 | no | 3.0 | 2.0 | 0.50 | 0.0986 | 0.9705 |
| gate_G2_perm | k562_hepg2_to_rpe1 | 2027 | sì | — | — | 1.00 | 0.0000 | 0.9676 |
| gate_G2_src | k562_hepg2_to_rpe1 | 2027 | no | 10.0 | 4.0 | 0.50 | 0.1324 | 0.9710 |
| gate_G3 | k562_hepg2_to_rpe1 | 2027 | sì | — | — | 1.00 | 0.0000 | 0.9676 |
| gate_G3_perm | k562_hepg2_to_rpe1 | 2027 | no | 10.0 | 4.0 | 1.00 | 0.1131 | 0.9717 |
| gate_G3_src | k562_hepg2_to_rpe1 | 2027 | no | 10.0 | 2.0 | 1.00 | 0.1927 | 0.9727 |
| gate_G1 | rpe1_hepg2_to_k562 | 2026 | sì | — | — | 1.00 | 0.0000 | 0.9994 |
| gate_G1_perm | rpe1_hepg2_to_k562 | 2026 | sì | — | — | 1.00 | 0.0000 | 0.9994 |
| gate_G1_src | rpe1_hepg2_to_k562 | 2026 | no | 3.0 | 4.0 | 1.00 | 0.0303 | 0.9967 |
| gate_G2 | rpe1_hepg2_to_k562 | 2026 | sì | — | — | 1.00 | 0.0000 | 0.9994 |
| gate_G2_perm | rpe1_hepg2_to_k562 | 2026 | sì | — | — | 1.00 | 0.0000 | 0.9994 |
| gate_G2_src | rpe1_hepg2_to_k562 | 2026 | no | 3.0 | 4.0 | 0.50 | 0.0249 | 0.9968 |
| gate_G3 | rpe1_hepg2_to_k562 | 2026 | sì | — | — | 1.00 | 0.0000 | 0.9994 |
| gate_G3_perm | rpe1_hepg2_to_k562 | 2026 | sì | — | — | 1.00 | 0.0000 | 0.9994 |
| gate_G3_src | rpe1_hepg2_to_k562 | 2026 | sì | — | — | 1.00 | 0.0000 | 0.9994 |
| gate_G1 | rpe1_hepg2_to_k562 | 2027 | no | 3.0 | 2.0 | 1.00 | 0.1190 | 0.9923 |
| gate_G1_perm | rpe1_hepg2_to_k562 | 2027 | no | 3.0 | 2.0 | 1.00 | 0.1091 | 0.9940 |
| gate_G1_src | rpe1_hepg2_to_k562 | 2027 | no | 10.0 | 4.0 | 1.00 | 0.1725 | 0.9882 |
| gate_G2 | rpe1_hepg2_to_k562 | 2027 | no | 3.0 | 2.0 | 0.50 | 0.0978 | 0.9921 |
| gate_G2_perm | rpe1_hepg2_to_k562 | 2027 | no | 1.0 | 2.0 | 0.50 | 0.0386 | 0.9969 |
| gate_G2_src | rpe1_hepg2_to_k562 | 2027 | no | 10.0 | 4.0 | 0.50 | 0.1427 | 0.9880 |
| gate_G3 | rpe1_hepg2_to_k562 | 2027 | no | 1.0 | 2.0 | 1.00 | 0.0324 | 0.9982 |
| gate_G3_perm | rpe1_hepg2_to_k562 | 2027 | no | 10.0 | 4.0 | 1.00 | 0.1028 | 0.9944 |
| gate_G3_src | rpe1_hepg2_to_k562 | 2027 | no | 3.0 | 2.0 | 1.00 | 0.0892 | 0.9964 |

## Riproduzione delle righe condivise con il run di riferimento

Righe condivise: 54. Differenza assoluta massima: 0.00e+00. Identiche: sì.
