# Testi della sottomissione del t08

Scritti il 22 settembre 2026, prima di qualunque invio e prima di qualunque punteggio del t08.
Descrivono ciò che il file contiene, non ciò che speriamo faccia. La previsione è registrata a
parte in `reports/prediction_t08_2026-09-22/prediction.json`.

## t08

**Model name:** `trial-08 trial-01 generator + K562+CD4 same-target transfer a=0.197`

**Description:**

Cells are sampled exactly as in trial-01: Poisson counts at library sizes resampled from each
context's own control cells, around that context's control profile shifted by the predicted
effect; no control cell is copied into the prediction. The predicted effect of a target is a
reliability-weighted mean of its measured CRISPRi response in public data -- K562 genome-wide
Perturb-seq (Replogle et al. 2022) and primary CD4+ T cells (GSE314342 pseudobulk, donor-matched
controls) -- with each source's mean response removed, scaled by 0.197 as in trial-01. No
perturbed cell of the official contexts is used.
