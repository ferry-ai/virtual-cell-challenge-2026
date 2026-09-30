# Stack A/B: nessun candidato supera il transfer

29 settembre 2026. **Misurato, sviluppo cellulare locale; non score VCC.**
Il selettore congelato ha completato tutte le verifiche e restituisce
`selected_variant=null`: entrambi i candidati falliscono la regola D > 0 e
variazione PDS >= 0. **Nessuna conferma Stack sulla riserva.**
Verdetto originale: [selection_manifest.json](stack_ab_selection_r2/selection_manifest.json),
SHA256 `cd15882b15884bfeb19958c321041fd525cd87cc72ebac90ff1303e4c94e9aee`.

## Confronto fissato e risultati

Il [protocollo A/B](PROTOCOLLO_STACK_AB.md) confronta gli stessi dodici target
development e gli stessi controlli. A azzera negli input i geni fuori dal supporto
comune S; B conserva l'asse misurato di ciascun input nel vocabolario Stack.
Entrambi correggono soltanto S in uscita e mantengono lo stesso transfer fuori S.
Checkpoint, seed, prompt, formula, 400 cellule finali per target e scorer restano
fissati. Il confronto usa 1.019 cellule perturbate reali e 2.000 controlli.

| Esito | A: input comuni | B: input propri |
|---|---:|---:|
| Delta proiezione cinque membri / sei | −0,1583214825 | −0,1285121072 |
| Delta PDS grezzo | −0,3333333333 | −0,2348484848 |
| IC95% bootstrap descrittivo della proiezione | [−0,236758; −0,082083] | [−0,243493; −0,017051] |
| Ammissibile alla conferma | no | no |

I cinque contributi alla proiezione sono negativi per entrambi. Il bootstrap è
descrittivo e non entra nella scelta. Tutte le maschere di eleggibilità coincidono:
12 target PDS, 9 NMAE, 12 fidelity yield, 11 reach e 12 Jaccard. Non sono stati
rimossi casi sfavorevoli per ottenere il verdetto.

| Metrica grezza | Transfer comune | Stack A | Stack B |
|---|---:|---:|---:|
| PDS, maggiore è meglio | 0,871212 | 0,537879 | 0,636364 |
| NMAE, minore è meglio | 0,970208 | 0,994376 | 1,015273 |
| Direction fidelity yield | 0,481182 | 0,450569 | 0,464460 |
| Direction reach | 0,108484 | 0,061073 | 0,005752 |
| Jaccard significativo | 0,047506 | 0,044218 | 0,047366 |
| MSE normalizzata, minore è meglio | 1,448774 | 1,303689 | 1,333849 |

Fonti complete: [A](stack_paired_scoring_results_r1/A/pilot_comparison.json) e
[B](stack_paired_scoring_results_r1/B/pilot_comparison.json). MSE è separata dalla
primaria e il suo rapporto di somme è verificato: il miglioramento MSE non compensa
la perdita degli altri cinque membri secondo la regola registrata. PDS è un rango
nel pannello di dodici target, non un coseno medio né un valore confrontabile
direttamente con pannelli di diversa cardinalità.

## Errore numerico risolto, risultato scientifico conservato

I job originali A/082 e B/084 terminano correttamente. Il primo selettore rifiuta
però una differenza di **11 ULP** in un solo valore transfer su 105: NMAE di
SETD1A. I sei aggregati erano identici. L'[evidenza del fallimento](stack_ab_selector_attempt1.json)
è una ricostruzione del lead dal tool, non un log stdout originale.

L'[emendamento operativo](EMENDAMENTO_NUMERICO_STACK_AB_01.md), congelato prima
del ricontrollo085, fissa hashseed e thread, mantiene codice/input/versioni e
richiede entrambi gli score nuovi in sequenza. Non allarga la tolleranza del
selettore e non sceglie il tentativo migliore.

- 084: preflight locale e remoto superati; scoring completo rc0 alle 21:25:06 UTC.
  [Ricevuta runtime](stack_b_scoring_runtime_r1/preflight_runtime_receipt.json) e
  [dieci report originali con hash](stack_b_scoring_r1_files.json).
- 085: 15 input verificati, stessi scorer congelati, versioni originali, thread1;
  entrambi gli score completi rc0 alle 21:52:28 UTC.
  [Ricevuta](stack_paired_scoring_runtime_r1/preflight_runtime_receipt.json) e
  [inventario dei 22 piccoli file recuperati](stack_paired_scoring_results_r1/collection.json).
- Le due baseline CSV sono ora identiche byte per byte. D e delta PDS di A/B
  sono **esattamente invariati** rispetto agli originali. Il selettore originale,
  SHA256 `1689b7398f066322167d737f36cdb889a69f4fc542408db9b407939e6c2bbe9f`, termina rc0.
  [Verifica prima/dopo](stack_ab_numerical_diagnostic_r2/verification.json).

L'[incidente E006](../learning/incidents/E-20260929-006.r002.json) è chiuso per
questa riparazione verificata: non identifica quale riduzione abbia causato i
11 ULP originali. La causa specifica rimane non attribuita. Il successo tecnico
del preflight e dello scoring è distinto dall'esito negativo del modello.

Il bundle080 della riserva è stato preparato e verificato su 15 file, senza
inferenza: [ricevuta](stack_confirmation_preparation_receipt_r2/verification.json).
Non sono stati letti outcome della riserva per scegliere A/B; il suo essere
pronto non autorizza a procedere dopo questo verdetto.

## Interpretazione e portata

**Interpretazione:** B recupera parte del PDS perso da A, ma peggiora maggiormente
NMAE e reach; conservare più input non rende utile questo ibrido nel confronto
fissato. La differenza A/B cambia anche la profondità vista dal modello e non
isola una singola causa biologica. La diagnostica post hoc
[di A](STACK_A_POSTHOC.md) resta un'ipotesi sul meccanismo, non una nuova selezione.

I dodici target sono esplorativi, i controlli sono condivisi, i profili derivano
da una sola inferenza per candidato e l'esclusione di HepG2 dal pretraining non è
verificata. Le pendenze globali definiscono l'indice locale; non dimostrano una
conversione esatta in punti VCC. Non è stato confrontato Stack con t25/t28 in
questo banco. Nessuna conclusione universale su tutti i modelli pretrained.

Conseguenza: si chiude questa candidatura senza conferma o promozione. Tutti
gli output, il fallimento operativo e la correzione rimangono disponibili; una
futura ipotesi distinta richiederà un nuovo disegno, senza riutilizzare questa
riserva per concedere una seconda chance al candidato respinto.
