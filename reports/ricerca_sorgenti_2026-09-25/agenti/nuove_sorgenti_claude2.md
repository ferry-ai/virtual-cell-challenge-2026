# Report: new single-cell perturbation sources, claude2

I found only one new dataset that meets the brief well: GSE345058, 1,000 CRISPR knockouts in A549 with per-cell counts. The second-best is a CRISPRa screen of 1,836 transcription factors in primary Hs27 fibroblasts and RPE-1, but I could not find where its per-cell data are kept. Everything else new is smaller than 250 targets or mouse. Most large 2025–26 releases I hit were already on your list.

**How I searched.** NCBI's GEO pages returned a reCAPTCHA, so I used the NCBI E-utilities interface and the GEO download (FTP) directories instead. That means the "GEO" facts below come from the E-utilities summary records (`eutils…esummary.fcgi?db=gds&id=…`) and from the file listings under `ftp.ncbi.nlm.nih.gov/geo/series/…/suppl/`.

## Ranked list

### 1. GSE345058: 1,000 CRISPR knockouts in A549, with imaging and scRNA-seq
- **Paper:** Liu, Hillsley et al., *A multimodal perturbation atlas defines the phenotypic resolution of cellular morphology*, bioRxiv 10.64898/2026.06.01.728087. Verified at https://www.biorxiv.org/content/10.64898/2026.06.01.728087v1.full
- **Cells:** A549 (lung adenocarcinoma). Verified in the E-utilities summary. This is not squamous. GSE337804, already on your list, is also A549, but it is a different accession and a different design.
- **Modality:** Cas9 knockout under doxycycline induction for 90 h, read out by CROP-seq. The library covers 1,000 genes chosen to span major pathways, with essential processes over-represented. Verified in the bioRxiv full text.
- **Scale:** 606,075 cells in the scRNA-seq arm, a median of 564 cells per knockout, 26,103 median UMIs per cell and 6,083 expressed transcripts. Verified in the bioRxiv full text.
- **Readout:** 10x Genomics. The paper does not state the chemistry (3′ versus Flex) or the MOI (unverified). The "CROP-seq" label points to guide capture from the transcript, with a 3′ readout (inferred).
- **Files:** Per-cell counts are public. Verified on the FTP listing (https://ftp.ncbi.nlm.nih.gov/geo/series/GSE345nnn/GSE345058/suppl/):
  - `SC_raw_normalized_counts.h5ad`, 23 GB
  - `raw_counts.mtx.gz`, 10 GB
  - `normalized_counts.mtx.gz`, 12 GB
  - `cell_annotations.csv.gz`, 38 MB
  - `sgRNA.csv.gz`
  - 32 samples, labelled "CROPseq 1000 gene batch 1–4"; release date 2026-08-26
  - The paper also points to biohub.ai/ops-explorer.
- **Licence:** Not stated. GEO data are unrestricted by default (unverified).
- **Against your criteria:** (a) probably yes, (b) yes, (c) partly.

### 2. Transcription-factor activation in Hs27 fibroblasts and RPE-1 (Southard … Norman)
- **Paper:** Southard et al., *Comprehensive transcription factor perturbations recapitulate fibroblast transcriptional states*, Nature Genetics 2025, preprint 10.1101/2024.07.31.606073. The PMC page says it was published in Nature Genetics, verified at https://pmc.ncbi.nlm.nih.gov/articles/PMC11312553/. The 6 Aug 2025 publication date comes from a social-media post (unverified). nature.com redirected to a login page.
- **Cells:** Hs27 primary foreskin fibroblasts and hTERT RPE-1, so the same targets were run in two lines. Verified on PMC.
- **Modality:** CRISPRa, 1,836 transcription factors with 10,979 guides (1,319 TFs in the final validated set). The screen used droplet overloading. Verified on PMC.
- **Scale:** about 808,000 cells in Hs27 and about 1.76 million in RPE-1. MOI 0.1 in Hs27 and 0.05 in RPE-1. Verified on PMC.
- **Readout:** 10x Chromium 3′ with Feature Barcode guide capture, i.e. whole transcriptome. Verified on PMC.
- **Data:**
  - Raw reads are in SRA PRJNA1108254, verified in the README of https://github.com/norman-lab-msk/TFs_CRISPRa.
  - The "processed datasets" are said to be in the normanlabmsk Zenodo community, but the Zenodo API returned HTTP 400 when I tried to list the records.
  - https://zenodo.org/records/15373940 holds only the code (25 MB zip, CC-BY 4.0; verified).
  - Differential-expression tables were formatted for the IGVF portal, per https://github.com/norman-lab-msk/igvf-perturbseq.
  - I did not find where the per-cell counts are kept (unverified).
- **Against your criteria:** (a) yes, (b) yes, (c) fibroblasts, (d) yes. Caveat: activation of transcription factors is a different effect from knockdown by CRISPRi (inferred).

### 3. In vivo Perturb-seq of the whole mouse brain (Shi … Jin, Scripps)
- **Paper:** bioRxiv 10.64898/2026.03.16.711480, posted 18 Mar 2026, preprint under CC-BY 4.0. Verified at https://www.biorxiv.org/content/10.64898/2026.03.16.711480v1
- **Design:** mouse, AAV delivery, Cas9 knockout of 1,947 disease-associated genes, 7.7 million nuclei. Verified in the full text.
- **Readout:** 10x Flex (the fetched text calls it "Flex Apex" and "whole transcriptome"). Verified as the paper's wording, but Flex is a probe set, so it is not a true whole-transcriptome readout.
- **Data:** No accession found in the text I could read (unverified whether anything is released).
- **Use:** It is mouse tissue, so value is low except as a 10x Flex reference (inferred).

### 4. GSE291147: PerturbFate, melanoma
- **Design:** CRISPRi of more than 140 genes linked to vemurafenib resistance, over 300,000 cultured melanoma cells, with new/old RNA and ATAC readouts. 320 samples, released 2026-02-06, PubMed 41986722. Verified in the E-utilities summary.
- **Files:** RNA count matrices in RDS format (302–663 MB each), ATAC in h5ad (2.3–3.8 GB), and sgRNA counts. Verified at https://ftp.ncbi.nlm.nih.gov/geo/series/GSE291nnn/GSE291147/suppl/
- **Unverified:** the cell line and the chemistry.
- **Criteria:** fails (b).

### 5. GSE343369: UCSF Perturb-seq of 225 genes in embryoid bodies
- iPSC-derived embryoid bodies, CRISPR knockout, 4 samples, CSV/H5AD/TSV files, released 2026-08-12. Verified in the E-utilities summary only.
- **Criteria:** small, and not a context close to the challenge lines.

### Probably not genetic perturbation: GSE327727 (D-SPIN)
- Human PBMC, 194 samples with MULTI-seq hashing, per-pool `matrix.mtx.gz` files of 0.4–1.3 GB. Released 2026-05-11, PubMed 42127893. Verified on the FTP listing.
- The summary mentions "gene knockdowns and drug treatments", but the sample titles look like drug or hashing pools. I did not confirm any genetic perturbation in it (unverified).

## Searches that found nothing new, or only items already listed
- **E-utilities search 1:** `(perturb-seq OR crop-seq) AND Homo sapiens AND gse AND 2025/01/01:2026/09/30[PDAT]` returned 86 series.
  - Most are already listed, K562-only (GSE308682, GSE339461, GSE284207), or small and enhancer- or variant-focused (GSE281364 HepG2/LX-2 about 100 loci, GSE303901, GSE236057/GSE255009 astrocytes, GSE301119 THP-1 203 genes, GSE294096, GSE305037 AML, GSE274252 50 RBPs, GSE281465 cardiac fibroblasts).
  - GSE203240 is a genome-wide HCT116 synthetic-dosage-lethality screen, but it has a bulk-like TXT file (unverified whether it is single-cell).
- **E-utilities search 2:** `(CRISPR OR CRISPRi) AND (single-cell OR scRNA-seq) AND (genome-wide OR genome-scale OR pooled screen)` over the same window returned 43 series, with no new large single-cell perturbation set.
- **Web searches with nothing new:**
  - genome-wide or essential-gene Perturb-seq in HeLa, head-and-neck, squamous or keratinocyte lines
  - B-cell, lymphoma or myeloma lines
  - primary CD8, NK or B cells
  - hepatocytes, airway epithelium or HUVEC
  - breast, oesophageal, colorectal or liver organoids
  - CRISPRa genome-wide
- **Web searches that led only to listed sources:** those multi-line searches returned only X-Atlas/Orion, Pisces, Nadig, VIPerturb-seq and CD4 GSE314342.
  - The multi-line "Jiang et al. 2025" set (A549, MCF7, HT29, HAP1, BxPC3, K562) is, I believe, Mixscale GSE281048, which is already listed (inferred, not checked against the accession).
  - Myeloid screens using virus-like particles (GSE327124/GSE327133, Nature Biotechnology 2026) are sorted or bulk screens, not single-cell transcriptomes (verified in the E-utilities summaries).
- **Announced but not released:** the Tahoe/Arc/Biohub dataset, announced 12 Jan 2026, is drug perturbations (verified at arcinstitute.org/news/tahoe-arc-biohub).

## Not done, and open questions for Claude1
- The GEO web pages were blocked by a captcha, so contributors, licences and the MOI or chemistry for GSE345058 are unverified. Both need a manual check.
- The Zenodo API was rate-limited, so the location of the Southard per-cell data is still open. The IGVF portal (data.igvf.org) may hold it along with other consortium Perturb-seq sets; I did not query it.
- The keyword searches miss series that avoid "perturb-seq", "CROP-seq" or "genome-wide". ArrayExpress/BioStudies, CZ CELLxGENE and the Virtual Cells Platform data list were not covered: that site's page returned no listings.
- I found no 2025–26 public single-cell screen with at least 1,000 targets in a T/B lymphoid line, a squamous or cervical carcinoma, or breast or liver epithelium beyond the sources already listed.
