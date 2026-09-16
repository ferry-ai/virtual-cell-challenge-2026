# Instructions for Codex and Grok

The working agreement for every agent in this repository is `CLAUDE.md`. It applies
to Codex and Grok in full: read it before anything else. The project map is
`docs/PROGETTO.md`.

The chain of cycles (plan → review → implementation → control) is described in
`docs/CICLO_GIORNALIERO.md`; `scripts/32_daily_cycle.py` moves it.

- **Codex, stage 2 of the morning cycle.** Started by the script with the skill
  `$revisione-piano` in `.agents/skills/`. Codex writes only inside the cycle's
  folder, `reports/ciclo_giornaliero/<giornata>/ciclo-01/`: the review, the sheet for
  Claude and the acceptance tests in `collaudo/`.
- **Codex in the desktop app, every later cycle.** The owner talks with Codex; when
  the owner asks for it, or has delegated it, Codex starts the next cycle with the
  skill `avvia-ciclo`. It writes a draft and runs `avvia`; it never writes a signal
  file and never starts Claude, Grok or the orchestrator by hand.
- **Grok, stage 4.** Started by the script, read-only, without web search. Grok writes
  nothing: it answers with the JSON its prompt asks for. A campaign of the orchestrator
  is something Grok requests in that JSON; the script validates and starts it.
