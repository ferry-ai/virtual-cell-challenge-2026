# CP-0033 — Il t15 in classifica: +0,108, nuovo migliore e sopra 0,1; raddoppiare l'ampiezza migliora tutti i membri che contano, e D-006 si riapre

- **Data:** 2026-09-24
- **Tipo:** esperimento
- **Redatto da:** agente (Claude Opus 5.5)
- **Revisione umana:** no. Invio autorizzato dal proprietario in chat il 24 settembre.
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

L'ampiezza degli effetti, 0,197, era stata scelta per minimizzare la MSE in pseudobulk
([CP-0003](0003-prima-pipeline-e-calibrazione-ampiezza.md),
[CP-0004](0004-primo-trial-locale-e-pacchetti.md), D-006). Sul punteggio ufficiale, però, lo
scalato della `mse` vale 0 in tutti gli invii. Raddoppiare l'ampiezza, con tutto il resto del
t11 invariato, cambia il punteggio?

## 2. Cosa è stato fatto

- **Ricetta** `configs/recipes/t15.json`: il t11 con ampiezza 0,394 invece di 0,197. Restano
  uguali sorgenti, pesi, cache r4, γ = 1, generatore di trial-01 e seme.
- **Previsione e regola** registrate il 23 settembre alle 21:25 UTC, prima della generazione e
  prima dei punteggi di t12 e t14 (`reports/prediction_t15_2026-09-23/prediction.json`):
  - banda +0,060…+0,095;
  - `pds_cosine` grezzo atteso 0,74–0,78, fedeltà 0,44–0,49, `nmae` 0,95–1,00;
  - se t15 ≥ t11 + 0,005, D-006 si riapre.
- **Generazione e impacchettamento** con gli stadi 45 e 48, il 24 alle 00:57–01:17 UTC:
  convalida superata, payload identico bit per bit (`reports/trial_2026-09-24/t15_packaging.json`).
- **Invio** alle 10:28Z del 24, con lo sha256 dell'archivio verificato prima. Il server
  verifica l'md5 e pubblica alle 10:59Z. Output verbatim in
  `reports/trial_2026-09-24/submit_U1K3SZuq7w5cef9lBKsn.json` e
  `status_U1K3SZuq7w5cef9lBKsn.json`.

## 3. Cosa si è osservato

**Misurato — il punteggio.** **+0,107533**, rango 436, entry `U1K3SZuq7w5cef9lBKsn`.
È il primo invio del progetto sopra 0,1. Il t11 aveva +0,070777.

**Misurato — sopra la banda registrata.** Il punteggio supera la banda +0,060…+0,095. Ogni
membro sta invece dentro l'intervallo previsto: quello che la banda non prevedeva è che
migliorassero tutti insieme.

**Misurato — i sei grezzi** (`reports/prediction_t15_2026-09-23/comparison.json`):

| membro | t11 | t15 | t15 − t11 | scalato t11 | scalato t15 |
|---|---|---|---|---|---|
| `pds_cosine` | 0,7392 | 0,7743 | +0,0351 (meglio) | +0,530 | +0,607 |
| `expr_mse_unbiased_capped_norm` | 1,1290 | 1,5794 | +0,4504 (peggio) | 0 (tosato) | 0 (tosato) |
| `de_wilcoxon_lfc_nmae` | 0,9774 | 0,9503 | −0,0271 (meglio) | +0,039 | +0,084 |
| fedeltà direzionale | 0,4582 | 0,4769 | +0,0186 (meglio) | −0,182 | −0,119 |
| `reach` | 0,1129 | 0,1389 | +0,0260 (meglio) | +0,038 | +0,067 |
| Jaccard | 0,0298 | 0,0325 | +0,0027 (meglio) | −0,002 | +0,006 |

**Misurato — le ancore reggono su un ottavo punto.** Riproducono gli scalati pubblicati con uno
scarto massimo di 0,00095 (stesso file, `anchor_check_on_t15`).

## 4. Interpretazione e incertezza

**Esito della regola scritta prima.** t15 − t11 = +0,0368, sopra +0,005:
«sul punteggio ufficiale la compressione scelta per la MSE in pseudobulk costa punti: D-006 si
riapre».

**Interpretazione:**
- **Migliorano tutti e cinque i membri che contano.** La MSE grezza peggiora (1,129 → 1,579),
  ma il suo scalato era già tosato a 0 e resta 0: la compressione pagava un membro che non ci
  dava nulla.
- **Anche la fedeltà sale**, da 0,458 a 0,477, e il Jaccard diventa positivo. Misurato con lo
  stadio 83 (`reports/prediction_calls_2026-09-23/t15/`): le chiamate mediane per bersaglio
  salgono da 543 / 582 / 764 a 804 / 730 / 1.009 in A / B / C, e restano per l'81–86% «in su»,
  come nel t11. Quante delle chiamate aggiunte abbiano il segno giusto non si vede da qui.
- **Il t14 aveva guadagnato in `nmae` e `reach`** alzando l'ampiezza con un altro generatore, e
  aveva perso in `pds_cosine`. Con il generatore di trial-01 anche `pds_cosine` sale.

**Incertezza:**
- un solo invio, senza intervallo;
- non sappiamo dove stia l'ottimo: 0,394 è il secondo punto di una curva;
- l'ottimo sul set di validazione può non valere per D/E/F, che hanno contesti e bersagli
  nuovi.

## 5. Spiegazione semplice

Finora le nostre previsioni erano volutamente timide: spostavamo le cellule solo di un quinto
di quanto suggerivano gli esperimenti pubblici, perché così l'errore medio era più piccolo. Ma
quell'errore medio, nella classifica, non ci dava comunque punti.

Abbiamo raddoppiato la spinta e il voto è salito da 0,071 a 0,108. Migliora tutto quello che
conta: il modello distingue meglio un gene spento dall'altro, e sbaglia meno spesso la
direzione dei cambiamenti.

## 6. Conseguenze

- **Il t15 è il nuovo riferimento** (+0,107533), sopra l'obiettivo di 0,1 del mandato.
- **D-006 è superata da D-042:** l'ampiezza degli invii si sceglie sul punteggio ufficiale, con
  un fattore alla volta, non sulla MSE in pseudobulk.
- **Il passo successivo è continuare la curva.** Il t16 è il t15 con ampiezza 0,788: se vince
  ancora, si sale; se perde, l'ottimo sta fra 0,394 e 0,788. Si registra prima di generarlo.
- **Le sorgenti vanno riprovate all'ampiezza nuova:** HEK293T entra sulla ricetta del t15,
  non su quella del t11.
- **Per il set finale** l'ampiezza è un parametro da decidere con i dati di validazione: va
  scritto nel piano del 22 ottobre.

## 7. Cosa corregge

- D-006, per la postura degli invii: comprimere l'ampiezza per la MSE costa punti sul punteggio
  ufficiale. Le misure in pseudobulk di [CP-0003](0003-prima-pipeline-e-calibrazione-ampiezza.md)
  restano vere per la MSE.
- Aggiorna il riferimento di PROGETTO.md §0: il migliore è il t15.

## 8. Domanda di comprensione

Perché una previsione che sbaglia di più in media (MSE da 1,13 a 1,58) può essere premiata di
più dalla classifica?
