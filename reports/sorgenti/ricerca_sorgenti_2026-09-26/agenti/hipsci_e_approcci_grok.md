# HIPSCI e resoconti pubblici della gara: grok

Rapporto integrale di grok (hub, esecuzione `20260926-144528-v2-grok-hipsci`, sola lettura, brief
`v2-grok-hipsci-approaches.md`), copiato il 26 settembre senza modifiche,
tranne i nomi utente di partecipanti privati (un repository GitHub e due account X), sostituiti fra parentesi quadre. **Rapporto di un agente:
ogni dato va verificato da una seconda famiglia prima di arrivare a una decisione.**

---

I'll verify the HIPSCI CRISPRi screen and public VCC 2026 write-ups from primary pages only, starting with the local catalogue and the Sanger/Figshare records.The HIPSCI CRISPRi screen is public 10x 5′ (not Flex) data with per-cell counts and log-fold-change tables, but overlap with the 300 panel was not computed; public VCC 2026 write-ups define `expr_mse_unbiased_capped_norm` and a mean-response baseline, and no participant source found states an amplitude calibration, a public Perturb-seq training set, or a cell-line identification.

## A. HIPSCI CRISPRi scRNA-seq

**Identity and accessions (measured).** One study, two screens, distinct from any record numbered 27261219 (that id is not cited by this paper).

- Paper: Feng et al., *Cell Genomics* 6:101076 (epub 1 Dec 2025; issue 11 Feb 2026). DOI [10.1016/j.xgen.2025.101076](https://doi.org/10.1016/j.xgen.2025.101076), PMID 41330380, PMCID [PMC12903452](https://pmc.ncbi.nlm.nih.gov/articles/PMC12903452/). Preprint 28 Nov 2024: [10.1101/2024.11.28.625833](https://www.biorxiv.org/content/10.1101/2024.11.28.625833v1).
- Raw reads: study [PRJEB81502](https://www.ebi.ac.uk/ena/browser/view/PRJEB81502), secondary id **ERP165335**. ENA XML: public, first public 2024-11-08, centre Wellcome Sanger Institute ([study XML](https://www.ebi.ac.uk/ena/browser/api/xml/PRJEB81502)). The Sanger page writes “ERP16533”; the paper’s data-availability statement and the ENA secondary id are ERP165335 ([Sanger](https://www.sanger.ac.uk/tool/crispri-scrna-seq-hipsci/), [PMC data availability](https://pmc.ncbi.nlm.nih.gov/articles/PMC12903452/)).
- Processed LFC and a sequencing-file table: Figshare [10.6084/m9.figshare.26819743](https://doi.org/10.6084/m9.figshare.26819743) (article 26819743, v1). Counts: [10.6084/m9.figshare.27989294](https://doi.org/10.6084/m9.figshare.27989294) (article 27989294, v2).
- Code: [github.com/claudiafeng123/crispri_scrnaseq_hipsci](https://github.com/claudiafeng123/crispri_scrnaseq_hipsci), MIT (GitHub API licence field; paper says MIT).
- GEO and EGA accessions: **not found** in the paper’s data-availability statement. Demultiplexing used HipSci consortium genotypes ([PMC STAR Methods](https://pmc.ncbi.nlm.nih.gov/articles/PMC12903452/)); whether those genotypes are controlled-access is **not stated** there.

**What is downloadable without controlled access (measured).** Figshare API: both articles `is_public: true`, `download_disabled: false`, `is_embargoed: false`, licence MIT ([26819743](https://api.figshare.com/v2/articles/26819743), [27989294](https://api.figshare.com/v2/articles/27989294)). ENA: public runs, submitted format CRAM, generated FASTQ also listed. Five-run sample of `submitted_bytes`: about 26.2–43.4 GB per CRAM ([filereport](https://www.ebi.ac.uk/ena/portal/api/filereport?accession=PRJEB81502&result=read_run&fields=run_accession,submitted_format,submitted_bytes,fastq_bytes&limit=5)). Total size not summed. ENA search count for the study: **564** runs ([count API](https://www.ebi.ac.uk/ena/portal/api/count?result=read_run&query=study_accession%3DPRJEB81502)). Sanger says the Figshare table describes **516** sequencing files. Those two counts were not reconciled (the 123 KB mapping CSV was not opened).

No file in either Figshare list is named pseudobulk or h5ad. **Inferred:** the LFC tables are the differential summaries; they are not a count-level pseudobulk matrix.

Figshare 26819743, API `size` 9,119,437,506 bytes; the HTML label is “Download all (8.49 GB)” ([page](https://figshare.com/articles/dataset/A_genome-scale_single_cell_CRISPRi_map_of_trans_gene_regulation_across_many_human_pluripotent_stem_cell_lines_Transcriptional_Changes_/26819743)). Files, all gzip except where noted:

| File | Bytes |
|---|---|
| `TargetedScreen_LFC_byGuide-perLine.tsv.gz` | 3,592,732,872 |
| `GenomeWideScreen_LFC_byGuide.tsv.gz` | 1,812,579,303 |
| `GenomeWideScreen_LFC_byGene.tsv.gz` | 794,610,300 |
| `GenomeWideScreen_Coperturbation-Expressed-Gene-Correlation.tsv.gz` | 529,575,408 |
| `TargetedScreen_LFC_byGuide.tsv.gz` | 231,621,570 |
| `GenomeWideScreen_Coregulation-Target-Correlation.tsv.gz` | 155,213,386 |
| `TargetedScreen_LFC_byGene-perLine.tsv.gz` | 1,919,661,029 |
| `TargetedScreen_LFC_byGene.tsv.gz` | 77,563,731 |
| `00_raw_data_id_mapping.csv` | 122,631 |
| `scripts.zip` | 3,303,491 |
| `Peer Review.pdf` | 2,453,785 |

Figshare 27989294, API `size` 7,925,882,368 bytes; HTML “Download all (7.38 GB)”. Per screen (fitness, non-fitness, targeted): RNA UMI counts, guide UMI counts, cell metadata.

| File | Bytes |
|---|---|
| `TargetedScreen_RNA-UMI-Counts.csv.gz` | 4,480,969,391 |
| `GenomeWideScreen_NonFitnessGenes_RNA-UMI-Counts.csv.gz` | 1,748,940,996 |
| `GenomeWideScreen_FitnessGenes_RNA-UMI-Counts.csv.gz` | 1,445,924,890 |
| `GenomeWideScreen_NonFitnessGenes_Guide-UMI-Counts.csv.gz` | 104,663,390 |
| `TargetedScreen_Guide-UMI-Counts.csv.gz` | 73,778,450 |
| `GenomeWideScreen_FitnessGenes_Guide-UMI-Counts.csv.gz` | 50,267,344 |
| `TargetedScreen_Cell-Metadata.tsv.gz` | 13,491,635 |
| `GenomeWideScreen_NonFitnessGenes_Cell-Metadata.tsv.gz` | 4,238,782 |
| `GenomeWideScreen_FitnessGenes_Cell-Metadata.tsv.gz` | 3,607,490 |

Guide assignment is a rule in the methods, not a separate named file: a cell is assigned if the top guide is 0.5–1 of guide UMIs (median threshold 0.75) and has at least 3 UMIs ([PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC12903452/)). Whether the metadata TSVs already store that call was **not opened**.

**Licence (measured).** Paper: CC BY 4.0. Both Figshare records and the GitHub repo: MIT. ENA reads: public, no data-access committee found on the study record.

**Assay (measured).** Not Flex and not 3′. STAR Methods: Chromium Next GEM Single Cell 5′ Kit v2 (PN-1000263), Chip K (PN-1000287), Library Construction Kit (PN-1000190), Dual Index TT Set A (PN-1000215). “An extra primer” was added to the GEM mix to capture gRNAs. 1.65×10⁴ cells loaded per inlet. Cell Ranger 6.0.1, default parameters, genome build written “GRch38”, plus BFP, mScarlet, BSD and dCas9-KRAB-MeCP2. ENA library source: transcriptomic single cell; platform Illumina NovaSeq 6000; paired; submitted CRAM. The ENA study description also says “10x Genomics 5′ v2” and direct capture of guides and transcriptome; that text is prospective (“we will”) and names “~64 lines”, which does not match the paper.

**Scale (measured, paper).** Genome-scale: 7,226 genes, 34 lines, 26 donors. Library construction: 6,784 guides for 2,264 iPSC-fitness genes (harvested 3, 4 and 5 days post-infection) and 14,883 guides for 4,962 other genes (day 6), plus 40 non-targeting Dolcetto guides. After QC and demultiplexing: 219,206 cells with a targeting guide (median 8 cells/guide, 25 cells/gene) and 499,998 control cells (unassigned or non-targeting). Analysis kept targets with ≥10 cells: 6,673/7,226. On-target knockdown significant for 2,900/4,874 expressed targets (median LFC −0.42).

Targeted arm: 1,355 guides against 444 genes plus 20 non-targeting guides; 20 lines from 10 donors. After QC: 1,161,864 cells; 635,022 (55%) assigned to 444 targets in **19** lines; median 74 cells per target per line. The preprint’s “nearly 2 million cells” and “over 20,000 guide RNAs” are the preprint’s wording, not a sum I recomputed from the count files.

**Whole transcriptome (measured plus inference).** Chemistry is 5′ poly(A) gene expression, not a probe panel (**inferred** from the kit, not from an opened matrix). The published analysis is not all detected genes: genes kept only if log-normalised mean expression (scale 10,000) exceeded 0.1 in every inlet, leaving **6,471** genes (genome-wide) and **6,517** (targeted). QC cells: inlet-specific UMI floors between 1,926 and 39,260 (mean 14,186), at least 2,000 features, mitochondrial fraction ≤10%. How many genes are in the RNA-UMI files before that filter: **not opened**.

**Overlap with the 300 (not computed).** Primary lists exist and were not opened: PMC Table S1, `mmc2.xlsx` (857 KB), “Selected genes for CRISPR knockdown in the genome-scale screen”, and Table S6 for the targeted arm ([PMC supplements](https://pmc.ncbi.nlm.nih.gov/articles/PMC12903452/)). `reports/data_audit/hipsci_coverage.json` was opened far enough to see that it is a local precomputed overlap with a `hits` list; that list was not copied and is not a primary source.

## B. Public write-ups of VCC 2026 approaches

**Organisers — task and data (measured).**

- [virtualcellchallenge.org](https://virtualcellchallenge.org/): no new training set; H1 data from the previous year plus any other public or private data are allowed. Six cell lines; validation is 300 CRISPRi knockdowns in three contexts, each with 18,400 non-targeting control cells (46 guides × 400 cells). Final test (22 Oct 2026) is a new panel of 300 knockdowns in three other contexts. Deadline 5 Nov 2026. The page does not name the metric identifiers.
- Arc news, 20 Aug 2026 ([arcinstitute.org/news/virtual-cell-challenge-2026](https://arcinstitute.org/news/virtual-cell-challenge-2026)): zero-shot CRISPRi in six lines never seen perturbed; assay described as CRISPRi, 10x Flex, Ultima UG100. Inputs are non-targeting profiles plus gene ids. Same dates.
- *Cell* commentary, 17 Sep 2026, volume 189, pp. 5827–5830 ([S0092-8674(26)00931-1](https://www.cell.com/cell/fulltext/S0092-8674(26)00931-1)): same zero-shot design and 10x Flex. Live leaderboard uses “a subset of metrics from Cell-Eval”; final score is “a reference-normalized aggregate across six metrics.” It does **not** print `expr_mse_unbiased_capped_norm`. STATE is cited as the Cell-Eval paper, not named as the 2026 scored baseline.

**Organisers — the expression-MSE member and the baseline (measured).** Arc’s [vcc2026-metrics-brief.md](https://raw.githubusercontent.com/ArcInstitute/cell-eval2/main/docs/vcc2026_metrics/vcc2026-metrics-brief.md), header date 2026/08/19, and the [full spec](https://raw.githubusercontent.com/ArcInstitute/cell-eval2/main/docs/vcc2026_metrics/vcc2026-metrics.md). Also summarised on [cell-eval2](https://github.com/ArcInstitute/cell-eval2/).

- Six scored members. `expr_mse_unbiased_capped_norm` is the panel-wide ratio of sampling-corrected squared profile error to the measured profile’s distance from control. Lower is better. It has no per-perturbation value. It is the only member clamped to [0, 1].
- The “capped” part is not called amplitude calibration. The spec says the sampling correction credited to the prediction is limited by `min(prediction, reference)`, and a factor ρ ≤ 1 further limits the total credit by the submission’s across-perturbation spread (`PRED_TRACE_CAP_K` = 1.0). A prediction that pastes the control has expected value 1; a perfect prediction has expected value 0.
- Scored baseline is not a trained model. For each metric, 0 is the context’s mean perturbation response (one profile copied onto every perturbation) and 1 is a five-split half-depth replicate. On the three reference bundles (`cell-eval2` 0.15.0, `rule_version` 3), this member’s baseline is 0.986–0.992 and its replicate is 0.028–0.045. The spec says a mean-response predictor is barely distinguishable from pasting the control.
- Evaluation axis stated there: 18,533 genes, 300 constructs plus a 46-guide non-targeting pool, 400 cells and median 20,000 UMIs per perturbation. All six metrics drop target genes.

The CLI wiki ([vcc-cli-wiki.virtualcellchallenge.org](https://vcc-cli-wiki.virtualcellchallenge.org/)) uses the short name “Expression accuracy mse” and says only that member is capped at 1.0. It shows an example status block (rank 2, overall 0.3614, mse 0.0). **Unverified** whether that block is a live leaderboard row. No page date found.

**Cell-line identity (measured).** The same wiki: contexts A, B and C are different cell lines; “We don’t publish which one”; labels are “deliberately opaque.” Final lines are D, E and F, different lines, labels not reused. Each validation context is 18,400 non-targeting cells in `context_A/B/C.h5ad`. A public write-up that identifies those lines from the controls: **not found**.

**Participants and other 2026 pages (measured).**

- [repository GitHub pubblico di un partecipante], created 27 Aug 2026. Says the six scores depend only on two scalars per gene (first moment and mean control quantile), so cell-level joint distributions do not affect the score. Stage 1, estimating the effects, is marked not done. Stage 2, turning those moments into 400 integer cells, is marked done and checked against `cell-eval2` 0.16.0 (DE gate 9,929 genes; significant-set symmetric difference 0 on three perturbations). It states a then-current first place overall of 0.1899; that was **not** checked against a live leaderboard. It does not describe training on public Perturb-seq, amplitude calibration, or naming the lines.
- X posts of 10 Aug 2026 and 16 Aug 2026 are calls for collaborators, not methods ([due post su X, account privati]).
- [Boom5426/Awesome-Virtual-Cell](https://github.com/Boom5426/Awesome-Virtual-Cell) still says, from a homepage reading dated 17 Aug 2026, that the 2026 scoring metrics were unpublished. That sentence is earlier than the 19 Aug metric spec.
- Ingenix, 2 Feb 2026 ([substack](https://ingenix.substack.com/p/the-virtual-cell-challenge-towards-bc9)), describes their 2025 models (μ-state, state.T, sc.fm) and 2025 metric complaints. It is not a 2026 submission. The phrase “amplitude calibration” for the 2026 metric: **not found**. A 2026 participant statement of which public Perturb-seq corpus they train on: **not found**. The organiser pages only say H1 plus any public or private data are allowed.

## Not done / open

Count matrices, Table S1/S6, and `00_raw_data_id_mapping.csv` were not opened, so the 300-target overlap, the gene count inside the UMI files, and the 516-vs-564 run discrepancy are unknown. No EGA/GEO id was found. No 2026 participant source found that states an amplitude-calibration procedure, names a Perturb-seq training set, or identifies contexts A–C. The dossier’s “first place 0.1899” and the CLI wiki’s example rank were not checked on the live leaderboard.
