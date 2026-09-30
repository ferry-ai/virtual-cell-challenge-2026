# Ripresa del pilot, aggiunta di una dipendenza mancante

**Errore osservato:** il job071 si è fermato durante l'import di Stack/scvi,
prima del download dei pesi, con `ModuleNotFoundError: No module named 'pooch'`.
Il traceback passa da `scvi/data/_built_in_data/_loom.py`. La risoluzione pip e
`pip check` erano riusciti: ciò non prova che gli import eager siano completi.
Gli originali restano in `runs/lead_stack_infer_2026-09-29_r1/` sul Drive.

**Implementato, non ancora eseguito:** il launcher072 riusa l'ambiente CPython
3.11.13 di `/content/lead_stack_scratch_r1/venv`. Verifica il binario gestito e il
freeze precedente, poi aggiunge soltanto `pooch==1.8.2` con `--no-deps`. Questa
[release ufficiale PyPI](https://pypi.org/project/pooch/1.8.2/) richiede Python
almeno 3.7. Non viene reinstallata CUDA e non cambia nessun pin precedente.
Il freeze successivo deve differire esclusivamente per questa aggiunta.

Seguono `pip check`, test del contratto del pilot, import Stack/scvi e verifica
CUDA. Eventuali altri errori saranno conservati e fermeranno il job; non sono
aggirati con import fittizi o modifiche a Stack/scvi. Non è ancora osservata una
incompatibilità JAX in questo percorso, quindi JAX non viene modificato.

Setup: `runs/lead_stack_infer_setup_2026-09-29_r2/`, con il solo
`colab_stack_infer_r2.py` richiesto dalla shell. Nuovo output:
`runs/lead_stack_infer_2026-09-29_r2/`. Bundle, plan, adapter, pesi e asse geni
restano quelli congelati. Restano i checksum integrali, la guardia di 6 GiB RAM
al loader e 2 GiB disco; la guardia RAM viene controllata anche prima dei pesi.

Il builder e il test sono `../build_stack_resume_r2.py` e
`../test_stack_resume_r2.py`. Il test confronta il payload scientifico completo
e il codice della guardia al loader con il launcher precedente, e verifica che
non sia possibile reinstallare l'ambiente completo dal nuovo `main`.
