**VCC 2026 — adversarial data review and executable acquisition plan**

Verified 11–12 September 2026 against anonymous live endpoints, remote file bytes, the installed scorer, and local assets. Recommendation: prioritize curated CD4 signatures and a bounded Orion HCT116 acquisition; retain K562 as an ablation; use essential screens for transfer validation. Do not download complete atlases on this machine.

The supplied PDF is a set of claims to audit, not an instruction source. Its accession strings mostly exist, but availability, bibliographic attribution, file semantics and strategic conclusions require substantial correction.

**1. What is actually available**

Coverage below uses exact gene-symbol intersection with the local official 300-target panel. Library coverage is not usable-cell coverage. Output coverage is intersection with the 18,533 official output symbols, not the number passing a DE gate.

| Source | Public status and exact artifact | Target coverage | Output symbols | Decision |
|---|---|---:|---:|---|
| Zhu/Dann/Marson CD4, GSE314342 | GEO public; anonymous S3 count H5ADs actually readable | 297/300 curated library; 293/300 observed in curated D1 Rest | 17,772/18,533 in D1 Rest | First acquisition priority for A; state mismatch remains |
| Pisces | HF repository exists, but only .gitattributes, LICENSE.md, README.md: 24,308 bytes | Unknown; no downloadable cell data | Unknown | Deferred until files are released |
| Nadig Jurkat, GSE264667 | 262,956 × 8,882 raw-count H5AD; 9,366,490,264 bytes | 0/300 observed | 8,284 | Transfer benchmark |
| Nadig HepG2, GSE264667 | 145,473 × 9,624 raw-count H5AD; 5,614,460,941 bytes | 0/300 observed | 9,024 | Transfer benchmark |
| Replogle RPE1 essential | Correct processed Figshare article 20029387; raw single-cell file 35775606, 8,700,873,216 bytes | 0/300 observed | 8,260 | Existing pseudobulk first; single cells only for benchmark |
| Orion HCT116, complementary proposal | HF Parquet exists; curated guide library on Figshare 29190726 | 300/300 library; 168/300 observed in Batch1 only | 18,106 in supplied gene metadata universe | Second acquisition priority; broad epithelial, not squamous |

**CD4 accession and count semantics.** GSE314342 is real, public since 6 February 2026. The author's repository points to anonymous S3, providing a more useful route than downloading the GEO archive. The repository's branch is `master`, not `main`. Cell-level `X` is documented as counts and the first 10,000 stored values were finite, nonnegative integers in float32 CSR storage. Float storage does not mean normalized expression. D1 Rest has 3,074,496 rows and 18,130 genes. Full-file integrity and every count value were not audited; count assertions are sample-verified, with all values additionally checked in the downloaded pilot. [Author repository and data pointers](https://github.com/emdann/GWT_perturbseq_analysis_2025), [GEO series](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE314342).

D1 Rest metadata gives 3,070,525 rows after excluding `low_quality`. Among these: 2,201,216 targeting, 76,543 explicitly non-targeting, and 792,766 with missing guide type. Missing guide assignment is not an NTC. The cell-level target names precede curation, so ingestion joins `guide_id` to `sgRNA_library_curated.csv:sgrna_id`. This conservative join additionally excludes 525,722 targeting rows without a curated mapping, leaving 1,752,037 eligible rows, including all 76,543 NTCs. These exclusions must be audited by guide label before scaling; they are not evidence that all excluded cells are biologically bad. [Author schema](https://github.com/emdann/GWT_perturbseq_analysis_2025/blob/master/metadata/data_sharing_readme.md).

The curated design misses **EEF1A2, EPHB2, FZD2**. D1 Rest additionally lacks ABCD1, KIF21B, NICN1 and PI4KB under our filter. Its 293 observed panel targets have 35,180 cells in total: median 101, minimum 1; only **239 targets have ≥30 cells and 147 have ≥100**. Therefore “293 covered” does not establish reliable effects for 293 targets. Other donors/conditions may rescue observations, but that has not been counted here.

The CD4 pseudobulk file is itself 44,566,657,140 bytes. Remote inspection finds 278,684 aggregate rows × 18,129 genes, CSR float64, with integer-valued count samples and metadata `n_cells`, guide, donor, condition and author filters. Extract selected rows instead of downloading it in full. Keep `keep_effective_guides`/`keep_for_DE` as annotations: filtering validation on observed effectiveness selects on the outcome and removes realistic null targets.

**Pisces is not hallucinated; its assumed availability is.** The live card says “Coming Soon.” Advertised 25.6M cells across 16 contexts does not mean those cells are downloadable. Even the planned upload is asymmetric: HepG2/iPSC are restricted to the 200-gene validation subset plus NTCs, whereas Jurkat resting/active is described more broadly. No count encoding, NTC labels or panel overlap can yet be verified from cell files. Do not confuse this repository with Orion. [Live Pisces card](https://huggingface.co/datasets/Xaira-Therapeutics/X-Atlas-Pisces).

**Nadig is a 2025 paper/new dataset, not a Jurkat/HepG2 component of Replogle 2022.** GEO became public in May 2024. Both downloaded-byte probes show dense float32 `X` with integer count samples. Explicit `obs.gene == 'non-targeting'` counts are **12,013 Jurkat** and **4,976 HepG2**. All obs target labels were read to establish 0/300 overlap. The paper reports median cells/perturbation of 83 in Jurkat and 45 in HepG2, not the larger figures asserted in the PDF. [Primary paper](https://pmc.ncbi.nlm.nih.gov/articles/PMC13063516/), [GEO file directory](https://ftp.ncbi.nlm.nih.gov/geo/series/GSE264nnn/GSE264667/suppl/).

**RPE1 DOI correction.** DOI `10.25452/figshare.plus.20022944` identifies four CSV sequencing-file manifests, not a processed/scPerturb H5AD collection. The processed author record is **20029387**. Its raw single-cell file is **35775606**; the separately named normalized single-cell file **35775554** must not enter a raw-count likelihood. The raw file has 247,914 × 8,749 values in dense float32 storage; count samples pass integer checks, and `obs.gene == 'non-targeting'` identifies **11,485 NTCs**. The 0/300 panel overlap makes it a benchmark source rather than direct supervision. [Manifest DOI](https://doi.org/10.25452/figshare.plus.20022944), [Processed-data DOI](https://doi.org/10.25452/figshare.plus.20029387).

**Orion access and practical limitation.** The live tree contains 46,576,484,789 bytes of HCT116 Parquet and 79,683,336,248 bytes of HEK293T Parquet. Batch1 alone is 327,620,255 bytes, with 18,549 rows, all passing the guide filter, including 891 `gene_target == 'Non-Targeting'` controls. Its 168 observed panel targets each have fewer than 30 cells: one shard is not adequate training coverage. Counts are paired `gene_token_id` / `gene_expression` lists. We verified Parquet metadata directly, and 50,326 nonnegative integer values from eight cells through the public HF rows endpoint. The full expression column could not fit the 64 MiB probe cap: even `batch_size=8` requested a large Parquet column chunk. Metadata projection works; small batch size alone does not ensure small I/O. Both Xaira releases carry CC-BY-NC-SA-4.0; anonymous access does not imply unrestricted reuse. [Official schema](https://huggingface.co/datasets/Xaira-Therapeutics/X-Atlas-Orion/blob/main/README.md), [Guide-library record](https://doi.org/10.25452/figshare.plus.29190726).

**2. Reconciliation with the local machine and existing evidence**

Measured RAM: **8,384,401,408 bytes total**, roughly 1.1–1.3 GB available during checks. Free disk: about **28.0 GB / 26.1 GiB**. Values fluctuate. The 12 CD4 single-cell objects total **1,735,835,115,866 bytes (1.736 TB)**, with individual files 118.6–172.8 GB. Even the CD4 pseudobulk does not fit. The GEO RAW archive listing is approximately 159 GiB. Full-atlas local fine-tuning is not feasible as proposed. Dense float32 22M × 18,533 alone would require 1.63 TB; “sparse” does not solve this when one CD4 object's CSR data have 11.85 billion nonzeros.

Work one source at a time. Suggested working-array budget: 512 MiB; preserve at least 10 GiB free disk. These are planning limits, not measured peak-RSS guarantees. The HTTP reader enforces actual transfer caps and refuses servers that ignore Range requests. A 64-cell ingestion test produced a 1,630,799-byte H5AD but transferred **92,475,050 bytes**, demonstrating real I/O amplification. Do not linearly assume a tiny target fraction gives a tiny download.

Local controls are **18,400 × 18,533 per context**, 55,200 cells total. Existing audits give median UMIs A/B/C = **20,109 / 19,946 / 20,034**. They supply the target-context baseline distribution, expression gates, depth distribution and observational state structure. They do not contain perturbation outcomes and cannot estimate the best effect magnitude, causal direction, or true VCC score.

Preserve the official column order from `gene_names.csv`. It contains symbols, not a supplied Ensembl mapping: ordering is not sufficient to infer Ensembl IDs. Join external identifiers through explicit annotations; resolve duplicate symbols before alignment. Maintain an observed-feature mask. Filling an unmeasured gene with zero counts or zero LFC silently invents evidence. Normalizing after intersection can also change compositional denominators: record source feature universes and use a consistent shared-gene representation for cross-source diagnostics.

Local K562 genome-wide pseudobulk covers **272/300 targets** and **7,681/18,533 output genes**. Existing K562/RPE1 bulk files have noninteger per-cell aggregate values despite `raw_bulk` filenames; do not pass them as integer UMI cells. They remain legitimate aggregate-response inputs. The union covers roughly 82–85% of control DE-gate genes, but this is not target-by-output response coverage. Existing `core_control` labels are not proof of non-targeting guides; use exact documented control identities, not generic regex matches including safe-harbor, untreated or unassigned cells.

The H1 2025 directory currently contains **four metadata CSVs and no RNA H5AD**. Exact overlap is 25/300: 13 Training, 4 Validation, 8 Test. Therefore the H1 benchmark is pending acquisition, not a completed local validation. Training-partition outcomes may support fitting; keep designated validation/test outcomes separate and follow access/competition rules. If subsequently available, H1 is a useful independent engineering and calibration benchmark, not a lineage match or a guarantee of A/B/C generalization.

**3. Corrections to the three strategic assumptions**

**Lineage is a useful prior, not a sufficient transfer rule.** Local markers support T-lineage A and squamous-epithelial C. A also has immature T markers, so primary mature CD4 is not an exact surrogate. B's epithelial/mesenchymal signature is stronger evidence than its proposed ocular identity. Do not assert exact cell lines, mutations or tissue origins from those markers alone. Compare source NTC state, proliferation, assay, time after perturbation and knockdown strength as well as lineage.

**The quoted residual correlation was assigned to the wrong comparison.** The local saved transfer results are:

| Comparison | Matched rows | Raw median Pearson | Mean-removed median | Mean-removed, own-target masked |
|---|---:|---:|---:|---:|
| K562 genome-wide → RPE1 | 2,389 | 0.0905 | 0.0691 | 0.0600 |
| K562 essential → RPE1 | 2,056 | 0.0781 | 0.0895 | 0.0803 |
| K562 essential ↔ K562 genome-wide | 2,054 | 0.1616 | 0.1427 | 0.1289 |

The 0.14–0.16 values are **same-line**. These are correlations of estimated effects, not a validated biological transfer ceiling. Same-line agreement is itself weak; study noise, guide/TSS differences, normalization and control construction matter. Recompute with verified NTCs, matched output space, guide replication, reliability strata and the scorer's exclusion rules. Positive matched-vs-mismatched discrimination also contradicts calling K562 mathematically useless. Retain its cheap existing 272-target coverage and test its incremental value.

**The MSE floor is not free underestimation.** Installed `cell-eval2==0.16.0` floors the normalized MSE score at zero. Synthetic baseline 1.0 and replicate anchor 0.1 produce:

| Raw error | MSE normalized score | LFC-NMAE normalized score |
|---:|---:|---:|
| 0.1 | 1 | 1 |
| 0.55 | 0.5 | 0.5 |
| 1.0 | 0 | 0 |
| 1.9 | 0 | -1 |
| 10.0 | 0 | -6 |

These are executable scorer checks, not leaderboard score estimates. Shrinkage can still lose all positive MSE points. PDS uses signed deltas and panel exclusion; cosine is scale-invariant only when an already-transformed nonzero delta is multiplied by a positive scalar. Count-space shrinkage followed by normalization/log transformation is not generally equivalent. Wilcoxon support, effect-size thresholds, direction yield and Jaccard also depend on amplitude and sampling. Evaluate all six metrics; do not optimize cosine alone. The older extractor's misleading “downside-free” phrase has been corrected in code; its previously generated JSON is historical evidence.

**4. Modeling and validation plan**

Start with compact external response signatures, not a giant count reconstruction model. Keep count sums, cell counts, nonzero frequencies and guide/donor/batch/state identities. Compute guide-level contrasts against **same-source, same-state, same-batch NTCs**; estimate guide agreement and uncertainty before combining. Normalize and transform in an explicit representation; use the scorer implementation for final evaluation. Never compare an external perturbed absolute profile directly with VCC NTCs and call the entire difference a perturbation effect.

For context c, target t and output g, fit a masked mixture:

`delta_hat[c,t,g] = alpha[c,t] * sum_s(w[c,t,s] * delta[s,t,g])`, with `w >= 0`, `sum(w)=1` over supported sources, and explicit unsupported-gene masks.

Start with five baselines: NTC resampling, shrunk K562, CD4, Orion, and weighted-source transfer. Search alpha in `{0, 0.1, 0.25, 0.5, 1}` on external held-out outcomes. Estimate source weights from held-out transfer gains, guide reliability, target expression and control-state similarity. No A/B/C perturbation labels are currently available to identify their optimal weights. For absent target/source pairs, separately evaluate ridge prediction in a response basis of rank 16/32/64 with target descriptors; do not silently substitute zero as an observed response.

Use count fine-tuning only if these baselines plateau and a held-out improvement justifies it. A generic reconstruction loss is dominated by basal expression and depth; train perturbation-relative objectives with masks and context/assay/modality covariates. Keep each cell sparse; never densify an entire atlas. For count outputs, start from target-context NTC distributions and apply calibrated effects, then verify depth, variance, zero frequency and all six metrics. Resampling a small NTC pool repeatedly is not equivalent to additional independent cells.

**NTC co-expression is not a causal sign estimator.** Correlation between target and output can arise from common regulators, cell-cycle state or compositional normalization. Negative correlation does not prove that knocking down the target increases the output. Use the 55,200 controls for a regularized state/module representation, expression gating and uncertainty; treat covariance-based direction as a separately tested weak prior. Avoid a full 18,533² float64 covariance matrix (~2.75 GB); use incremental low-rank modules or target-to-output blocks. Fit nuisance adjustments on the training split and do not automatically regress out genuine biological responses.

Validation must separate three questions: held-out target, held-out donor/study, and held-out lineage. Split whole perturbation targets and guides, not random cells from the same perturbation into both train and test. For CD4, compare resting and stimulated effects and test held-out donors. For essential screens, compare shared target responses across Jurkat/HepG2/RPE1/K562; flag their essential-gene selection bias relative to the official panel. For H1, freeze an outer test set before tuning. Use NTC-vs-NTC pseudo-perturbations to measure false-positive behavior, but never mistake this for a response-prediction benchmark. Retain weak/null targets and bootstrap targets, guides or donors rather than claiming millions of cells are independent replicates.

**Context C needs a branch that challenges the modality-only rule.** Orion HCT116 is a colorectal epithelial line, not squamous; RPE1 is not an exact match either. Test shared response modules gated by C's expressed programs, while retaining a strongly shrunk baseline for unsupported effects. An accurately matched human keratinocyte knockout dataset could inform module identity despite being unsuitable for direct CRISPRi-amplitude pooling. Learn or validate a modality adapter; do not negate CRISPRa effects or assume CRISPRko equals stronger CRISPRi.

A targeted search found the primary human epidermal ADGRL2 study. However, its cited **GSE281860**, while live and public, currently exposes **guide-count/CRISPR-Flow files**, not the promised Perturb-seq RNA matrix in the series listing. This is another accession/readout mismatch: keep it as a follow-up lead, not a ready RNA training source. The literature supports investigating this route, not claiming a verified squamous CRISPRi dataset has been found. [Primary study](https://pmc.ncbi.nlm.nih.gov/articles/PMC11888183/), [Live GEO record](https://www.ncbi.nlm.nih.gov/geo/query/acc.cgi?acc=GSE281860).

**5. Ranked actions and concrete implementation**

1. **Now, existing disk:** use `panel_coverage.csv` to select supported targets and assess low-cell coverage; preserve local NTCs and gene order. Recompute strict-control transfer diagnostics and run the five aggregate baselines before choosing an external fine-tuning architecture. The current task has audited their inputs, not trained these models or completed the H1 benchmark.
2. **Next anonymous acquisition:** CD4 selected pseudobulk rows for panel targets plus donor/condition-matched NTCs. Start with resting, then add stimulated conditions only as separate sources. Retain guide metadata and author QC annotations. Fetch enough biological replication before simply increasing cells per guide. Plan approximately 297 × 18,129 × 4 bytes = 21.5 MB per dense float32 context-level effect matrix, plus masks/uncertainty; do not store all aggregate rows densely at once.
3. **Next complementary source:** Orion HCT116 metadata projection across shards, followed by selected count acquisition with explicit I/O caps. Library coverage is 300/300, but usable coverage needs aggregated observed counts and guide QC. Scan one shard at a time; use the public tutorial as schema documentation, not its `streaming=False` full-download recipe. Consider releasing a small controlled number of whole shards locally only when the download/processing disk budget is demonstrated.
4. **Benchmark acquisition:** bounded raw-cell subsets from Jurkat/HepG2 and RPE1; obtain H1 RNA through its verified official route when available. These acquisitions test whether calibration and source weighting work; they are not new direct panel coverage. Do not download all three 5.6–9.4 GB dense files together on this disk.
5. **Explicit user sign-off before expansion:** paid cloud compute/storage/egress, a new large disk, or full-atlas acquisition. No cloud job, paid service or full-atlas download has been started. Check Xaira license and competition external-data/publication conditions before using its outputs in a submission or redistributing derived assets; the license is recorded, eligibility has not been certified here.

**Rejected for the direct CRISPRi-count training pool:** Pisces today (no matrices); Figshare 20022944 as an H5AD source (wrong artifact); normalized RPE1 as raw counts; GSE281860 guide counts as RNA; Norman 2019 as interchangeable CRISPRi (CRISPRa and combination design); the report's “Datlinger in vivo” attribution without a resolved study. The cited TNF epithelial paper is **Renz et al., 2024**, a mouse in-vivo context, adding species/environment shifts as well as modality differences. Reject naive pooling, not all possible auxiliary biological uses. K562 genome-wide is **not** definitively rejected: its existing coverage warrants a controlled ablation. [Norman primary study](https://pmc.ncbi.nlm.nih.gov/articles/PMC6746554/), [Renz primary study](https://www.nature.com/articles/s41586-024-07663-y).

**Executable artifacts and evidence**

`configs/candidate_ingestion.json` records the source decisions, exact NTC predicates, model grids and proposed resource policy. It is a plan/configuration manifest, not a claim that a training runner has consumed it. Scripts added in this session:

| Script | Function | Verification |
|---|---|---|
| 20_verify_candidate_accessions.py | Bounded public metadata snapshots, dates, hashes, sizes | Executed against GEO, HF, Figshare, GitHub and S3 |
| 21_probe_remote_h5ad.py | Remote HDF5 schema/count probes and target/NTC census | Executed for four single-cell sources and CD4 pseudobulk |
| 22_fetch_candidate_annotations.py | Explicit small guide/gene annotations with hashes | Executed |
| 23_probe_orion.py | Parquet metadata projection plus bounded HF count sample | Executed |
| 24_scorer_clamp_check.py | Installed 0.16.0 numeric score-floor check | Executed; assertions passed |
| 25_ingest_cd4_pilot.py | Curated, guide/lane-stratified raw-count extraction | Executed: 32 NTC + 16 STAT6 + 16 VIM; full output readback passed |
| 26_candidate_coverage.py | Per-target CSV and summary; design vs observed distinction | Executed |

Run from `C:/Users/ferra/OneDrive/Desktop/vcc2026`:

```powershell
.\scripts\py.cmd scripts/26_candidate_coverage.py
.\scripts\py.cmd scripts/24_scorer_clamp_check.py
.\scripts\py.cmd -m unittest discover -s tests -v
# New output path required; existing pilot is protected against overwrite.
.\scripts\py.cmd scripts/25_ingest_cd4_pilot.py --targets VIM STAT6 --cells-per-target 16 --ntc 32 --max-mib 128 --out reports/candidate_verification/pilot/cd4_replication.h5ad
```

The HTTP reader's four tests cover range access/cache/EOF, refusal of a full-download response, cumulative byte budgets and short files/invalid seeks. PyArrow 25.0.1 was installed only in ignored `.runtime-deps` for the Orion probe. Source matrices remain remote except for the 64-cell pilot. Evidence lives in `reports/candidate_verification`; original prior audits remain available for comparison. Pending work is explicitly separated from tested ingestion: no claimed model improvement, full-atlas validation or completed competition benchmark follows from these probes.
