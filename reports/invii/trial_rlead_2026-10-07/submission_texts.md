# Testi dell'invio t38

Scritti prima del caricamento, 7 ottobre 2026 notte. Il proprietario ha dato il via in chat («sì, invia il t38 appena
è pronto»). Previsione e regola: [prediction_t38_2026-10-07/prediction.json](../prediction_t38_2026-10-07/prediction.json).

- **Nome del modello:** `trial-38 all-source transfer + learned correction, amplitude 1.0`
- **Descrizione:** uguale al nome (regola del proprietario: in classifica solo il nome dell'invio).
- **Pacchetto:** `vcc2026-data/artifacts/t38pack/prediction.vcc`, prodotto dallo stadio 48 sul file dello stadio 45
  `t38gen` (effetti `effects_t36_2026-10-06`, `--effects-scale 1.0 --gene-dispersion --gene-dispersion-scale 1.0`,
  seme 20260912). Hash in `t38_packaging.json`.
- **Script:** [submit_t38.ps1](submit_t38.ps1); il keep-awake è [keep_awake_t38.ps1](keep_awake_t38.ps1).
