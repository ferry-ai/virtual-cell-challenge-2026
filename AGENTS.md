# Instructions for Codex and any other agent

**CRUCIALE, prima di ogni lavoro:** leggere subito il riquadro iniziale di
[`CLAUDE.md`](CLAUDE.md): **Colab = CPU stabile; Kaggle = GPU; portatile = sviluppo
e test piccoli.** La procedura per scegliere il runtime e preparare i job è
[PROCEDURE §3](docs/PROCEDURE.md#3-job-su-colab-e-kaggle).

The working agreement for every agent in this repository is `CLAUDE.md`, and it applies to Codex
in full: read it before anything else, then only what its task table names for your task.

**NON NEGOZIABILE:** applicare anche il riquadro di `CLAUDE.md` sulla copertura di tutte le
linee e i contesti idonei (D-053), con la verifica dell'uso effettivo e le esclusioni di
validazione definite in [GENERALIZZAZIONE §2.1](docs/GENERALIZZAZIONE.md#21-copertura-integrale-vincolo-non-negoziabile).

Codex does not load the folder guides by itself: before editing a file in `configs/`,
`src/vcc2026/`, `scripts/`, `docs/`, `docs/piani/` or `reports/`, read that folder's `CLAUDE.md`.
