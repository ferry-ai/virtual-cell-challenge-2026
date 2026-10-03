# generalizzazione_contesti_2026-10-02 — R-LEAD P0–P3

Claude Code, sessione `22d21f`, macchina `LAPTOP-DLG1LHV1`, dal commit `3600fe0`, 2 ottobre 2026
dalle 16:47 CEST. Scheda: [R-LEAD](../../../docs/piani/strategia-scientifica.md). Codice:
[risposta_contesto_2026-10-02](../../modelli/risposta_contesto_2026-10-02/README.md). Nessun download,
job cloud, agente, invio o push. Le misure sono **sviluppo**: ogni linea del banco era già stata letta.

Da P4 (3/10) corse su Kaggle, condivisioni e download di output con il via del proprietario in chat (`reports/invii/trial_2026-09-22/autorizzazioni.md`).

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
| `p1_r2/` | P1, dieci gruppi | gli stessi manifest su `p0_r2` e `cube_r2` (dieci gruppi di linea, 110 split C/J/T): prova di stabilità passata (fold uguali per le chiavi comuni, nessun ruolo cambiato togliendo un quinto delle tabelle) | misurato |
| `PROTOCOLLO.md`, `PROTOCOLLO.json` | P2 | bracci, metriche, aggregazione, soglie motivate, regola C/J | protocollo |
| `p2_parity/` | P2 | parità degli adattamenti di HepG2 e dell'esportazione effetti → generatore (stadio 45 contro trial-01) | misurato |
| `ceiling_r1/` | P2 | tetto della verità: coseno pesato fra metà indipendenti delle cellule | misurato |
| `p3_decision_c_r1/`, `p3_decision_cj_r1/` | P3 | la regola congelata su C e su C+J: `no_benefit` | misurato |
| `p3_six_member_r2/` | P3 | i bracci di P3 sui sei membri ufficiali su HepG2 (3/10, 2.048 controlli): il transfer resta il migliore, con [LETTURA.md](p3_six_member_r2/LETTURA.md) | misurato |
| `RISULTATI.md` | P0–P3 | lettura dei risultati e limiti della primaria | interpretazione |
| `p4/` | P4 | ipotesi e protocollo congelato della rete non lineare sul pseudobulk | protocollo |
| `p4_decision_nn_r1/` | P4 | la regola della rete sui sette gruppi (`no_benefit`), con [LETTURA.md](p4_decision_nn_r1/LETTURA.md) | misurato |
| `p4_decision_c_r3/`, `p4_decision_cj_r3/` | P4, dieci gruppi | le regole C e C+J dei bracci semplici calcolate nel kernel CPU `rlead-bench-cpu-r1`, copiate senza modifiche (`no_benefit`) | misurato |
| `p4_decision_nn_r2/` | P4, dieci gruppi | la regola della rete sul kernel GPU `rlead-bench-nn-r1` (`no_benefit`), con [LETTURA.md](p4_decision_nn_r2/LETTURA.md) che legge anche i bracci semplici | misurato |
