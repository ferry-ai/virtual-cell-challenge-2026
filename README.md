# Virtual Cell Challenge 2026

**DATA ARCHIVE — REUSE, DO NOT REINGEST:** [current dataset index, versions and hashes](reports/modelli/percorso_riusabile_2026-10-05/cloud_catalog_r11/manifest.json)
and [verified selection, data and remaining gaps](reports/analisi/riconciliazione_banca_2026-10-05/README.md).
The main path is verified archive → reusable banks and cell samples → extended training.
**Next training — reuse the existing bank:** [single entry point, canonical source registry and frozen release](reports/modelli/banca_canonica_2026-10-07/README.md) (7 October; the [5 October page](reports/modelli/percorso_riusabile_2026-10-05/README.md) remains the evidence of the td 36 release).
**Training coverage is tracked separately:** [all expected inputs, frozen](reports/analisi/riconciliazione_banca_2026-10-05/frozen/expected_r3.json).
Archived GB and launched jobs do not certify that every context contributed to a fitted model.

**Start here:** agents read [CLAUDE.md](CLAUDE.md), then
[current state](docs/PROGETTO.md) §0 and the [plan index](docs/PIANI.md) §2–3.
There is one implementation plan: [R-LEAD](docs/piani/strategia-scientifica.md),
with a [ready-to-use Claude prompt](docs/PROMPT_CLAUDE.md).
On another machine, also read the [environment handoff](docs/CONSEGNA_TEAMMATE.md).

After td 29, no neural model is promoted. The current reference and observed scores
are maintained in PROGETTO and the [submission ledger](reports/invii/README.md).
Since 10 October candidate names carry their author, `td NN` for Davide and `ta NN` for
Alfredo (D-058); the ledger maps the historical `tNN` names of both, with entry IDs.
The earlier training queues and instructions are [preserved as history](docs/storico/rinnovo_2026-10-01/INDICE.md).

This README covers the challenge and setup. Use [PROCEDURE](docs/PROCEDURE.md) for
execution, [AMBITI](docs/AMBITI.md) for one area's evidence, and
[reports](reports/README.md) for dated results. The final test set D/E/F arrives
on **22 October 2026**; submissions close on **5 November 2026**.

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
