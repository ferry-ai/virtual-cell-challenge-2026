# Verifica di grok sulle pagine primarie

Rapporto integrale di grok (base di lancio, run `20260927-141544-v2-verify-multictx`, grok-4.7, sola lettura, brief `v2-grok-verify-multictx.md`), copiato il 27 settembre senza modifiche.

I'll open the primary pages for all four leads and report only what those pages actually state.The DOI and Kaggle pages did not return usable text. I'll follow the redirects and search for the preprint and database pages directly.None of the four leads is a measured screen of the same genes in five or more cell types. The supplied HyperMap DOI does not resolve; the real preprint is a prediction atlas, and the only new public measurements are VIPerturb-seq, whose genome-wide arm is K562 alone.

## 1. VIPerturb-seq (Bradu et al. 2026)

**Exists, with a narrower cell-line design than claimed.** Record read at https://zenodo.org/records/18460279 (DOI https://doi.org/10.5281/zenodo.18460279) and the preprint at https://www.biorxiv.org/content/10.64898/2026.02.12.705613v1.full (DOI https://doi.org/10.64898/2026.02.12.705613, posted 14 Feb 2026). **Measured.**

| Item | What the pages say |
| --- | --- |
| Cell lines | Pilot: one pool of CRISPRi (KRAB-dCas9-MeCP2) **K562, HEK293 and HAP1**, 10x Flex v1, plus pRPS6 ADT and hashing. Genome-wide unbiased screen and the vimentin-enrichment screen: **K562 only**. HEK293FT is the virus-packaging line, not a screened line. **Measured.** |
| Perturbation | CRISPRi. Pilot: **100 sgRNAs** against known and putative mTOR regulators plus non-targeting controls. Genome-wide: GuEST-List, Dolcetto set A adapted, **three sgRNAs per annotated human protein-coding gene, 57,050 sgRNAs** (barcode space 57,120). **Measured.** How many distinct genes those 100 sgRNAs cover: **not stated.** |
| Shared across lines | The 100-sgRNA library was put into the three-line pool, so those guides are shared across K562, HEK293 and HAP1. The genome-wide library was not run in HEK293 or HAP1. **Measured.** |
| Readout | Probe-based **10x Genomics Flex** transcriptome plus custom barcode probes, not a small gene panel. Pilot Flex v1: 6,700 RNA UMIs/cell. Genome-wide Flex v2 (Apex), two lanes, ~880,000 cell barcodes, median 15,100 RNA UMIs and **5,300 genes/cell**, median 14 cells/sgRNA and **42 cells/targeted gene**; sequenced on an Ultima UG100. Vimentin arm: Flex v1, one lane, 12,000 gRNA singlets after sorting the top 3% VIM-high K562 cells. **Measured.** The words “whole transcriptome” are **not stated**; “transcriptome … probes” and thousands of genes per cell are. |
| Processed data | Open download, no application. Seurat objects. Zenodo page header: **Files (17.3 GB)**. API file sizes sum to **17,295,387,725 bytes**. **Measured.** `multimodal_cell_line_mixing_pilot.rds` 1.6 GB; `genome_wide_binA/B/C.RDS` 3.6 / 3.8 / 2.9 GB; `genome_wide_filtered.rds` 3.6 GB (**6,724** perturbations whose fingerprints passed QC); `vimentin_screen.rds` 1.9 GB; `genome_wide_manifest.txt` 399 kB (columns `gene`, `cell_count`, `file`, `is_in_filtered_obj`; no cell-line column). |
| Licence | Zenodo `license.id` **cc-by-4.0**, `access_right` open. **Measured.** No data-use agreement on the record. Preprint licence line: **not read.** |

## 2. Echoes of Silenced Genes (Myllia, Kaggle, 2026)

**The competition exists. It is not a public multi-cell-line screen.** Live fetches of https://www.kaggle.com/competitions/echoes-of-silenced-genes/overview, `/data` and `/rules` returned only the title or, via a reader proxy, an anti-forgery crash. Facts below from pages that did render are marked separately from search-index extracts of the Kaggle URLs.

**Read live:** https://myllia.com/events/community-prediction-competition/ and the 22 Jan 2026 BioSpace release https://www.biospace.com/press-releases/myllia-biotechnology-launches-global-virtual-cell-challenge-echoes-of-silenced-genes. Both say: predict how **one human cancer cell line** responds to **CRISPRi**, using public atlases plus a limited set of Myllia perturbed cells; goal is transfer across cell types. Cell-line name, CROP-seq as the assay name, 10x chemistry, gene counts, size and licence: **not stated** on those two pages. **Measured.**

**Search-index extract of the Kaggle data URL** (live page did not render): CRISPRi scRNA-seq; predict log2 fold-change for **5,127 genes** across **120** perturbations (60 public leaderboard, 60 held-out test); `training_data_means.csv` has non-targeting cells plus **80** perturbations; `training_cells.h5ad` and `training_cells.RDS` are raw UMIs for **19,226 genes** (GENCODE v46) plus a `channel` batch column, then subset to 5,127 genes. Page shows **845.42 MB**, types csv/h5ad/rds, licence **CC BY-NC-SA 4.0**, and “To see this data you need to agree to the competition rules.” **Measured as an index extract, not a live render.** Cell-line name, CROP-seq-versus-Perturb-seq for this file, and 10x chemistry: **not in that extract.**

**Search-index extract of** https://www.kaggle.com/datasets/mylliabiotechnology/myllia-echoes-of-silenced-genes-competition-data : same files, **Version 2 (845.43 MB)**, licence **CC BY-NC 4.0**, description “No description available.” **Measured as an index extract.** The two Kaggle pages disagree (CC BY-NC-SA 4.0 vs CC BY-NC 4.0).

**Outside the competition:** the rules body was **not readable**. Both indexed licences are non-commercial; whether share-alike applies, and whether a signed competition agreement adds further limits, is **unverified**. A host discussion post points to https://myllia.notion.site/echoes-of-silenced-genes2026 for ground truth after the challenge; that page required JavaScript and returned no text. **Measured** that it did not render.

## 3. HyperMapDB (2026)

**The cited DOI is wrong, and the matrix is mostly predictions.** https://doi.org/10.1101/2026.04.26.691475 returns **DOI Not Found**. **Measured.**

The paper that defines HyperMapDB is Dhaka, Gao and Ideker, “HyperMap…”, https://www.biorxiv.org/content/10.64898/2026.04.23.720505v1.full and the PDF, DOI https://doi.org/10.64898/2026.04.23.720505, posted **27 April 2026**. Preprint text: **CC-BY-NC-ND 4.0**. **Measured.**

**Measured from the PDF:** not a new screen. Existing Perturb-seq studies were merged into **18 contexts**. Perturbations per context **14 to 2,317**. **2,531** distinct single-gene knockdowns observed in at least one context, covering **12,861 of 45,558** context-by-perturbation pairs. The model then fills unobserved pairs and extends to **19,036** protein-coding genes (GENCODE v47 ∩ GenePT), **342,648** combinations, described as a 27-fold expansion. Named contexts include HepG2, hESC, Jurkat, K562, Luhmes, MCF10A, neurons, RPE1 and iPSC donors; the full list is Extended Table 2, **which was not opened**. Feature space after intersection and highly variable genes: **2,500 genes**, not a full-transcriptome count matrix. A separate evaluation uses **1,742** knockdowns shared by RPE1, Jurkat, K562 and HepG2 (those are source atlases, including Replogle and Nadig). Data-availability paragraph: profiles for 19,036 gene knockdowns across 18 cell contexts on Figshare **10.6084/m9.figshare.31831081**; code at https://github.com/bhavya1929/HyperMap.

**Figshare API** https://api.figshare.com/v2/articles/31831081 (**measured**): public, not embargoed, `download_disabled` false, licence **CC BY 4.0**. One file, `HyperMapDB1.h5ad`, **16,924,297,965 bytes**. Description on Figshare says “predicted single-cell gene expression deltas for 2,500 genes” and also “**19** human cell lines” and “**19,036 genetic and chemical** perturbations.” That 19-versus-18 and chemical-versus-knockdown wording conflicts with the preprint. The h5ad itself was **not opened**.

## 4. scPerturb and PerturBase

**scPerturb exists and does not, on the pages read, add a same-gene genetic screen in five or more cell types outside the excluded list.**

- https://scperturb.org redirects to http://projects.sanderlab.org/scperturb/. Landing page: harmonized single-cell perturbation sets; RNA Zenodo https://zenodo.org/record/7041849; the interactive table is JavaScript and returned only column titles, not rows. **Measured.**
- Latest RNA record, https://zenodo.org/records/13350497 (concept https://doi.org/10.5281/zenodo.7041848), version **1.4**, published note dated 26 Aug 2024, **CC BY 4.0**, open h5ad, no application. Note: “1.4 adds more RNA datasets.” **Measured.** File names include `ReplogleWeissman2022_K562_essential.h5ad`, `_K562_gwps.h5ad`, `_rpe1.h5ad` (separate files), `NadigOConner2024_hepg2.h5ad` and `_jurkat.h5ad` (separate), `SrivatsanTrapnell2020_sciplex3.h5ad`, `McFarlandTsherniak2020.h5ad`. No filename for X-Atlas/Orion, HIPSCI/Feng, GSE314342 or GSE337988. **Measured** from the file list, not from inside the files.
- Nature Methods paper, read at https://pmc.ncbi.nlm.nih.gov/articles/PMC12220817/ (doi:10.1038/s41592-023-02144-y). Table 1 is 44 datasets. Replogle is CRISPRi with three perturbation counts **2,058; 2,394; 9,867** (the excluded two-line study, stored as separate files). sci-Plex3 is described in the text as **188 drugs across three cell lines**. McFarland is one row: **drugs and CRISPR-cas9, 18 perturbations, 182,875 cells**. No Table 1 row is a large genetic library shared across five cell types. **Measured.** Supplementary Table 1 (the cell-type column) was **not opened**. Zenodo 1.4 is larger than the paper’s 44 datasets; those extra files were identified by name only.

**PerturBase:** http://www.perturbase.cn/ and https://www.perturbase.cn/ **failed to load**. **Measured** as a failed request. NAR paper text, via the Oxford Academic / PubMed record PMID 39377396 (Nucleic Acids Research, 8 Oct 2024): **122 datasets, 46 studies, 101 genetic and 21 chemical, 24,254 genetic and 230 chemical perturbations, about 5 million cells**. The multi-line case study is Srivatsan sci-Plex: **188 compounds in A549, K562 and MCF7** (three lines, drugs). **Measured** from that paper text. Supplementary Table S1 was **not opened**, so a 5-line genetic screen hiding in the catalogue is **unverified**, not ruled out by reading every row. GitHub https://github.com/bm2-lab/PerturBase is the pipeline (GPL-3.0 on the code); Zenodo https://zenodo.org/records/17972932 is a 21.6 MB code/demo zip, not the screens. **Measured.**

## Summary

| Lead | As claimed? | Same genes in ≥5 cell types? | Download without an application | Size | Licence |
| --- | --- | --- | --- | --- | --- |
| VIPerturb-seq | Partly. Three lines only for a 100-sgRNA pilot; genome-wide and vimentin are K562. Flex v1/v2, CRISPRi. | No. Three lines, and only for the pilot. | Yes. Seurat `.rds` / `.RDS` | 17.3 GB (pilot file 1.6 GB) | CC BY 4.0 |
| Echoes of Silenced Genes | Partly. CRISPRi scRNA-seq in one unnamed human cancer cell line; public atlases plus Myllia cells. CROP-seq not stated as this assay. | No. One target line; 80 training perturbations. | Files are on Kaggle; rules text not readable. Indexed licences are non-commercial. | 845 MB | Data tab CC BY-NC-SA 4.0; dataset page CC BY-NC 4.0. Rules unread. |
| HyperMapDB | The DOI 10.1101/2026.04.26.691475 does not exist. Real object is predicted profiles, 18 contexts × 19,036 knockdowns, 2,500 genes. | The matrix is filled by a model. Observed coverage is 2,531 genes, not a new 5-line screen. | Yes. `HyperMapDB1.h5ad` | 16,924,297,965 bytes | Data CC BY 4.0. Preprint text CC BY-NC-ND 4.0. |
| scPerturb / PerturBase | Both are harmonized collections of public studies. | No such screen identified. Site table and PerturBase catalogue not fully read. | scPerturb h5ad: yes, CC BY 4.0. PerturBase website down. | scPerturb: many files, largest seen `Replogle…_K562_gwps.h5ad` at 8.8 GB. PerturBase bulk download: not stated. | scPerturb data CC BY 4.0. Underlying studies keep their own terms. PerturBase data licence: not stated. |

## Related lead (not one of the four)

Myllia’s own page https://myllia.com/resources/crop-seq-training-datasets-for-ai-based-foundation-models-of-human-cell-biology/ (**measured**, live fetch) describes a CROP-seq set in which **the same 218 genes** were perturbed in **THP-1, Jurkat, K562, A549, U2OS or K562** (K562 is written twice), with THP-1 also pushed to M0/M1 macrophages, read by “unbiased single-cell RNA sequencing.” The same page then says a slide deck covers **8** cancer cell lines with one sgRNA library against those 218 genes. Access is “contact info@myllia.com”; no public download, size or licence is stated. That is the only lead here that matches “same genes, several cell types,” and it is proprietary.

None: do not ask the owner to download any of the four for a five-cell-type measured gene screen. The only new public measurements are VIPerturb-seq, already open at 17.3 GB under CC BY 4.0, and the multi-line part of that record is the 1.6 GB three-line pilot.
