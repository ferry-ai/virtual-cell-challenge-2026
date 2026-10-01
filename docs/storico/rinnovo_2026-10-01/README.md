# Virtual Cell Challenge 2026

> **Teammate handoff:** [brief, repository map and machine checks](docs/CONSEGNA_TEAMMATE.md),
> with a [ready-to-use Claude prompt](docs/PROMPT_CLAUDE_TEAMMATE.md) for the R-LEAD programme.

> **Today's plan for Claude: [cell-level data, quality and biological modelling](docs/piani/piano-giorno-2026-09-30.md).**
> Full dataset coverage, resumable ingestion, assay-aware QC and a model trained on individual cells where available.
> Research programme and promotion criteria: [modello competitivo](docs/piani/modello-competitivo.md).

**Zero-shot** prediction of the transcriptional response to CRISPRi knockdown in
cell lines never seen during training.

Submissions close **5 November 2026**. Final test set drops **22 October 2026**.

> **Start from [`docs/PROGETTO.md`](docs/PROGETTO.md) §0** — where the project stands
> today (best observed score +0.144845, t28; inconclusive improvement, t22 recipe remains the reference) — and [`docs/PROCEDURE.md`](docs/PROCEDURE.md),
> the live pipeline with its exact commands. Agents: the working agreement is
> [`CLAUDE.md`](../../../CLAUDE.md). Open work is indexed in [`docs/PIANI.md`](docs/PIANI.md); the
> evidence, filed by topic with the status of every folder, in
> [`reports/README.md`](reports/README.md).
> This README covers the task, the scoring and the setup. Its sections of 11–13 September
> (the plan by phases and the first reviews) moved on 28 September to
> [`docs/storico/README_2026-09-11_13.md`](../README_2026-09-11_13.md); six of
> their claims are flagged in [`docs/REGISTRO.md`](../../REGISTRO.md), sheet R-001. The
> submission contract is in [`docs/SOTTOMISSIONE.md`](../../SOTTOMISSIONE.md) §1.

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
evaluation requirements are in [`docs/GENERALIZZAZIONE.md`](../../GENERALIZZAZIONE.md)
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
  docs/                      <- state, plans, procedures, decisions, registry, checkpoints
  reports/                   <- the evidence, in eight categories (reports/README.md)

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
