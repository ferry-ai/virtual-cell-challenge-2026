# Working agreement for agents

## Read this first

Start from [`docs/PROGETTO.md`](docs/PROGETTO.md) — the project map — then
[`docs/checkpoints/0001-ricostruzione-stato-2026-09-12.md`](docs/checkpoints/0001-ricostruzione-stato-2026-09-12.md).
Do not treat `README.md` or any document in `docs/` as current until you have checked
its row in [`docs/REGISTRO.md`](docs/REGISTRO.md). Several documents contain
conclusions that later work corrected; the registry says which.

Four files hold the project's understanding of itself:

| File | Answers |
|---|---|
| `docs/PROGETTO.md` | What are we solving, where are we, what is uncertain |
| `docs/checkpoints/` | What happened, when, on what evidence — immutable |
| `docs/DECISIONI.md` | What we chose, why, and when to reopen it |
| `docs/REGISTRO.md` | Which documents and data can still be relied on |

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
  endpoint looked like that day. New runs go to a new `--out` destination, the way
  `scripts/27_verify_grok_leads.py` does.
- Never invent dates, results, reviewer approvals, or decisions. If you reconstruct
  history from artifacts, say so in the text.

## When to write a checkpoint

Write one when a dataset is adopted or rejected, a benchmark completes, a hypothesis
is contradicted, or the modeling or validation strategy changes. Not for a tool call,
an edit, or an iteration.

```bash
python scripts/30_new_checkpoint.py --slug cd4-benchmark --title "Primo benchmark su CD4"
```

**Never edit an existing checkpoint.** A correction is a new checkpoint plus the
"Corretto da" column in `docs/checkpoints/INDICE.md`. Historical disagreement has to
stay readable.

## When you touch documents or data

- A document that is contradicted gets a status change and a review sheet listing the
  specific disputed claims — not deletion, and not a rewrite of the whole file.
- `da-verificare` never becomes `superato` without naming the material that replaced it.
- Do not delete documents, reports or datasets. Do not move large data files or copy
  datasets into the repository. Cleanup candidates are listed in the registry and need
  the owner's explicit consent.
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
