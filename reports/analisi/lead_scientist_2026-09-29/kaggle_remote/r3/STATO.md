# Runner di conferma dopo la correzione del backend dello scorer

Preparato, non inviato né eseguito. Mantiene il nome remoto approvato del generatore,
ma richiede lo snapshot r3 della sessione principale, SHA256
`f7324778e5d7225552734e2c7303353f46dee6c01e9d455703adce3b9b105860`, in
`C:/Users/ferra/vcc2026-data/interim/lead_generator_code_r3/`.

La sessione principale ha fissato il backend CPU di `FullTruthBench` dopo l'errore
GPU/CuPy della seconda esecuzione Colab. I notebook r1/r2 restano conservati; non
vengono modificati. Nessuna soglia, famiglia di generatori o split cambia nel launcher.
Per assemblare gli input della conferma si usa `prepare_kaggle_confirmation.py` con
questa cartella in `--snapshot-root` e soltanto lo sviluppo completato con r3.
