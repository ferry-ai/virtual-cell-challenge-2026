# Che cosa pubblicano gli organizzatori della VCC 2026: grok

Rapporto integrale di grok (base di lancio, run `20260927-144815-v2-vcc2026-organizers`, grok-4.7, sola lettura, brief `v2-grok-vcc2026-organizers.md`), copiato il 27 settembre senza modifiche. Il testo integrale dell'articolo su Cell non si è aperto (captcha, login); i fatti dall'articolo vengono da estratti indicizzati.

I'll pull the organisers' own pages and the Cell paper routes, then report only what those sources state about the 2026 data, baselines, and zero-shot results.The challenge site and the Arc news post are open. Next I’ll read the Cell commentary and the scoring pages in full.The organisers describe a zero-shot 2026 task on six unnamed cell lines, with one scoring baseline (a constant within-context mean response, scaled to 0) and no published linear or cross-line baseline scores on this year’s data.

Sources fully fetched: the Arc 20 Aug 2026 news post, the 6 Dec 2025 wrap-up, the VCC CLI wiki, and Arc’s `cell-eval2` spec (`vcc2026-metrics.md` and the 19 Aug 2026 brief). The challenge homepage and the *Cell* commentary were only partly recovered (details under “Not verified”).

## 1. Data

**Read.** Chemistry and design, Arc news (https://arcinstitute.org/news/virtual-cell-challenge-2026): Perturb-seq on **six cell lines from different tissues of origin**, **CRISPRi**, **10x Flex**, sequenced on **Ultima UG100**. Perturbations were “chosen to provide a strong set of perturbations and responses.” Three lines are the validation/live leaderboard; three are held for the final test. Per line, participants get **non-targeting (NT) control profiles** and **gene identifiers** only. “Arc’s experimental measurements themselves are withheld and serve as ground truth.” Participants “never see a perturbation response measured in it.” Any other public or private data may be used for training. The **full 2025 dataset** (train, validation, and held-out test) is now on the Arc Virtual Cell Atlas.

**Read.** Homepage search-index text (https://virtualcellchallenge.org/): no net-new training set; the 2025 **H1** data may be used. Predictions are scored against new Arc perturbation data “without your model having been trained on any of that data.” Controls: **18,400 unperturbed cells for each of three cell contexts — 46 non-targeting guides at 400 cells each.** Validation: **300 CRISPRi perturbations in each of three contexts.** Final test (22 Oct 2026): **a new panel of 300** perturbations in **three different** contexts. Final-test scores stay hidden until winners (late November 2026).

**Read.** CLI wiki (https://vcc-cli-wiki.virtualcellchallenge.org/): each context is a **different cell line**; **“We don't publish which one.”** Labels `A`/`B`/`C` (validation) and `D`/`E`/`F` (final) are opaque. Final round uses **different cell lines and different perturbation panels**, scored separately and **not comparable** to validation. Same 300 perturbations are predicted in all three validation contexts. Submission shape (not the raw experiment): exactly **400 cells per perturbation**, **18,533 genes**, raw counts, no NT cells in the file; **300 × 400 × 3 = 360,000 cells**.

**Read.** Scoring spec, ArcInstitute/cell-eval2 `docs/vcc2026_metrics/vcc2026-metrics.md` and `vcc2026-metrics-brief.md` (19 Aug 2026): the **reference used for scoring** is, per context, 300 target constructs (one per gene) plus a pooled NT control from **46 constructs**, **downsampled to exactly 400 cells and a median of 20,000 UMIs per cell**, on **18,533 genes**. Cell count and depth are fixed because they move every metric.

**Read (index excerpts only).** *Cell* commentary, DOI [10.1016/j.cell.2026.08.004](https://doi.org/10.1016/j.cell.2026.08.004), PMID 42648290: six lines, different tissues, CRISPRi, 10x Flex; NT profiles plus gene IDs; withheld measurements are ground truth; no matched perturbation-response examples from those contexts. “The final test set will follow a similar structure, but it will use three different cell lines from the validation set.” Europe PMC abstract matches the zero-shot framing. No bioRxiv or arXiv of this commentary (Crossref, Unpaywall, OpenAlex: no repository copy).

**Not stated** on any page opened: raw (pre-downsample) cells or UMIs per perturbation; dual-guide vs single-guide; Flex v1 vs v2; knockdown efficiency; a rule for how the six lines were picked beyond “different tissues” and a “strong” perturbation set; the lines’ names; whether those lines already have public perturbation data under another name; whether the 2026 perturbation matrices will be released after the challenge. The 2025 figures (**>50,000 UMIs/cell**, **~1,000 cells/perturbation**, H1, dual-guide) are in the 2025 wrap-up and “Behind the Data” post and are **not** stated for 2026. **H1 is last year’s context, not named as a 2026 evaluation context.**

## 2. Baselines

**Read.** One official baseline, and it is the zero of the score, not a leaderboard row of model scores. Spec: baseline \(b\) is **“the context's mean perturbation response”**: an equal-weight average, over constructs in that context that pass a cell-count and knockdown-efficiency filter, of the per-construct mean count vector, **assigned identically to every perturbation**. Replicate \(r\) is a **split-half** of the real experiment (five splits, each half with its own controls). Arc’s 20 Aug 2026 post (https://x.com/arcinstitute/status/2090492642841039139) calls the low end the **“cell context mean”** and the high end **“a real replicate.”** The CLI wiki says the same in participant language: **0 = “pasting the average cell onto every perturbation.”**

**Read.** On contexts A–C (`cell-eval2` 0.15.0, `rule_version` 3), raw anchors are:

| Metric | Baseline \(b\) | Split-half \(r\) |
|---|---|---|
| Perturbation discrimination `pds_cosine` (higher better) | **0.500 exactly** | 0.927–0.984 |
| Expression error `expr_mse_unbiased_capped_norm` (lower better) | 0.986–0.992 | 0.028–0.045 |
| DE direction fidelity (higher better) | 0.505–0.522 | 0.795–0.832 |
| DE direction reach (higher better) | 0.047–0.097 | 0.958–0.978 |
| DE significance overlap, Jaccard (higher better) | 0.021–0.037 | 0.375–0.423 |
| DE log-fold-change error, nMAE (lower better) | 1.0009–1.0017 | 0.369–0.431 |

**Read.** The spec states that this constant mean response is **barely distinguishable from pasting the unperturbed control**: expression error sits within 0.014 of the no-skill value 1; log-fold-change error sits within 0.002 of predicting no change (control-pasting itself measured 1.008–1.010). PDS of a shared profile or a zero effect is exactly 0.5. Direction fidelity of the baseline is at chance (~0.5).

**Not stated:** any 2026 score for a **cross-context perturbation mean**, a **linear** model, STATE, or any other named method. No leaderboard table was retrieved. The CLI page’s printed scores (Overall 0.3614, PDS 0.6222, and so on) are an **example of command output**, not a reported baseline. **Inferred:** the public phrase “cell context mean” and the spec’s “mean perturbation response” are the same anchor, because the spec says those \(b\) and \(r\) values are the ends the scorer applies.

## 3. Unseen contexts, and what 2025 showed

**Read (2026 task, not a result).** Arc news: 2025 asked for **held-out perturbations in the same H1 cells**, with a training set from that context. 2026 has **no challenge training set**; the task is zero-shot across contexts. “Doing well means inferring how perturbation effects transfer and change between cell types.” They do **not** say which method succeeds at that. Winners are not announced (final test 22 Oct 2026; deadline 5 Nov 2026). They point teams at the Altos Labs 2025 flow-matching preprint before building this year.

**Read (2025 results).** Wrap-up, https://arcinstitute.org/news/virtual-cell-challenge-2025-wrap-up (also summarised in the 2026 news and in indexed *Cell* excerpts): >5,000 registrants, >1,200 teams, >300 final submissions. **“Perturbation prediction models are not yet consistently outperforming naive baselines across all metrics,”** with gains on perturbation discrimination and DE-gene identification. **Almost all models were worse than baseline on MAE**, so the leaderboard was effectively PDS and DES. **Winning pattern they state:** hybrids of deep learning and classical statistics beat pure end-to-end nets; protein embeddings helped; no single metric captured quality.

- 1st, BioMap `xTrimoSCPerturb`: hybrid; they quote the team that purely AI methods **did not consistently beat statistical baselines on DES and MAE**, so the model used training-set DEG frequency and mean expression as features. Trained on public Perturb-seq plus challenge data.
- 2nd: small net on pseudo-bulk, ESM-2 embeddings, residual deltas; public Perturb-seq including a small H1 set in PerturbAtlas.
- 3rd, `TransPert`: **cross-line transfer from summary statistics of other lines**, then **global linear scaling fit on challenge training data**.
- Generalist prize, Altos `go-with-the-flow`: flow matching, pretrained on ~7 million cells including Altos screens **none in H1**, then **fine-tuned on h1ESC and challenge perturbations**.

**Read.** *Cell* index excerpts: strongest 2025 models improved discrimination and DE prediction, but “current models are not yet consistently replacing experimental measurements across all evaluation criteria.” 2026 tests generalisation “without matched perturbation-response examples from those contexts.”

**Not stated for 2026:** that transfer from other lines beats a constant profile, or the reverse. **Inferred from the task rules only:** the 2025 winners all used some **in-context** H1 perturbation data (training or fine-tuning); that set does not exist for the 2026 lines.

## 4. Scoring

**Read.** Six metrics, unweighted mean. Scale \(s = (u - b) / (r - b)\): **0 = baseline above, 1 = split-half replicate.** Above 1 and below 0 are kept. Arc news: final rank is an aggregate of these six (cell-eval, with NVIDIA). Arc post: the overall score averages the six metrics **and** the cell contexts. CLI: the six average to Overall exactly.

Leaderboard names (CLI) and spec members:

1. Perturbation discrimination — `pds` / `pds_cosine`. Cosine distance on log-normalised pseudobulk effects vs control, **all 300 panel target genes removed**. Higher better.
2. Expression accuracy — `mse` / `expr_mse_unbiased_capped_norm`. Noise-corrected MSE as a fraction of distance from control. Lower better. **Scaled score clamped to [0, 1].**
3. DE log-fold-change accuracy — `nmae` / `de_wilcoxon_lfc_nmae`. nMAE of log2 fold change on the reference significant genes. Lower better. **Scaled score floored at −6.**
4. DE direction fidelity — `fid` / `de_wilcoxon_direction_fidelity_yield_raw`. Sign agreement, penalised if fewer genes are called than the reference found. Higher better. Unclamped.
5. DE direction reach — `reach` / `de_wilcoxon_direction_reach_raw`. How far down the prediction’s ranking the signs stay ≥90% pure. Higher better. Unclamped.
6. DE significance overlap — `jac` / `de_wilcoxon_sig_jaccard`. Jaccard of significant-gene sets. Higher better. Unclamped.

DE test (spec): Wilcoxon rank-sum, two-sided, Benjamini–Hochberg **per perturbation**, \(\alpha = 0.05\), genes kept only if **>5 CPM in the reference control**. An exact copy of the reference scores about **1.03–1.17 (PDS), 1.00 (expression, clamped), 1.51–1.72 (fidelity), 1.02–1.05 (reach), 2.48–2.85 (Jaccard), 1.58–1.75 (logFC)** — 1.0 is a half-depth replicate, not perfection, except expression, which is capped at 1.

**2025 score, for contrast (wrap-up):** DES, PDS (L1), MAE; each normalised to a **perturbation-mean** baseline; composite = mean of the three, with per-metric floors. That is a different baseline and a different formula from 2026.

Homepage prize blurb still says criteria “to be released when the Challenge is launched.” The 20 Aug 2026 news and the 19 Aug spec supersede that. **Not retrieved:** the JS page https://virtualcellchallenge.org/evaluation (fetch returned only “Loading…”).

## Three statements for choosing transfer vs other approaches

1. **There is no in-context perturbation training set.** The only released profiles of the evaluation lines are NT controls (18,400 cells, 46 guides). Challenge knockdown matrices are withheld, line names are unpublished, and a post-challenge release is not promised. Transfer has to come from other data (the public 2025 H1 set is explicitly allowed). Whether any public screen is secretly the same line is **not stated**.
2. **The score’s zero is a constant profile** (the within-context mean response), which on expression error and log-fold change is almost the same as predicting the control. Organisers publish that anchor’s raw values (table above) and **do not** publish a cross-line perturbation-mean or linear baseline on the 2026 contexts. Beating 0 does not mean beating transfer.
3. **2025 did not show that end-to-end models beat simple baselines**, and the entries Arc highlights either mixed in statistical features or transferred from other lines **and then used H1 challenge training data**. That second step is unavailable in 2026. Rank is an unweighted mean of six metrics, so a method that only separates perturbations (PDS) can lose on direction, overlap, and fold-change magnitude.

## Not verified / open questions

- *Cell* full text did not open. Routes: cell.com HTML (“Just a moment…”), cell.com PDF (Elsevier login), doi.org → linkinghub (“Redirecting”), ScienceDirect (captcha), PubMed 42648290 (reCAPTCHA), Europe PMC (abstract only, not in PMC), Unpaywall and OpenAlex (no PDF), Semantic Scholar (abstract only), Wayback Machine (no capture). No preprint found. Indexed HTML excerpts may have missed a data-release or baseline sentence.
- https://virtualcellchallenge.org/ and `/evaluation` are a client-rendered site; fetch saw “Loading…” Homepage facts are from the search index of the rendered page, not a full HTML save. No FAQ page turned up.
- Raw experimental depth before the 400-cell / 20,000-UMI downsample is **not stated**.
- No public 2026 leaderboard snapshot was opened, so current entrant scores are unknown.
- Open for Claude1: will Arc release the six perturbation matrices after judging; do the unnamed lines occur in public Perturb-seq; is the homepage “cell context mean” ever shown as a leaderboard row next to a cross-line mean.
