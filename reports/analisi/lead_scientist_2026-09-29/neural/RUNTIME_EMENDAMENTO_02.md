# Stack: bootstrap senza ensurepip del Python ospite

Il job066 del 29 settembre si è fermato prima di installare uv: il Python3.13
di Colab non riesce a eseguire `ensurepip` durante `python -m venv`.
`dependencies_failure_r2/job066.log` conserva l'errore. Non sono stati risolti
pacchetti, scaricati checkpoint o eseguiti modelli da quel job.

`colab_stack_dependencies_r3.sh` e il runner aggiornato installano uv0.8.22
tramite il pip già disponibile, con `--no-deps --ignore-installed --target`
verso una cartella nuova dello scratch. Non installano pacchetti nell'ambiente
Colab. Dal binario uv isolato si scarica il medesimo CPython3.11.13 e si crea la
venv scientifica con `uv venv --seed`, senza dipendere da ensurepip dell'ospite.
Pin scientifici, modello, target, celle e correzione restano invariati. La nuova
prova di risoluzione non è ancora un successo d'installazione o d'inferenza.
