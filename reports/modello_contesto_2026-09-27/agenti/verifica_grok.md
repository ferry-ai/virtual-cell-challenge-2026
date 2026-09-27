# Verifica di grok della letteratura del disegno

Rapporto integrale di grok (base di lancio, run `20260927-143453-v2-check-design-lit`, grok-4.7, sola lettura, brief `v2-grok-check-design-literature.md`), copiato il 27 settembre senza modifiche.

I'll check the design report's literature claims against the primary papers and data records, reading only.The report’s literature section is loaded. Next I’ll open each primary source and match the cited numbers to the text.Variance split and Nadig numbers are on the pages. I’ll pull the remaining model claims and the DepMap file record.The literature check is done: the variance split, the Nadig folds, the 8% recurrence, the cross-line linear win, the TxPert baseline, the State 30% split, and both download records match the sources; the Molina correlation, the Zhu mean r, and the TxPert “various cell types” phrase do not.

Read `reports/modello_contesto_2026-09-27/agenti/disegno_claude2.md` lines 16–107, then the full texts below. No shell commands. Figure images were not read, so bar heights stay unchecked.

## 1. Molina & Zhang 2026 — partially wrong

**Measured.** Full text: https://www.biorxiv.org/content/10.64898/2026.07.24.740459v1.full

The four-way split is in the paper and sums to 100%: “reproducible variance was distributed across the cell-line-specific component (the cell-line template; 27.8%), the conserved perturbation-specific component (29.4%), and the cell-line-by-perturbation interaction (23.5%), with the remaining 19.3% attributable to measurement noise.” Calling the noise share “reproducible” is the report’s compression; the four numbers and their labels match.

The template-from-controls claim matches the abstract (“can be inferred from control gene expression”) and Fig. 1i (“Control expression PCs captured much of the template direction”). Fig. 1g also says baseline identity axes explain only a small fraction of the template.

Zero-shot interaction: “neither model recovered the cell-line-by-perturbation interaction” (Ridge and MLP). “Given that all benchmarked methods were unable to predict the interaction component in held-out context.” STATE and MORPH source-only transfer had “little or negative interaction recovery.” Adding 30% of target-line perturbations did recover it. So “no zero-shot model recovered the interaction” is right for the models they benchmarked, not a proof that none could.

The r range is mis-assigned. “MLP predictions aligned more strongly with the perturbation-specific component conserved across cell lines than Ridge predictions (r=0.25–0.39 versus 0.10–0.13).” That is MLP versus the conserved component βp(g). Ridge is 0.10–0.13. The models “mapped projected DepMap profiles to pseudobulk responses”; DepMap principal components are the input (signal saturates at 20–50 components; an ablation uses DepMap PCA50). The paper does not say the regression target was response principal components. Double-unseen transfer stays positive: “DepMap-based Ridge and MLP retained positive perturbed-reference Pearson across all target cell lines.”

## 2. Nadig et al., PMC11244993 — partially right

**Measured.** https://pmc.ncbi.nlm.nih.gov/articles/PMC11244993/

“56% of the perturbations had high correlations across all cell types (mean correlation within similar cell type pairs: 0.75; outside similar pairs: 0.66); 44% had higher correlations across similar cell types (mean correlation within similar cell type pairs: 0.61; outside similar pairs: 0.35).”

The 0.61 / 0.35 pair is the 44% cluster only. The denominator is not all essential perturbations: correlations were estimated for 2,053 shared essential genes and then restricted to 1,660 with significant transcriptome-wide impact in all four lines (Z > 0.5, “a p-value of roughly 0.3”).

Enrichment, on the K562 genome-wide screen, is perturbation-impact enrichment: constrained genes “~1.57x”; “genes with a strong growth effect in K562 cells (roughly, those that are essential in culture) … 4.22x”; highly expressed genes “2.26x”. The folds match. “Essential” in that sentence is a growth effect in culture, not the four-line essential screens.

## 3. Zhu … Marson 2025 — partially right

**Measured.** https://www.biorxiv.org/content/10.64898/2025.12.23.696273v1.full

“approximately 8% of trans-effects detected in CD4+ T cells across 3,081 shared perturbations were also observed in K562 cells.” That part is right.

The mean r is a different comparison: “For perturbations with measurable trans-effects in K562 cells (n = 1880) … (Mean Pearson R = 0.32)”, versus random pairs, and lower than donor replicates. It is not the correlation over all 3,081 shared perturbations.

## 4. Ahlmann-Eltze et al. — right on the ranking; the gene phrase is both classes

**Measured** on bioRxiv v5 (7 Feb 2025): https://www.biorxiv.org/content/10.1101/2024.09.16.613342v5.full. The Nature Methods typeset PDF was not opened.

Abstract: for doubles, deep models “did not perform better than a simple additive model”; for unseen genes, they “did not outperform the baseline of predicting the mean”; “a simple linear model reliably outperforms all other models when pre-trained on another perturbation dataset.” Metrics in the text are L2 on the top 1,000 genes and Pearson delta.

“The approach that did consistently outperform all other models was a linear model pre-trained with P from Replogle (using the K562 cell line data to predict the Adamson and RPE1 results, and the RPE1 cell line for the K562 results).” P is a perturbation embedding fit on the other line’s perturbation profiles.

“genes that differed more between K562 and RPE1 were less accurately predicted (Suppl. Fig. S9).” The figure is both:
- S9B: absolute prediction error per read-out gene against that gene’s expression difference between RPE1 and K562. The caption places those points on the double-perturbation splits (“122 double perturbations”).
- S9C: Pearson delta per perturbation on the RPE1 dataset against “the differential expression of the perturbation target gene between RPE1 and K562.”

The sentence is not only readout genes and not only perturbed genes.

## 5. TxPert — setting and baseline right; the proprietary-cell-type quote is not in the paper

**Measured.** https://arxiv.org/html/2505.14919v1

Held-out line: “four leave-one-out experiments, where we hold out all perturbation examples from the target cell type, but do train on all controls.” Lines are K562, RPE1, HEPG2, Jurkat. “TxPert exceeded the general baseline in all four held out cell lines” on Pearson Δ (Fig. 3C). Bar values are only in the figure, so unread. Methods also say the cross-cell-type test set has “a breakdown into seen and unseen perturbations.”

Section 4.2.3, for a seen perturbation: prediction = mean test-cell-type control + the mean of that perturbation’s deltas in training (an unweighted mean over training samples, which weights cell lines by sample count). For an unseen perturbation it substitutes the global perturbation mean. The report’s “test-line control mean plus the perturbation’s mean change in training” matches the seen-perturbation branch. That is a same-target transfer, and it is the baseline the held-out-line result beat.

Proprietary graphs: “PxMap and TxMap are proprietary Recursion relationship-datasets” from phenomics and “single-cell transcriptomics perturbation screens.” They are in the best within-line single model (Exphormer-MG: STRINGdb, GO, PxMap, TxMap) and the double model (GAT-MultiLayer: GO, PxMap, TxMap). PxMap is “derived entirely from high throughput perturbational screening in Primary Human Umbilical Vein Endothelial Cells; HUVEC.” The words “in various cell types” are not used for these graphs. “various cell lines” in the paper refers to scVI pretraining. The cell-line ablation that names a graph (Fig. 7) uses “a vanilla GAT using the STRINGdb graph.” The paper does not say the Fig. 3C model included PxMap or TxMap. **Inferred:** leakage from those graphs into the held-out line is not established by the text.

## 6. State — the 30% is right; “zero-shot only ranks strength” overstates the paper

**Measured.** https://www.biorxiv.org/content/10.1101/2025.06.26.661135v2.full

Cross-line setting (Fig. 2, Replogle–Nadig): “models were trained on the remaining three cell lines plus an additional 30% of perturbations randomly sampled from the test cell line.” Section 4.2.1 sets α = 0.30. Controls from the test context are available. On that genetic split, “State matched the performance of the perturbation mean baseline” on discrimination, and “Linear model outperformed on DE overlap by 20% and the context mean baseline outperformed on fold change prediction by 12%.”

Zero-shot is a different task (section 2.3 and 4.2.2). Pretrain on Tahoe-100M, fine-tune on other contexts of a query dataset that “contain a superset of the perturbations found in the held-out context,” then test those same perturbations in the held-out context. Controls of the held-out context are available. “For larger datasets like Parse-PBMC and Replogle-Nadig … an absolute Spearman correlation greater than 0.5” is the effect-size ranking. The same paragraph says Parse-PBMC also had “an average of 15% improvement across all five metrics” in section 2.2. “Only ranks perturbation strength” is the report’s compression, not the paper’s claim, and the perturbations were seen in other contexts.

## 7. Download sizes and licences — right

**Measured.**

DepMap 24Q4, Figshare article 27993248, DOI https://doi.org/10.25452/figshare.plus.27993248. File API https://api.figshare.com/v2/articles/27993248/files: `CRISPRGeneEffect.csv` size 428678699; `CRISPRInferredCommonEssentials.csv` size 20795. The item page https://plus.figshare.com/articles/dataset/DepMap_24Q4_Public/27993248 shows Licence CC BY 4.0 (page extract). A later direct fetch of that HTML returned empty; the byte sizes were re-read from the API.

CORUM, https://zenodo.org/api/records/17419058: version “5.1”, license id `cc-by-4.0`. Eight files sum to 26,396,188 bytes (26.4 MB at 10⁶ bytes/MB). There is no single 26.4 MB file.

## Verdicts

| # | Claim | Verdict |
|---|---|---|
| 1 | Molina split; no zero-shot interaction; ridge/MLP r 0.25–0.39 onto response PCs | Partially wrong. Split and zero-shot interaction failure match. r 0.25–0.39 is MLP vs β; Ridge is 0.10–0.13; the target is not response PCs. |
| 2 | Nadig 56%, 0.61 vs 0.35, enrichments 4.22× / 2.26× / 1.57× | Partially right. Numbers match a filtered 1,660-gene set and the 44% cluster; 4.22× is K562 growth effect. |
| 3 | Zhu ~8% over 3,081, mean r 0.32 | Partially right. 8% and 3,081 match. Mean r 0.32 is n = 1,880. |
| 4 | Ahlmann-Eltze: no deep model beat the simple baselines; cross-line linear best; which genes | Right on the ranking. The gene sentence covers readout genes (S9B) and perturbation targets (S9C). |
| 5 | TxPert held-out line, baseline, proprietary graphs | Setting and baseline right. “In various cell types” is not in the paper. Proprietary graphs are used for other tasks; not stated for Fig. 3C. |
| 6 | State 30% in the cross-line setting; what zero-shot did | 30% is right. Zero-shot still trains on those perturbations in other contexts and is not limited to strength ranking. Spearman > 0.5 is the effect-size ranking on the larger sets. |
| 7 | DepMap byte sizes and CC BY 4.0; CORUM 5.1, 26.4 MB, CC BY 4.0 | Right. |

## Corrections that change the design

1. Do not treat r 0.25–0.39 as a ridge map from DepMap co-essentiality onto response principal components. In Molina & Zhang that range is the MLP’s correlation with the conserved component β; the ridge on the same comparison is 0.10–0.13, and both models predict pseudobulk responses from DepMap components. The supported claim is narrower: a DepMap-aligned MLP recovers part of the conserved effect in a held-out line, including when the gene is also held out, and none of their zero-shot models recovered the interaction.

2. State’s published cross-line comparison keeps 30% of the test line’s perturbations in training. Its zero-shot task still fine-tunes on those perturbations in other contexts and still sees the held-out line’s controls. Spearman > 0.5 is effect-size ranking on Parse-PBMC and Replogle–Nadig, and Parse-PBMC also moved on the other metrics. It is not evidence that a controls-only model can only rank strength.

3. TxPert’s held-out-line win is against test-line control mean plus that perturbation’s mean change in the training lines, for perturbations seen in other lines, with the test line’s controls in training. The phrase “proprietary screens in various cell types” is not in the paper: PxMap is a HUVEC imaging screen, TxMap’s cell types are unstated, and the cell-line ablation that names a graph uses STRING. The leakage warning is not earned by the text that was checked.

## Not done

Nature Methods PDF versus bioRxiv v5; pixels inside TxPert Fig. 3C and State’s plots; which graph the TxPert Fig. 3C model used; TxMap’s cell types; a second read of the Figshare HTML after the refetch came back empty. Author bylines were not re-read; papers were identified by the cited DOIs and PMC id.
