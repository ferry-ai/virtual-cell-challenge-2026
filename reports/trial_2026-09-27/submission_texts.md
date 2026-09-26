# Testi delle sottomissioni preparate il 27 settembre

## t23

Scritto il 27 settembre alle 01:15 (ora italiana), dopo la registrazione del t23 (23:14 UTC del 26) e
durante la sua generazione. Ricetta `configs/recipes/t23.json`; previsione e regola di lettura in
`reports/prediction_t23_2026-09-27/prediction.json`. L'invio consuma quota e aspetta il via del
proprietario.

**Model name:** `trial-23 t22 + per-gene shared-response weighting from genome-wide K562, CD4 and HCT116`

**Description:**

Identical to trial-22 (K562, primary CD4+ T cells and HCT116/HEK293T from X-Atlas/Orion, locally shrunk effects, mean response removed, reliability-weighted mean times 1.576, CRISPRi cis head) with one change: the transferred part is weighted gene by gene by the share of the knockdown response that different cell lines have in common. For each gene of the official axis that share, sigma2 / (sigma2 + tau2), is estimated by moments over 6,000 genome-wide knockdowns outside the 300 panel targets in K562 (Replogle et al. 2022), CD4 (GSE314342) and HCT116 (X-Atlas/Orion): sigma2 is the covariance of the gene's response between lines, tau2 the line-specific excess over sampling noise. Genes the lines cannot estimate get zero. Per context, the weighted effects are scaled back to trial-22's median number of detectable genes, cis head included. On held-out public sources the weighting raised a generator-level PDS and nMAE proxy on three of four held-out lines. Cells are sampled exactly as in trial-01 (Poisson counts at library sizes resampled from each context's own control cells; no control cell is copied). No perturbed cell of the official contexts is used.
