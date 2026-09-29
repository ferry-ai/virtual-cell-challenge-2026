# Testi delle sottomissioni preparate il 29 settembre

## t26

Scritto il 29 settembre alle 14:26 (ora italiana), dopo la registrazione del t26 (12:24 UTC) e prima della sua
generazione. Ricetta `configs/recipes/t26.json` sulla cache r9; previsione e regola di lettura in
`reports/invii/prediction_t26_2026-09-29/prediction.json`. L'invio consuma quota e aspetta il via del proprietario.

**Model name:** `trial-26 trial-25 with no predicted change on genes below 5 CPM in the context's controls`

**Description:**

Identical to trial-25 (K562 from Replogle et al. 2022, primary CD4+ T cells from GSE314342 and HCT116 and HEK293T from X-Atlas/Orion, Xaira, CC-BY-NC-SA-4.0, at equal weight; locally shrunk effects with each source's mean response removed, estimated without the constant-pseudocount artefact; the reliability-weighted mean scaled by 1.576; a CRISPRi cis head) with one change: every predicted effect on a gene whose mean expression in the context's own control cells is below 5 counts per million is set to zero, for every perturbation. In each context this removes about 70% of the squared predicted effect, which sat on the 46-48% of genes the context barely expresses and which the public sources estimate worst; every gene at or above 5 CPM keeps its prediction unchanged. The rule needs only the control cells, so it applies unchanged to new contexts. Cells are sampled exactly as in trial-01 (Poisson counts at library sizes resampled from each context's own control cells; no control cell is copied). No perturbed cell of the official contexts is used.
