# Working agreement for agents

## CRUCIALE — dove eseguire i calcoli (leggere prima di ogni lavoro)

**Configurazione del progetto confermata dal proprietario il 2 ottobre 2026:
Colab = CPU stabile; Kaggle = GPU.** Prima di ogni calcolo pesante leggere
[PROCEDURE §3](docs/PROCEDURE.md#3-job-su-colab-e-kaggle), sede della procedura operativa.

- **Portatile:** sviluppo, fixture e test piccoli. Un job pesante in locale richiede
  una motivazione esplicita basata su risorse, input e runtime disponibili.
- **Colab CPU:** destinazione preferita per banchi C/J, preprocessing, predizione,
  scoring e altri calcoli pesanti su CPU. Questi lavori non richiedono una GPU.
- **Kaggle GPU:** destinazione preferita per training neurale che usa effettivamente
  CUDA; selezionare una GPU nel notebook non trasferisce da solo modello e tensori.

Misurare RAM libera, CPU, disco, accessi e job attivi prima del lancio: i circa 10 GB
liberi ricordati per Colab non sono una quota garantita. Il vantaggio di velocità si
misura, non si deduce dalla sola RAM. Preparare gli input e il codice necessari:
**la sincronizzazione standard su Drive non include `reports/`**, dove vivono i banchi
di ricerca. La mancanza di quel pacchetto è un passo da completare, non una ragione
automatica per eseguire ore di calcolo sul portatile. Restano valide le autorizzazioni
in chat e il preflight: questa regola di instradamento non autorizza nuovi job o acquisti.

The project: predict how cells respond to 300 CRISPRi knockdowns in cell contexts never seen
perturbed (Virtual Cell Challenge 2026). Only the final set counts: three new contexts, D, E and
F, released on 22 October; submissions close on 5 November. Where the project stands and where it
is heading is one page, [`docs/PROGETTO.md`](docs/PROGETTO.md) §0.

## NON NEGOZIABILE — tutte le linee e tutti i contesti idonei

**Mandato del proprietario, 3 ottobre 2026 (D-053):** il percorso principale deve includere
tutte le linee e tutti i contesti scientificamente utilizzabili del catalogo, con le
esclusioni richieste dalla validazione. Campionare cellule non autorizza a eliminare
contesti per comodità, dimensione, somiglianza alla gara o overlap dei bersagli.
Prima di dichiarare completo un corpus o training, verificare **copertura prevista e uso
effettivo**, con ogni lacuna o esclusione nominata e motivata. Un pilot ridotto resta tale.
La regola completa e i requisiti di accettazione stanno in
[GENERALIZZAZIONE §2.1](docs/GENERALIZZAZIONE.md#21-copertura-integrale-vincolo-non-negoziabile).

**Mandatory reading is this file, PROGETTO §0 and the row of the task table below that matches
your task — nothing else.** Everything else is read on demand, by section, and each row says where
to stop. State, scores and assignments are never written here: they change, and each has one home
(`docs/CLAUDE.md` lists them all).

## Four perimeters

| Perimeter | What it holds | Entry | Who can leave it aside |
|---|---|---|---|
| VCC project | data, models, evaluation, the live pipeline code | [`docs/AMBITI.md`](docs/AMBITI.md), one section per area | whoever works only on the launch base |
| Execution tools | Colab and Kaggle jobs, generation, packaging, submissions | [`docs/PROCEDURE.md`](docs/PROCEDURE.md), by section | whoever only analyses or writes |
| Agent infrastructure | the launch base `C:/Users/ferra/agent-hub` (outside this repo), the orchestrator and cycles retired on 23 September, coordination between sessions | [`docs/AGENTI.md`](docs/AGENTI.md) | whoever works on data, models or submissions |
| Archive and history | decisions, checkpoints, registry, archived code, superseded analyses, `reports/storico/` | the last row of the task table | anyone, until a current document cites it |

## Task table: read this, then stop

| If you must… | Read | Stop there; leave aside |
|---|---|---|
| Take, resume or hand off work | [`docs/PIANI.md`](docs/PIANI.md) §2–3, then the one plan card | other cards; the "next steps" of dated reports |
| Know an area: state, evidence, plan | that section of `docs/AMBITI.md`, then only the sources it cites | the other sections; browsing `reports/` folder by folder |
| Change the generator or another stage or module | `scripts/CLAUDE.md` or `src/vcc2026/CLAUDE.md`; the stage's docstring and test; AMBITI §3 for the evidence | submission rules and Colab, unless you then generate a trial |
| Study a data source, design a predictor | AMBITI §4–5; [`docs/GENERALIZZAZIONE.md`](docs/GENERALIZZAZIONE.md) (scope D-044, leakage); `reports/sorgenti/README.md`; the table of [`docs/STRADE.md`](docs/STRADE.md), then the entries your design relates to (what was tried, why it failed, what would reopen it) | submissions, Colab, agent infrastructure |
| Read an official score | PROCEDURE §2, point 7; the latest scored checkpoint as a model; `reports/invii/README.md` | bench scores, which are not VCC scores |
| Prepare, generate or submit a trial | PROCEDURE §1–2; `reports/CLAUDE.md`, "What a submission leaves"; `configs/CLAUDE.md`, and the recipe and stage-45 options of the submission you start from (PROCEDURE §1 names those of t28) | the analyses in `docs/storico/` |
| Prepare or follow a Colab or Kaggle job | PROCEDURE §3; [`docs/ERRORI.md`](docs/ERRORI.md) from "Prima del prossimo job" to "Registro immutabile", and its operational lessons | the job's own log: it syncs only when the job ends |
| Prepare the final set (D, E, F) | PROCEDURE §7 | |
| Draw a conclusion, write a report or a checkpoint | ERRORI, "Errori di metodo già commessi" (one table); `reports/CLAUDE.md` or `docs/CLAUDE.md`; when the outcome of a rule is read, the entry of [`docs/STRADE.md`](docs/STRADE.md) it opens or updates, in the same commit as the checkpoint | |
| Run or change research code in a report | the table "Il codice di ricerca che sta qui" in `reports/README.md` | editing a file other benches import: copy it into your new folder |
| Work on the launch base or coordinate agents | `docs/AGENTI.md`; then the hub's own instructions, outside the repo | the project perimeters |
| Reconstruct a past decision or result | the table atop [`docs/DECISIONI.md`](docs/DECISIONI.md), then that one section; the checkpoint it cites, via [`docs/checkpoints/INDICE.md`](docs/checkpoints/INDICE.md) and its column "Corretto da"; `--status` (below) on each document it cites | the other sections; `docs/storico/` unless cited |

**Before relying on any document your row does not name**, ask about that path alone:
`python scripts/31_check_docs.py --status <path>` prints its registry state (`attuale`,
`da-verificare`, `superato`, `storico`), what replaced it, its review sheet, what corrected a
checkpoint, and the verdict of the folder index that lists it. When they disagree, both are shown:
trust the stricter one and say so. A path `reports/<folder>/` written before 28 September is now
`reports/<categoria>/<folder>/`; the command follows it.

## Global rules

**Evidence.** This repository was built quickly by agents; its failure mode is confident prose
outrunning what was measured.
- A script existing is not proof it ran; a run completing is not proof its output is right;
  ingesting data is not proof a model improved.
- An agent-written summary is not evidence: trace each claim to a report, a script output, a
  primary source or your own re-run, and cite the path. Label it: measured, interpretation,
  hypothesis, proposal or implemented.
- Summarising is where claims get promoted: keep the caveats of the source (CP-0002). A newer
  document is not more correct by being newer: if two disagree without decisive evidence, record
  the contradiction as open.
- Register a prediction, with the rule you will read it by, before the submission; the threshold
  does not move after the number is known (CP-0030).
- Never invent dates, results, approvals or decisions; read times with `date` or from a commit,
  and say so when you reconstruct history from artifacts.

**Nothing is lost.** Reports, checkpoints and data are never deleted or overwritten: a new run
writes to a new `--out` or report folder. A checkpoint is never edited: a correction is a new
checkpoint and the column "Corretto da". A contradicted document gets a registry status and a
review sheet, not a rewrite; `da-verificare` becomes `superato` only by naming what replaced it.
Code and documents leave the live tree only through the archive (tag, rows in
`docs/ARCHIVIO.md`, `git rm`); an untracked file goes to the Recycle Bin. New material in `docs/`
or `reports/` gets a registry row.

**Learning from failures** (D-055). Before designing a model, a correction or an experiment, read the table of
[`docs/STRADE.md`](docs/STRADE.md). A new protocol has a section "Precedenti": the entries it relates to, how its design
differs from each mechanism, and the cheap early signal that will stop the work if the same failure shows again. An
outcome read (passed, failed, incomplete) becomes a checkpoint and an entry there, with the mechanism labelled verified,
hypothesised or unknown; where a check can recognise the failure, the lesson becomes a guard in code.
`scripts/31_check_docs.py` enforces the form, not the truth.

**The owner authorises** anything that spends quota (a submission, cloud compute, a launch of
other agents), every download and every push, in chat. Past goes for submissions are transcribed
in `reports/invii/trial_2026-09-22/autorizzazioni.md`; a new agent confirms them in chat before
using one. On cloud compute two historical records disagree, and the contradiction is open: R-V2 (F7)
notes Colab and Kaggle as authorised on 27/09, while R-REV (28/09) asks for it in chat.
Those original cards are preserved in `docs/storico/rinnovo_2026-10-01/docs/piani/`. Until the owner settles it, ask. The repository is **public** on GitHub,
one branch `main`: never commit a secret or private data, and never write a cell-line identity
next to the contexts A, B, C.

**Shared checkout.** Other agents work in this folder. Start from `git status --short`; an
untracked file or an unassigned plan is not proof that nobody is working on it. Re-read before
patching and preserve others' changes; never touch the files of a session that is still active.
Commit your own work, file by file and by name (never `git add -A`), before your session ends; for
a file others are editing too, commit only your own lines (`docs/AGENTI.md` §3). Work a finished
session left uncommitted is committed as it is, crediting its author. Session scratchpads are
temporary: results go into `reports/` first (D-048). A worker launched by the agent hub does not
commit: its launcher does.

**No preset limits** (D-045): do not estimate durations or cap the work. A candidate that fails its
registered rule does not close the day: pivot to another one while the quota window is open.

**Conventions.** Documentation in plain Italian; code, identifiers, docstrings and commit messages
in English. Data live outside the repository at `C:/Users/ferra/vcc2026-data` (D-001;
`VCC2026_DATA_ROOT` overrides it); raw inputs are never modified, large data files are not moved,
and no dataset, venv, cache or copy of the repository goes inside it. Run project code through
`.\scripts\py.cmd` and `.\scripts\vcc.cmd`; scripts 30 and 31 need only Python 3.11+. Edit files
with the editor tools or a script saved to a file: in Git Bash a heredoc piped into `py` halves
backslashes (ERRORI, operational lessons).

## Repository map

```
vcc2026/
├── CLAUDE.md            this agreement, for every agent
├── AGENTS.md            the pointer for Codex
├── README.md            the task, the scoring and the setup, for people (in English)
├── requirements*.txt    dependencies; the venv lives in the data root
├── configs/             paths and constants, the stage-45 trial, one recipe per submission
├── src/vcc2026/         the library of the live stages, one module per concern
├── scripts/             the numbered stages, and the wrappers py.cmd and vcc.cmd
├── tests/               unittest suite; test_live_tree keeps these maps true
├── notebooks/           the Colab dispatcher and its job scripts (docs/PROCEDURE.md §3)
├── docs/                state, areas, plans, procedures, errors, decisions, registry, archive, checkpoints
└── reports/             the evidence, reports/<categoria>/<tema>_<data>/, with a README per category
C:/Users/ferra/vcc2026-data/   data, venv and artifacts, outside the repository (D-001)
```

Only code that produces or scores a submission is in the tree (D-040, D-043); the research
benches live in the report folders that used them. `configs/`, `src/vcc2026/`, `scripts/`,
`docs/`, `docs/piani/` and `reports/` each have a `CLAUDE.md` with the index and rules of that
folder: Claude Code loads it when you read a file there, other agents read it before editing there.

## Before you finish

```bash
python scripts/31_check_docs.py
.\scripts\py.cmd -m unittest discover -s tests
```

The checker verifies paths, anchors, checkpoint numbering and registry metadata; the suite keeps
the tables of stages and modules true. Neither says whether a claim is true: that is your job.
