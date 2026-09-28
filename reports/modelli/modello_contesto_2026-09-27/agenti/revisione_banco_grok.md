# Revisione di grok del banco del modello a cancelli

Rapporto integrale di grok (base di lancio, run `20260927-170939-v2-review-gated-bench`, grok-4.7, sola lettura, brief `v2-grok-review-gated-bench.md`), copiato il 27 settembre senza modifiche. Si riferisce alla prima versione di `gated_bench.py`, poi corretta punto per punto (vedi RISULTATI.md).

I'll review the gated benchmark driver against the leakage and metric rules, starting from the driver, the gated model, and the comparison code it imports.The family holdout and the rho exclusion hold, but the gates are fit on shrunken context features and at a different amplitude from the one used at test, and E1's PDS still contains each test target's own gene, so a positive result would not be trustworthy.

Read only: `gated_bench.py`, `gated.py`, `share_panel_bench.py` (full), and the imported pieces of `atlas_bench.py` (`family`, `Universe.table`, `blend`), plus `mix`, `cis_prior`/`add_cis`, `match_detectable`, `pds_proxy`, `realise`, `rank_pds`, and `boot`. Nothing was executed.

## 1. Leakage

**No — a held-out truth, and any row of the held-out family, does not reach rho, the fit labels, `a_fit`, or `m_h`.** **Yes — the test-target exclusion passed to `shared_share` is the right call.**

**Measured.** `family()` is `name.split("_")[0]` (`atlas_bench.py:82-83`), so both Orion lines are `"orion"` and `cd4_mix`, `cd4_Rest`, and `cd4_Stim48hr` are `"cd4"`. For each design, `train` is `TRAIN_SOURCES` with that family removed (`gated_bench.py:51`, `172-173`). `TRAIN_SOURCES` has no CD4 condition, so an E2 CD4 holdout also drops `cd4_mix`. Rho, fit rows, and `m_h` are read only from `train` (`185-186`, `201-209`, `233`).

**Measured.** `shared_share(unis, train, panel | tset, ...)` (`185-186`). Inside, estimation targets are those measured in at least two of `inputs` and absent from that set (`share_panel_bench.py:69-73`). Fit targets also drop `panel`, `tset`, and the essential screen (`gated_bench.py:201-205`). `a_fit` is a weighted product of those families' `y` and `m` only (`218-223`).

**Measured, narrow exception.** The cis head is not in that list, but it does enter the fit residual (`signal + k - y` in `gated.py:230`). `cis_prior` is built once, outside the loop, with only the VCC panel removed (`gated_bench.py:141`; `priors.py:20-23`), from `reports/cis_2026-09-17/k562_neighbour_pairs.csv` (`t22.json` cis block). The atlas refits per fold on `panel | test_set` (`atlas_bench.py:315`). Bin medians, not per-target vectors, are what get added (`predictor_sc.py:137-151`). On a K562 holdout those medians are held-out-family data, so they can move α, β. On every other holdout they are a training line. The same `k` is added to every arm (`238-242`, `245`), so it cancels in E1 differences and in E2.

**Smallest fix:** build `cis_model` inside the design loop as `cis_prior(pairs, sorted(panel | tset))`. That still leaves the rest of the K562 pairs in the K562 holdout; the pairs file has no other line.

## 2. Gate fit

**Yes for the transfer matrix. Yes for the context-row indices. No for the source reference used while fitting. One real NaN-coding bug; no shape mismatch that would run silently.**

**Measured.** For each training family, `m = transfer(unis, others, fit_t)` with `others` equal to the other training families (`194-209`). Labels `y` come from the family member itself (`206`).

**Measured.** `ctx_names = train + truths`, `context_l` is stacked in that order (`191-192`). `Family.context` is `ctx_names.index(n)` for a training member (`214`). E1 calls `ctx_names.index(h)` (`252`); E2 calls it for `h1` and `h2` (`296-297`). `source_l` is the training basals only (`193`), and `meas` is stacked in the same `train` order (`211`, `236`), which matches `gate_features` (`gated.py:108-110`).

**Measured, and this is wrong at fit time.** The same `source_l` / `meas` include the family being fit. `Δℓ` is context minus the mean of those sources (`gated.py:102-123`). Every fit target was measured in that context (`gated_bench.py:201-202`), so the context's own basal is inside the training mean and the training delta is shrunk (by about 1/2 with two training sources, about 1/3 with three). At test the held-out context is not in `source_l`, so the delta is the full gap. α, β are then applied to larger features than they were fit on.

**Smallest fix:** inside the fit loop, call `gate_features` with `source_l` and `meas` built from `others` only. Keep the shared `context_l` and the same context index. Leave the test call on all of `train`, which is what `m_h` is mixed from.

**Measured.** `shared_share` writes `0` where the moments are missing (`share_panel_bench.py:123-128`). `gate_features` median-imputes only non-finite rho (`gated.py:96-100`). A structural zero is finite, so it is treated as known rho = 0 (logit clipped to about `log(0.001/0.999)`), which is the "not estimable = not shared" coding the design wanted to avoid. Shapes line up: each `Family` has its own `(T, G)` `y`, `m`, `k` and a feature tensor with that `T` and `C = len(ctx_names)`. NaN basal becomes a zero term with the mask off (`gated.py:113-125`). `m`/`y` NaNs are dropped in the loss (`gated.py:209-214`). A missing basal column would throw on `vstack`, not silently score.

**Smallest fix:** keep the zeros for the `excl` / `share` multipliers; pass the gate `np.where(has, share, np.nan)`. `has` is local to `shared_share` today, so return it (do not change the array `t23_share.py` writes).

## 3. E1 metrics

**Yes for the combined-score algebra, the seeds, and the pairing. Yes, two arm treatments differ before that shared loop. The copied gene mask does not do what it does on the panel bench.**

**Measured.** Per target, `0.36 * pds_gen - 0.27 * nmae_gen`, then the paired difference, then `boot` on finite entries (`gated_bench.py:43`, `261-284`). That is the same algebra as `share_panel_bench.py:235-236`. `realise` is called with seeds `(1, 2, 3)` and `default_rng([seed, ord(c)])` (`268-269`), identical to `share_panel_bench.py:213-214`. `rank_pds`, the log1p map, `clip(-20, 20)`, and `observed | (abs(E) > 0)` match (`206-219` there, `261-274` here).

**Inferred.** nMAE is NaN only when `ref == 0`, and `ref` depends on `y` and `sig`, not on the arm (`272-274`). `rank_pds` returns finite ranks (`noise_sim.py:43-51`). Every contrast therefore keeps the same targets. The noise draw has a fixed shape (`noise_sim2.py:56`), so the same seed is the same noise field.

**Measured.** `excl` and `share` go through `match_detectable` (`241-242`); `transfer`, `gated`, `gated_blind`, and `gated_swap` do not. `gated` against `excl` (`280`) mixes an unscaled arm with an arm rescaled to the transfer's detectable-gene count. The ablation bench already keeps an unscaled `excl_noscale` for this reason (`ablation_bench.py:113-117`).

**Measured.** `keep` and `pds_proxy` drop `panel_cols` (`152-154`, `266`, `275`). Here the scored targets are a non-panel sample (`181-183`). On the panel bench those columns are the scored targets (`share_panel_bench.py:152-153`, `185`). On the genome-wide atlas the dropped columns are the test targets (`atlas_bench.py:386-388`, `402`, `412`). nMAE already drops the on-target gene (`255-258`); both PDS paths keep it. One gene with a large knockdown can dominate the cosine, and `s`/`h` were fit with that gene still in the loss.

**Smallest fix:** set `keep[tcols[tcols >= 0]] = False` and pass those columns to `pds_proxy`, as in `atlas_bench.py:386-412`. Compare `gated` with `tx * (rho > 0) + k_h` before `match_detectable`, or scale `gated` the same way, and do not treat the mixed comparison as the result.

## 4. E2

**Yes for the gene set, with one hole. Yes, `transfer` and `gated_blind` are exactly zero. The correlation itself is not signed toward a positive result.**

**Measured.** `obs = y1 - y2` (`299`). `weighted_corr` keeps genes that are finite in that difference (so both truths are finite), finite in the prediction, and `w > 0` (`96-97`). `w` is 0 within 5 kb, including the target's own column, and 0 where the mean basal weight is 0 (`80-93`, `294-302`, `NEAR_BP = 5000`). Distance `<= 5000` is removed, so "farther than 5 kb" is `> 5000`. Fewer than 20 genes returns NaN (`98-99`).

**Measured.** If the target is missing from the coordinate table, only its own column is masked (`88-92`); the 5 kb window is not. Those neighbors can enter.

**Measured.** `transfer` uses `(base, base)` (`298`), so the difference is identically 0. Blind prediction uses context-independent terms (`gated.py:139-143`) and the same `m_h`, `k_h`, and `A` for both lines (`296-297`). `k` does not depend on context (`157-161`). The recorded check is `abs(dpred) < 1e-7` (`303`); the construction is exact, not merely small.

**Inferred.** A positive correlation is not forced. Global scale cancels in the correlation, so the `a_fit` versus `1.576` swap does not sign E2. Undefined `m` becomes `k` on both lines (`244-246`) and contributes zeros, which pulls the correlation toward 0. Rho coded as 0 saturates `h` and also flattens context differences. There is no permutation arm and no split-half ceiling (the design asked for both). The train/test delta mismatch in point 2 can still change the number, because `s = exp(α Δℓ)` is not scale-invariant in α.

**Smallest fix:** if a test target is absent from `coords`, drop it from E2. Add the permutation control before reading a positive mean as context use.

## 5. Other ways a positive result would be untrustworthy

**Measured.** Gates are fit at `a_fit` and applied at `AMPLITUDE` (`1.576`) (`215-224`, `238`, `245`). `a_fit` is the slope of `y` on `m` with `k` left in `y` (`218-223`). There is no intercept in `s` or `h` (`gated.py:146-154`), so the fitted `(α, β)` is not invariant to `A`. E1 nMAE, and therefore the combined score, compares a gate trained at one scale with a transfer fixed at `1.576`. Cosine PDS is invariant to a global scale; nMAE is not. `res.success` is stored (`229`) and not required before `res.x` is used; `gated.py:258` says to check it.

**Smallest fix:** `gated.fit(..., A=AMPLITUDE)`, keep `a_fit` as a reported diagnostic, and skip the design when `res.success` is false. If `a_fit` is ever put back into the model, regress `y - k` on `m`.

**Measured.** `transfer()` loads only the query targets and `mix(..., gamma=1)` centres on `tab.common()` of that subset (`69-77`; `multisource.py:256-261`, `282-283`). Fit centres on fit targets; test centres on test targets. `pair_features` documents the opposite for a bench: centre on training targets so held-out targets do not move the feature (`transfer_model.py:87-94`). This matches what `atlas_bench.py:307-320` actually does. The offset is shared by both E2 contexts, so it cancels in the E2 difference; it does not cancel between E1 arms once `s` and `h` multiply `m`.

**Smallest fix:** pass one `common`, computed on training targets outside `tset` and the panel, into both the fit and the test `mix`.

**Measured.** `gated_swap` draws `rng.integers(0, len(train))` (`251-253`), a training context. That does not enter the fit. The registered contrasts are against `transfer`, `gated_blind`, and `excl` (`280`), not against swap.

## Three findings that matter

1. **Training context features are shrunk, test features are not** (`gated_bench.py:191-214` with `gated.py:102-123`). A gain of `gated` over `gated_blind`, and a nonzero E2 correlation, can be an over-applied α, β. Fix the fit-time `source_l` to `others`.

2. **E1 PDS includes the on-target gene** (`gated_bench.py:152-154`, `266`, `275` against `atlas_bench.py:386-412`). nMAE drops it; PDS does not. The fit loss also keeps it, so E1 can be won by rescaling the knockdown. Fix the mask to the test-target columns.

3. **The scored gates are not the fitted model.** Fit uses `a_fit` and a rho of structural zeros; test uses `1.576` and that same rho (`gated_bench.py:215-245`, `share_panel_bench.py:123-128`, `gated.py:96-100`). Combined with `match_detectable` on `excl` only (`241-242`, `280`), `gated` versus `transfer` and `gated` versus `excl` mix scale, imputation, and context. Fit at `1.576`, pass NaN rho into the gate only, and compare like with like on scaling.

## Not verified

No design was run, and no universe matrix, basal CSV, or pairs file was loaded beyond the pairs header and the code that writes them. Whether `a_fit` lands near `1.576`, and how many genes have missing moments, is unknown until a run. Open for Claude1: on a K562 holdout, is the production K562 cis curve allowed to stay in `k` (as in `share_panel_bench.py:161-162`), given the leakage rule says the cis head must not see the held-out line?
