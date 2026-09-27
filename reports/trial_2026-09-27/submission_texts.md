# Testi delle sottomissioni preparate il 27 settembre

## t23

Scritto il 27 settembre alle 01:15 (ora italiana), dopo la registrazione del t23 (23:14 UTC del 26) e
durante la sua generazione. Ricetta `configs/recipes/t23.json`; previsione e regola di lettura in
`reports/prediction_t23_2026-09-27/prediction.json`. L'invio consuma quota e aspetta il via del
proprietario.

**Model name:** `trial-23 t22 + per-gene shared-response weighting from genome-wide K562, CD4 and HCT116`

**Description:**

Identical to trial-22 (K562, primary CD4+ T cells and HCT116/HEK293T from X-Atlas/Orion, locally shrunk effects, mean response removed, reliability-weighted mean times 1.576, CRISPRi cis head) with one change: the transferred part is weighted gene by gene by the share of the knockdown response that different cell lines have in common. For each gene of the official axis that share, sigma2 / (sigma2 + tau2), is estimated by moments over 6,000 genome-wide knockdowns outside the 300 panel targets in K562 (Replogle et al. 2022), CD4 (GSE314342) and HCT116 (X-Atlas/Orion): sigma2 is the covariance of the gene's response between lines, tau2 the line-specific excess over sampling noise. Genes the lines cannot estimate get zero. Per context, the weighted effects are scaled back to trial-22's median number of detectable genes, cis head included. On held-out public sources the weighting raised a generator-level PDS and nMAE proxy on three of four held-out lines. Cells are sampled exactly as in trial-01 (Poisson counts at library sizes resampled from each context's own control cells; no control cell is copied). No perturbed cell of the official contexts is used.

## t24

Scritto il 27 settembre alle 02:02 (ora italiana), dopo la registrazione del t24 (00:02 UTC del 27) e
prima della sua generazione. Il t24 è il t22 rigenerato con un altro seme del generatore: stessi file
degli effetti, stessa ricetta `configs/recipes/t22.json`; previsione e regola di lettura in
`reports/prediction_t24_2026-09-27/prediction.json`. Serve a misurare il rumore del generatore sul
punteggio ufficiale. L'invio consuma quota e aspetta il via del proprietario.

**Model name:** `trial-24 replicate of trial-22 with another generator seed (measures seed-to-seed noise)`

**Description:**

Identical to trial-22 in every respect except the random seed of the cell generator (20260927 instead of 20260912): the same per-context effects files, recipe and packaging. It is a replicate, submitted to measure how much the official score and each of its members move between two random draws of the same prediction. The model is trial-22's: K562 (Replogle et al. 2022), primary CD4+ T cells (GSE314342 pseudobulk, donor-matched controls) and HCT116 and HEK293T (X-Atlas/Orion, Xaira, CC-BY-NC-SA-4.0) at equal weight, each source's effect locally shrunk (ln fold change times z^2/(z^2+4)) with its mean response over targets removed, the reliability-weighted mean scaled by 1.576, plus a CRISPRi cis head for genes whose TSS lies within 5 kb of the target's TSS. Cells are sampled exactly as in trial-01 (Poisson counts at library sizes resampled from each context's own control cells; no control cell is copied). No perturbed cell of the official contexts is used.

## t25

Scritto il 27 settembre alle 14:58 (ora italiana), dopo la registrazione del t25 (11:41 UTC) e dopo il suo
impacchettamento. Ricetta `configs/recipes/t25.json` sulla cache r9; previsione e regola in
`reports/prediction_t25_2026-09-27/prediction.json`. Per istruzione del proprietario, per ora nessun invio.

**Model name:** `trial-25 trial-22 with the pseudobulk estimator corrected for genes without evidence`

**Description:**

Identical to trial-22 (K562 from Replogle et al. 2022, primary CD4+ T cells from GSE314342 and HCT116 and HEK293T from X-Atlas/Orion, Xaira, CC-BY-NC-SA-4.0, at equal weight; locally shrunk effects with each source's mean response removed; the reliability-weighted mean scaled by 1.576; a CRISPRi cis head) with one change in how the pseudobulk sources are estimated. With a constant pseudocount, a gene with no count in either group read as the ratio of the two library sizes: in the CD4 data the Y-chromosome genes of the female donors came out induced by nearly every knockdown, and low-count genes of HCT116 did the same. Here a donor (or an X-Atlas/Orion pool of GEM batches) whose controls predict fewer than one count of a gene in the target group is left out for that gene, whatever the target's own count; a gene no donor informs is treated as unmeasured. Everything else is unchanged. Cells are sampled exactly as in trial-01 (Poisson counts at library sizes resampled from each context's own control cells; no control cell is copied). No perturbed cell of the official contexts is used.
