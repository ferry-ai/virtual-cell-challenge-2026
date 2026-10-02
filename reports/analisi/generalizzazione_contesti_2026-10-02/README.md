# generalizzazione_contesti_2026-10-02 — R-LEAD P0–P3

Claude Code, sessione `22d21f`, macchina `LAPTOP-DLG1LHV1`, dal commit `3600fe0`, 2 ottobre 2026
dalle 16:47 CEST. Scheda: [R-LEAD](../../../docs/piani/strategia-scientifica.md). Codice:
[risposta_contesto_2026-10-02](../../modelli/risposta_contesto_2026-10-02/README.md). Nessun download,
job cloud, agente, invio o push. Le misure sono **sviluppo**: ogni linea del banco era già stata letta.

**Leggere prima:** [PROTOCOLLO.md](PROTOCOLLO.md) (regola congelata alle 17:40, prima dei dati reali).

| Cartella o file | Passo | Che cosa contiene | Tipo |
|---|---|---|---|
| `p0_r1/preflight.json` | P0 | git, interprete, librerie, scorer `cell_eval2` 0.16.0 importabile con preset `vcc2026`, risorse | misurato |
| `p0_r1/input_manifest.json` | P0 | 457 file, 17,5 GB, sha256; 0 discrepanze con gli hash registrati dagli universi | misurato |
| `p0_r1/tables.csv`, `context_target_study.csv.gz` | P0 | una riga per tabella e per (tabella, bersaglio): linea, gruppo, studio, saggio, modalità, cellule, geni misurati, chiave riconciliata | misurato (attributi dal registro con fonte) |
| `p0_r1/overlap.json`, `group_overlap.csv`, `confounding.csv`, `aliases.json` | P0 | collegamenti fra gruppi, confondimenti linea/studio/saggio, alias | misurato |
| `p1_r1/split_manifest.json`, `split_folds.csv.gz` | P1 | split per gruppi di linea, regimi dopo QC, perdite, prova di stabilità | misurato |
| `p1_r1/exposure_manifest.json` | P1 | esposizioni del banco e dei modelli r2/r3 dai loro prepass | misurato |
| `p1_r1/reserve_manifest.json` | P1 | storia delle letture per dataset e candidate riserve per P5 | registro |
| `PROTOCOLLO.md`, `PROTOCOLLO.json` | P2 | bracci, metriche, aggregazione, soglie motivate, regola C/J | protocollo |
