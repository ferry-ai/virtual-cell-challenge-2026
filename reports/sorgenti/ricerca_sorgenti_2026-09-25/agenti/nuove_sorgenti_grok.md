I'll search public repositories for 2025–2026 single-cell genetic perturbation datasets and check each accession against the team's existing list.Found eight public 2025–2026 single-cell genetic-perturbation datasets not on the 24 September list. Best match is an expressed-genome CRISPRi atlas in one hiPSC line; the only same-target, two-context screen is CRISPRa of 1,836 transcription factors in fibroblasts and RPE-1.

Excluded after checking: Zhu/Marson primary CD4+ T cells are **GSE314342** (already in use; GEO release 6 Feb 2026). The 34-line iPSC map is card 17. No new scPerturb or PerturbSeq.db release (news stops in 2024).

### 1. KOLF2.1J expressed-genome CRISPRi — best on target universe
Nourreddine, Doctor et al., *Nat Biotechnol* 2026, https://doi.org/10.1038/s41587-026-03199-w. Preprint https://doi.org/10.1101/2024.11.03.621734. **Verified** on https://www.ncbi.nlm.nih.gov/bioproject/PRJNA1173491 and the Figshare+ record https://doi.org/10.25452/figshare.plus.27261219 (page text: “Download all (233.38 GB)”, licence **CC BY 4.0**, posted 2026-05-18; a direct fetch of that URL returned empty).

- **Cells:** one line, KOLF2.1J hiPSC. Not multi-line, not Flex.
- **Modality:** CRISPRi, CROP-seq-style guides, 10x chip. BioProject: separate **GEX** and CRISPR dial-out of protospacers (not a targeted gene panel). **Verified**.
- **Targets:** **11,739** expressed genes × 3 sgRNAs plus **478** non-targeting controls — not every human gene. **Verified** on the Figshare description and the preprint.
- **Cells / MOI:** >2.5 million cells after QC from ~11 million loaded; median >5,000 UMIs. **Verified** on the preprint, not re-counted in the h5ad. Numeric MOI **unverified**; preprint says ~28% of cells had >1 sgRNA and treats that as the 10x doublet rate at 60k recovery.
- **Files:** per-cell `KOLF_Pan_Genome_QC_Filtered.h5ad` (and a 1,655-perturbation subset) in the 233.38 GB Figshare bundle. Raw SRA is listed as **16.72 TB / 45,642 Gbases / 192 BioSamples**. The author site https://y-doctor.github.io/KOLF2.1J_Perturbation_Cell_Atlas/ says FASTQs are **not** openly shareable because of Y-chromosome reads (Jackson Labs). Whether those SRA runs actually download is **unverified**.

### 2. CRISPRa of 1,836 TFs in Hs27 fibroblasts and RPE-1 — best context pair
Southard et al., *Nat Genet* 2025, https://doi.org/10.1038/s41588-025-02284-1. **Verified** on https://www.ncbi.nlm.nih.gov/bioproject/PRJNA1108254 (1,836 TFs; primary fibroblasts and RPE-1; **1,090** SRA experiments; **1.69 TB**).

- **Readout:** 10x Chromium **3′ v3.1** with Feature Barcode CRISPR (CG000316), whole transcriptome plus guides. **Verified** in the journal methods PDF. Droplet overloading, ~125,000 cells/lane. Viral MOI for the TF arm **not stated** on BioProject or Zenodo.
- **Cells:** about **808,000** Hs27 and **1.76 million** RPE-1; **10,979** guides. **Verified** on the preprint (PMC11312553), not re-counted in the h5ad. A filtered reuse library of 3,154 guides / 1,319 TFs is a subset, not the screen.
- **Files / licence:** per-cell h5ad with raw counts in `layer['counts']`. Hs27 singlets h5ad **8.05 GB**, full population **9.72 GB**, cellranger zip **21.6 GB** (https://doi.org/10.5281/zenodo.15200179, https://doi.org/10.5281/zenodo.15213597). RPE-1 population h5ad **29.7 GB**, singlets **11.7 GB**, cellranger zip **46.8 GB** (https://doi.org/10.5281/zenodo.15213619, https://doi.org/10.5281/zenodo.15211972). All **CC BY 4.0** (**verified** via the Zenodo API). CRISPRa, not knockdown. RPE-1 overlaps Replogle; Hs27 does not.

### 3. Gastric dcPerturb-seq across several lines — epithelial, same small library
Tan lab, bioRxiv https://doi.org/10.1101/2025.04.16.649236 (v2, 2 Dec 2025). **Verified** on https://www.ncbi.nlm.nih.gov/bioproject/PRJNA1219803: “Single Cell CRISPR Screening in GC”, registered 6 Feb 2025, **291** SRA experiments, **3.24 TB**. I did not open a run, so download permission is **inferred** from that listing.

- **Design (preprint, not re-counted):** Cas9 knockout, 10x direct-capture (feature-barcode) Perturb-seq; **226** genes; lines named GES1, HFE145, SNU719, NUGC3, LMSU, SNU1750, HGC27; v2 reports **625,866** cells and four epigenetic drugs. v1 had quoted 669,065 cells — treat the cell total as version-dependent. MOI **not stated**.
- **Counts:** raw reads are on SRA. No public count matrix or h5ad on the BioProject page (**unverified** that processed matrices exist). Data licence **not stated** (preprint: all rights reserved).

### 4. Mouse BMDC E3-ligase Perturb-seq — ≥1,000 targets, primary cells, not human
Geiger-Schuller, Regev et al., bioRxiv 23 Jan 2023, https://doi.org/10.1101/2023.01.23.525198. GEO **GSE327057**, public date **2026-04-06** (NCBI esummary). Series text: 1,130 E3 ligases/partners/substrates, primary mouse dendritic cells, LPS, supplementary types **CSV and H5AD**. FTP `filelist.txt` 404’d and the GEO HTML page was a reCAPTCHA, so **file sizes are unverified**. Patent JP2026505163A states 3,390 targeting guides, 330 controls, planned **MOI 0.2**, **838,201** cells, 10x feature-barcode v3/v3.1 — **verified** only as patent text, not on GEO.

### 5. Also opened, weaker fit
- **GSE344535** (public 2026-08-21, esummary): RPE-1, **10x Flex** 16-plex, paired whole transcriptome plus custom ORF probes, infection rate **<30%**. Targets are viral microprotein ORFs (300mer/400mer sublibraries); **human-gene count not stated**. Supplementary type CSV/TAR; sizes not retrieved.
- **GSE320250** (public 2026-08-27): CRISPRi of **520** genes in primary **mouse** HSPCs; sample titles say whole transcriptome; summary lists H5AD/MTX. The FTP filelist I got contained only a **20,480-byte** `RAW.tar` and a **15 KB** guide-count file, so a usable count matrix is **unverified**.
- **GSE274113** (GEO viewer; Science 2025, https://doi.org/10.1126/science.ads7951): Perturb-multiome, **19** transcription factors, primary human HSPCs in erythroid differentiation. Supplementary h5s about **49–77 MB** plus a 3.2 MB metadata csv. Joint RNA+ATAC; I did not read the feature count inside the h5. Too few targets to transfer.
- **GSE343369** (public 2026-08-12): knockout of **225** genes in iPSCs and embryoid bodies; supplementary CSV/H5AD/TSV. Cell number and chemistry **not** in the summary.

### Searches with nothing usable
NCBI esearch `Perturb-seq[All Fields] AND 2025:2026[PDAT]` (297 series) and `CROP-seq` (241). New human hits were mostly the excluded cards, drug screens (GSE306429, GSE344269, GSE327727), or <100-gene libraries. 10x’s public dataset index showed Flex CRISPR only in **K562** (including the 320k Ultima set), already the kind of demo on the list. Illumina “100 million cells” abstract P588 (*Genetics in Medicine Open* 2026) has **no accession**. bioRxiv 2026.08.24.746802 is Cas9 Perturb-seq in **16** cancer lines but only **100** genes, and no accession was in the text I saw. E-MTAB-14567 (ArrayExpress page did not load). CELLxGENE: no genetic-perturbation collection beyond Orion.

**Open for Claude1:** confirm KOLF SRA runs actually download; gastric processed matrices and exact line list; GSE320250 h5ad location; whether GSE327057’s h5ad is on a GEO supplementary path the FTP listing missed. I did not count genes inside any matrix.
