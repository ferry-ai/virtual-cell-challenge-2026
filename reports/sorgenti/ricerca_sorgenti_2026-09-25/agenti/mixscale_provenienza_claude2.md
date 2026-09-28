The per-line `log2FC_<line>` columns in the Zenodo DE archive look like within-line, unweighted fold changes, but the `beta_*` and `p_*` columns come from one regression fitted on all six lines together, and which genes appear in a file depends on all six lines. So the log2FC values carry little cross-line information, but row membership and all the regression outputs do.

## 1. How the DE tables were computed

The authors' papers and readme do not say which function or settings produced `DE_results_all_pathway.zip`. What follows rests on matching our local file headers to the Mixscale package code.

**Our local files.** Every file header reads `gene_ID log2FC_A549 … log2FC_MCF7 beta_cell_typeA549 … p_cell_typeMCF7` (`reports/dld1_audit_2026-09-24/source_inventory_r2/mixscale_inventory.json:1961`). One row, `ZFPM2-AS1`, has `NA` for HAP1, HT29 and MCF7 in its log2FC columns but finite values in all six beta columns (`:1968`). This is **measured**.

**The package code**, `Run_wmvRegDE` in https://raw.githubusercontent.com/satijalab/Mixscale/main/R/scoring_de.R. I read it through WebFetch, which passes the page through a summarising model, so the quotes are **verified-via-summariser** and should be re-read in the raw file:
- **Joint fit when there is more than one cell type.** `design = ~ 0 + cell_type + weight:cell_type + log_ct`. Each line gets its own intercept and its own weight slope. The sequencing-depth covariate `log_ct = log10(nCount_RNA)` is shared across lines.
- **Dispersion shared across lines.** A rough fit, `design = ~ 0 + cell_type + log_ct`, runs on the non-targeting and perturbed cells of all lines together. Its per-gene overdispersion then goes into the final fit: `glm_gp(..., overdispersion = fit_rough$overdispersions, overdispersion_shrinkage = F, size_factors = F)`.
- **Test.** A Wald chi-square: `p = pchisq((beta/se)^2, df = 1, lower.tail = F)`. The summaries disagreed on where `se` comes from (`predict(fit, se.fit=TRUE)` in one), so re-check that line.
- **Weights.** Mixscale scores are standardised against the non-targeting cells of each line separately (`mean_NT`/`sd_NT` inside `for(celltype in celltype_list)`), and negative scores are set to 0.
- **log2FC.** `FoldChange_new()` compares the perturbed cells of one line with that line's non-targeting cells, with no weights. It averages raw counts plus a pseudocount (`log(x = (rowSums(x = x) + pseudocount.use)/NCOL(x), base = base)`), not normalised data. Columns are named `paste0("log2FC_", celltype)`.
- **Gene filter.** It is computed per line: `abs(avg_log2FC) >= logfc.threshold & (pct.1 >= min.pct | pct.2 >= min.pct) & (min.cell…)`. The defaults are `logfc.threshold = 0`, `min.pct = 0.1` and `min.cells.group = 10`. The genes tested are then the union over lines, `idx_for_DE = which(apply(..., FUN = any))`, and a line's log2FC is set to `NA` where the gene failed that line's filter.
- **Scores.** `RunMixscale` computes perturbation signatures and scores separately for each `split.by` group (`for (s in splits)`, https://raw.githubusercontent.com/satijalab/Mixscale/main/R/perturbation_scoring.R); the fetch paraphrased this rather than quoting it. Its `harmonize` option (default `F`) rebalances non-targeting cells across groups.

**The paper**, bioRxiv v2 (https://www.biorxiv.org/content/10.1101/2024.01.29.576933v2.full), **verified**: wmvReg "accounts for multiple variables, including a cell's perturbation score, cell line identity, and sequencing depth". MultiCCA is applied "separately to each of our five pathways", which means the published signatures pool lines. I could not reach the full Methods: PMC showed a CAPTCHA and nature.com redirected to a login.

**What this means for our tests** (**inferred**):
- The prediction-vs-truth comparisons in `MIXSCALE_PROTOCOLLO.md` use only the `log2FC_*` columns (line 7). Those values come from each line's own cells.
- The row universe can still leak: a gene is present because some line passed the filter. Our protocol keeps only genes finite in all six lines (line 13), and that set equals the intersection of the per-line filters, so no line decides another line's rows. The residual leak is small.
- Anything that uses `beta_*` or `p_*` is not independent across lines.
- None of this holds unless the archive was made with this code and `split.by = cell_type`. That is inferred from the column names, not stated by the authors.

## 2. Files

**Zenodo 14518762** (v2.1, published 18 Dec 2024, modified 27 Feb 2025; https://zenodo.org/records/14518762, **verified**). Record 10520189 opens the same file list and v2.1 metadata, so it looks like the concept DOI that resolves to the latest version.

| File | Size | Content |
|---|---|---|
| `Seurat_object_IFNB/IFNG/INS/TGFB/TNFA_Perturb_seq.rds` | 4.3 / 2.9 / 5.6 / 2.6 / 4.7 GB | per-cell counts, one object per stimulus |
| `DE_results_all_pathway.zip` | 324.1 MB | DE tables (local md5 `f077cba6…`, `mixscale_inventory.json:3`) |
| `Pathway_genelist.rds` | 20.7 kB | MultiCCA signatures |
| `Pathway_Exclusive_genelist.rds` | 9.0 kB | signatures |
| `HClust_Pathway_celltype_specific_genelist.rds` | 69.5 kB | line-specific signatures |
| `Bulk_RNAseq_Seurat_object_IFNG_and_TGFB_stim.rds` | 3.4 MB | bulk RNA-seq |
| `Parse_Guide_Capture_Protocol.pdf` | 303.9 kB | protocol |
| `A_readme.txt` | 1.5 kB | readme |

**GSE281048** (https://ftp.ncbi.nlm.nih.gov/geo/series/GSE281nnn/GSE281048/suppl/, **verified**): only the five objects as `.rds.gz`, sized 4.0G (IFNB), 2.7G (IFNG), 5.2G (INS), 2.4G (TGFB) and 4.3G (TNFA). The GEO landing page showed a CAPTCHA, so I have no sample list or design text.

**Metadata columns:** the authors do not document them anywhere I could read, including the readme. **Unverified.** The tutorial uses `gene`, `cell_type` and `guide_identity`, but on the Jost 2020 data, not on this study.

**Unstimulated cells:** the preprint says cells were "stimulated with the corresponding cytokine for 24 hours". I found no statement that unstimulated cells were profiled. **Unverified** either way.

## 3. Per-line control profiles

The DE function requires non-targeting cells in every line, and the preprint reports "14 non-targeting (NT) controls" (**verified**). So they should be in each Seurat object, marked by a guide or gene label and a cell-line column (**inferred**). The DE zip holds no control profiles: its columns are fold changes, betas and p-values only (`mixscale_inventory.json:1961`).

## 4. Memory (estimate)

- The smallest object is 2.6 GB as `.rds`. `.rds` is normally gzip-compressed, so it grows in RAM.
- The preprint reports about 2.6 million cells over the five screens, so each object holds very roughly 0.5 million cells. At about 2,000 non-zero counts per cell, which I assume and did not measure, that is about 1e9 non-zeros, or about 12 GB as a sparse matrix.
- **Estimate:** 8 GB will not load any object. 12 GB Colab is marginal to infeasible, even for TGFB. A high-RAM runtime, or conversion in pieces somewhere else, is likely needed.

## 5. Licence

CC-BY-4.0 on the Zenodo record (**verified**). GEO carries no explicit licence; the NCBI terms apply (**unverified**).

## Still unknown

- Whether the archive was actually made with `Run_wmvRegDE(split.by = cell_type)`, and with which `logfc.threshold`, `min.pct` and package version.
- The Methods and Supplementary Methods text of the Nature Cell Biology paper.
- The metadata columns of the Seurat objects, and whether they hold unstimulated cells, replicate or batch labels, and Mixscale scores.
- Cell counts per object, and the uncompressed size of each `.rds`.
- The GSE281048 sample list and design.
- A raw-text check of the code quotes above.
