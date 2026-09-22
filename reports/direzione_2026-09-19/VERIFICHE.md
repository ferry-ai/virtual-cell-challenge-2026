# Verifiche del 19 settembre 2026

Eseguite in questa sessione; riepilogo degli output, non log verbatim.

| Controllo | Esito |
|---|---|
| Main a0ab5fb, wrapper locale, unittest discover | 581 test in 308,785 s; 1 errore, 1 saltato |
| Refactor 51a9c60, wrapper del worktree, unittest discover | 78 test in 202,642 s; 1 errore |
| Checker main prima del nuovo rapporto | OK, 27 checkpoint |
| Checker refactor | OK, 26 checkpoint, 134 percorsi accettati come archiviati |
| Import isolato `cell_eval2.config` nei due checkout | ModuleNotFoundError in entrambi |
| Stato dei cicli su main | Guardiano attivo, PID 6612; nessun ciclo elencato per la giornata |

L'errore comune delle suite è `test_components_reproduce_the_scored_fidelity`: `load_eval_config` non riesce a importare `EvalConfig`. Non è stata determinata la causa dell'installazione incompleta; nessun pacchetto è stato modificato. La prima invocazione sul branch aveva usato il wrapper di main: è stata rifatta col wrapper corretto e il percorso importato di `vcc2026` è stato controllato. I risultati della prima invocazione non sono usati come verifica definitiva.

## Conteggio da oggetti Git

`audit.json` registra gli hash completi e conta le righe con `bytes.splitlines()` nei file `.py` elencati da `git ls-tree -r --name-only` sotto src, scripts e tests, leggendo il contenuto con `git show`. Non usa file non tracciati né copie locali.

| Cartella | main a0ab5fb | refactor 51a9c60 |
|---|---:|---:|
| src | 24.039 | 4.902 |
| scripts | 18.248 | 5.497 |
| tests | 8.956 | 1.405 |
| totale | 51.243 | 11.804 |

Riduzione con questo metodo: 39.439 righe (76,96%). Il resoconto allegato dice 51.215 → 11.804: la differenza di 28 righe nel punto di partenza non è stata riconciliata e non viene nascosta. Può dipendere dal metodo/perimetro di conteggio; non è prova di una modifica scientifica. Il contenuto degli oggetti e gli hash restano la misura riproducibile.

## Limiti

Non rieseguite le quattro riproduzioni 94/84/95/75 dichiarate dal resoconto. Non misurata una nuova efficacia predittiva. La lettura web verifica alcune righe AtlasShift della classifica, non tutti i primi 100 né il codice sottostante.
