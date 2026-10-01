# Rete cellulare, versione corretta per il passo A di R-LEAD

1 ottobre 2026, presa in carico del teammate (Claude, sessione di Alfredo). Copia di
`reports/modelli/risposta_biologica_2026-09-30/` al commit `1f086cb`, con le correzioni del passo A
della [scheda R-LEAD](../../../docs/piani/strategia-scientifica.md). La cartella originale resta
com'è: r2, r3 e t29 la importano, e i controesempi dell'audit dimostrano il suo comportamento.
Matrice di applicabilità, ambiente e verifiche: [presa in carico](../../analisi/presa_rlead_2026-10-01/README.md).

**Stato: implementato e provato su dati sintetici, su CPU.** Nessun training su dati reali, nessun
confronto di modelli. Che le correzioni migliorino la previsione non è misurato.

## Che cosa cambia

Ogni correzione ha un'opzione che riproduce il comportamento precedente, per i confronti a parità.

| Difetto dell'audit | Correzione | Opzione (nuovo / precedente) | Test |
|---|---|---|---|
| Split che cambiano quando cresce il corpus (REVISIONE §2.1) | Decisione per simbolo da `sha256(sale|simbolo)`; manifest congelato riletto con la propria regola; nuovi simboli per hash | `--split-rule stable` / `legacy`; `--split-salt`, `--split-manifest` | `Splits` |
| Classi C/T/J assegnate prima del QC (§2.6) | Dopo l'ammissione un bersaglio è C solo se ha cellule di training ammesse ed estraibili; riclassificazioni registrate in `splits.json` | sempre attiva | `ClassesAfterQC` |
| Pesi della loss normalizzati nel batch (§2.2) | Somma pesata divisa per il numero di cellule del batch: ogni studio attivo vale 1/S dell'obiettivo; S conta solo gli studi con cellule di training | `--loss-norm global` / `batch` | `LossWeights` |
| Serbatoio dei controlli che perde le librerie e dipende dall'ordine (§2.3) | Per libreria, le righe di priorità minima (hash dell'identità della cellula): campione uniforme senza reinserimento, indipendente da ordine e partizione degli shard; ogni libreria tiene `min(n, 64)` righe, il pool cresce se serve. `controls.json` registra copertura prima e dopo il cap e probabilità d'inclusione; `config.json` la quota di cellule che ricadono sul pool comune | `--pool-min-per-library 64` / `0` | `ControlPool` |
| Gradiente del cancello nullo sotto il clamp (AGGIORNAMENTO_R3) | Pesi della miscela dal logit, `logsigmoid` stabili (`cellnet.gate_logs`), compatibili con `--pi-floor` | `--mixture logits` / `clamp` | `Mixture` |
| Confronto con `unknown` mai addestrato (§2.4) | Braccio `generic`: ogni cellula riceve la riga senza bersaglio, addestrata dalle perturbate, con la stessa lettura del contesto | `--arm NOME=generic` | `GenericArm` |
| 400 gruppi più numerosi: interi contesti assenti (§3.1) | Selezione a turno fra le chiavi, dal gruppo più grande; tabella ammessi/scelti per classe e chiave in `splits.json` | `--eval-selection stratified` / `largest` | `EvaluationGroups` |

Un checkpoint scritto prima di queste opzioni riprende solo con i valori precedenti
(`--loss-norm batch --mixture clamp`): il controllo di ripresa li confronta.

## Che cosa non cambia ancora

- Il ramo base riceve ancora gradiente dalle perturbate (§2.5): l'ablazione basale empirica, solo
  controlli o congiunta è un confronto del passo C, non una correzione.
- La valutazione resta il coseno diagnostico top-200, non i sei membri dello scorer; manca la
  versione trans che esclude il gene bersaglio.
- Non esistono ancora il bilineare a stessi input né i descrittori permutati (passo C).
- Il collasso di `pi`: la miscela dal logit toglie la zona piatta, ma non prova di prevenire il
  collasso in un training finito; warm-up o prior restano da confrontare.

## Verifiche

```text
python -m unittest test_rlead_fixes -v       # 15 test, le correzioni
python -m unittest test_cell_data test_prepass test_read_csr   # i test originali, sulla versione nuova
```

Esiti, interpreti e hash nella cartella di presa in carico.
