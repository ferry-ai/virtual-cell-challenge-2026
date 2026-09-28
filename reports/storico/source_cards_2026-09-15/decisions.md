# Source-card decisions — 15 September 2026

Compiled from existing local evidence and public records. Not a new measurement of any matrix.

| ID | Class | Decision | Why |
|---|---|---|---|
| `replogle_k562_gwps_singlecell` | CRISPRi | **defer** | Adds real cells for validation/generator work on a line we already train from as pseudobulk. Not a new biological context. Download only a bounded extract after remote preflight; do not replace the local baseline until an ablation says so. |
| `vcc2025_h1` | CRISPRi | **defer** | Need a file manifest and the RNA matrix. Pluripotent lineage matches none of A/B/C. Useful as an extra perturbed context once RNA exists. |
| `cd4_marson` | CRISPRi | **defer** | Highest panel coverage among candidates, nearest lineage to context A, but 1.7 TB single-cell. Reopen after Jiang/Jurkat audits. Do not double-count GEO, Zenodo and the S3 mirror as three sources. |
| `srivatsan_sciplex3` | drug | **exclude** | Pharmacological. Useful at most as pretraining or a context descriptor. No knockdown labels. Not in the first acquisition wave. |
| `mcfaline_sciplex_gxe` | combo_genetic_chemical | **defer** | Genetic plus chemical. Do not treat the combined arm as CRISPRi. After Jiang/Jurkat: verify mechanism, vehicle controls, separable arms. |
| `tahoe_100m` | drug | **exclude** | Pharmacological atlas. No automatic drug → knockdown map. D-005. |
| `scbasecount` | observational | **exclude** | Observational atlas. May describe basal state; does not label knockdowns. |
