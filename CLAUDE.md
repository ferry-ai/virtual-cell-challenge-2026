# Working agreement for agents

## Start here

1. [`docs/PROGETTO.md`](docs/PROGETTO.md) §0 — where the project stands today, on one page:
   best score, what is in flight, what is decided next.
2. [`docs/PIANI.md`](docs/PIANI.md) — open priorities, dependencies and the relevant plan
   card. Before taking work, check its assignment and the shared-workspace rules in §3.
3. The last three rows of [`docs/checkpoints/INDICE.md`](docs/checkpoints/INDICE.md).
4. The row below that matches your task, and only what it names. For anything that runs
   code, that includes [`docs/LAVORO.md`](docs/LAVORO.md), the procedural guide.

Before you rely on any other document, check its row in [`docs/REGISTRO.md`](docs/REGISTRO.md):
several contain conclusions that later work corrected.

| Your task | Read | Leave aside |
|---|---|---|
| Choose, resume or hand off an open plan | `docs/PIANI.md`; `docs/piani/CLAUDE.md`; the one relevant plan card | treating old reports' next steps as current assignments |
| Prepare, generate or submit a trial | LAVORO §1–2; `reports/CLAUDE.md`, which lists what a submission leaves, with a complete example; the latest recipe in `configs/recipes/` | the analyses of 11–15 September in `docs/` |
| Read an official score | LAVORO §2, point 7; `reports/anchors_2026-09-17/`; the latest checkpoint as a model | the benches' local scores, which are not VCC scores |
| Prepare the final set (D, E, F; 22 October) | LAVORO §7 | |
| Find data, choose sources or design a generalizing predictor | `docs/GENERALIZZAZIONE.md`; D-044 in `docs/DECISIONI.md` | ranking datasets only by overlap with the current 300 targets |
| Queue or follow a Colab job | LAVORO §3 | the job's own log: it syncs only when the job ends |
| Change a stage | `scripts/CLAUDE.md`; the stage's docstring and its test | |
| Change a library module | `src/vcc2026/CLAUDE.md`, which says which stages import it | |
| Know why something was decided, or when to reopen it | the table at the top of `docs/DECISIONI.md`, then that one section | the other sections |
| Find the evidence behind a claim | the checkpoint or decision that makes it, then the report it cites | browsing `reports/` |
| Bring back archived code | `docs/ARCHIVIO.md`: restore from the tag, with its test | rewriting it |
| Write a recipe or change a setting | `configs/CLAUDE.md` | |
| Write in `docs/` or `reports/` | `docs/CLAUDE.md` or `reports/CLAUDE.md` | |

## Repository map

```
vcc2026/
├── CLAUDE.md            this agreement, for every agent
├── AGENTS.md            the pointer for Codex
├── README.md            the task, the scoring and the setup, for people (in English)
├── REPORT_2026-09-24_stato_e_interpretazioni.md   state and interpretations of 24 September
├── requirements*.txt    dependencies; the venv lives in the data root
├── configs/             paths and constants, the stage-45 trial, one recipe per submission
├── src/vcc2026/         the library of the live stages, one module per concern
├── scripts/             the numbered stages, and the wrappers py.cmd and vcc.cmd
├── tests/               unittest suite; test_live_tree keeps these maps true
├── notebooks/           the Colab dispatcher and its job scripts (docs/LAVORO.md §3)
├── docs/                map, working guide, decisions, registry, archive, checkpoints
└── reports/             the evidence, one folder per experiment
C:/Users/ferra/vcc2026-data/   data, venv and artifacts, outside the repository (D-001)
```

`configs/`, `src/vcc2026/`, `scripts/`, `docs/` and `reports/` each have a `CLAUDE.md` with the
index and the rules of that folder. Claude Code loads it when you read a file there; other
agents read it before editing there. `tests/test_live_tree.py` fails if this map, or one of
those indexes, stops matching the tree.

## What is live

Open work is indexed in `docs/PIANI.md`, with separate editable cards under `docs/piani/`.
These manual plans do not start jobs or revive the retired orchestrator. Current status
lives in PROGETTO, procedures in LAVORO, evidence in reports/checkpoints, and validity in
REGISTRO. In a shared checkout, preserve other agents' changes and re-read before patching;
an untracked file or an unassigned plan is not evidence that nobody is working on it.

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

### Research scope: new targets and new contexts (D-044)

- **Shared perturbation targets with the current panel are not required for a useful
  dataset.** Do not reject a source or discard its other targets solely for low or zero
  overlap with the current 300. Retain distant contexts as research candidates.
- Distinguish perturbation targets from measured response genes. Missing response
  measurements keep a mask (D-009); eligibility without target overlap does not imply
  that incompatible response axes or assays can be concatenated without reconciliation.
- The production same-target transfer pipeline is a baseline, not the limit of the
  research objective. Evaluate new-target, new-context and jointly new-target/context
  regimes separately. A target held out as unseen must have its perturbation outcomes
  excluded from training across every source and derived feature.
- More contexts improving generalization is a hypothesis to test, not an assumed result.
  Read `docs/GENERALIZZAZIONE.md` for source roles, leakage controls and the next work.

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
- There is one branch, `main`, on the laptop and on GitHub, where the repository is
  **public**: whatever is pushed is published. Push only with the owner's go, and never
  commit a secret or data that must stay private. Retired branches are tags `archivio/*`
  (`docs/ARCHIVIO.md`).

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
