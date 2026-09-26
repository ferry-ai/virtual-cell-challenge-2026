# Testi delle sottomissioni preparate il 26 settembre

## t20

Scritto il 26 settembre verso le 00:20 (ora italiana), dopo la registrazione del t20 (22:04 UTC
del 25) e durante la sua generazione. Ricetta `configs/recipes/t20.json`; previsione e regola
di lettura in `reports/prediction_t20_2026-09-26/prediction.json`. L'invio consuma quota e
aspetta il via del proprietario.

**Model name:** `trial-20 trial-01 generator + K562+CD4+HCT116 shrunk transfer a=1.576 + CRISPRi cis head`

**Description:**

Identical to trial-19 plus a CRISPRi cis head, a model of the knockdown itself: dCas9-KRAB bound at a target's promoter also represses genes whose TSS lies within a few kb (bidirectional promoters above all), in any cell type. For every gene whose TSS is within 5 kb of the target's TSS (GENCODE v50), twice the median ln fold change of that distance bin is added to the transferred effect, outside the amplitude that scales the transferred part. The distance prior comes from K562 genome-wide Perturb-seq (Replogle et al. 2022) with every panel target removed, so no predicted target informs it. The transferred part: each source's effect locally shrunk (ln fold change times z^2/(z^2+4)), an equal-weight reliability-weighted mean over K562, primary CD4+ T cells (GSE314342 pseudobulk, donor-matched controls) and HCT116 from X-Atlas/Orion (Xaira, CC-BY-NC-SA-4.0), each source's mean response removed, scaled by 1.576. Cells are sampled exactly as in trial-01 (Poisson counts at library sizes resampled from each context's own control cells; no control cell is copied). No perturbed cell of the official contexts is used.

## t21

**Non generato né inviato.** Alle 15:05 il banco isolato r5 non ha soddisfatto la regola fissata
alle 14:48 (`reports/trasferimento_appreso_2026-09-26/RISULTATI.md`, sezione r5): il testo resta
come documento di ciò che era stato preparato, e non esiste una previsione registrata del t21.

Scritto il 26 settembre verso le 14:25 (ora italiana), prima della generazione del t21. Definizione:
effetti del t20 (`configs/recipes/t20.json`, stadio 100) ripesati dallo stadio 104 con esponente
0,25; previsione e regola in `reports/prediction_t21_2026-09-26/prediction.json`. L'invio consuma
quota e aspetta il via del proprietario.

**Model name:** `trial-21 t20 + learned magnitude channel (gradient boosting on public sources) a=0.25`

**Description:**

Trial-20's effects (shrunk same-target transfer from K562 (Replogle et al. 2022), CD4+ T cells (GSE314342) and HCT116 (X-Atlas/Orion, Xaira, CC-BY-NC-SA-4.0), scaled by 1.576, plus a CRISPRi cis head for genes whose TSS lies within 5 kb of the target's) keep their direction and are reweighted gene by gene by a learned magnitude channel: a gradient-boosting regressor, trained only on public perturbation sources (each source held out in turn and predicted from the other source families, labels centred per gene over targets so that it learns the target-specific part), predicts how much each gene moves for each target from features of the sources' measurements (pooled effects, agreement, z-scores), of the gene (responsiveness and common response across ~9,600 K562 knockdowns outside the panel, expression in the context's own control cells and in the sources), of the target (strength, expression) and of the genome (cis distance prior, STRING partners). Effects are multiplied by (predicted magnitude / its mean over genes)^0.25 and rescaled so that each context moves as many detectable genes as trial-20. No perturbed cell of the official contexts is used; the contexts enter only through their control cells. Cells are sampled exactly as in trial-01.
