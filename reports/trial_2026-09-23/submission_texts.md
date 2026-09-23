# Testi della sottomissione del t10

Scritti il 23 settembre 2026, prima dell'invio e prima di qualunque punteggio del t10. La
previsione e la regola di lettura sono in `reports/prediction_t10_2026-09-23/prediction.json`.

## t10

**Model name:** `trial-10 trial-01 generator + K562-only same-target transfer a=0.197`

**Description:**

Attribution control for trial-08: identical to it except that the CD4 source is removed.
Cells are sampled exactly as in trial-01 (Poisson counts at library sizes resampled from each
context's own control cells, around the context's control profile shifted by the predicted
effect; no control cell is copied). The predicted effect of a target is its measured CRISPRi
response in K562 genome-wide Perturb-seq (Replogle et al. 2022), with K562's mean response
removed, scaled by 0.197. No perturbed cell of the official contexts is used.

## t11

Scritto il 23 settembre, prima della generazione completa e prima di qualunque punteggio del
t11. Previsione e regola di lettura in `reports/prediction_t11_2026-09-23/prediction.json`.

**Model name:** `trial-11 trial-01 generator + K562+CD4+HCT116 same-target transfer a=0.197`

**Description:**

Cells are sampled exactly as in trial-01 (Poisson counts at library sizes resampled from each
context's own control cells, around the context's control profile shifted by the predicted
effect; no control cell is copied). The predicted effect of a target is an equal-weight,
reliability-weighted mean of its measured CRISPRi response in three public sources -- K562
genome-wide Perturb-seq (Replogle et al. 2022), primary CD4+ T cells (GSE314342 pseudobulk,
donor-matched controls) and HCT116 from X-Atlas/Orion (Xaira, CC-BY-NC-SA-4.0; GEM-batch-matched
controls) -- each source's mean response removed, scaled by 0.197. No perturbed cell of the
official contexts is used.
