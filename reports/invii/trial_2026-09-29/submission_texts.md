# Testi delle sottomissioni preparate il 29 settembre

## t28

Registrazione alle 18:56 UTC, prima della generazione completa, in
`reports/invii/prediction_t28_2026-09-29/prediction.json`. Sceglie la combinazione
confermata su 96 bersagli pubblici e tre semi; la previsione numerica resta soggettiva
per il cambio di dominio. L'invio attende il via del proprietario sul file convalidato.

**Model name:** `trial-28 amplified multi-source transfer with control-fitted gene dispersion`

**Description:**

The trial-25 multi-source prediction combines public K562 perturbations from Replogle et al., primary CD4+ T cells from GSE314342, and HCT116 and HEK293T from X-Atlas/Orion (Xaira, CC-BY-NC-SA-4.0), with local shrinkage, source-mean removal and a CRISPRi cis component. This model multiplies the complete saved trial-25 effect vector by 1.5 and generates new gamma-Poisson count vectors using gene-specific dispersion estimated from the destination context's control cells. Library sizes are sampled from the same controls; no control-cell vector is copied and no realized group total is fixed. The amplitude and dispersion combination was selected in a preregistered factorial benchmark on public HepG2 cells and checked on disjoint targets with three generation seeds. This public benchmark does not establish its official challenge performance. No perturbed cells of the official contexts are used. This candidate contains no neural correction.

## t26

Scritto il 29 settembre alle 14:26 (ora italiana), dopo la registrazione del t26 (12:24 UTC) e prima della sua
generazione. Ricetta `configs/recipes/t26.json` sulla cache r9; previsione e regola di lettura in
`reports/invii/prediction_t26_2026-09-29/prediction.json`. L'invio consuma quota e aspetta il via del proprietario.

**Model name:** `trial-26 trial-25 with no predicted change on genes below 5 CPM in the context's controls`

**Description:**

Identical to trial-25 (K562 from Replogle et al. 2022, primary CD4+ T cells from GSE314342 and HCT116 and HEK293T from X-Atlas/Orion, Xaira, CC-BY-NC-SA-4.0, at equal weight; locally shrunk effects with each source's mean response removed, estimated without the constant-pseudocount artefact; the reliability-weighted mean scaled by 1.576; a CRISPRi cis head) with one change: every predicted effect on a gene whose mean expression in the context's own control cells is below 5 counts per million is set to zero, for every perturbation. In each context this removes about 70% of the squared predicted effect, which sat on the 46-48% of genes the context barely expresses and which the public sources estimate worst; every gene at or above 5 CPM keeps its prediction unchanged. The rule needs only the control cells, so it applies unchanged to new contexts. Cells are sampled exactly as in trial-01 (Poisson counts at library sizes resampled from each context's own control cells; no control cell is copied). No perturbed cell of the official contexts is used.

## t27

Scritto il 29 settembre alle 17:46 (ora italiana), dopo la registrazione del t27 (15:45 UTC) e prima della sua
generazione. Ricetta `configs/recipes/t27.json` sulla cache r9; previsione e regola di lettura in
`reports/invii/prediction_t27_2026-09-29/prediction.json`. L'invio consuma quota e aspetta il via del proprietario.

**Model name:** `trial-27 trial-25 without the genes that fewer than two public cell lines can estimate`

**Description:**

Identical to trial-25 (K562 from Replogle et al. 2022, primary CD4+ T cells from GSE314342 and HCT116 and HEK293T from X-Atlas/Orion, Xaira, CC-BY-NC-SA-4.0, at equal weight; locally shrunk effects with each source's mean response removed, estimated without the constant-pseudocount artefact; the reliability-weighted mean scaled by 1.576; a CRISPRi cis head) with one change: the transferred prediction is set to zero on the 8,247 genes whose knockdown response is shared by too few public lines to be estimated, measured over about 6,000 genome-wide knockdowns outside the 300 panel targets in K562, CD4 and HCT116; every other gene keeps its full prediction, with no reweighting and no rescaling. It is trial-23's exclusion without its per-gene weighting and rescale, to tell which part moved the score. The gene list does not depend on the targets or contexts, so it applies unchanged to new ones. Cells are sampled exactly as in trial-01 (Poisson counts at library sizes resampled from each context's own control cells; no control cell is copied). No perturbed cell of the official contexts is used.
