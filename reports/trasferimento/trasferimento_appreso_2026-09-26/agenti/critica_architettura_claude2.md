I read the bench and the four reports; the report follows.

# Report: critique and redesign of the learned transfer bench (`lct_bench.py`)

I found eight more problems besides the two known leaks. Four of them bias the comparison toward the learned model: labels that keep the common response, the MSE comparison, K562 priors when K562 is held out, and target-identifying features. So the r1 result can't be read as "the learned model beats t20". For the v2 design I recommend a model with few parameters, per-target amplitudes and a separate calibration per scored member, rather than a per-(target, gene) gradient-boosting model.

## 1. What else makes the comparison unfair or misleading

Beyond the two known leaks:

**a. The labels keep the common response; the features and the t20like arm do not.** *Measured* by reading the code.
- `y = truth.raw` is not centred (`lct_bench.py:158`).
- `m_raw`/`m_shr` come from `mix(..., gamma=1.0)`, which subtracts each source's `common()` (`lct_bench.py:98-99`; `multisource.py:231-243`).
- So only the learned model can learn the held-out source's mean response across targets. `gene_common` is a direct feature for that (`lct_bench.py:86`).
- *Inferred:* this mostly helps `mse_ratio` against "no change", and it can move the PDS proxy either way. The official `mse` zero point is the mean-perturbation baseline, which already contains that common response. So this gain would not carry over.
- Fix: centre the labels by the held-out source's `common()`, or give both arms the same common term.

**b. When K562 is held out, it shares far more than "context" with the features.** *Measured* from the code.
- `gene_common`, `gene_resp` and `gene_spread` are K562's own mean, hit-rate and spread over the ~9.6k non-panel targets (`lct_bench.py:68-87`). With uncentred labels (a), `gene_common` is almost exactly the label's common component.
- The docstring (`lct_bench.py:26-27`) understates this.
- *Inferred:* the K562 task is not credible. Drop it, or build these gene priors from a family other than the held-out one.

**c. `mse_ratio` compares arms at different amplitudes.**
- The fixed arms use amplitudes tuned for the DE members: 0.788 and 1.576 (`lct_bench.py:235-236`).
- The learned model is a conditional mean under squared loss, so it sits near the amplitude that minimises squared error. `reports/banco_varianti_2026-09-25/MSE.md:21-24` measured that amplitude at 0.02–0.16 and the fixed arms' ratios at 1.07–1.45. *Measured.*
- *Inferred:* the learned model "winning" on MSE is automatic. Compare every arm at its own optimal amplitude, or at the same per-target norm.
- The PDS proxy, reach and prec_200 are per-target scale-invariant, so they are fair on this point. The official DE members are not: a model that predicts shrunken values calls far fewer genes once cells are generated.

**d. The model can identify a target, or a gene, from constant features.** *Measured.*
- `target_strength` and `target_expr` are the same for every gene of a target; the `gene_*` priors and `expr_*` are the same for every target of a gene (`lct_bench.py:137-157`).
- With 63 leaves and up to 400 iterations, the model can memorise target × gene cells from other tasks' labels on the same 300 targets.
- *Inferred:* target-disjoint folds fix the evaluation. For deployment on new targets, `target_strength` does not exist anyway (no source measured the target), so it should not be a feature of the new-target model at all.

**e. Early stopping picks rows at random.** *Measured* (`validation_fraction=0.1`, `lct_bench.py:223-225`). The validation rows share targets and tasks with the training rows, so stopping is chosen on memorisable rows. Use a validation split grouped by target, or by task.

**f. t20like is not t20.** *Measured.*
- `configs/recipes/t20.json:8-10` pools K562, CD4 and HCT116 only.
- The bench pools every other-family source, HEK293T included, which t17 could not attribute (CP-0038).
- The shrinkage and reliability settings go through `mix` with the default settings rather than the recipe; I did not diff them line by line.

**g. The training objective and the evaluation weights disagree.** *Measured.*
- Training uses squared loss on raw effects clipped at ±4, weighted by (x/(1+x))² from the held-out context's CPM, with no per-pair SE (`lct_bench.py:159-161, 212`).
- The PDS proxy weights genes by A/B/C CPM (`lct_bench.py:190-192`).
- *Inferred:* raw labels from targets with few cells are noisy, and nothing downweights them. The loss is not a ranking loss, so better squared error need not mean better PDS; the programs projection showed the two can split (`programmi_2026-09-26/RISULTATI.md:41-43`).

**h. The inference machinery is weak and some features won't transfer.**
- *Measured:* one model fit per task, no seed or subsample variance; the bootstrap is over targets only. The two Orion tasks share one family, so four tasks are about three independent tests.
- *Inferred, carry-over risk:* `expr_ctx`/`expr_src` are percentiles from 10x 3′ sources and CD4, while A/B/C and D/E/F are 10x Flex probe data (memory note). The model learns what expression percentile means on one platform and applies it on another.
- *Measured:* `cd4_mix` basal is a mean of three conditions (`basal_profiles.py:83`). That is not one cell state, so the CD4 task's context features blur Rest and Stim.

## 2. Proposed v2: a hierarchical model with few parameters, calibrated per member

**Evidence for the principle.** Each of these is *measured* on proxies. What carried over was noise reduction and low-parameter mechanism: more sources (CD4 +0.0102, CP-0030), the shrinkage restriction, and the cis prior fitted off-panel (positive on every held-out source, shuffled control at zero). What failed was anything fitted on context structure:
- weighting sources by basal similarity (H6: Mantel +0.08 with p = 0.43; loses on 4 of 6 lines);
- projection on shared programs (every rank loses);
- the linear gene-embedding model (0.50 even on its own training targets).

With 4–10 source contexts, any parameter that varies by context is estimated from 4–10 points. A 19-feature GBM per (target, gene) cannot carry over to Flex D/E/F; a model with about 10 global parameters can.

**The model.** For target t, gene g, context c:

`ŷ = s_t(c) · h_g(c) · μ_tg + cis_tg + [fallback_tg, for targets no source measured]`

1. **μ_tg: random-effects meta-analysis across sources** (proposal). Use effect ± SE per source, in the scorer's own space (log1p of the pseudobulk at 5·10⁴). Weight each source by 1/(SE² + τ_s²), with the heterogeneity τ_s² estimated per source (or per gene-expression bin) from leave-one-source-out residuals. This replaces the cells-based reliability plus one global shrinkage.
   - It also gives a posterior variance v_tg, which drives the call decision in 4.
   - *Expected to matter most for PDS*, because PDS gains so far came from noise reduction.
   - Parameters: about 4–8.

2. **s_t(c): per-target amplitude, read from the new context's control cells** (proposal; I expect this matters most for the DE members).
   - Inputs: the target's expression in c from its controls, the median number of DE genes across sources, knockdown efficiency, and the own-gene effect in the sources.
   - Fit: a monotone GAM or isotonic regression predicting the held-out source's per-target DE count or norm; about 300 targets × contexts rows, target-disjoint.
   - Why: CRISPRi of a gene not expressed in c should do almost nothing except cis. The scorer notes say 12–30% of targets in val A have fewer than 10 DE genes (CP-0039, *measured by the organizers*). The global amplitude calls hundreds of genes on those targets. Fidelity-yield scores the sign on every called gene, so those calls are near-coin-flips; *inferred:* they cost Jaccard, fidelity and nMAE.
   - Scale-invariant PDS is untouched, so this lever is almost free for the largest member.
   - *Unverified:* I found no bench of per-target amplitude by target expression. A grep only shows the idea at `docs/data_strategy_2026-09-11.md:98`.

3. **h_g(c): an expression gate per gene** (proposal). A two- or three-parameter logistic of the gene's log expression in c, adjusted for platform (quantile-matching Flex against 3′ on shared genes).
   - It damps predicted moves of genes with low detection in c.
   - It is fitted with a PDS-aligned loss (below).
   - *Hypothesis*; small expected gain.

4. **Calibration per member, not one amplitude** (proposal). Four separate knobs:
   - **Direction and ranking** (PDS, reach, fidelity): the sign and order of μ_tg divided by the square root of v_tg. Reach sorts by |prediction|, so the ordering should favour posterior confidence, not raw size.
   - **Magnitude** (mse, nMAE): the mean shift should be the Bayes-optimal shrink for squared loss, roughly ρ̂ × the norm.
     - *Inferred:* at the current accuracy the `mse` member stays at 0 whatever the amplitude. The optimal-amplitude ratio is 0.999, against an estimated baseline of 0.996 (`MSE.md:30-34`). So don't trade DE members for it, unless the HepG2 bench shows the true ρ is much higher than the noisy-truth proxy implies.
     - nMAE does need magnitudes near the truth on reference-significant genes.
   - **Call set** (Jaccard, fidelity): the call set for each target should be the top-k genes by posterior probability of a nonzero effect, with k = the ŝ_t-predicted number of DE genes (val A averages about 340, heavily skewed).
   - **The emission step has to turn these into cells.** The call count depends on per-cell dispersion and on cells per target (the spec allows variable counts), not only on the mean shift.
     - *Measured:* trial-01's generator calls 543–764 genes per target (`dispersion_2026-09-23/RISULTATO_NULLO.md:18-19`). The dispersion-per-gene generator still makes 5–31 spurious calls per target at zero effect.
     - *Hypothesis:* part of t20's raw `mse` of 3.88 may be emission noise the capped correction does not remove (`cell_eval2/metrics/delta.py:981-988`). The decomposition should be measured on the HepG2 bench.
     - Using cell count or dispersion to decouple call count from mean shift is a scorer-structure lever. The organizers close such levers (#247, #348 in `delta.py`), so the owner should rule on it before anyone builds on it.

5. **Losses** (proposal).
   - PDS-facing parameters (τ_s, h_g): an InfoNCE/softmax loss over targets on weighted cosine, i.e. −log softmax_j(cos(P_i, T_j)/τ) at index i. This is directly the discrimination being ranked.
   - s_t: Poisson or ordinal loss on the held-out source's significant-gene count.
   - Magnitude: weighted squared error in the scorer's log1p geometry, with the "no change" (1.0) normalisation.
   - Train with leave-one-family-out × target-disjoint folds. Features for held-out targets are built with `exclude=` (as `partner_effects` already supports, `100_build_context_effects.py:133-141`).
   - Choose between models on the real scorer (the HepG2 F2 bench), with the rule registered first.

6. **Where learned capacity belongs: only the new-target fallback.**
   - There, a ranking-trained model on target descriptors (STRING, CORUM, TF edges; partners' K562 universe effects) plus the cis term can be tested against cis + 0.1 × STRING. That baseline scores 0.58–0.61 PDS proxy, against 0.71–0.75 for a measured target (`bersagli_nuovi/RISULTATI.md:37-49`).
   - Coverage beats modelling there: extract every CD4 and Orion target. *Measured gap; the conclusion is an interpretation.*
   - Arc's State conditions on control-cell sets across about 70 contexts (https://www.biorxiv.org/content/10.1101/2025.06.26.661135v1, code at https://github.com/ArcInstitute/state). With 4–10 contexts we cannot train that kind of conditioner. That is the argument for low-parameter conditioning.
   - Systema (https://www.nature.com/articles/s41587-025-02777-8) warns that systematic, common response inflates metrics. That supports centring labels and features (point 1a) and scoring on perturbation-specific signal.

**What contradicts or weakens this.**
- H6 says context similarity doesn't help, which also warns against h_g and s_t. They differ in being defined per target or per gene from biology (target expression), not as whole-profile similarity; H6's report leaves exactly that open (`contesti/RISULTATI.md:50-52`).
- Leaders at PDS 0.82–0.87 with `mse` 0.6–0.85 suggest a different information source, possibly data from the same lines (*hypothesis*, `modello-v2.md`). No architecture here closes that gap by itself.

## 3. The three cheapest experiments that would most reduce uncertainty

1. **Per-target amplitude from target expression, on the existing bench** (about an hour on CPU, no new data).
   - On the cis-bench loader, regress each held-out source's per-target norm or DE count (|z| ≥ 3) on target CPM in that context and source strength, target-disjoint.
   - Report the rank correlation, then reach, prec_200 and the call-count match against the global 1.576.
   - If the correlation is ≲ 0.2, drop s_t.

2. **Re-run `lct_bench` with the four controls from section 1.** Centred labels (a), K562 task dropped or its priors swapped (b), every arm at its own optimal amplitude plus matched per-target norm (c), t20like with the exact t20 sources (f).
   - Also compare against a four-parameter random-effects pooling baseline.
   - If the learned model doesn't beat that baseline on the PDS proxy with target-disjoint folds, the GBM is not worth deploying.

3. **Split `mse` and calls by cause on the HepG2 bench** (job 046 already queued; one extra arm).
   - Score t20 cells against the same effects emitted with half the dispersion or twice the cells, and at a 0.1 amplitude.
   - This tells us how much of the raw 3.88 is emission noise versus effect error, and whether call count can be tuned apart from the mean. That decides whether section 2.4 is real.

## Not done, and open questions
- I ran nothing: read-only mode, and Bash was denied. There are no r1 outputs in `reports/trasferimento_appreso_2026-09-26/r1/`, so I couldn't check the learned model's actual numbers.
- I did not trace every default of `mix` against the t20 recipe (shrink_k, `zshrink`).
- Open for the owner: is the emission lever in 2.4 (cells per target, dispersion) acceptable?
- Open: the `mse` baseline 0.996 is an estimate from two rows (`MSE.md:32`), not a measurement; the anchors only bound it at ≤ 1.231 (`anchors.json:135`).

Sources:
- [State, bioRxiv](https://www.biorxiv.org/content/10.1101/2025.06.26.661135v1)
- [ArcInstitute/state](https://github.com/ArcInstitute/state)
- [Systema, Nature Biotechnology](https://www.nature.com/articles/s41587-025-02777-8)
