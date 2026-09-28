Fidelity is dragged down because our target-specific sign accuracy is barely above random, and we are heavily penalized either for calling too many spurious "up" genes (inflating the formula's denominator) or for calling too few genes (triggering a recall penalty against the true reference).

### 1. Reasons fidelity sits below baseline
- **Measured**: Fidelity is defined as `k / max(n_pred, n_conf)`.
- **Measured**: The generator artificially inflates detected genes by 2.1-6.3% even at zero effect (`docs/PROGETTO.md`:176).
- **Measured**: Target-specific sign agreement between sources is weak. Target-swapped agreement is 53.85%, while a naive "always up on the same genes" baseline gets 63.58% (`docs/checkpoints/0034-audit-segni-e-ampiezza.md`:28-29).
- **Measured**: t11/t15 produce 500-1000 median calls per target, heavily skewed 81-86% "up" (`docs/checkpoints/0033-t15-ampiezza-doppia.md`:71-72).
- **Measured**: When t14 removed spurious calls, median calls dropped to 136-218, but fidelity fell to 0.447 because the metric formula became clamped to `k / n_conf` (`docs/checkpoints/0032-t14-controlmodel-fedelta.md`:38-39, 88-89).
- **Inferred**: In t11/t15, the massive "up" skew and generator artifacts push `n_pred` far above `n_conf`. Because the denominator is `max(n_pred, n_conf)`, these false positives severely penalize the score (precision penalty). Furthermore, our base sign precision on called genes is only ~54-56%, so `k` remains small.
- **Inferred**: In t14, `n_pred` was pushed well below `n_conf`. The denominator clamped to `n_conf`, and because we called so few genes while still only having ~54% sign accuracy on them, `k` was too small to offset the fixed denominator (recall penalty).

### 2. Testable Levers
**Lever A: Match `n_pred` to a plausible `n_conf` via Top-K thresholding (Proposal)**
- **Mechanism**: Sort genes by absolute predicted effect and hold all but the top `K` (our best estimate of `n_conf`) at zero. This mathematically bounds the denominator to `n_conf` (fixing the t15 precision penalty) while keeping the largest effects to maximize `k` (fixing the t14 recall penalty).
- **Risk to others**: May lower `reach` and slightly drop `pds_cosine` by zeroing true tail effects.
- **Local test**: Apply a top-K mask to predictions. Run stage 83 (`reports/prediction_calls_2026-09-23/`). Reject if local `pds_cosine` surrogates drop unacceptably or if the total call count collapses.

**Lever B: Balance the up/down calls by centering / removing common response (Proposal)**
- **Mechanism**: The 81-86% "up" skew and the 63.58% "always up" baseline show a massive common shift. Mean-centering our predictions per target will eliminate spurious "up" calls, shrinking `n_pred` without losing target-specific signal `k`.
- **Risk to others**: `pds_cosine` uses continuous correlation, which is shift-invariant, so risk is minimal. `nmae` might shift.
- **Local test**: Apply mean-centering to the predicted log2FC. Run stage 83. Reject if the up/down ratio doesn't balance to ~50% or if median calls drop to t14 levels.

**Lever C: Mask unexpressed genes in contexts A/B/C (Proposal)**
- **Mechanism**: Genes not expressed in the real context cannot be significantly DE in `n_conf`. If the generator calls them, they only inflate `n_pred`. Holding them at zero stops this.
- **Risk to others**: Negligible. Unexpressed genes are noise.
- **Local test**: Filter predictions using the 5 CPM gate (`docs/PROGETTO.md`:188). Run stage 83. Reject if `n_pred` doesn't change, meaning the generator wasn't calling them anyway.

**Lever D: Only predict genes where multiple sources agree on the sign (Proposal)**
- **Mechanism**: Masking out genes without sign consensus increases the precision `k / n_pred`, as consensus tops ~64% (`reports/direzione_2026-09-24/direction.json`:377).
- **Risk to others**: High risk to `pds_cosine` by discarding true, target-specific effects captured by only one source.
- **Local test**: Run `scripts/103_direction_transfer.py` using consensus masking. Reject if total calls drop too close to t14 levels.

### 3. Ranking by expected value and attribution
1. **Top-K thresholding**: Highest expected value (directly targets the `max()` denominator math). Very clean attribution in one submission.
2. **Balance up/down calls**: High expected value (fixes the massive 86% "up" artifact). Clean attribution.
3. **Mask unexpressed genes**: Low expected value (only trims the tail), but extremely clean and safe attribution.
4. **Consensus masking**: Lowest expected value due to high risk of triggering a t14-style recall penalty and destroying `pds_cosine`. Mixed attribution.

### 4. What I did not do or could not verify, and open questions
- **Unverified**: I could not determine the exact value of `n_conf` for the official test set.
- **Unverified**: I could not read `reports/dispersion_2026-09-23/` or `reports/common_component_2026-09-18/` because headless mode strictly prohibits running directory listing commands to find the exact filenames, and guessing standard names (`summary.json`, `README.md`) failed.
- **Open Question for Claude1**: What is our best statistical estimate of the average `n_conf` in the official test set? We need this to calibrate the Top-K lever.
- **Open Question for Claude1**: Does the evaluation metric compute `pds_cosine` on the exact same zero-masked vector used for the DE calls, or can we submit continuous values for PDS while implicitly forcing DE calls through another mechanism? (If they use the exact same predicted values, zeroing genes heavily risks `pds_cosine`).
