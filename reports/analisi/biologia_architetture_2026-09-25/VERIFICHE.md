# Verifiche della consegna

25 settembre 2026. Questa nota registra i controlli della nuova cartella e le
condizioni osservate nel checkout condiviso, non un certificato di correttezza
biologica. Nessun commit o push eseguito da questa sessione.

## Analisi e revisione

- Eseguito `scripts/py.cmd -B reports/biologia_architetture_2026-09-25/analyze.py`
  con output nuovo r1: terminato con codice 0. Hash degli input, versioni e misure
  in [measurements.json](r1/measurements.json); tabelle richiamate dal report.
- Riesecuzione concordante con i numeri esplorati in chat. Nessun dato sorgente
  modificato. Nessun training o download di dataset.
- Revisione in sola lettura dell'agente `review_mse_reconciliation`: verificati
  supporti e numeri rispetto al JSON, limiti del proxy MSE e distinzione fra
  maggiore accordo delle due metà ristrette e migliore previsione contro una
  verità fissa. Precisazione incorporata in RISULTATI §5.
- `git diff --check`: nessun errore di whitespace; avvisi di normalizzazione
  LF/CRLF di Git, non errori del controllo.

## Controlli del repository

La suite richiesta `scripts/py.cmd -B -m unittest discover -s tests` ha eseguito
152 test in 356,812 secondi: 2 failure documentali e 1 errore di ambiente.

1. R-018 inizialmente usava un nome di campo non riconosciuto dal checker:
   corretto in `Evidenza contraria`, precisando che la contestazione riguarda
   la sufficienza dell'inferenza, non i numeri r10. Il controllo successivo non
   segnala più questo problema.
2. La mappa legge i file registrati in Git: la nuova cartella era ancora non
   tracciata. Aggiunti all'indice soltanto i file della consegna; rieseguito
   `scripts/py.cmd -B -m unittest discover -s tests -p test_live_tree.py`:
   **11 test superati** in 2,959 secondi.
3. `test_components_reproduce_the_scored_fidelity` fallisce importando
   `cell_eval2.config`: `ModuleNotFoundError`, da `load_eval_config` in
   `src/vcc2026/de_tools.py`. Questa consegna non modifica codice di produzione
   o dipendenze. Non è stata eseguita una riparazione dell'ambiente.

Il controllo documentale e il test mirato `test_doc_workflow.py` sono stati
rieseguiti dopo la correzione R-018. Il test mirato ha eseguito 17 test, con
un'unica failure: nel frattempo un'altra sessione ha creato la cartella
`reports/modulo_cis_2026-09-26/`, ancora senza voce nel registro. Al momento della
verifica erano segnalati lo script cis e due CSV della sua r1. Quella cartella
non appartiene a questa consegna e non è stata modificata o registrata alla
cieca. Il numero dei file può cambiare mentre l'altra analisi procede.

Non si dichiara quindi verde l'intera suite del checkout condiviso. I problemi
locali alla documentazione di questa consegna sono stati corretti; restano il
modulo dello scorer mancante e la registrazione del lavoro concorrente.
