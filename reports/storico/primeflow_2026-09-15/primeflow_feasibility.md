# PRiMeFlow — fattibilità per VCC 2026

Fonte: [arXiv:2604.13986v2](https://arxiv.org/abs/2604.13986), consultato il 2026-09-15.
Nessun peso è stato scaricato e nessun modello è stato eseguito.

| ID | Tipo | Affermazione | Sezione |
|---|---|---|---|
| A1 | cited | PRiMeFlow is an end-to-end flow-matching model in gene-expression space (U-Net velocity field). | abstract |
| A2 | cited | Reported 'outstanding performance' on ARC VCC 2025 H1 uses a pretraining-then-finetuning strategy, not pretrained-only. | 4.4 / Appendix B |
| A3 | cited | On H1 public test, pretrained-only PDS 0.712 vs finetuned-200pts PDS 0.817 (Table 5). Finetuning helps. These are VCC 2025 metrics, not 2026. | Appendix C Table 5 |
| A4 | cited | Finetuning variants include H1 perturbations and, in 300pts, external data covering public and private test perturbation identities. Control cells from external data are kept during finetuning. | Appendix B |
| A5 | derived | VCC 2025 H1 provided perturbative training in the query context. VCC 2026 query contexts have no perturbations. A 2025 H1 number does not demonstrate 2026 zero-shot context transfer. | interpretation |
| A6 | cited | Covariate-transfer experiments on Srivatsan20 and Jiang24 in PerturBench are a closer analogue, but the paper's VCC headline result is the H1 finetuned number. | 2.1-2.2 |
| A7 | missing | Official code and weights were not located in this session. | — |
| A8 | cited | Inference uses Dopri5 ODE integration from Gaussian noise with classifier-free guidance (weight 20 perturbed / 5 control) and manually zeros the target gene. Cost of a 18,533-gene U-Net ODE on this hardware is unmeasured. | B.3 |

## Decisione

Do not port PyTorch flow-matching before a measured cost and a protocol that holds out ALL query-context perturbations. The VCC 2025 H1 headline is the wrong task. A minimum experiment, if code appears, is pretrained-only on our frozen splits versus ShrunkTransfer, with query perturbations excluded.
