# Testi delle sottomissioni preparate il 25 settembre

Scritti il 25 settembre verso le 01:30 UTC, dopo i punteggi di t16 e t17 e prima della
generazione del t18. Ricetta in `configs/recipes/t18.json`; previsione e regola di lettura in
`reports/prediction_t18_2026-09-25/prediction.json`. L'invio consuma quota e aspetta il via del
proprietario.

## t18

**Model name:** `trial-18 trial-01 generator + K562+CD4+HCT116 same-target transfer a=1.576`

**Description:**

Identical to trial-16 except that the predicted effects are scaled by 1.576 instead of 0.788. Cells are sampled exactly as in trial-01 (Poisson counts at library sizes resampled from each context's own control cells, around the context's control profile shifted by the predicted effect; no control cell is copied). The predicted effect of a target is an equal-weight, reliability-weighted mean of its measured CRISPRi response in public sources -- K562 genome-wide Perturb-seq (Replogle et al. 2022), primary CD4+ T cells (GSE314342 pseudobulk, donor-matched controls) and HCT116 from X-Atlas/Orion (Xaira, CC-BY-NC-SA-4.0; GEM-batch-matched controls) -- each source's mean response removed, then scaled. No perturbed cell of the official contexts is used.

## t19

Scritto il 25 settembre verso le 01:38 UTC, prima della generazione del t19. Ricetta
`configs/recipes/t19.json`; previsione e regola in `reports/prediction_t19_2026-09-25/prediction.json`.

**Model name:** `trial-19 trial-01 generator + K562+CD4+HCT116 same-target transfer, shrunk effects a=1.576`

**Description:**

Identical to trial-16 except that each source's effect is locally shrunk before averaging (ln fold change times z^2/(z^2+4), with z the effect over its standard error; for CD4 the mean of its three culture conditions, each shrunk) and the averaged effects are scaled by 1.576. Cells are sampled exactly as in trial-01 (Poisson counts at library sizes resampled from each context's own control cells, around the context's control profile shifted by the predicted effect; no control cell is copied). The predicted effect of a target is an equal-weight, reliability-weighted mean of its measured CRISPRi response in public sources -- K562 genome-wide Perturb-seq (Replogle et al. 2022), primary CD4+ T cells (GSE314342 pseudobulk, donor-matched controls) and HCT116 from X-Atlas/Orion (Xaira, CC-BY-NC-SA-4.0; GEM-batch-matched controls) -- each source's mean response removed, then scaled. No perturbed cell of the official contexts is used.
