# Primo training su dati reali della rete cellulare: protocollo e regola di lettura

1 ottobre 2026, notte, Claude Code (sessione `07ebf08b`), scheda
[R-LAB](../../../docs/piani/piano-giorno-2026-09-30.md). **Scritto prima del lancio del pre-passo e del training**
(CP-0030): nessun numero di questo training era noto quando la regola è stata fissata. Codice:
[risposta_biologica_2026-09-30](../risposta_biologica_2026-09-30/) (`train_cellnet.py`, `cellnet.py`, `cell_data.py`,
`kaggle_train.py`), al commit indicato in `LANCIO.md` di questa cartella, scritto al momento del lancio.

## 1. Che cosa è

Una **verifica tecnica**, come ha stabilito il proprietario il 30/09 («un primo training su un sottoinsieme vale come
verifica tecnica, non come risultato»). Serve a sapere se la catena regge su dati reali e sulla piattaforma: pre-passo
su CPU, training su GPU con checkpoint e ripresa, valutazione, esportazione, entro la quota. **Non** decide se la rete
generalizza: un solo seme, un solo contesto tenuto fuori, nessun confronto a sei membri, nessuna riserva aperta.

## 2. Dati

I dataset pubblicati su `davidmaisterx` e pronti al lancio, tutti interi:

| Dataset Kaggle | Studio | Contesti | Cellule |
|---|---|---|---|
| `rlab-hepg2-nadig` | Nadig 2025, HepG2 | HepG2 | 145.473 |
| `rlab-jurkat-nadig` | Nadig 2025, Jurkat | Jurkat | 262.956 |
| `rlab-h1-vcc2025-trainval` | gara 2025, train e validation | H1 | 320.200 |
| `rlab-k562-gwps` | Replogle 2022, genome-wide | K562 | 1.989.578 |
| `rlab-hipsci-gwfit`, `rlab-hipsci-gwnonfit`, `rlab-hipsci-targeted19` | HIPSCI, tre schermi | 19 linee iPSC | 1.881.069 |

Totale 4.599.276 cellule. **Fuori, con il motivo:** Jurkat GSE249595 (nessuna chiamata delle guide: non
supervisionabile finché l'assegnazione non è provata); K562 essenziali e RPE1 (in ingestione, job 112: entrano nel
training successivo); lo split di test di H1 2025 (la riserva: non scaricato); tutte le altre sorgenti del catalogo
(non ancora ingerite). Le cellule che entrano davvero nel training, dopo QC e identità, sono in `qc.json`,
`splits.json` e `coverage.json` del pre-passo e dei bracci.

## 3. Ruoli e disegno

- **Contesto tenuto fuori: HepG2.** I suoi perturbati sono le classi C (bersaglio visto altrove) e J (bersaglio mai
  visto, o nascosto); i suoi controlli entrano solo come input dell'encoder di contesto.
- **Bersagli nascosti (T):** il 10% dei simboli addestrabili, seme 20260930 (`cell_data.splits`).
- **Regole dei dati:** le quattro chiuse il 1/10 (identità per provenienza, combinate, guardia dei fenotipi, maschere
  per shard), senza modifiche.
- **Pre-passo** su CPU (kernel `rlab-prepass-r1`, nessuna quota GPU): argomenti di default di `train_cellnet.py
  prepass` con `--holdout-context HepG2`.
- **Training** su GPU T4×2 (kernel `rlab-cellnet-r1`): due bracci in parallelo, stessi argomenti salvo il codice del
  bersaglio: `descriptors` (cuda:0) e `identity` (cuda:1). All'inizio, sul braccio `descriptors`, un ciclo di ripresa
  su GPU (arresto al passo 50, ripresa fino al 100, confronto con una corsa diretta al 100).
- **Quota:** 6 ore di GPU dichiarate dal proprietario la notte del 30/09. Questo lancio ne usa al massimo il budget
  scritto in `LANCIO.md` (ciclo, due bracci, valutazione ed esportazione compresi); il resto resta per il training
  successivo con K562 essenziali e RPE1.

## 4. Regola di lettura, fissata ora

**A. Esito tecnico (passa o non passa, voce per voce):**
1. il kernel del pre-passo e quello del training finiscono con codice 0;
2. `resume_check.json`: `passed` vero (sequenza dei dati identica; parametri entro 1e-3 del massimo su GPU);
3. `verify.json` di ogni braccio: nessuno shard diverso dallo stato del pre-passo;
4. `coverage.json`: controllo di non-contaminazione passato; se `epochs_done` ≥ 1, ogni cellula di training ammessa
   vista almeno una volta (`distinct_cells_seen` = `admitted_training_cells`); altrimenti si riporta la frazione;
5. `eval.json`: valutazione completa (`complete` vero) entro il budget;
6. `plan.json` e il log: throughput misurato, frazione di attesa dei dati, memoria di processo e di GPU riportate.

Un punto che non passa si registra come incidente (ERRORI) prima di ogni nuovo lancio.

**B. Lettura descrittiva (non decide nulla sulla rete; registrata qui per non leggerla a posteriori):**
- per classe (C, T, J) e per braccio: guadagno di log-verosimiglianza rispetto a nessun effetto e rispetto allo
  stesso modello senza bersaglio; quota di gruppi con guadagno specifico positivo; coseni dello spostamento previsto,
  del trasferimento e della perturbazione generica rispetto all'osservato;
- **attese scritte ora:** (i) guadagno rispetto a nessun effetto positivo in media su C e T in entrambi i bracci;
  (ii) su J il braccio `identity` non ha informazione sul bersaglio nuovo, quindi quota di guadagno specifico
  positivo vicina o sotto 0,5; il braccio `descriptors` sopra `identity` su J è ciò che l'ipotesi dei descrittori
  prevede; (iii) su C nessuna attesa che la rete batta il trasferimento, che nel progetto è una baseline forte;
- con un seme e un contesto tenuto fuori nessuna di queste attese, vera o falsa, è una prova: non entrano in
  PROGETTO §0 come risultati e non sostituiscono il confronto a sei membri di R-COMP.

## 5. Dopo

Se A passa: training successivo con K562 essenziali e RPE1 (e ciò che nel frattempo è stato ingerito), entro la
quota restante, con lo stesso protocollo o uno nuovo scritto prima. Se A non passa: incidente, correzione, nuovo
lancio in cartelle nuove. Uno **scoring** ufficiale (autorizzato dal proprietario il 1/10 alle 00:29, uno) richiede un
suo protocollo con previsione e regola registrate prima dell'invio (PROCEDURE §1–2), non questo.
