# Working agreement for agents

## Read this first

Read these, in this order, before anything else:

1. [`docs/PROGETTO.md`](docs/PROGETTO.md) §0 — where the project stands today, on one page:
   best score, what is in flight, what is decided next.
2. [`docs/LAVORO.md`](docs/LAVORO.md) — the live pipeline: which stages run, in what
   order, with which commands; the rules for a submission and for Colab.
3. The last three rows of [`docs/checkpoints/INDICE.md`](docs/checkpoints/INDICE.md).

That is enough to work. Everything else is reference, to open when a task needs it — and
before you rely on any document, check its row in [`docs/REGISTRO.md`](docs/REGISTRO.md):
several contain conclusions that later work corrected.

| File | Answers |
|---|---|
| `docs/PROGETTO.md` | What are we solving, where are we, what is uncertain |
| `docs/LAVORO.md` | How the live pipeline is run, and the rules that protect it |
| `docs/checkpoints/` | What happened, when, on what evidence — immutable |
| `docs/DECISIONI.md` | What we chose, why, and when to reopen it |
| `docs/REGISTRO.md` | Which documents and data can still be relied on |
| `docs/ARCHIVIO.md` | What left the tree, and how to bring it back |

## What is live

Only the code that produces or scores a submission is in the tree (D-040, 23 September
2026): 22 numbered scripts, listed one per line in `docs/LAVORO.md` §4, the modules they
import, and their tests. Everything else — the orchestrator, the pairwise oracle, the chain
of cycles, the pseudobulk modular benchmark, the conditioned predictor, the source probes,
the remote ingestion, the one-off stages of the trial-01 pipeline, the expired plans — is
in the tag `archivio/pre-pulizia-2026-09-23`, file by file in `docs/ARCHIVIO.md`.

- There is no chain of cycles, no orchestrator and no morning plan: you work in a session
  with the owner, and the owner authorises anything that spends quota.
- If you need archived code, restore it from the tag with its test; do not rewrite it.
  Reviving a subsystem is a decision: record it in `docs/DECISIONI.md`.
- Checkpoints still name archived paths. That is expected; the checker accepts them.

## Evidence discipline

This repository was built quickly by agents, and its main failure mode has been
confident prose outrunning what was measured. Hold these lines:

- **A script existing is not proof it ran.** A run completing is not proof the output
  is correct. Successful ingestion is not proof of model improvement.
- **An agent-written summary is not evidence.** Trace every factual claim to a report,
  a script output, a primary source, or your own re-run. Cite the path.
- **Label the claim type**: measured, interpretation, hypothesis, proposal, or
  implemented. The map uses these words on purpose; keep using them.
- **A newer document is not automatically more correct.** When two documents disagree
  and neither has decisive evidence, record the contradiction as open rather than
  picking a winner.
- **Summarising is where claims get promoted.** The documented failure in this repo is a
  chain: "absent from the essential panels" → "non-essential" → "effects are small by
  construction", each step reading like a paraphrase and each one a deduction. Before
  restating an earlier document's conclusion, check whether it carried a caveat you are
  about to drop. See CP-0002.
- **Never overwrite a probe output or a report.** A failed request documents what the
  endpoint looked like that day. New runs go to a new `--out` or `--report-dir`, the way
  every stage in `docs/LAVORO.md` refuses to overwrite.
- **Register the prediction before the submission**, with the rule you will read the
  result by; the threshold does not move after the number is known (CP-0030).
- Never invent dates, results, reviewer approvals, or decisions. If you reconstruct
  history from artifacts, say so in the text.

## When to write a checkpoint

Write one when a dataset is adopted or rejected, a benchmark completes, a submission is
scored, a hypothesis is contradicted, or the modeling or validation strategy changes. Not
for a tool call, an edit, or an iteration.

```bash
python scripts/30_new_checkpoint.py --slug cd4-benchmark --title "Primo benchmark su CD4"
```

**Never edit an existing checkpoint.** A correction is a new checkpoint plus the
"Corretto da" column in `docs/checkpoints/INDICE.md`. Historical disagreement has to
stay readable.

## When you touch documents, code or data

- A document that is contradicted gets a status change and a review sheet listing the
  specific disputed claims — not deletion, and not a rewrite of the whole file.
- `da-verificare` never becomes `superato` without naming the material that replaced it.
- Reports, checkpoints and datasets are never deleted. Do not move large data files or
  copy datasets into the repository.
- Code and documents that stop being live leave the tree only through the archive: an
  annotated tag, rows in `docs/ARCHIVIO.md`, then `git rm` (D-040, `docs/LAVORO.md` §5).
  An untracked file goes to the Recycle Bin, never through a hard delete.
- New material in `docs/` or `reports/` needs a registry row; the checker enforces it.

## Conventions

- Human-facing documentation in plain Italian. Code, identifiers, CLI flags,
  docstrings and commit messages in English, matching the existing analysis scripts.
- Data lives outside the repo at `C:/Users/ferra/vcc2026-data` (`configs/config.yaml`,
  overridable with `VCC2026_DATA_ROOT`). Raw inputs are never modified in place.
- Run project code through the wrappers, which set UTF-8 and `PYTHONPATH`:
  `.\scripts\py.cmd script.py` and `.\scripts\vcc.cmd`. The two documentation scripts
  (30, 31) are standard-library only and run under any Python 3.11+.
- Scripts are numbered and single-purpose; new ones continue the sequence.

## Before you finish

```bash
python scripts/31_check_docs.py
.\scripts\py.cmd -m unittest discover -s tests
```

The checker verifies paths, anchors, checkpoint numbering and required metadata. It
says nothing about whether a claim is true — that is still your job.
