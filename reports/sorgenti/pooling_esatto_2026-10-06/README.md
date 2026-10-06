# Pooling esatto dello stadio 98 per la banca estesa

6 ottobre 2026. Claude Code per Alfredo, che ha chiesto in chat di aiutare Davide a sbloccare il rifit identico del
t28 sulla banca estesa.

## Il problema

Il riferimento è il [review r6](../../modelli/percorso_riusabile_2026-10-05/GROK_REVIEW_r6.md), su `main`.
- **Il mixer di Grok r6** fa lo shrinkage di ogni unità della banca (BIO o frammento) e poi media.
- **Lo stadio 98 originale**, cioè `effects_from_pseudobulk` di [scripts/98_multisource_effects.py](../../../scripts/98_multisource_effects.py),
  fa un'altra cosa:
  1. dentro ogni donatore somma i **conteggi** di tutte le righe di un bersaglio. Con `condition=None`, come per le
     sorgenti extra, li somma anche fra condizioni;
  2. calcola un solo ln fold change per donatore;
  3. fa la media dei donatori pesata sulle cellule;
  4. applica `z_shrink` **una volta**.

  La maschera `usable` viene dai controlli di tutti i donatori insieme.
- **L'eccezione dichiarata è CD4:** uno stimatore per condizione su tutti i donatori, poi le tre condizioni si
  mescolano con γ 0 dopo lo shrinkage.
- **Conclusione:** cambiare solo la banca non autorizza a cambiare questa aggregazione.

## Che cosa c'è qui

- **[pooling.py](pooling.py)** contiene quattro funzioni:
  - `pool_units`, la strada identica: concatena le righe di somme di conteggi delle unità che formavano una tabella
    originale e chiama la **funzione originale**, importata da `src/` e non copiata;
  - `donor_stats` e `combine_donors`, la scorciatoia **solo per donatori disgiunti**: è esatta partendo, per ogni
    donatore, da ln fc non mascherato, varianza, cellule, maschera di evidenza e somme dei controlli;
  - `compare_tables`, il confronto di uguaglianza fra una tabella nuova e quella di riferimento: bersagli, geni,
    disegno dei NaN, shrunk, raw, se e cellule.
- **[test_pooling.py](test_pooling.py)**: cinque fixture sintetiche contro lo stimatore originale, con tutti i
  parametri della chiamata del t28. Ci sono geni a bassissima espressione per esercitare `usable` e
  `min_expected`.

## Esito dei test (misurato, dati sintetici, `test_pooling.py`, 5/5 OK)

| Caso | Risultato |
|---|---|
| `pool_units` su un donatore spezzato in train/val | identico all'originale |
| `pool_units` con `condition=None` e due condizioni | identico |
| `combine_donors`, donatori disgiunti, `min_expected` 0 e 1 | identico, maschera `usable` compresa |
| Shrinkage per unità e poi media, cioè r6 | **diverso**: scarto relativo mediano 0,21 sugli effetti con \|ref\| > 0,1; massimo 0,61; correlazione 0,94 |
| `combine_donors` usato su un donatore spezzato | **sbagliato**: scarto massimo 1,8 su shrunk, perché il log di somme non è la media dei log |

## Che cosa ne segue per il rifit (proposta per Davide)

1. **Donatore spezzato fra più unità** (H1 train/val, frammenti multi-BIO, condizioni sommate con `condition=None`):
   servono le **somme di conteggi** per (unità, donatore, bersaglio) e per i controlli. Poi si usa `pool_units`. È
   la strada che la sessione r7 di Grok sta preparando.
2. **Donatori distinti, una riga ciascuno:** bastano le statistiche per donatore **non mascherate**. Si ricombinano
   con `combine_donors`, senza rileggere le matrici.
   - Non bastano le tabelle `raw` già salvate: `raw` è azzerato dove la maschera `usable` del singolo donatore è
     falsa, e quella del pool può essere vera.
3. **Certificare l'uguaglianza da capo a fondo**, prima di chiamare «identico» il rifit:
   - su una sorgente già nel cache del t28 (per esempio HCT116 o HEK293T), con gli stessi input;
   - si confronta l'uscita del nuovo adattatore con la tabella del cache usando `compare_tables`;
   - le otto fixture del mixer verificano la formula, non l'adattatore (review r6).

## Limiti

- **I dati sono sintetici.** Il confronto su una tabella reale del cache richiede gli input di Davide: righe
  pseudobulk e cache r9, che non sono in locale.
- **La parte K562** passa per un altro stimatore (`k562_table`) e non è coperta qui.
