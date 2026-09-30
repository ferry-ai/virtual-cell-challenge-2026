# Venv senza ensurepip

**Correzione infrastrutturale, non cambiamento del modello.** La sessione principale
ha osservato il fallimento del job 067 in `venv.EnvBuilder(..., with_pip=True)`:
`ensurepip` non era disponibile nel runtime Colab. L'errore precedeva ogni installazione.
Il codice r1 e la sua corsa restano conservati.

`bootstrap_candidate_env_r2.py` crea invece la venv con `with_pip=False` e mantiene
`system_site_packages=True`. Prima di qualsiasi installazione esegue un processo con
l'interprete della venv e `-I`: richiede `sys.prefix != sys.base_prefix`, verifica che
`purelib`, `platlib` e `scripts` risolvano dentro la nuova venv e importa il pip ereditato.
Se pip non è ereditabile fallisce esplicitamente; non usa apt, get-pip o installazioni
globali. Le chiamate pip mantengono `--isolated`, i vincoli delle versioni della base
e aggiungono `--prefix` esplicito della venv già controllata.

Rimangono il confronto dell'ambiente base prima/dopo, gli import scientifici, il
roundtrip AnnData/HDF5 e il parsing di entrambi gli stadi dello snapshot r3.
`selftest_bootstrap_r2.py` passa: accetta il caso isolato e rifiuta l'interprete base
o ciascuna delle tre destinazioni che esce dalla venv. Compilazione Python riuscita.
Questo test locale non simula un'installazione Colab.

Il nuovo wrapper `colab_candidate_environment_r2.sh` usa soltanto directory r2 nuove
e resta preparato per la lead; qui non è stato accodato né eseguito. Nessuna generazione.
