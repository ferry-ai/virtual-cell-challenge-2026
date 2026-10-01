# docs — where each kind of information lives

The rules for every document (nothing deleted, checkpoints never edited, registry states) are in
the root `CLAUDE.md`, which is always loaded. This page is the map of **canonical homes**: a piece
of information updated by hand has one home, and anywhere else it appears only as a link or as a
short extract that names its home. Read the row you need, not the whole folder.

## Canonical homes

| Information | Home | Updated when |
|---|---|---|
| Current state and general direction | `docs/PROGETTO.md` §0 | after every scored submission, and when the direction changes |
| Official scores, one row per submission, with the outcome of its registered rule | `reports/invii/README.md` | after every score, with `comparison.json` and a checkpoint; PROGETTO §0 keeps only the best observed and the reference recipe |
| State, first reads and evidence of one area of the work | `docs/AMBITI.md`, that area's section | in the same commit as the evidence that changes it (D-048) |
| What the project knows, does not know, and its known weaknesses | `docs/PROGETTO.md` §3–§5 | when a result changes a conclusion |
| Priorities and dependencies between plans | `docs/PIANI.md` §2 | when a priority changes |
| Assignment, next step and closure evidence of one plan | its card in `docs/piani/` (`docs/piani/CLAUDE.md`) | by whoever takes, hands off or closes the work (PIANI §3) |
| Initial implementation prompt | `docs/PROMPT_CLAUDE.md`, pointing to R-LEAD; `docs/CONSEGNA_TEAMMATE.md` only adds portable environment checks | when the entry path changes; do not duplicate the plan in the prompt |
| Procedures: submission path and rules, Colab, stages, final set | `docs/PROCEDURE.md` | when the live path changes |
| Job preflight, incident ledger, operational traps | `docs/ERRORI.md` | when a failure is recorded |
| Method errors already made | `docs/ERRORI.md`, "Errori di metodo già commessi" | a new row with its source; old rows are not rewritten |
| Research scope for new targets and contexts, leakage controls (D-044) | `docs/GENERALIZZAZIONE.md` | when the research rules change |
| Agent infrastructure and its interface with the project | `docs/AGENTI.md` | when the interface changes, or a system is retired or revived |
| Evidence | `reports/<categoria>/<tema>_<data>/`, never edited; the map is `reports/README.md` | a new folder for every run |
| What happened, when, on what evidence | `docs/checkpoints/`, immutable; `docs/checkpoints/INDICE.md` with "Corretto da" | one checkpoint per significant event |
| Whether a document can be relied on | `docs/REGISTRO.md`; for one path, `python scripts/31_check_docs.py --status <path>` | when a document changes state |
| What was decided, why, and when to reopen it | `docs/DECISIONI.md`: a table row and a `### D-NNN — …` section | when a decision is taken or superseded |
| What left the tree, and the command that brings it back | `docs/ARCHIVIO.md` | a section per cleanup, a row per file |
| Texts that no longer guide the work | `docs/storico/`, indexed by its `README.md` | moved there with their text unchanged, except paths |
| The submission contract | `docs/SOTTOMISSIONE.md` §1–2 | `da-verificare`: §3 and §6 name archived stages (sheet R-015) |

`scripts/31_check_docs.py` enforces the structure of the registry, the decisions and the index,
and every link in the documents that route agents. It says nothing about whether a claim is true.

## Writing here

- **A checkpoint:** when to write one, the command that numbers it and how it is corrected are the
  header of `docs/checkpoints/INDICE.md`, and only there.
- **A synthesis** (a map, an index, a state page) says its perimeter, its sources and when it is
  updated. It routes to the evidence and does not become evidence: keep the claim types and the
  caveats of what it cites. If it grows into a summary of everything, shorten it; do not add a
  second one.
- **PROGETTO §0** is rewritten, not appended to. What leaves it goes to `docs/storico/` when it is
  worth keeping as it was (as on 28 and 30 September), with a registry row.
- **A contradicted document** keeps its text: its registry row changes state and a review sheet
  lists the disputed claims.
- **Every new file** under `docs/` gets a registry row in the same commit.

## The analyses of 11–15 September, and other superseded texts

They are in `docs/storico/`, with an index: the eight analyses of 11–15 September (benchmarks,
encoder inputs, SVD, the first reviews and data strategy), the history sections of the root
README and the old sections of PROGETTO. Most of the experiments they discuss are closed and their
code is archived. They are not a guide to today's pipeline. Open one when a decision or a
checkpoint cites it — a checkpoint names it as `docs/<file>`, and it is found in `docs/storico/`
— after checking its state with `--status`: their states differ.
