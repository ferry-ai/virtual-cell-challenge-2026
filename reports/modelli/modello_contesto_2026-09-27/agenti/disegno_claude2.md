# Disegno di un modello bersaglio × contesto: claude2

Rapporto integrale di claude2 (base di lancio, run `20260927-140821-v2-target-context-design`, Opus 5.5 con sforzo massimo, sola lettura con ricerca web, brief `v2-claude2-target-context-design.md`), copiato il 27 settembre senza modifiche. Le affermazioni di letteratura sono in verifica da grok.

Outcome: I have a design ready — one context-gated version of the current same-target transfer, with about six parameters shared by every context, plus its comparison set and a test for context use that can be registered before running. No published model has predicted the target × context interaction for a cell line it has only seen as controls, so the expected gain is small, and whether the model really uses the context must be decided by a test on the difference between two held-out contexts, not by the score alone.

**How I worked.** Read mode; I wrote no file, so this message is the `result.md` content. I read PROGETTO §0, GENERALIZZAZIONE, D-044, the R-V2 card, the atlas, biology, pseudocount, new-target, contexts, learned-transfer, shared-share, EB, cis and t23-ablation reports, the source cards and searches, the relevant REGISTRO rows, codex's 27/09 review, `scripts/105_ctj_bench.py` and `src/vcc2026/ctj.py`. Bash and PowerShell were denied, so I inventoried the data root with Glob only. The literature comes from web search and the fetch tool, which returns a model-written summary of each page: re-check numbers on the PDFs before building on them.

**Labels.**
- **measured**: a project file I read, or a Glob count.
- **published**: a paper. *R* = I read the primary page through the fetch tool; *A* = only through a project agent report; *S* = search snippet only.
- **inferred**, **proposal**, **unverified**: as in the brief.

---

## 1. Literature

### 1.1 What changes a knockdown's response between cell types
These are all descriptive comparisons; none is a prediction.

- **Line and lab matter far more than cell state.**
  - Published (A): median r between K562 day 6 and day 8 is 0.50; between K562 and RPE1 it is 0.23 ([Replogle 2022](https://pmc.ncbi.nlm.nih.gov/articles/PMC9380471/)).
  - Measured, same targets, cosine not corrected for noise (`reports/atlante_2026-09-26/RISULTATI.md`, "Linea, laboratorio e stato"):
    - CD4 states against each other: 0.20–0.25;
    - two K562 experiments: 0.16;
    - another line from the same lab: ≈0.07;
    - another line from another lab: 0.02–0.03.
- **Target class decides what transfers.**
  - Published (R): ~8% of CD4 trans-effects recur in K562 over 3,081 shared perturbations, mean r 0.32. The best-conserved targets are housekeeping: transcription, chromatin, telomere, cell cycle ([Zhu…Marson 2025](https://www.biorxiv.org/content/10.64898/2025.12.23.696273v1.full)).
  - Published (R): 56% of essential perturbations correlate highly in all four lines; 44% only within similar pairs (0.61 within, 0.35 across) ([Nadig 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC11244993/)).
  - Published (R): perturbations strong in every context are OXPHOS; context-restricted ones sit in identity pathways ([X-Cell preprint 2026](https://www.biorxiv.org/content/10.64898/2026.03.18.712807v1.full)).
  - Measured: K562→CD4 transfer is highest for Mediator, TFIID and the mitochondrial ribosome; cytosolic ribosome and proteasome are ≈0 (atlas `condivisione_r1/`).
- **Pathway state.**
  - Published (A): IFN programmes are conserved across six lines; TGFβ and insulin are line-specific ([Jiang 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC12083445/)).
  - Measured: STAT2 is predicted from the other lines at r 0.53–0.71 under IFNB and ≈0 under IFNG, on the same genes (`reports/biologia_architetture_2026-09-25/RISULTATI.md` §2).
- **p53 status, growth mode, generic stress.**
  - Published (R): the similar pairs share p53 status and growth mode (Nadig, authors' interpretation).
  - Published (R): p53 and lysosome programmes respond to almost every perturbation; mitochondrial knockdowns induce the ISR in K562 but not in RPE1 ([Pan 2026](https://www.biorxiv.org/content/10.64898/2026.05.16.725005v1.full)).
  - Measured: weighting sources by p53 state does not help (`reports/contesti_2026-09-26/` r2; registry status *da-verificare*).
- **Target strength and expression.**
  - Published (R): essential (4.22×), highly expressed (2.26×) and constrained (1.57×) targets are enriched for large impact (Nadig).
  - Published (R): 30.5% of K562 perturbations have more than 10 DE genes ([Replogle bioRxiv](https://www.biorxiv.org/content/10.1101/2021.12.16.473013v1.full)).
- **Knockdown efficacy.**
  - Published (R): median knockdown 85.5% in K562 vs 91.6% in RPE1, with different KRAB effectors (Replogle).
  - Published (A): 75.4% in HCT116 vs 51.5% in HEK293T with the same effector ([Orion](https://www.biorxiv.org/content/10.1101/2025.06.11.659105v1.full.pdf)).
- **Basal-state distance: open contradiction.**
  - Published (R): a perturbation's shift becomes less similar as the starting states grow apart (Pan 2026, Fig. 4A, qualitative).
  - Measured: whole-profile DepMap similarity does not predict transfer among six Mixscale lines (Mantel +0.08, p 0.43; *da-verificare*).
- **How big the interaction is.**
  - Published (R): in the K562/RPE1/HepG2/Jurkat essential screens, reproducible variance splits into line template 27.8%, conserved effect 29.4%, line × perturbation interaction 23.5% and noise 19.3%. The template can be inferred from controls; no zero-shot model recovered the interaction ([Molina & Zhang 2026](https://www.biorxiv.org/content/10.64898/2026.07.24.740459v1.full)).
  - Measured: two disjoint CD4 donor groups agree at a median r of only 0.084, with 35% opposite signs among pairs with |z| ≥ 2 (`biologia…/RISULTATI.md` §5).

### 1.2 Models tested out of sample
Regimes as in GENERALIZZAZIONE: C, T, J. "Mixed" means the target was measured in another line while the test line contributes other perturbations to training.

| Paper | Regime | Result (metric) | Simple baseline beaten? | Read |
|---|---|---|---|---|
| [Ahlmann-Eltze, Nat Methods 2025](https://www.biorxiv.org/content/10.1101/2024.09.16.613342v5.full) | T; mixed | No deep or foundation model beat the mean, additive or linear baselines (L2, Pearson Δ). A linear model with perturbation embeddings from **another line's perturbation data** (K562↔RPE1) was best | Deep models: no. Cross-line linear: yes | R |
| [TxPert, arXiv / Nat Biotech 2026](https://arxiv.org/html/2505.14919v1) | C: one of four lines held out, its controls available | Beat the "general baseline" in all four lines (Pearson Δ). For seen perturbations that baseline is the test-line control mean plus the perturbation's mean change in training, i.e. a same-target transfer | Yes, per the authors. Numbers are only in Fig. 3C, which I could not read. Its graphs include proprietary screens "in various cell types", so held-out-line leakage cannot be ruled out | R |
| [X-Cell, bioRxiv 2026](https://www.biorxiv.org/content/10.64898/2026.03.18.712807v1.full) | C, zero-shot: held-out progenitors from the same iPSC screen; primary CD4 T cells (291 perturbations) | Beat the perturbation mean, an additive Jurkat transfer, State and scGPT on Pearson Δ and DE direction | Yes, per the authors. Numbers only in figures; 4.9B parameters | R |
| [Molina & Zhang, bioRxiv 2026](https://www.biorxiv.org/content/10.64898/2026.07.24.740459v1.full) | T, C, J | A ridge or MLP from DepMap co-essentiality to response PCs recovers the conserved component (r 0.25–0.39 across lines) and stays positive when both target and line are new. It does not recover the interaction | Beats State, MORPH, scGPT; I did not verify it against the mean | R |
| [State, bioRxiv 2025](https://www.biorxiv.org/content/10.1101/2025.06.26.661135v2.full) | Mixed: 30% of the held-out line's perturbations in training | Discrimination equal to the perturbation-mean baseline; the linear model was +20% on DE overlap and the context mean +12% on fold change. Zero-shot it only ranks perturbation strength (Spearman > 0.5) | Mostly no | R |
| [LPM, Nat Comput Sci 2025](https://arxiv.org/html/2503.23535v1) | Mixed | The authors state an "inability to extrapolate to unseen contexts in a zero-shot manner" | — | R |
| [PerturBench](https://arxiv.org/html/2408.10609) | C ("covariate transfer"), includes Mixscale | Simple models are competitive. On Mixscale a decoder with no perturbation input scored best on average-response cosine but at chance on rank metrics | No | R |
| [bioRxiv 2024.12.23.630036](https://www.biorxiv.org/content/10.1101/2024.12.23.630036v1.full); [scPerturBench](https://github.com/bm2-lab/scPerturBench) | C, stimuli in PBMC types | scGen and trVAE beat the baseline; accuracy falls with cell-type dissimilarity. The genetic cross-line case was "limited" by lack of data | Stimuli yes; genetic untested | R (I did not confirm the two are the same study) |
| [Mao, arXiv 2026](https://arxiv.org/abs/2604.27646) | C, T, cross-dataset | Performance "drops markedly" under strict evaluation; linear is comparable; pooling datasets can hurt | No | R (abstract) |
| [Systema, Nat Biotech 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC13271886/) | T | The perturbed-mean baseline beats the methods on standard metrics | No | R |
| [Csendes, BMC Genomics 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC12016270/) | T | The training mean beats scGPT (K562 Pearson Δ 0.373 vs 0.327); a random forest on GO terms reaches 0.480 | GO forest: yes | R |
| [Kernfeld, Genome Biol 2025](https://pmc.ncbi.nlm.nih.gov/articles/PMC12621394/) | T; GRN forecasting | "the mean or median baseline was almost always the top performer"; cell-type-specific networks gave no clear gain | No | R |
| [GEARS, Nat Biotech 2024](https://www.nature.com/articles/s41587-023-01905-6) | T and combinations, one line | Beaten by linear baselines in Ahlmann-Eltze | No | S |
| [VCC 2025 wrap-up](https://arcinstitute.org/news/virtual-cell-challenge-2025-wrap-up) | T, one context | "Purely AI-based approaches did not consistently outperform statistical baselines"; almost all models were worse than the baseline on MAE | Mixed | R |
| [Stable-Shift, arXiv 2026](https://arxiv.org/abs/2606.24940) | T, K562 | Cosine 0.592 vs 0.569 for GEARS | Mean and linear not reported | R (abstract) |

**Where the evidence is thin (inferred):**
- Every cross-line CRISPRi test uses the essential screens of Replogle and Nadig (one lab, by authorship) or proprietary Xaira data. Our panel has 0/300 essential targets. Essential targets have about twice the energy and transfer better: energy 29.5 vs 14.5, K562×CD4 cosine 0.022 vs 0.008 (measured, atlas amendment of 20:05).
- Nothing published tests the VCC regime: non-essential targets, a new line from another lab, Flex chemistry, scored with PDS and the DE metrics.
- The positive C-regime claims come from industry with figure-only numbers; the only result with both target and line new is a preprint.
- The metrics are Pearson Δ; here a model that correlated better still lost `pds_cosine` (CP-0026).

## 2. Features computable offline
Local presence checked with Glob (measured). "D/E/F" = computable from the controls alone; "new target" = computable for a gene never perturbed.

**Context features — all computable for D/E/F**

| Feature | Source | Evidence it matters |
|---|---|---|
| Expression of each response gene in the context, as a within-context rank | `raw/controls/context_*.h5ad`; `processed/basal_sources_2026-09-26.csv`; control rows of `external/*_raw_bulk_01.h5ad`; `raw/nadig_hepg2/…h5ad` | 72% of t22's energy sits on genes not expressed in the context (measured, pseudocount report); Nadig (A) |
| Expression of the target | same files | Nadig 2.26× (R). But 288/300 panel targets are above 5 CPM in all three contexts (measured, PROGETTO §3), so there is little variation on today's panel |
| Expression of the target's cis neighbours | GENCODE v50 (local) + controls | the cis head has no context term yet (`modulo_cis…`) |
| Programme activity: IFN, p53, E2F/G2M, UPR, ISR/ATF4, cholesterol, OXPHOS, NF-κB, hypoxia | gene sets from local GO (`interim/encoder_inputs_2026-09-14/goa_human_gaf`, `go_basic_obo`) | Jiang, Pan; STAT2 (measured) |
| Per-gene Flex vs 3′/5′ offset | VIPerturb-seq, Zenodo 18460279, 3.61 GB, CC-BY-4.0 (verified in `ricerca_sorgenti_2026-09-25`) | A/B/C are Flex, the sources are not (CP-0028) |
| DepMap features of the line itself | **not used**: it would mean identifying the line | privacy rule |

**Target features — all computable for a new target**

| Feature | Source | Evidence |
|---|---|---|
| TSS neighbours and bidirectional pairs | GENCODE, `k562_neighbour_pairs.csv` (local) | cis head: +0.0012…+0.0048 PDS through the generator (measured) |
| STRING physical partners | `string_physical_links.gz` (local) | 0.1 × STRING + cis beats cis alone by +0.009…+0.035 (measured, `bersagli_nuovi`) |
| Complex or family membership | HGNC groups (local), or CORUM 5.1 (Zenodo 17419058, 26.4 MB, CC BY 4.0, verified) | Mediator/TFIID transfer (measured) |
| DepMap co-expression profile | `external/depmap_24q4/…TPMLogp1.csv` (local, 507 MB) | my stand-in for co-essentiality: untested |
| DepMap co-essentiality; common-essential flag | `CRISPRGeneEffect.csv` 428,678,699 B and `CRISPRInferredCommonEssentials.csv` 20,795 B; DepMap 24Q4 Figshare+, CC BY 4.0 (verified via API) | Molina & Zhang (R); Nadig 4.22× (R) |
| Expression breadth across DepMap lines (housekeeping index) | local DepMap | Zhu, X-Cell (R) |
| GO terms | local | Csendes (R) says they help; D-028 (GO slim did no better than permuted labels) says not. Open |
| GenePT text embeddings | Zenodo 10833191, 574.4 MB, CC-BY-4.0 (verified) | only as an ablation |

CollecTRI, Hallmark and protein embeddings are **not proposed**: I could not verify their size or licence.

**Target–gene features**
- Same-target pooled effect from the universes (measured): K562 9,866 targets, CD4 12,238, HCT116 16,438, HEK293T 17,270, K562-essential 2,057, RPE1 2,393.
- Per-gene shared share ρ(g) (measured): passes the panel rule on 3 of 4 held-out sources; it flattens when both Orion lines enter the estimate (atlas r2).

**Gaps (measured):**
- The CD4 and Orion universes carry the pseudocount artefact; `universo_corretto_2026-09-27/rebuild.py` has not been run yet.
- HepG2 exists only as an h5ad, not as a stage-98 cache. The Nadig Jurkat and Song Jurkat matrices are not local.
- DLD-1 and Mixscale have no basal profiles.
- The K562 column of `basal_sources` has NaN values (for example TSPAN6), but stage 105 requires finite basal values on the whole axis.

## 3. The model: a gated conserved-effect model (proposal)

**ŷ(t,g,c) = A · s(t,c) · h(g,c) · m(t,g) + k(t,g,c)**

- **m, the conserved effect.**
  - For a measured target: the production transfer, unchanged (t25 form, corrected estimator). Any difference from the current transfer therefore comes from the gates.
  - For a target no source measured: λ_S·(mean effect of its STRING partners, each partner's own gene excluded) + λ_D·V·R·φ(t). Here φ is the target's 50-PC DepMap profile, V the top response PCs of the training data, and R a ridge map from one to the other (the Molina & Zhang recipe).
- **s, amplitude of the target in the context:** exp(α1·Δℓ_t − α2·softplus(ℓ_min − ℓ_t,c) − α3·(1 − H_t)·D(c, S_t)).
  - Δℓ_t = the target's expression in the context minus its mean in the sources.
  - H_t = housekeeping index; D = basal distance between the context and the sources that measured t.
  - Hypothesis: a knockdown does less where the target is less expressed, and lineage-restricted targets lose transfer as contexts diverge. Basal distance enters only through this interaction, which is what H6 left open.
  - s only rescales each target, so it moves the DE metrics and nMAE, not the cosine PDS.
- **h, gene gate in the context:** 2σ(β1·Δℓ_g + β2·Σ_k P_gk·Δa_k + β3·logit ρ̃_g).
  - P_gk = membership of gene g in programme k; Δa_k = programme activity in the context minus the sources.
  - ρ̃ = the shared share, with genes the universes cannot estimate set to the median plus an indicator. t23 sets 8,247 such genes to 0, which confuses "not estimable" with "not shared".
  - h = 1 when the context looks like the sources; β3 alone reproduces t23, so t23 is a special case of this model.
- **k, cis head:** the production cis head × 1[the neighbour is expressed in the context].
- **A:** as D-042 (official score). A separate amplitude for predicted-only targets, calibrated on the new-target (T) validation folds.

**Shared vs context-specific.** About six shared parameters (α, β) plus λ, R and V. The context enters only as inputs read from its controls (and through A); nothing is learned per context. That avoids learning a vector per context, which failed with two training contexts (CP-0013, CP-0026) and which LPM names as its own limit.

**Fitting.**
- Weighted least squares on effects with each source's mean response removed, only where the labels are finite.
- Weights: the stage-105 gene weight × 1/(SE² + τ²_family).
- L2 penalty pulling the parameters back to the plain transfer, tuned by leaving one family out inside the training set.
- Training families with their own controls: K562 (genome-wide and essential), RPE1, HepG2, CD4 (three states as one family), Orion (two lines as one family).

**Unmeasured values are never zero.**
- A missing label is masked (D-009).
- For a measured target, a gene that no source measured takes the prior at its own reliability, flagged; otherwise it stays NaN and emission applies an explicit "no change" rule.
- A missing feature gets an indicator and is imputed; never 0 CPM.
- Inferred: with 16–17k targets in the Orion universes, most final-set targets will be measured somewhere (regime C).

**Comparison set.**
- **M0:** the current transfer — t25 form, and t23 as a second reference. When target and line are both new (J), the current fallback: cis + 0.1 × STRING.
- **M1-lin:** the same inputs in a linear form, A·m·(1 + γᵀx) + k with ridge, plus stage 105's `context_linear` (`src/vcc2026/ctj.py:175`).
- **M1-blind:** every context feature set to the average of the training sources, so every context gets the same profile.
- **M1-perm:** programmes, housekeeping index and DepMap rows permuted within expression deciles; STRING rewired preserving degree.
- **M1-swap:** another context's controls given at prediction.
- **null** and **common**, as in stage 105.

**Evidence that the model uses the context (register before running).**
- **E1:** M1 − M1-blind > 0 on at least 3 of 4 held-out families, with the interval above zero on at least 2 and no interval wholly below −0.002. Measured both as effect-space PDS and as 0.36·ΔPDS − 0.27·ΔnMAE through the generator. The same rule applies to M1 vs M0 before saying it beats the transfer.
- **E2 (decisive):** hold out two contexts together and correlate the predicted difference between them with the observed difference, per target, on trans genes only (genes within 5 kb of the target excluded):
  - HCT116 vs HEK293T;
  - CD4 Rest vs Stim48hr;
  - essential Replogle/Nadig lines, reported separately.
  The weighted correlation must be above 0, with the interval above 0, and above M1-perm. M0 and M1-blind give exactly 0 by construction. Report against a split-half ceiling.
- **E3 (supporting only):** the loss under swapped controls grows with basal distance.
- **How to read it:**
  - E1 without E2 means gene re-weighting (t23-like), not a target × context effect.
  - E2 without E1 means the context is used but the metrics do not reward it.
  - Expected result (inferred): E2 small or null.

## 4. Leakage, input by input

| Input | How it leaks | Prevention |
|---|---|---|
| m (same-target transfer) | The held-out line comes back through another experiment of the same line (K562 genome-wide ↔ essential), shared donors (CD4 states and halves) or a shared lab (the two Orion lines; the Replogle/Nadig lines). For new targets: aliases, ENSG duplicates, other guides | Exclude whole families; label "new line, same lab" separately. Drop new targets by ENSG and alias from every source |
| CRISPRi neighbours | A training target within ~5 kb of a test target represses it, so its profile carries the test knockdown (inferred from Replogle and Zhu) | Put such pairs in the same fold |
| Mean-response removal, shrinkage, SE calibration | Centres computed before splitting carry test targets (R-019) | Compute inside each fold |
| ρ(g), V, R | Estimated with the held-out family or test targets | Re-estimate per fold, one line per lab |
| α, β, λ, penalties | Selected on the test family | Nested family-grouped validation; freeze before testing |
| Basal features | Normalisation, expressed-gene lists or programmes built from the held-out context's perturbed cells | Controls only; programmes from GO or training folds |
| STRING partner mean | Partners measured in the held-out context, or partners that are test targets | Training families and targets only |
| DepMap | Viability, not transcriptional outcomes, so admissible for targets (GENERALIZZAZIONE §3.5) | Target-level use only, declared; no per-line use |
| Graphs or features derived from perturbation data | Contain test targets' outcomes | Rebuild within each fold, or omit |
| GO (IMP evidence), GenePT | Literature about the gene's own knockdown | Declare; run an ablation without them |
| Complex partners and paralogues | Siblings fall on both sides of a random target split | Also report folds grouped by HGNC/CORUM group |
| Test targets and amplitude | Selecting strong knockdowns; tuning A on the test family | Sample blind to effects and exclude or stratify essential targets (D-011); fix A a priori and report energy |

## 5. What I would build first
- **Model:** the gated model restricted to basal expression — α1, α2 (target expression) and β1, β3 (gene expression, shared share) on the unchanged t25 transfer and cis head. Four parameters, local inputs, no download.
- **Why:** controls are all D/E/F give us. Four shared parameters can be identified from 4–7 families, whereas per-context vectors failed. It contains t23 as a special case, so any gain can be attributed. Codex's review already queued a basal-expression test.
- **Experiment:** the atlas harness on the corrected universes — 1,000 held-out non-panel, non-essential targets per family, whole family excluded.
  - Arms: t25-like, t23-like, M1-basal, M1-basal-blind, M1-basal-swap.
  - Rule E1 + E2 (HCT116 vs HEK293T; CD4 Rest vs Stim48hr), registered before running.
- **Reading:**
  - E1 and E2 pass → add programme activity and target class, then the new-target-and-line (J) regime.
  - E1 only → call it re-weighting.
  - Neither → the signal readable from controls is below the noise, and the work goes to coverage.

## 6. Not done, and open questions for Claude1
- **Not done:** no code run and no file written. Pages behind reCAPTCHA or 403 were not read: Replogle on PMC, TxPert in Nat Biotech, the organizers' VCC 2026 paper in Cell ([link](https://www.cell.com/cell/fulltext/S0092-8674(26)00931-1)) — the Cell paper may report their own zero-shot baselines and is worth a manual read. Figure-only numbers (TxPert, X-Cell) are not extracted. I could not verify the OP3 winners against the per-compound mean.
- **Unverified:** the "genes that differed more between K562 and RPE1 were less accurately predicted" sentence in Ahlmann-Eltze. The fetch summary said these are the perturbed genes, but I could not confirm whether it means perturbed or readout genes. A memory note mentions de-noised cross-line correlations from session 76a3a45e (K562–RPE1 0.42, RPE1–HepG2 0.75); they exist only in that session's scratchpad, not in the repository, and would be worth transcribing.
- **Prerequisites:**
  - run `universo_corretto_2026-09-27/rebuild.py` for the corrected universes;
  - build a complete K562 basal vector;
  - build a HepG2 cache.
- **Owner decisions:**
  - downloads: CRISPRGeneEffect (428.7 MB), CORUM (26.4 MB), VIPerturb-seq (3.61 GB);
  - whether to align Flex against 3′ beyond rank transforms;
  - DepMap features of the context's own line (these would identify it).
- **Open contradictions to record:** Pan's state-distance result against H6; GO helping in Csendes against D-028.
