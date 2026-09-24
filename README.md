# Virtual Cell Challenge 2026

**Zero-shot** prediction of the transcriptional response to CRISPRi knockdown in
cell lines never seen during training.

Submissions close **5 November 2026**. Final test set drops **22 October 2026**.

> **Start from [`docs/PROGETTO.md`](docs/PROGETTO.md) §0** — where the project stands
> today — and [`docs/LAVORO.md`](docs/LAVORO.md), the live pipeline with its exact
> commands. Agents: the working agreement is [`CLAUDE.md`](CLAUDE.md).
> Open priorities, promising research and past outcomes are indexed in
> [`docs/PIANI.md`](docs/PIANI.md); each plan has its own card for coordination.
> This README covers the task, the scoring and the setup. Parts of it are older than
> the analyses in `docs/`, and six of its claims are flagged: see its entry in
> [`docs/REGISTRO.md`](docs/REGISTRO.md), sheet R-001. The sections from "Plan" onward
> are a record of 11–13 September: the scripts they name were archived on 23 September
> (`docs/ARCHIVIO.md`). The submission contract is in
> [`docs/SOTTOMISSIONE.md`](docs/SOTTOMISSIONE.md) §1.

## The task

No training set is provided. You are given only the **basal state** of three
anonymized cell lines, and must simulate what happens when 300 genes are silenced.

| | |
|---|---|
| Input | Non-targeting control profiles for 3 contexts (A, B, C) — 18,400 cells x 18,533 genes each, raw counts, ~20k median UMIs, 46 NTC guides x 400 cells |
| Predict | 300 CRISPRi knockdowns in **every** context, 400 cells per perturbation |
| Output | One `.h5ad`: 360,000 cells x 18,533 genes, raw counts, sparse |
| Training data | Any public or proprietary data you may use: H1 hESC from VCC 2025, Arc Virtual Cell Atlas, Replogle, ... |
| Final phase | Same structure on 3 **different** lines (D, E, F) and 300 new perturbations |

Final ranking depends **only** on the final test set.

Research datasets **do not need perturbation targets in common with the current
300-target panel**. We also aim to predict unseen targets in unseen contexts;
the production same-target transfer pipeline is one baseline. Source selection and
evaluation requirements are in [`docs/GENERALIZZAZIONE.md`](docs/GENERALIZZAZIONE.md)
(D-044). Target overlap and coverage of measured response genes are separate quantities.

## How it is scored

Six metrics computed by `cell-eval2` on its `vcc2026` preset. PDS excludes all
panel target genes; the other five exclude each perturbation's own target gene.

| Metric | What it measures |
|---|---|
| `pds` | Discrimination: is the prediction closer to its own true effect than to any other perturbation's? Rank by cosine distance within the panel |
| `mse` | Expression accuracy, corrected for the finite-cell sampling floor and normalized by the size of the real effect. The only metric bounded on [0, 1] |
| `nmae` | Normalized mean absolute error on log2 fold changes, over genes the reference calls significant |
| `fid` | Of the genes the prediction calls significant, the share moving in the right direction. Scaled by yield |
| `reach` | How deep directional agreement holds when reference-significant genes are ranked by the prediction's own confidence |
| `jac` | Jaccard overlap between predicted and real DE gene sets |

**The scaling is the crux.** Every metric is anchored to two points measured in
its own cell context:

- **0** = the official mean perturbation-response baseline in that context
- **1** = as accurate as a real replicate experiment
- **> 1** = better than a real replicate (possible: five of six have no ceiling)
- **< 0** = worse than the context mean

The final score is an **unweighted mean** over 6 metrics x 3 contexts. It is not a
percentage, and 1.0 is not the maximum.

The baseline is an equal-weight average of filtered perturbed construct means,
not the non-targeting control mean. Copying controls does **not** guarantee zero.
See the [official metric specification](https://github.com/ArcInstitute/cell-eval2/blob/main/docs/vcc2026_metrics/vcc2026-metrics-brief.md).
The scorer specification allows variable predicted cell counts; this project's
writer uses 400 per perturbation. Check the active submission CLI separately.

## Layout

```
vcc2026/                     <- this repo (Desktop, synced by OneDrive)
  configs/config.yaml        <- paths + official challenge constants
  src/vcc2026/               <- library
  scripts/                   <- executables and wrappers
  notebooks/                 <- the Colab dispatcher and its job scripts
  tests/
  docs/

C:/Users/ferra/vcc2026-data/ <- data + venv, OUTSIDE OneDrive
  .venv/                     <- Python 3.12
  raw/                       <- downloaded bundles, untouched
  interim/  processed/
  external/                  <- Replogle, Arc Atlas, H1 2025
  predictions/  models/
```

Data sits outside the repo because the Desktop is inside OneDrive: syncing tens of
GB of `.h5ad` would be slow and would eat the cloud quota. The path lives in
`configs/config.yaml` and can be overridden with `VCC2026_DATA_ROOT`.

## Setup

Requires **Python 3.12**: `arc-state` pins `>=3.11,<3.13`. The environment already
exists at `C:\Users\ferra\vcc2026-data\.venv` with `vcc-cli`, `cell-eval2`,
`anndata`, `scanpy`.

Windows defaults to `ExecutionPolicy = Restricted`, which blocks **every** `.ps1`
script — including the venv's own `Activate.ps1`. The project therefore ships two
`.cmd` wrappers, which that policy does not touch:

```powershell
.\scripts\vcc.cmd whoami        # the challenge CLI
.\scripts\py.cmd script.py      # venv Python, with src/ already on PYTHONPATH
```

Both set `PYTHONIOENCODING=utf-8`, without which the `vcc` CLI dies with
`UnicodeEncodeError` on a cp1252 console.

To activate the venv the classic way instead, you need a more permissive policy
(once, per user, no admin rights):

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

After that `. .\scripts\env.ps1` works. This changes a Windows security setting:
`RemoteSigned` permits local scripts and requires a signature for downloaded ones.
The `.cmd` wrappers sidestep the question entirely.

### Authentication

The token is generated on the app's **Credentials** page. It is not a metered API —
it is a free access credential, the terminal-side equivalent of being logged in to
the website. Generating a new one revokes the previous one. Never paste it into a
chat and never commit it:

```powershell
.\scripts\vcc.cmd login --token-stdin    # paste the token, then Enter
.\scripts\vcc.cmd whoami
```

The token is stored in the Windows credential manager, not in a project file.

## Plan

| Phase | Goal | Status |
|---|---|---|
| 0 | Environment, CLI, control data in hand, streaming submission writer verified against official `prep` | **done**, with a caveat — see below |
| 1 | Local scorer with `cell-eval2` on leave-one-cell-line-out splits from public data, to iterate without burning the 2 submissions/day | next |
| 2 | Baselines: control resampling, estimated mean response, log2FC transfer from public Perturb-seq conditioned on basal expression | |
| 3 | Learned model: maps (basal state, perturbation identity) -> response. Trained on Colab/Kaggle | |
| 4 | Ensemble, DE-call calibration, final submission on D/E/F | |

**Phase 1 is the real bottleneck.** Without faithful local evaluation you can test
at most 2 ideas a day.

> **Status note, 12 September 2026.** Phase 1 has not started, and it is blocked
> rather than merely next: it needs perturbed counts plus NTCs in some context, and
> the local H1 2025 directory holds four metadata CSVs and no RNA matrix. See
> [`docs/DECISIONI.md`](docs/DECISIONI.md), D-003.

> **Correction to phase 0, 12 September 2026 (evening).** "Verified against official
> `prep`" is not supported by any artifact: no `vcc prep` log predates today, and the
> only candidate file holds 3 of the 300 required perturbations, which `prep` rejects
> by default. What is supported is that the writer produces a structurally valid
> `.h5ad` (`scripts/02_smoke_test_submission.py`). Sheet R-001, claim 6.
>
> **Phase 2 has since run.** Two complete submission-shaped predictions for contexts
> A/B/C — control resampling and calibrated log2FC transfer — were generated locally
> and pass all 18 contract checks re-derived from the written file. As of 13 September
> `trial-01-transfer` is also **packaged**: a 3.91 GiB `.vcc`, produced by a path that
> validates and writes without materialising the matrix (0.52 GiB peak, against the
> 33.5 GiB the CLI's own model attributes to `vcc prep`), with all 24 checks enabled
> and the payload verified bit-for-bit against the input. See
> [CP-0004](docs/checkpoints/0004-primo-trial-locale-e-pacchetti.md),
> [CP-0005](docs/checkpoints/0005-packaging-streaming-trial01.md) and
> [`docs/SOTTOMISSIONE.md`](docs/SOTTOMISSIONE.md).
>
> **First submission: 13 September 2026.** Entry `PNn227rxP3bVByS37W41` was accepted
> and scored — overall **0.045929**, rank **446 of 920 teams**. The server read and
> scored the archive produced by the streaming packager, which settles that path
> end-to-end. The score itself is low and expected to be: only `pds` (0.413) beats the
> cell-context mean, and `fid` is negative. See
> [CP-0006](docs/checkpoints/0006-prima-sottomissione-e-punteggio.md).
> `trial-00-controls` was **not** submitted and must not be (D-017).

## Data strategy audit (11 September 2026)

Scientific recommendations and acquisition priorities: `docs/data_strategy_2026-09-11.md`.
Reproduce local input and gene coverage checks with `scripts/12_audit_data_strategy.py`.
Public Figshare metadata catalog: `scripts/13_catalog_public_data.py`.
HIPSCI metadata retrieval and target support: scripts `14` and `15`.
These scripts put small reports in `reports/data_audit`; expression inputs remain untouched.

> **Superseded as an acquisition order**, twice — by the review below and then by the
> 12 September review. Its preprocessing contract (§4) and its local measurements (§1)
> are still current. See [`docs/REGISTRO.md`](docs/REGISTRO.md), sheet R-003.

## Review and reorientation (11 September 2026)

`docs/revisione_analisi_2026-09-11.md` revises the audit above. Three of its conclusions
change, and the acquisition order changes with them.

The contexts are not anonymous to their transcriptomes: **A** is T-lymphoid (CD3D/E/G,
ZAP70, DNTT, RAG1, TAL1; male), **B** an epithelial-mesenchymal hybrid carrying eye-field
transcription factors (CLU, KRT7/8/18 with VIM, PAX6/LHX2/MITF; female), **C** squamous
epithelium (TP63, KRT5/13/14/15, SOX2; male). None is erythroid and none is pluripotent,
so K562 is the wrong lineage for all three and the iPSC atlases match none of them.
Reproduce with `scripts/16_probe_context_identity.py`.

The scorer was already installed. `scripts/17_extract_scorer_contract.py` pulls the six
decisive metrics and their clamps out of `cell-eval2` itself. The clamps are sharply
asymmetric: `mse` cannot go below 0, predicting no change costs about -0.04 on `nmae`,
and `pds` ranks by **cosine distance on the signed delta**, so it is scale-invariant.
Four of the six metrics score direction or ranking. Commit on direction, shrink magnitude.

> **Two claims in this section are flagged** ([`docs/REGISTRO.md`](docs/REGISTRO.md),
> sheet R-001). The `mse` floor applies to the *normalized score*, not to the error, so
> shrinking can still forfeit every positive point on that metric, and the PDS is
> scale-invariant on the already-transformed delta — not under shrinkage applied in
> count space. "Commit on direction, shrink magnitude" is therefore a posture under
> test, not a settled rule: [`docs/DECISIONI.md`](docs/DECISIONI.md), D-006. The
> eye-field reading of context **B** is a weak hypothesis (PAX6 34, LHX2 38, MITF 27
> CPM against CLU 7,857): its epithelial-mesenchymal signature is the solid part.

## Adversarial candidate review (12 September 2026)

`docs/candidate_adversarial_review_2026-09-12.md` audits an external PDF's dataset
claims against live endpoints, remote file bytes and the installed scorer, and reorders
acquisition again — this time by measured coverage rather than by lineage alone.

CD4 (GSE314342) becomes the first target: 297/300 panel genes in the curated library,
293 observed in D1 Rest, though only 239 have at least 30 cells. Orion HCT116 is second
(300/300 in library, 168 observed in Batch1, all under 30 cells). K562 is retained as an
ablation rather than discarded. Pisces has no downloadable matrices, and several
accessions in the source PDF were misattributed. With 8.4 GB of RAM and ~28 GB of free
disk, no full atlas is downloaded on this machine.

Per-target evidence: `reports/candidate_verification/panel_coverage.csv`. Decisions and
their revisit conditions: [`docs/DECISIONI.md`](docs/DECISIONI.md).
