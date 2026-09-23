# Archivio — 23 settembre 2026

Il codice e i documenti tolti dall'albero di lavoro non sono perduti: stanno in un tag, e
questo file dice che cosa c'è dentro e come si riprende. **Nessun report, checkpoint o dato
è stato cancellato**, e i checkpoint continuano a citare per nome ciò che è archiviato,
come devono, perché sono immutabili.

| | |
|---|---|
| Tag | `archivio/pre-pulizia-2026-09-23` (annotato) |
| Punta a | `6cf3806`, l'ultimo commit con tutti i file qui elencati |
| Dove sta | solo in locale: il tag **non è stato inviato** a nessun remoto |
| Quanto | 244 file, 50.306 righe, di cui 128 file Python per 40.078 righe |
| Perché | [D-040](DECISIONI.md#d-040--il-codice-vivo-è-solo-quello-che-produce-o-valuta-una-sottomissione): nell'albero resta solo ciò che produce o valuta una sottomissione |

## Come si recupera

```bash
git show archivio/pre-pulizia-2026-09-23:scripts/44_calibrate_transfer.py              # a schermo
git show archivio/pre-pulizia-2026-09-23:scripts/44_calibrate_transfer.py > 44.py      # su disco
git checkout archivio/pre-pulizia-2026-09-23 -- src/vcc2026/benchmark                  # un'intera cartella
```

Riprendere un file non basta a farlo girare: controlla con la chiusura degli import che i
moduli di cui ha bisogno siano ancora nell'albero, e altrimenti riprendi anche quelli.

## Che cosa non è stato toccato

- `reports/`: nessun file rimosso. I report dei sottosistemi archiviati restano la prova di
  ciò che hanno misurato;
- `docs/checkpoints/`, [DECISIONI.md](DECISIONI.md), [REGISTRO.md](REGISTRO.md) e i documenti
  di analisi (`docs/revisione_*`, `docs/candidate_*`, `docs/data_strategy_*`,
  `docs/BENCHMARK_*`, `docs/ENCODER_INPUTS.md`, `docs/SVD_E_RANGO.md`,
  [SOTTOMISSIONE.md](SOTTOMISSIONE.md));
- i dati fuori dal repository (`C:/Users/ferra/vcc2026-data`), le copie su Drive e la coda Colab.

## Come lo usa il controllo documentale

`scripts/31_check_docs.py` verifica che ogni percorso citato fra backtick, e ogni link
markdown, nella mappa, nel registro, nelle decisioni e nei checkpoint esista sul disco. Legge
anche **questo file**: un percorso elencato qui, o che sta sotto una cartella elencata qui
(voce che finisce con `/`), conta come esistente. Un percorso che sparisce senza comparire
qui resta un errore: è la differenza fra archiviare e perdere.

## Il precedente del 19 settembre

Il branch `refactor/pulizia` (worktree `../vcc2026-refactor`, tag
`archivio/pre-pulizia-2026-09-19`) aveva già fatto una pulizia simile, mai integrata. La
revisione del 19 (`reports/direzione_2026-09-19/VALUTAZIONE.md` §6) la fermava perché
toglieva la catena di cicli senza una decisione esplicita. Dal 22 settembre, poi, due cose che
quel branch archiviava sono tornate vive: lo stadio 45 (il generatore del t08, t10, t11) e la
lettura a intervalli di byte (`remote_ranges.py`, usata dagli stadi 97 e 102). Questa pulizia
è rifatta da capo sull'albero del 23, con lo stesso meccanismo; del branch si riusa il
disegno, non l'elenco.

## Le tabelle

Una riga per file: il percorso come lo citano registro e checkpoint, le righe, e che cosa il
file dice di sé (la prima riga del suo docstring o della sua intestazione, citata e non
parafrasata; per i file che non ne hanno, una descrizione dai loro campi).


### Agenti e orchestrazione: orchestratore, oracolo, catena di cicli — 119 file, 21.245 righe

Consultazione multi-modello (orchestratore), oracolo numerico del confronto pairwise, catena di cicli Codex → Claude → Grok con guardiano e piano mattutino. L'ultima campagna vera dell'orchestratore è l'audit Jiang del 15 settembre ([CP-0016](checkpoints/0016-piano-operativo-audit-protocollo.md)). La catena non ha completato nessun ciclo: in `reports/ciclo_giornaliero/` non esiste una cartella `ciclo-NN/`, e dal 19 al 23 settembre il task giornaliero di Windows è uscito ogni giorno con «nessun piano sigillato» (`C:/Users/ferra/vcc2026-data/ciclo/scheduler.log`). L'attività pianificata del piano mattutino è disabilitata. Nessuno di questi file è importato dal codice che produce una sottomissione. Ritiro deciso in [D-040](DECISIONI.md#d-040--il-codice-vivo-è-solo-quello-che-produce-o-valuta-una-sottomissione).

| Percorso | Righe | Che cosa dice di sé |
|---|---:|---|
| `src/orchestrator/__init__.py` | 19 | A local, human-started orchestrator for multi-model research sessions. |
| `src/orchestrator/adapters/__init__.py` | 61 | Adapter construction. One service, one channel, chosen only by configuration. |
| `src/orchestrator/adapters/base.py` | 107 | The adapter interface, and the error taxonomy the engine reacts to. |
| `src/orchestrator/adapters/gemini_cli.py` | 117 | Gemini through its official CLI, authenticated with the operator's Google account. |
| `src/orchestrator/adapters/manual.py` | 68 | The human-in-the-channel adapter: the prompt is handed over, the answer is pasted back. |
| `src/orchestrator/adapters/scripted.py` | 87 | An offline adapter that reads its answers from files. |
| `src/orchestrator/adapters/web.py` | 902 | Web chats driven in the operator's own browser session, through Playwright. |
| `src/orchestrator/briefs.py` | 277 | The incarico: the only thing the operator hands to the system, and its versioning. |
| `src/orchestrator/checks.py` | 187 | Acceptance checks: the only thing allowed to turn a criterion green. |
| `src/orchestrator/cli.py` | 853 | `orch`: the operator's console. Nothing starts a campaign except a person typing here. |
| `src/orchestrator/convergence.py` | 382 | When to keep going, when to stop, and which kind of stop it was. |
| `src/orchestrator/engine.py` | 1.143 | The loop itself: deterministic code that decides who is asked what, and when to stop. |
| `src/orchestrator/protocol.py` | 665 | What we ask a model for, and what we are willing to read back. |
| `src/orchestrator/report.py` | 342 | The final report: result, evidence, checks actually run, disagreements, and limits. |
| `src/orchestrator/research/__init__.py` | 30 | The scientific-research mode: three phases, a structured record, a deterministic dossier. |
| `src/orchestrator/research/campaign.py` | 309 | The research half of a brief: scope, relevance, hypotheses, budget, search policy. |
| `src/orchestrator/research/contract.py` | 664 | What a research reply may say, and what we are willing to write down as a fact. |
| `src/orchestrator/research/dossier.py` | 785 | The common dossier, assembled by code, and the report a person reads. |
| `src/orchestrator/research/engine.py` | 528 | The three-phase research loop. Deterministic code, from the first prompt to the dossier. |
| `src/orchestrator/research/leads.py` | 221 | Choosing which lines of enquiry phase 3 pays for. Deterministic, and written down. |
| `src/orchestrator/research/prompts.py` | 341 | The three questions a research campaign asks, and the contract it asks them under. |
| `src/orchestrator/settings.py` | 211 | The orchestrator's own configuration: services, roles, routes, limits, guards. |
| `src/orchestrator/store.py` | 484 | Persistent state: a SQLite index, an append-only event log, and files on disk. |
| `src/orchestrator/util.py` | 132 | Deterministic helpers: ids, hashes, clocks, write-once files, text deltas. |
| `scripts/orch.cmd` | 14 | The orchestrator console. Mirrors py.cmd: UTF-8 and src/ on PYTHONPATH. |
| `configs/orchestrator/briefs/campagna-dati.yaml` | 51 | Incarico dell'orchestratore: Ricerca e verifica di ulteriori dataset per VCC2026 |
| `configs/orchestrator/briefs/collaudo-canale.yaml` | 20 | Un solo invio, per verificare che un canale web funzioni davvero: nuova conversazione, |
| `configs/orchestrator/briefs/collaudo-deep-kimi.yaml` | 42 | Incarico sintetico per il primo collaudo del ciclo DeepSeek-Kimi sui servizi reali. |
| `configs/orchestrator/briefs/critica-prospetto-modello.yaml` | 119 | INCARICO DI CRITICA sul prospetto del prossimo modello (docs/PROSPETTO_MODELLO_2026-09-14.md). |
| `configs/orchestrator/briefs/materiali/prospetto-modello-2026-09-14.md` | 199 | Documento in esame — prospetto interno di un progetto, datato 2026-09-14. |
| `configs/orchestrator/briefs/materiali/vcc2026-panel-2026-09-15.csv` | 301 | Pannello dei 300 bersagli allegato agli incarichi |
| `configs/orchestrator/briefs/prova-fattoriale.yaml` | 31 | Incarico di collaudo. Innocuo di proposito: non contiene nulla del progetto VCC. |
| `configs/orchestrator/briefs/prova-split-e-pairing.yaml` | 104 | Incarico sintetico per la prima esecuzione reale del ciclo DeepSeek-Kimi. |
| `configs/orchestrator/briefs/ricerca-collaudo.yaml` | 86 | Incarico di collaudo della modalita' scientific_research, per la prova a secco. |
| `configs/orchestrator/briefs/ricerca-perturbseq-t-squamoso.yaml` | 122 | PRIMO INCARICO SCIENTIFICO REALE per la modalita' scientific_research. |
| `configs/orchestrator/briefs/vcc2026-jiang-audit.yaml` | 57 | Incarico dell'orchestratore: Jiang: audit dati e split per il primo pilot remoto VCC2026 |
| `configs/orchestrator/briefs/vcc2026-jurkat-audit.yaml` | 51 | Incarico dell'orchestratore: Nadig Jurkat: quarto contesto e riconciliazione col mirror HepG2 |
| `configs/orchestrator/briefs/vcc2026-pharma-atlas-audit.yaml` | 44 | Incarico dell'orchestratore: Srivatsan, McFaline-Figueroa, Tahoe, scBaseCount: classe di perturbazione |
| `configs/orchestrator/briefs/vcc2026-primeflow-audit.yaml` | 47 | Incarico dell'orchestratore: Audit mirato PRiMeFlow per trasferimento a contesti mai perturbati |
| `configs/orchestrator/briefs/vcc2026-validation-review.yaml` | 36 | Incarico dell'orchestratore: Review del protocollo per decidere il prossimo candidato VCC2026 |
| `configs/orchestrator/offline-deep-kimi.yaml` | 39 | Prova a secco del percorso deep_kimi: stessa forma del percorso reale (solo il ciclo a |
| `configs/orchestrator/offline-ricerca.yaml` | 53 | Prova a secco della modalita' scientific_research: stessa forma del percorso reale |
| `configs/orchestrator/offline.yaml` | 40 | Configurazione per la prova a secco: nessuna rete, nessun servizio esterno. |
| `configs/orchestrator/orchestrator.yaml` | 193 | Orchestratore locale — configurazione operativa. |
| `configs/orchestrator/rehearsal/` | 564 | 21 file. Risposte registrate per le prove a secco dell'orchestratore (tre prove) |
| `configs/orchestrator/services/deepseek.yaml` | 91 | Profilo dell'interfaccia web di DeepSeek. |
| `configs/orchestrator/services/grok.yaml` | 40 | Profilo dell'interfaccia web di Grok, non verificato (la prima riga del file dice «DeepSeek», copiata) |
| `configs/orchestrator/services/kimi.yaml` | 99 | Profilo dell'interfaccia web di Kimi, non verificato (la prima riga del file dice «DeepSeek», copiata) |
| `tests/test_orchestrator.py` | 2.015 | Tests for the ways the orchestrator could quietly do the wrong thing. |
| `tests/test_orchestrator_research.py` | 946 | Tests for the ways the research mode could quietly say more than it knows. |
| `docs/ORCHESTRATORE.md` | 704 | L'orchestratore locale — architettura, stato, e che cosa è stato davvero provato |
| `docs/RICERCA_SCIENTIFICA.md` | 354 | La modalità `scientific_research` — come funziona, e che cosa è stato davvero provato |
| `src/oracle/README.md` | 18 | Oracolo numerico |
| `src/oracle/__init__.py` | 11 | Deterministic numerical oracles. |
| `src/oracle/__main__.py` | 5 | python -m oracle |
| `src/oracle/cli.py` | 78 | CLI dell'oracolo pairwise sulla loss. |
| `src/oracle/fixtures/pairwise_loss/` | 115 | 22 file. Fixture dei test dell'oracolo: CSV e JSON di casi limite |
| `src/oracle/pairwise_loss.py` | 1.013 | Pairwise loss comparison: recalculate from CSV, compare to a claim. |
| `tests/test_oracle_pairwise_loss.py` | 591 | Tests for the pairwise-loss numerical oracle. |
| `docs/oracle/CONTRATTO.md` | 326 | Contratto dell'oracolo di confronto pairwise sulla loss |
| `scripts/32_daily_cycle.py` | 1.851 | Run the chain of cycles -- plan, review, implementation, control -- as often as asked. |
| `scripts/ciclo.cmd` | 18 | Chain of cycles: plan, review (Codex), implementation (Claude), control (Grok). |
| `configs/ciclo_giornaliero/ciclo.json` | 76 | Impostazioni della catena di cicli, lette da scripts/32_daily_cycle.py. Contratto: docs/CICLO_GIORNALIERO.md. Le chiavi che iniziano con _ sono com... |
| `configs/ciclo_giornaliero/claude_output.schema.json` | 13 | Schema JSON della risposta di Claude nella fase 3 |
| `configs/ciclo_giornaliero/codex_output.schema.json` | 33 | Schema JSON della risposta di Codex nella fase 2 |
| `configs/ciclo_giornaliero/grok_output.schema.json` | 45 | Schema JSON della risposta di Grok nella fase 4 |
| `configs/ciclo_giornaliero/preambolo_claude.md` | 25 | Preambolo fisso del prompt di Claude (fase 3) |
| `configs/ciclo_giornaliero/prompt_codex.md` | 13 | Prompt fisso di Codex (fase 2, skill `$revisione-piano`) |
| `configs/ciclo_giornaliero/prompt_grok.md` | 40 | Prompt fisso di Grok (fase 4) |
| `configs/ciclo_giornaliero/prompt_grok_seguito.md` | 16 | Prompt di Grok per il seguito dopo una campagna |
| `tests/test_daily_cycle.py` | 780 | Tests for the chain of cycles (scripts/32_daily_cycle.py). |
| `docs/CICLO_GIORNALIERO.md` | 209 | Catena di cicli: piano, revisione, implementazione, controllo |
| `.agents/skills/avvia-ciclo/SKILL.md` | 85 | Avvio di un ciclo dal dialogo |
| `.agents/skills/avvia-ciclo/agents/openai.yaml` | 4 | Manifest della skill `avvia-ciclo` per Codex |
| `.agents/skills/piano-mattutino/SKILL.md` | 195 | Piano mattutino — VCC 2026 |
| `.agents/skills/revisione-piano/SKILL.md` | 109 | Revisione del piano del mattino — fase 2 del ciclo 01 |
| `.agents/skills/revisione-piano/agents/openai.yaml` | 4 | Manifest della skill `revisione-piano` per Codex |
| `.claude/skills/piano-mattutino/SKILL.md` | 195 | Piano mattutino — VCC 2026 |


### Benchmark modulare pseudobulk ed esperimenti collegati — 36 file, 11.954 righe

Il confronto modulare in spazio pseudobulk ([CP-0011](checkpoints/0011-primo-benchmark-modulare.md), [CP-0013](checkpoints/0013-hepg2-terzo-contesto.md)), il pilot GO slim e la verifica GPU ([CP-0014](checkpoints/0014-go-slim-e-gpu.md)), SVD randomizzata e rango ([CP-0015](checkpoints/0015-svd-randomizzata-e-rango.md)), il protocollo congelato ([CP-0016](checkpoints/0016-piano-operativo-audit-protocollo.md)) e il gate di espressione ([CP-0017](checkpoints/0017-gate-espressione-destinazione.md)). Esiti inconcludenti o scartati dalle loro regole; le tabelle restano in `reports/`. Nessuno degli stadi che producono il t08, il t10 e il t11 importa questi moduli.

| Percorso | Righe | Che cosa dice di sé |
|---|---:|---|
| `src/vcc2026/benchmark/__init__.py` | 26 | Common protocol for comparing transfer, linear, MLP and modular predictors. |
| `src/vcc2026/benchmark/descriptors.py` | 532 | Context and target descriptors with an explicit provenance record. |
| `src/vcc2026/benchmark/evaluate.py` | 341 | Proxy evaluation, paired target differences, and resource accounting. |
| `src/vcc2026/benchmark/factorization.py` | 236 | Truncated SVD of an already-centred response matrix. |
| `src/vcc2026/benchmark/gate.py` | 698 | Expression gate arms: shrink a prediction where the destination does not express. |
| `src/vcc2026/benchmark/generator_spec.py` | 157 | Specification of the missing single-cell bundle for generator × predictor. |
| `src/vcc2026/benchmark/inventory.py` | 404 | Machine-readable inventory of what is actually on disk. |
| `src/vcc2026/benchmark/models.py` | 772 | Compared predictors: ShrunkTransfer, masked low-rank, compact MLP, modular. |
| `src/vcc2026/benchmark/protocol.py` | 257 | Uniform interfaces: descriptors, splits, fit/predict/save, no leakage. |
| `src/vcc2026/benchmark/run.py` | 1.258 | Run the modular pilot on local pseudobulk signatures. |
| `src/vcc2026/benchmark/universe.py` | 118 | Gene universe actually measured in every compared source. |
| `src/vcc2026/presence.py` | 208 | Per-gene presence in a context's unperturbed cells, and a graded weight from it. |
| `src/vcc2026/eval_protocol.py` | 411 | Frozen evaluation protocol: leakage, local anchors, promotion. |
| `scripts/50_inventory_data.py` | 69 | Build a machine-readable inventory of data that is actually on disk. |
| `scripts/51_run_modular_pilot.py` | 88 | Run the first modular-vs-monolithic pilot on local pseudobulk signatures. |
| `scripts/56_probe_target_descriptors.py` | 769 | Probe target-descriptor sources for unseen-gene (mode B) inputs. |
| `scripts/57_generator_x_predictor.py` | 368 | Generator x predictor on real HepG2 cells, with the six VCC metrics. |
| `scripts/58_build_go_slim_table.py` | 303 | Freeze the table `gene symbol -> 140 GO slim bits + missing indicator`. |
| `scripts/59_gpu_readiness.py` | 320 | Would a GPU make this code faster? Measured, not assumed. |
| `scripts/60_compare_factorization.py` | 556 | Exact vs randomized truncated SVD, on the matrices the benchmark actually uses. |
| `scripts/65_eval_protocol_pilot.py` | 163 | Freeze-check the evaluation protocol on existing splits and HepG2 cells. |
| `scripts/69_expression_gate_decision.py` | 275 | Apply the pre-declared decision rule to an expression-gate run, and say nothing else. |
| `scripts/70_context_presence_audit.py` | 219 | How much room an expression gate would have on the official contexts A/B/C. |
| `configs/benchmark.yaml` | 126 | First modular-vs-monolithic pilot. Numbers here are the protocol, not results. |
| `configs/benchmark_3ctx.yaml` | 171 | Three-context benchmark. Numbers here are the protocol, not results. |
| `configs/benchmark_3ctx_hepg2_predictions.yaml` | 156 | Derived from configs/benchmark_3ctx.yaml, and nothing about the protocol is |
| `configs/benchmark_expression_gate.yaml` | 364 | Gate di espressione: una regola scritta a mano, messa alla prova con il protocollo |
| `configs/benchmark_go_slim.yaml` | 202 | Pilot GO slim: l'unica estensione dei descrittori proposta da CP-0012. |
| `configs/benchmark_rank.yaml` | 161 | Rank of the response basis: 16 vs 32 vs 64 vs 128, selected on inner val. |
| `configs/benchmark_svd_exact.yaml` | 169 | Exact SVD reference for the substitution check (D-029). |
| `configs/benchmark_svd_randomized.yaml` | 165 | Randomized SVD candidate for the substitution check (D-029). |
| `configs/eval_protocol.yaml` | 107 | Frozen evaluation protocol. Numbers here are rules, not results. |
| `tests/test_modular_benchmark.py` | 690 | Contracts for the modular pilot: masks, leakage, save/load, prediction identity. |
| `tests/test_expression_gate.py` | 677 | Contracts for the expression gate: the ways it could be wrong in silence. |
| `tests/test_factorization.py` | 256 | Factorisation contract: exact vs randomized, centring, pooled bootstrap. |
| `tests/test_eval_protocol.py` | 162 | Contracts for the frozen evaluation protocol: leakage, anchors, promotion. |


### Predittore condizionato e letture una tantum dei banchi (17-19 settembre) — 21 file, 2.827 righe

Il predittore neurale condizionato, scartato dalla sua regola ([CP-0026](checkpoints/0026-predittore-neurale-condizionato.md)), e le letture una tantum dei banchi del 17-19 settembre ([CP-0021](checkpoints/0021-ancore-ufficiali-e-troppe-chiamate.md)–[CP-0025](checkpoints/0025-componente-comune-scartata.md)): scelta del t02, bilancio delle chiamate, confronto delle sorgenti, componente comune. Regole ed esiti restano in `reports/`.

| Percorso | Righe | Che cosa dice di sé |
|---|---:|---|
| `src/vcc2026/conditioned.py` | 326 | Effect predictors conditioned on the target and on the cell context (2026-09-18). |
| `src/vcc2026/bench_score.py` | 79 | Official-anchor scores of bench arms, from per-target values, with a paired bootstrap. |
| `scripts/78_coexpression_predictor_test.py` | 132 | Stage 78: does control-cell co-expression predict where a knockdown moves genes? |
| `scripts/80_call_budget.py` | 197 | Stage 80: how many significant genes a predictor configuration makes, in an official context. |
| `scripts/81_choose_trial02.py` | 102 | Stage 81: apply the trial-02 rule to the two bench results, mechanically. |
| `scripts/86_source_panel_coverage.py` | 149 | Stage 86: how much of a bench panel does a transfer source actually cover? |
| `scripts/87_compare_source_benches.py` | 157 | Stage 87: apply `configs/source_lineage_rule.yaml` to two stage-75 benches. |
| `scripts/88_matched_volume_reading.py` | 140 | Stage 88: read two stage-75 benches at matched call volume, not at matched amplitude. |
| `scripts/89_specificity_reading.py` | 164 | Stage 89: apply `configs/specificity_rule.yaml` to two stage-75 benches with shuffled arms. |
| `scripts/90_per_target_precision.py` | 52 | Stage 90: per-target sign precision (k / n_pred) of bench arms, from `components_<arm>.csv`. |
| `scripts/91_common_component_verdict.py` | 152 | Stage 91: apply `configs/common_component_rule.yaml` -- KEEP or DISCARD the common component. |
| `scripts/92_train_conditioned.py` | 375 | Stage 92: train the target- and context-conditioned predictors and export their effects. |
| `scripts/93_pick_amplitudes.py` | 67 | Stage 93: choose each family's amplitude on a VALIDATION bench and write the test bench's arms. |
| `scripts/94_conditioned_verdict.py` | 124 | Stage 94: apply `configs/conditioned_rule.yaml` to the two test benches -- KEEP or DISCARD. |
| `scripts/95_centered_effect_space.py` | 154 | Stage 95: the target-SPECIFIC part of an effect prediction, in effect space. |
| `configs/conditioned_rule.yaml` | 82 | Keep or discard the first target- and context-conditioned neural predictor. |
| `configs/common_component_rule.yaml` | 72 | Keep or discard the RPE1 common component. Written 2026-09-18 15:21 (Europe/Rome), BEFORE |
| `configs/specificity_rule.yaml` | 71 | How the target-identity control (shuffled_aX) is read on the HepG2 bench. Written |
| `configs/source_lineage_rule.yaml` | 81 | How the RPE1-vs-K562 transfer comparison is read. Written 2026-09-18 ~00:15 (Europe/Rome), |
| `configs/trial02_rule.yaml` | 37 | How trial-02's predictor amplitudes are chosen. Written 2026-09-17 ~17:45 (Europe/Rome), |
| `tests/test_conditioned.py` | 114 | Tests for the target- and context-conditioned effect predictors (src/vcc2026/conditioned.py). |


### Sonde e audit delle sorgenti, ingestione remota — 41 file, 7.428 righe

Sonde e audit delle sorgenti candidate (11-15 settembre) e l'ingestione remota del 15 settembre con il suo catalogo. I dati che hanno portato stanno sotto la radice dati e su Drive, i report in `reports/`. Restano invece `src/vcc2026/remote_ranges.py` e `src/vcc2026/remote_csr.py`: gli stadi 97 e 102 leggono CD4 e Orion a intervalli di byte.

| Percorso | Righe | Che cosa dice di sé |
|---|---:|---|
| `scripts/01_inspect_controls.py` | 125 | Inspect the downloaded control bundle and report what the data actually looks like. |
| `scripts/02_smoke_test_submission.py` | 110 | Round-trip the submission machinery on a handful of perturbations. |
| `scripts/10_fetch_external.py` | 50 | Download public perturbation datasets into data_root/external. |
| `scripts/11_check_target_coverage.py` | 153 | Check how much of the official challenge panel the Replogle data actually covers. |
| `scripts/12_audit_data_strategy.py` | 118 | Read-only audit of local inputs; write small reports inside the repository. |
| `scripts/13_catalog_public_data.py` | 32 | Fetch public Figshare metadata only; never download expression matrices. |
| `scripts/14_fetch_hipsci_metadata.py` | 35 | Download only the three HIPSCI cell-metadata tables (about 21 MB). |
| `scripts/15_audit_hipsci_coverage.py` | 49 | Measure target and context support from downloaded HIPSCI metadata only. |
| `scripts/16_probe_context_identity.py` | 146 | Identify what cell types the anonymized contexts A/B/C actually are. |
| `scripts/17_extract_scorer_contract.py` | 94 | Extract the scoring contract from the installed cell-eval2, not from prose. |
| `scripts/18_cells_per_pert_replogle.py` | 357 | How does the reliability of a per-perturbation response estimate depend on the number of cells behind it? (Replogle 2022 pseudobulk) |
| `scripts/18_check_external_compat.py` | 736 | Ask the same questions of every candidate external dataset, once, cheaply. |
| `scripts/19_power_curve_vcc_ntc.py` | 273 | The reliability-vs-n question, measured in-domain: on the real VCC 2026 NTC cells (contexts A/B/C) |
| `scripts/20_verify_candidate_accessions.py` | 89 | Snapshot public candidate metadata, never expression matrices (4 MiB/URL cap). |
| `scripts/21_probe_remote_h5ad.py` | 89 | Inspect real remote HDF5 bytes under a bounded budget, no full download. |
| `scripts/22_fetch_candidate_annotations.py` | 36 | Download small, explicit public annotations, not complete cell atlases. |
| `scripts/23_probe_orion.py` | 51 | Bounded Parquet column projection; no full atlas download. |
| `scripts/24_scorer_clamp_check.py` | 22 | Verify score floors with synthetic baseline/replicate anchors, not leaderboard estimates. |
| `scripts/25_ingest_cd4_pilot.py` | 108 | Extract a small stratified CD4 raw-count pilot with a hard HTTP byte budget. |
| `scripts/26_candidate_coverage.py` | 33 | Produce per-target coverage; distinguish library design from observed cells. |
| `scripts/27_verify_grok_leads.py` | 25 | Bounded metadata verification of new leads in the user-supplied Grok inventory. |
| `scripts/28_probe_grok_files.py` | 44 | Inspect small public files and bounded count samples for the Grok leads. |
| `scripts/61_probe_jiang.py` | 338 | Probe Jiang/Mixscale from public records. No Seurat object is downloaded. |
| `scripts/62_reconcile_nadig.py` | 249 | Reconcile Nadig HepG2 GEO vs scPerturb mirror vs Jurkat. No new download. |
| `scripts/63_runtime_preflight.py` | 139 | Measure this machine and write the remote-job contract inputs. |
| `scripts/64_source_cards.py` | 405 | Source cards for Replogle SC, H1, CD4, Srivatsan, McFaline, Tahoe, scBaseCount. |
| `scripts/66_primeflow_feasibility.py` | 191 | PRiMeFlow feasibility from the paper text. Not a run of the model. |
| `scripts/67_remote_ingest.py` | 59 | Run the remote-ingest contract, or pack the tiny upload bundle. |
| `scripts/68_remote_catalog.py` | 77 | Plan or run the multi-source remote catalog. Does not train. |
| `src/vcc2026/external.py` | 198 | Registry and downloader for the public perturbation datasets we train on. |
| `src/vcc2026/remote_catalog.py` | 769 | Multi-source remote ingest: one catalog, independent checkpoints, one block at a time. |
| `src/vcc2026/remote_ingest.py` | 455 | First remote job: HepG2 parity, resume proof, then a gated Jiang block. |
| `src/vcc2026/remote_job.py` | 330 | Resumable remote-job primitives: one block, checksums, interrupt recovery. |
| `src/vcc2026/runtime.py` | 203 | Runtime inventory for local and remote jobs. |
| `src/vcc2026/source_card.py` | 165 | Mandatory per-source card. Missing fields stay missing. |
| `configs/remote_catalog.yaml` | 280 | Remote ingest catalog. Numbers are copied from named evidence. |
| `configs/candidate_ingestion.json` | 65 | Piano di ingestione delle sorgenti candidate del 12 settembre, con `resource_policy` (pavimento di 10 GiB di disco) |
| `tests/test_remote_catalog.py` | 252 | Catalog contracts: measured bytes, no silent 61.3 GB, one-block disk gate. |
| `tests/test_remote_ingest.py` | 63 | Remote-ingest contract: path rules, disk gate, no silent Windows paths. |
| `tests/test_remote_job.py` | 143 | Resumable fetch and export: interrupt must not duplicate or restart. |
| `notebooks/remote_ingest_hepg2.ipynb` | 272 | VCC 2026 — un solo notebook, più sorgenti |


### Pipeline pseudobulk di trial-01, stadi una tantum (lo stadio 45 resta) — 16 file, 5.141 righe

La pipeline verticale del 12-13 settembre: firme pseudobulk e registro delle sorgenti (40, `configs/sources.yaml`), esperimento di trasferimento e calibrazione annidata dell'ampiezza (41, 44), calibrazione nulla (42), congelamento del trial (43), convalida con `vcc prep` (46), bilancio delle risorse (47), HepG2 in pseudobulk (52-55). Restano lo stadio 45, il generatore di trial-01 usato dal t08 al t11 con `--effects`, e lo stadio 48, l'impacchettamento a flusso. Senza `--effects` lo stadio 45 legge ancora le firme `e001` sotto la radice dati; per rigenerarle servono 40 e 44 dal tag.

| Percorso | Righe | Che cosa dice di sé |
|---|---:|---|
| `scripts/40_build_signatures.py` | 248 | Stage 1 of the pipeline: registry -> selection -> ingestion -> QC -> signatures. |
| `scripts/41_transfer_experiment.py` | 337 | Stage 2: measure how well a response transfers, and calibrate its amplitude. |
| `scripts/42_null_calibration.py` | 257 | Stage 3: run the REAL scorer end-to-end on a bundle where the truth is known. |
| `scripts/43_freeze_trial.py` | 215 | Freeze one trial: the exact state the run was executed from. |
| `scripts/44_calibrate_transfer.py` | 570 | Stage 4: calibrate ShrunkTransfer by NESTED cross-validation on held-out targets. |
| `scripts/46_validate_package.py` | 583 | Stage 6: verify a prediction against the contract, then package it as .vcc. |
| `scripts/47_resource_report.py` | 213 | Stage 7: consolidate the measured cost of a set of runs into one table. |
| `scripts/52_audit_hepg2.py` | 465 | Audit an acquired single-cell perturbation object before anything uses it. |
| `scripts/53_build_hepg2_signatures.py` | 347 | Build HepG2 signatures from single cells, on the same axis and the same |
| `scripts/54_context_target_table.py` | 193 | Context x target census across every signature set on disk. |
| `scripts/55_control_profile.py` | 124 | Basal NTC profile of a single-cell source, saved for the benchmark to load. |
| `src/vcc2026/pseudobulk.py` | 287 | Read Replogle-style pseudobulk H5ADs into signatures on the official axis. |
| `src/vcc2026/registry.py` | 250 | The source registry: what each dataset is, and how far it has been checked. |
| `src/vcc2026/splits.py` | 156 | Splits that answer the three generalisation questions separately. |
| `configs/sources.yaml` | 519 | Source registry — VCC 2026 |
| `notebooks/kaggle_package_trial01.ipynb` | 377 | Package a VCC 2026 prediction on Kaggle, in bounded memory |


### Piani scaduti e documenti del codice archiviato — 11 file, 1.711 righe

Piani datati 14-16 settembre, la roadmap e la descrizione della pipeline del 13 settembre, il piano locale/remoto del 12, la consegna GPU e gli appunti RL. Il loro periodo è finito e ciò che hanno prodotto sta nei checkpoint. Lo stato corrente è in [PROGETTO.md](PROGETTO.md), il percorso di lavoro in [LAVORO.md](LAVORO.md).

| Percorso | Righe | Che cosa dice di sé |
|---|---:|---|
| `docs/PIANO_OPERATIVO_2026-09-15.md` | 303 | Piano operativo scientifico e ingegneristico — 15 settembre 2026 |
| `docs/REGIA_PARALLELA_2026-09-15.md` | 90 | Regia parallela — tutto il lavoro disponibile oggi |
| `docs/PIANO_IMPLEMENTATIVO_2026-09-16.md` | 154 | Workflow 1 — Implementazione: verso un candidato competitivo |
| `docs/PIANO_COMPRENSIONE_2026-09-16.md` | 131 | Workflow 2 — Comprensione: stato, esperimenti, criticità, studio |
| `docs/PROSPETTO_MODELLO_2026-09-14.md` | 195 | Prospetto del prossimo modello |
| `docs/ROADMAP.md` | 178 | Roadmap — ordinata per valore informativo diviso costo |
| `docs/PIPELINE.md` | 172 | La pipeline — architettura e come si esegue |
| `docs/ESECUZIONE_REMOTA.md` | 204 | Locale e remoto — che cosa gira dove, con quali risorse |
| `docs/CONSEGNA_GPU.md` | 155 | Consegna alla macchina con GPU del compagno di squadra |
| `requirements-gpu.txt` | 26 | Aggiunte per una macchina con CUDA. Deliberatamente NON contiene torch per i |
| `docs/RL/README.md` | 103 | RL — idee da riprendere in futuro |
