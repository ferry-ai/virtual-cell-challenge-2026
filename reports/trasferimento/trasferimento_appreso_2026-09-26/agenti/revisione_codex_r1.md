**Inferred:** The comparison is not trustworthy yet: training features expose test-family outcomes, the network prior lacks panel exclusions, and CD4 and precision metrics contain errors.

Paths below are relative to the repository. `LCT` means `reports/trasferimento_appreso_2026-09-26/lct_bench.py`.

1. **Critical — outer-family exclusion does not reach training features.**  
   **Measured:** `LCT:92–99` builds each task using every other family; `LCT:200–212` caches those tasks globally. `LCT:219–226` excludes only tasks whose **label** belongs to the test family.  
   **Inferred:** For test H=`k562`, training task `cd4_mix` includes K562 measurements of overlapping test targets in pooled effects, agreement, spread, z-scores and strength. K562 outcomes also enter source centering (`src/vcc2026/multisource.py:206–211`). The same problem applies to other outer folds. This violates the requested isolation even though training labels exclude H.  
   **Fix:** Rebuild training tasks separately inside each outer fold, excluding the outer test family from all source inputs and derived aggregates, as well as excluding each training task’s own label family.

2. **Critical — `partner_effects` can include K562 test-target outcomes.**  
   **Measured:** `LCT:197` omits `exclude`. Its default is empty (`scripts/100_build_context_effects.py:132–141`). Self-partner removal at line 153 does **not** remove the target from the global center at lines 163–170; other panel targets can also be partners.  
   **Inferred:** Whenever panel targets occur in the universe, a target’s own K562 effect contributes negatively through the center, and other test-target outcomes can contribute through partners. The “not target outcomes” statement at `LCT:26–27` is therefore unsupported. Actual cache overlap was not inspected.  
   **Fix:** Pass `exclude=frozenset(panel_list)` for both partners and center. An existing bench already does this: `reports/bersagli_nuovi_2026-09-26/checks_self.py:52–53`.

3. **High — source-side CD4 z-features silently discard CD4 evidence.**  
   **Measured:** Stage 98 writes CD4 mixture SE as entirely NaN (`scripts/98_multisource_effects.py:126–129`). `LCT:112–124` nevertheless divides its effects by that SE. At `LCT:153–154`, `nan_to_num` converts these missing z-scores to zero before counting significant genes.  
   **Inferred:** CD4 contributes no z-information and receives strength zero despite having measured effects. A CD4-only available source produces all-NaN z summaries while strength falsely indicates no signal. This specifically damages learned features; fixed arms still use CD4 effects.  
   **Fix:** Reconstruct mixture uncertainty consistently with its pooling weights; preserve unavailable strength as NaN. Do not use the existing `truth_z` formula unchanged—see finding 4.

4. **High — CD4 `truth_z` uses the wrong pooling uncertainty.**  
   **Measured:** `reports/modulo_cis_2026-09-26/cis_bench.py:155–167` computes `sqrt(sum(se²))/n`, the independent equal-weight mean SE. CD4 raw effects instead use reliability-weighted pooling (`scripts/98_multisource_effects.py:121–125`; `src/vcc2026/multisource.py:240–244`).  
   **Inferred:** Unless contributing weights are equal, the z-score denominator does not correspond to the numerator. This changes the significant-gene set used by reach and can change arm rankings.  
   **Fix:** Under an explicitly stated independence approximation, use `sqrt(sum(r²*se²))/sum(r)` with the same per-target/per-gene availability and reliability weights as the raw mixture. Handle covariance separately if conditions share relevant noise.

5. **High — precision@200 compares arm-dependent target populations.**  
   **Measured:** `reports/banco_varianti_2026-09-25/analyze.py:101–106` filters on `P != 0` and skips targets with fewer than 50 eligible genes. Lines 112–115 use fewer than 200 genes when necessary. `LCT:254` independently averages each resulting array while reporting the original shared target count.  
   **Inferred:** Sparse fixed predictions and dense LCT predictions can be averaged over different targets and denominators. Missing difficult targets can improve an arm’s reported precision.  
   **Fix:** Return target-indexed results and eligible counts; predefine a shared target cohort and policy for fewer than 200 predictions. Report coverage alongside precision, with paired comparisons.

6. **Medium — nonfinite evaluation weights can produce impossible PDS values.**  
   **Measured:** `LCT:189–193` reindexes basal expression without validating finite A/B/C weights. `analyze.py:82–91` propagates NaN weights into cosines, then counts comparisons and subtracts one from tie counts.  
   **Inferred:** If all cosines in a row are NaN, both comparison counts are zero and the resulting score is `1 + 0.5/(n−1)` for `n>1`, exceeding 1. MSE also becomes NaN (`LCT:241–250`). Actual missing weights are **unverified**.  
   **Fix:** Validate finite weights, predictions and positive truth norms before scoring; explicitly mask unsupported genes identically for all arms and reject invalid score inputs.

7. **Medium — training and reported evaluation optimize different objectives.**  
   **Measured:** Training uses held-context expression weights squared, clipped labels and sampled genes (`LCT:158–161, 206–212`). Evaluation uses A/B/C-average expression weights, unbounded truth and excludes panel genes from MSE/PDS (`LCT:190–193, 238–250`). Training includes panel genes. Rows are concatenated without family normalization (`LCT:219–222`), so Orion supplies two tasks versus one for other families.  
   **Inferred:** This is an objective mismatch, not a missing square: multiplying both MSE vectors by `w_eval` correctly induces squared weights. Clipping, gene subsampling, different expression weights and family counts can nevertheless materially alter the learned optimum.  
   **Fix:** Declare the intended estimand; align training weights/masks with it or report both objectives. Normalize family/task contributions if equal-family weighting is intended.

8. **Medium — empty-support cases can abort reporting or yield undefined summaries.**  
   **Measured:** `LCT:134, 211` assumes nonempty target lists; `LCT:265` samples 400 genes without checking that a selected target has any finite positive-weight labels. `cis_bench.py:170–174` has no empty-difference guard. `LCT:250` has no zero-null-energy guard.  
   **Inferred:** Empty cohorts can fail stacking/concatenation or permutation sampling; entirely undefined reach and zero truth energy cannot produce valid comparisons. Occurrence on current data is **unverified**.  
   **Fix:** Check support explicitly, record excluded counts and reasons, and emit an explicit unavailable result for empty bootstrap inputs or zero denominators.

**Checks that found no additional defect**

- **Measured:** `gene_priors` explicitly excludes every panel target before calculating its moments (`LCT:76–86`); the cis prior also excludes panel targets (`scripts/100_build_context_effects.py:108–111`). These carry other-target K562 information, not direct panel-target outcomes, assuming consistent identifiers.
- **Measured:** Test-task transfer inputs exclude the entire held family (`LCT:92`); both Orion sources share one family (`analyze.py:39`). No explicit `y` value is used to construct ordinary features; truth supplies labels and eligibility.
- **Measured:** Basal-profile construction selects control rows (`reports/trasferimento_appreso_2026-09-26/basal_profiles.py:65–71, 77–83, 87–93`). **Inferred:** Held-context basal expression is therefore not perturbation-label leakage under the stated control-access regime.
- **Measured:** `pct` preserves missing genes as NaN (`LCT:60–65`). **Inferred:** `nanmean` over entirely missing source percentiles leaves NaN rather than inventing zero expression. Empty-slice warnings remain possible; `np.errstate` does not suppress those warnings.
- **Inferred:** Broadcasting and prediction chunk ordering are consistent: repeated target indices, tiled gene indices and reshape agree, including the final partial chunk (`LCT:137–157, 165–166, 231–234`).
- **Measured:** PDS/MSE/reach receive one shared target ordering. Bootstrap subtracts aligned per-target arm scores before resampling (`LCT:255–260`); reach eligibility depends on truth rather than arm. **Inferred:** Pairing itself is correct. Its intervals describe target resampling conditional on the fitted model, not training or context uncertainty.

**Measured — review scope:** Used read-only `Get-Content` with numbered-line formatting, `Select-String`, and `Get-ChildItem` to inspect the named scripts and dependencies. `rg` printed “not recognized”; subsequent searches used `Select-String`. No bench, tests, imports, installations or writes were run. This message is the report; `result.md` was not created because read mode forbids file creation.

**Unverified / open for Claude1:** Actual universe-panel overlap, cache axis identity/order, missing-weight incidence, empty cohorts, and numerical impact require data checks. Confirm the intended training/evaluation weighting before rerunning after the two leakage fixes.
