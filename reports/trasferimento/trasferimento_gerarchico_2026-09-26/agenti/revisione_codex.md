# Revisione del banco EB: codex

Rapporto integrale di codex (hub, esecuzione `20260926-152047-v2-codex-eb-review`, sola lettura, brief
`v2-codex-eb-review.md`), copiato senza modifiche il 26 settembre. **Rapporto di un agente.**

---

**Inferred — changes requested:** the transfer path has no evident held-out-value leakage, but the strict family exclusion has a documented K562 exception, and bin weighting and scale matching can silently alter the comparison.

“Measured” below means inspected in source, not executed. `EB` denotes `reports/trasferimento_gerarchico_2026-09-26/eb_bench.py`.

1. **High — K562 is not a family-isolated fold.**  
   **Measured:** the cis model is fitted before the holdouts (`EB:154–156`) from K562 neighbour measurements (`configs/recipes/t20.json:12`). `cis_prior` removes panel targets, not the held-out family (`src/vcc2026/priors.py:20–23`). The same prior enters every arm and the EB scaling objectives (`EB:168–191`). The script acknowledges this (`EB:26`, `EB:229`).  
   **Inferred:** this violates the task’s literal family-exclusion requirement for K562. It is not leakage of the evaluated panel rows, and it does not necessarily favour EB: nevertheless, the shared additive term does not cancel from nonlinear scoring or scale selection. Treat K562 separately or exclude it from new-family conclusions.

2. **Medium — bin-blending weights do not implement “n targets with data.”**  
   **Measured:** `s_den` counts valid target/source-pair observations; `n_ex` counts target/source observations. Their conversions are `s_den/(S−1)` and `n_ex/S` (`EB:80–100`), contrary to the stated target count (`EB:10–11`).  
   **Inferred:** with three complete sources and T targets, sigma uses **1.5T**, while tau uses T. With partial coverage, neither expression generally counts distinct targets. K562/CD4 holdouts use three inputs, whereas Orion holdouts use two (`EB:64`, `EB:163`), introducing different regularization beyond the intended data difference. This changes EB predictions, not just reporting.

3. **Medium — scale matching can return an unmatched scale without failure.**  
   **Measured:** detectable matching bisects on the count of `|s*effect + cis|` (`src/vcc2026/transfer_model.py:223–233`); energy matching similarly bisects a fixed `[0.001, 10000]` interval (`EB:116–124`). Neither checks attainability or the final residual.  
   **Inferred:** opposite-sign cis and transfer contributions can make detectable counts decrease before increasing, invalidating monotone bisection. Counts also have jumps, so exact equality need not exist. For energy, the objective is a convex quadratic; when reference energy exceeds cis-only energy and the positive crossing is bracketed, the search works. Those conditions are not enforced. An all-zero theta is another unattainable case. These failures could confound a claimed comparison at matched amplitude. The printed energy ratio/count helps detect them (`EB:226–233`), but does not prevent them.

4. **Medium, conditional — the combined effect uses a different cohort from the displayed PDS effect.**  
   **Measured:** nMAE is NaN for targets without qualifying truth signal (`EB:203`, `EB:221–225`). The combined difference discards those targets (`EB:241–242`), while displayed PDS means use all targets (`EB:230–232`).  
   **Inferred:** if any targets lack qualifying signal, the combined estimate is not `0.36 × displayed ΔPDS − 0.27 × displayed ΔnMAE`. Its PDS component is conditional on truth-significant targets. This remains paired and arm-shared, but can change the conclusion relative to the full-cohort aggregate. Report its cohort size and conditional interpretation.

5. **Lower, conditional — generator support is defined by baseline values.**  
   **Measured:** all arms use `observed = abs(t20) > 0` (`EB:204`, `EB:218`). `realise` zeroes deterministic effects outside that mask and normalizes within it (`reports/banco_varianti_2026-09-25/noise_sim2.py:48–54`).  
   **Inferred:** an EB effect where t20 is exactly zero is discarded in generator metrics. Shared support is deliberate and useful, but using nonzero baseline values instead of measurement coverage makes it baseline-dependent. Actual affected entries are unverified.

**Checks without an implementation finding**

- **Measured / inferred — direct leakage:** source families are excluded before mixing, centring, SE extraction and expression-bin construction (`EB:163–185`). `load` exposes raw effects through the first `AxisTable`, so `rows()` here really returns raw effects (`scripts/104_learned_reweighting.py:69–76`; `src/vcc2026/multisource.py:197–211`). No sibling-style pre-split truth centring was found. Held-out target *membership* selects the estimation/evaluation rows (`EB:164–166`); held-out effect values and Z enter only evaluation (`EB:194–242`).
- **Measured / inferred — moments and posterior:** cross-products, mean noise-subtracted squares, subtraction of the raw cross-product estimate, then nonnegative clipping follow the stated calculation (`EB:80–93`). Finite masks exclude NaNs; gene-wise broadcasting is correct. The posterior formula returns zero for no observations or sigma²=0, with a numerical variance floor of `1e-12` (`EB:104–113`). Bin medians and indexing are otherwise consistent; genes without pair overlap or finite expression are explicitly zeroed (`EB:94–100`).
- **Measured / inferred — fairness:** cis stays outside both scales (`EB:188–191`; `src/vcc2026/transfer_model.py:233`). Precision uses one intersection of valid target cohorts for all arms (`EB:207–208`, `EB:239`). Combining paired per-target differences **before** bootstrapping correctly preserves covariance between PDS and nMAE (`EB:241–242`; `reports/modulo_cis_2026-09-26/cis_bench.py:170–174`).
- **Measured — terminology only:** baseline source coefficients are equal, but effective weights include cell reliability (`src/vcc2026/multisource.py:242–245`). Calling this a literal equal-weight mean is cosmetic unless a different baseline was intended.

**Limits and open questions**

**Measured:** only read/search commands were used: `Get-Content` with numbered output and `Select-String` printed the cited source. `rg` failed because it is unavailable. No Python, tests, bench, installs or writes were run.

**Unverified:** actual numerical impact; cache column order and mixture ancestry. The loader assumes the stored official gene axis without validating gene labels (`scripts/104_learned_reweighting.py:71–75`), and reconstructed SE follows metadata parts without a family check (`scripts/104_learned_reweighting.py:84–85`). Claude1 should verify those cache invariants, scaling residuals, combined-cohort counts, and whether the K562 exception is explicitly acceptable.
