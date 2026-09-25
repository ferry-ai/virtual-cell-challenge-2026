# Testi delle sottomissioni preparate il 26 settembre

## t20

Scritto il 26 settembre verso le 00:20 (ora italiana), dopo la registrazione del t20 (22:04 UTC
del 25) e durante la sua generazione. Ricetta `configs/recipes/t20.json`; previsione e regola
di lettura in `reports/prediction_t20_2026-09-26/prediction.json`. L'invio consuma quota e
aspetta il via del proprietario.

**Model name:** `trial-20 trial-01 generator + K562+CD4+HCT116 shrunk transfer a=1.576 + CRISPRi cis head`

**Description:**

Identical to trial-19 plus a CRISPRi cis head, a model of the knockdown itself: dCas9-KRAB bound at a target's promoter also represses genes whose TSS lies within a few kb (bidirectional promoters above all), in any cell type. For every gene whose TSS is within 5 kb of the target's TSS (GENCODE v50), twice the median ln fold change of that distance bin is added to the transferred effect, outside the amplitude that scales the transferred part. The distance prior comes from K562 genome-wide Perturb-seq (Replogle et al. 2022) with every panel target removed, so no predicted target informs it. The transferred part: each source's effect locally shrunk (ln fold change times z^2/(z^2+4)), an equal-weight reliability-weighted mean over K562, primary CD4+ T cells (GSE314342 pseudobulk, donor-matched controls) and HCT116 from X-Atlas/Orion (Xaira, CC-BY-NC-SA-4.0), each source's mean response removed, scaled by 1.576. Cells are sampled exactly as in trial-01 (Poisson counts at library sizes resampled from each context's own control cells; no control cell is copied). No perturbed cell of the official contexts is used.
