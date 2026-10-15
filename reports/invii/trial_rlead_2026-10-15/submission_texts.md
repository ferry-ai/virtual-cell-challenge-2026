# Testi dell'invio ta 42

Scritti il 15 ottobre 2026, prima di generare e prima di ogni caricamento. Il via è di Alfredo in chat il 15/10: «vedi
che dati ti servono e procedi al lavoro». Previsione e regola:
[prediction_ta42_2026-10-15/prediction.json](../prediction_ta42_2026-10-15/prediction.json).

- **Nome del modello:** `ta 42 T3 x centred bridge network ensemble`
- **Descrizione:** uguale al nome.
- **Pacchetto:** `vcc2026-data/artifacts/ta42pack/prediction.vcc`; sha256 in `ta42_packaging.json`.
- **Effetti:**
  - 0,7 di T3 (gli effetti di `td 38`, dal dataset pubblico di Davide `vcc-rsb-inputs-70dc-r1`);
  - 0,3 della rete centrata di `ta 40`;
  - entrambe le parti a norma unitaria, poi riportate alla norma di T3;
  - esportazione: [esporta_ens.py](../../modelli/rete_su_t3_2026-10-15/esporta_ens.py) `--w 0.7`.
- **Emissione:** lo stadio 45 con `--effects-scale 1.5 --gene-dispersion --gene-dispersion-scale 1.0`, seme del
  profilo 20260912.
- **Script:** [genera_ta42.ps1](genera_ta42.ps1), [submit_ta42.ps1](submit_ta42.ps1).
