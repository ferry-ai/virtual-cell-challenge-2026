# Verifica delle modifiche al generatore

29 settembre 2026. Risultati osservati nella sessione, non punteggi scientifici.

- Tre test della scala di dispersione: passati. I pilot sintetici conservano l'H5AD
  intero identico byte per byte per Poisson, dispersione piena predefinita e scala zero
  equivalente a Poisson (`generatore/dispersion_default_parity_r1.json`).
- Otto test del generatore a profondità: passati. Il pilot prima/dopo conserva l'output
  dei tre percorsi preesistenti (`generatore/default_parity_r1/parity.json`).
- Banco finale con riparazioni di formato/device: 15 test passati, compresa integrazione
  con cell-eval2 su cellule sintetiche. La prima esecuzione locale senza accesso completo
  alla venv falliva l'import; con accesso al runtime la suite passa.
- Suite dell'intero progetto: 282 test eseguiti in 410,145 secondi, con un solo fallimento
  documentale. Mancava la registrazione di due file dell'analisi condivisa
  `reports/sorgenti/basali_asse_2026-09-29/`; la voce ora è inserita come lavoro in corso,
  senza promuoverne il protocollo a risultato. Gli altri 281 test sono passati.
- Dopo la registrazione, il checker conferma 45 checkpoint, registro, decisioni e link
  coerenti; anche i 19 test documentali e di workflow sono passati in 9,971 secondi.
  Il controllo strutturale non certifica le conclusioni biologiche.

Le modifiche vive sono opzionali nello stadio 45. Il nuovo banco e i modelli di ricerca
restano nella cartella del report, separati dalla pipeline di invio.

## Ricontrollo dopo t28, 19:26 UTC

Una seconda esecuzione dei 282 test nel sandbox ha incontrato tre errori di import
del pacchetto locale `cell_eval2` e un errore di pulizia di `desktop.ini` in una
directory temporanea OneDrive. Verificato fuori dal sandbox, lo stesso pacchetto
0.16.0 è presente e importabile; i quattro test funzionali rieseguiti con accesso
al runtime sono passati. Nessuna reinstallazione o modifica dello scorer locale.

Il controllo degli indici ha individuato una voce t28 duplicata, ora rimossa.
Il suo secondo limite era procedurale: usa `git ls-files` e dunque non vede i due
nuovi report ancora non aggiunti all'indice. Gli 11 test delle mappe passano usando
una copia temporanea dell'indice con quei due report aggiunti soltanto come
intent-to-add; l'indice reale e il lavoro dell'altra sessione non sono stati
modificati. Il checker documentale conferma 47 checkpoint, registro e link coerenti.
La suite completa e le riprese mirate sono esecuzioni distinte, non un unico run
di 282 test passato senza interruzioni.
