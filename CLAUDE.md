# Working agreement for agents

## Start here

1. [`docs/PROGETTO.md`](docs/PROGETTO.md) §0 — where the project stands today, on one page:
   best score, what is in flight, what is decided next.
2. The last three rows of [`docs/checkpoints/INDICE.md`](docs/checkpoints/INDICE.md).
3. The row below that matches your task, and only what it names. For anything that runs
   code, that includes [`docs/LAVORO.md`](docs/LAVORO.md), the one operational guide.

Before you rely on any other document, check its row in [`docs/REGISTRO.md`](docs/REGISTRO.md):
several contain conclusions that later work corrected.

| Your task | Read | Leave aside |
|---|---|---|
| Prepare, generate or submit a trial | LAVORO §1–2; `reports/CLAUDE.md`, which lists what a submission leaves, with a complete example; the latest recipe in `configs/recipes/` | the analyses of 11–15 September in `docs/` |
| Read an official score | LAVORO §2, point 7; `reports/anchors_2026-09-17/`; the latest checkpoint as a model | the benches' local scores, which are not VCC scores |
| Prepare the final set (D, E, F; 22 October) | LAVORO §7 | |
| Queue or follow a Colab job | LAVORO §3 | the job's own log: it syncs only when the job ends |
| Change a stage | `scripts/CLAUDE.md`; the stage's docstring and its test | |
| Change a library module | `src/vcc2026/CLAUDE.md`, which says which stages import it | |
| Know why something was decided, or when to reopen it | the table at the top of `docs/DECISIONI.md`, then that one section | the other sections |
| Find the evidence behind a claim | the checkpoint or decision that makes it, then the report it cites | browsing `reports/` |
| Bring back archived code | `docs/ARCHIVIO.md`: restore from the tag, with its test | rewriting it |
| Write in `docs/` or `reports/` | `docs/CLAUDE.md` or `reports/CLAUDE.md` | |

`src/vcc2026/`, `scripts/`, `reports/` and `docs/` each have a `CLAUDE.md` with the rules of
that folder. Claude Code loads it when you read a file there; other agents read it before
editing there.

## What is live

Only the code that produces or scores a submission is in the tree (D-040, D-043):
- the stages are the table in `docs/LAVORO.md` §4;
- the modules are the table in `src/vcc2026/CLAUDE.md`;
- `tests/test_live_tree.py` fails if either table disagrees with the tree, or if a definition
  has no live caller.

Everything else is in the tags listed file by file in `docs/ARCHIVIO.md`: the orchestrator,
the pairwise oracle, the chain of cycles, the pseudobulk benchmark, the conditioned predictor,
the source probes, the remote ingestion, trial-00 and trial-01, the expired plans.

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
- Scripts are numbered and single-purpose; new ones continue the sequence
  (`scripts/CLAUDE.md`).
- Edit files with the editor tools, or with a script saved to a file. In Git Bash, a
  heredoc piped into `py` halves backslashes: on 24 September an escaped `\r\n` written that
  way became a real line break.

## Before you finish

```bash
python scripts/31_check_docs.py
.\scripts\py.cmd -m unittest discover -s tests
```

The checker verifies paths, anchors, checkpoint numbering and required metadata, and the
suite includes `tests/test_live_tree.py`, which keeps the tables of stages and modules true.
Neither says whether a claim is true — that is still your job.
