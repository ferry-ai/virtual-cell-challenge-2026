# Testi delle sottomissioni del 24 settembre

Scritti il 24 settembre verso le 11:20 UTC, dopo il punteggio del t15 e prima della generazione di t16 e t17. Ricette in `configs/recipes/`; previsioni e regole di lettura in `reports/prediction_t16_2026-09-24/` e `reports/prediction_t17_2026-09-24/`.

## t16

**Model name:** `trial-16 trial-01 generator + K562+CD4+HCT116 same-target transfer a=0.788`

**Description:**

Identical to trial-15 except that the predicted effects are scaled by 0.788 instead of 0.394. Cells are sampled exactly as in trial-01 (Poisson counts at library sizes resampled from each context's own control cells, around the context's control profile shifted by the predicted effect; no control cell is copied). The predicted effect of a target is an equal-weight, reliability-weighted mean of its measured CRISPRi response in public sources -- K562 genome-wide Perturb-seq (Replogle et al. 2022), primary CD4+ T cells (GSE314342 pseudobulk, donor-matched controls) and HCT116 from X-Atlas/Orion (Xaira, CC-BY-NC-SA-4.0; GEM-batch-matched controls) -- each source's mean response removed, then scaled. No perturbed cell of the official contexts is used.

## t17

**Model name:** `trial-17 trial-01 generator + K562+CD4+HCT116+HEK293T same-target transfer a=0.4285`

**Description:**

Identical to trial-15 except that HEK293T from X-Atlas/Orion is added as a fourth source at equal weight and the effects are scaled by 0.4285, which gives the same median 99th-percentile absolute effect as trial-15. Cells are sampled exactly as in trial-01 (Poisson counts at library sizes resampled from each context's own control cells, around the context's control profile shifted by the predicted effect; no control cell is copied). The predicted effect of a target is an equal-weight, reliability-weighted mean of its measured CRISPRi response in public sources -- K562 genome-wide Perturb-seq (Replogle et al. 2022), primary CD4+ T cells (GSE314342 pseudobulk, donor-matched controls) and HCT116 and HEK293T from X-Atlas/Orion (Xaira, CC-BY-NC-SA-4.0; GEM-batch-matched controls) -- each source's mean response removed, then scaled. No perturbed cell of the official contexts is used.
