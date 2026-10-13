# Testi dell'invio ta 41

Scritti il 13 ottobre 2026, prima di generare e prima di ogni caricamento. Il via è di Alfredo in chat, il 13/10:
«mandala direttamente a gradare se funziona o no poi lo valutiamo noi». Previsione e regola:
[prediction_ta41_2026-10-13/prediction.json](../prediction_ta41_2026-10-13/prediction.json).

- **Nome del modello:** `ta 41 capped centred bridge network`
- **Descrizione:** uguale al nome.
- **Pacchetto:** `vcc2026-data/artifacts/ta41pack/prediction.vcc`; sha256 in `ta41_packaging.json`.
- **Effetti:** quelli di `ta 40` con il tetto |lfc × 1,5| ≤ 1,0, gene bersaglio intatto
  ([esporta_tetto.py](../../generatore_e_banchi/budget_chiamate_2026-10-13/esporta_tetto.py) `--cap 1.0`), in
  `processed/effects_ta41_tetto_2026-10-13`.
- **Emissione:** lo stadio 45 con `--effects-scale 1.5 --gene-dispersion --gene-dispersion-scale 1.0` e il seme del
  profilo (20260912), come `td 28` e `ta 40`.
- **Script:** [genera_ta41.ps1](genera_ta41.ps1), [submit_ta41.ps1](submit_ta41.ps1).
