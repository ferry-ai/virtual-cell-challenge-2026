# Verifica del JSON usato dalla shell

29 settembre 2026. **Misurato:** non c'è il mismatch operativo sospettato nella
review. La shell `colab_stack_production_prepare_r1.sh` passa
`--registration "$REPORT/expansion_metadata_r1.json"`. Questo file è incluso
nell'archivio congelato e contiene i tre campi effettivamente letti dal packer:
`production_targets_subset_ge64`, `production_fallback_targets`,
`counts_per_panel_target`.

Il file esterno `target_registration.json` è un riepilogo per il revisore, con
nomi brevi differenti; non viene passato al packer. Il test
`../test_stack_expansion_contract.py` risolve il nome del JSON direttamente dalle
due shell, verifica hash e allowlist dell'archivio, estrae tramite AST i campi
letti dal packer e controlla che siano presenti nell'input effettivo. Controlla
anche l'uguaglianza fra riepilogo e input, i 254 target ammessi, i 46 fallback e
le soglie relative ai conteggi preregistrati.

**Due test passati**, senza letture di matrici reali. Nessun file del payload
congelato è stato modificato; gli SHA e le shell già consegnati restano validi.
