# reports — the evidence, one folder per experiment

A folder here is evidence of what was seen on its date, and it is never edited: a new run
writes to a new folder, `reports/<tema>_<data>/`. Every new file or folder needs a row in
`docs/REGISTRO.md`, and one row can cover a folder of homogeneous files (a path ending in `/`).

Choose current work through `docs/PIANI.md`, not through next steps in a dated report.
After a run, link its evidence from the relevant plan card; keep the report immutable.

## Index

Grouped by what the folder is about, not by whether it still holds: a folder's row in
`docs/REGISTRO.md` says that. `tests/test_live_tree.py` fails if a folder is missing here.

**State and analyses** — read after `docs/PROGETTO.md` §0:
`ipotesi_trasferimento_2026-09-24/` (research hypotheses, switch genes and targeted data acquisition),
`analisi_2026-09-24/` (Claude, with calculations), `audit_stato_2026-09-24/` (ChatGPT,
with CP-0034), `direzione_2026-09-19/` (retrospective audit of the branches).

**Submissions and official scores** — one `trial_<data>/` per upload day, one
`prediction_t<NN>_<data>/` per registered prediction:
`trial_2026-09-12/`, `trial_2026-09-13/`, `trial_2026-09-17/`, `trial_2026-09-19/`,
`trial_2026-09-22/`, `trial_2026-09-23/`, `trial_2026-09-24/`, `trial_2026-09-25/`, `trial_2026-09-26/`, `prediction_t03_2026-09-17/`,
`prediction_t07_2026-09-19/`, `prediction_t08_2026-09-22/`, `prediction_t10_2026-09-23/`,
`prediction_t11_2026-09-23/`, `prediction_t12_2026-09-23/`, `prediction_t14_2026-09-23/`,
`prediction_t15_2026-09-23/`, `prediction_t16_2026-09-24/`, `prediction_t17_2026-09-24/`, `prediction_t18_2026-09-25/`,
`prediction_t19_2026-09-25/`, `prediction_t20_2026-09-26/`,
`trial02_decision_2026-09-17/`, `anchors_2026-09-17/` (the official anchors),
`scorer/`, `scorer_2026-09-12/` (the scorer contract), `leaderboard_2026-09-16/`.

**Sources and transfer** — stages 71, 97, 98 and 100–103:
`modulo_cis_2026-09-26/` (CRISPRi cis head: repression of genes near the target's TSS, added to transfer),
`programmi_2026-09-26/` (projection of transferred effects on shared programs: loses at every rank),
`bersagli_nuovi_2026-09-26/` (targets no source measured: linear gene embeddings, STRING partners, cis),
`universo_2026-09-26/` (K562 genome-wide caches for every target, not only the panel),
`rete_2026-09-26/` (network smoothing of measured targets with STRING partners: small effect),
`contesti_2026-09-26/` (H6 on Mixscale: basal similarity does not predict transfer; weighting by it loses),
`trasferimento_appreso_2026-09-26/` (learned transfer per target-gene pair; the magnitude channel is not adopted after the isolated bench r5; agent reports),
`risposta_comune_2026-09-26/` (the response all knockdowns share: 1-14% of the energy, does not transfer between lines),
`banco_varianti_2026-09-25/` (leave-one-source-out bench of recipe variants: shrinkage, gamma, consensus, gating, generator noise),
`ricerca_sorgenti_2026-09-25/` (agent search of 25 September: Mixscale provenance, microglia, Flex bridge, full catalogue of new sources),
`pattern_mixscale_2026-09-24/` (paired reanalysis: target/stimulus heterogeneity and sign specificity),
`dld1_audit_2026-09-24/` (exploratory DLD-1 audit and Mixscale file inventory),
`dld1_ceiling_2026-09-24/` (DLD-1 within-context ceiling against cross-context transfer),
`schede_sorgenti_2026-09-24/` (cards of 17 candidate sources, D-044 format),
`k562_sc_2026-09-17/`, `cd4_rows_2026-09-22/`, `orion_2026-09-23/`, `multisource_2026-09-22/`,
`direzione_2026-09-24/` (stage 103), `cis_2026-09-17/`, `coexpression_2026-09-17/`,
`source_coverage_2026-09-17/`, `source_lineage_2026-09-18/`, `transfer_ceiling/`,
`external_compat/`.

**Contexts A/B/C** — stages 85 and 99:
`contexts_2026-09-17/`, `context_identity/`, `context_fingerprints_2026-09-22/`.

**Generator, DE and benches** — stages 72–79 and 83:
`generator_null_2026-09-17/`, `generator_null_smoke_2026-09-17/`, `fast_de_2026-09-17/`,
`bench_2026-09-17/`, `prediction_calls_2026-09-17/`, `prediction_calls_2026-09-23/`,
`dispersion_2026-09-23/`, `call_budget_2026-09-17/`,
`banco_hepg2_v2_2026-09-26/` (inputs of the HepG2 bench with the real metrics, Colab job 046).

**Pseudobulk experiments of 12–19 September** — their code is archived (D-040):
`pipeline/`, `hepg2_2026-09-14/`, `benchmark_2026-09-14/`, `benchmark_3ctx_2026-09-14/`,
`encoder_inputs_2026-09-14/`, `svd_2026-09-15/`, `go_slim_2026-09-15/`, `rank_2026-09-15/`,
`gpu_2026-09-15/`, `runtime_2026-09-15/`, `eval_protocol_2026-09-15/`,
`expression_gate_2026-09-16/`, `conditioned_2026-09-18/`, `common_component_2026-09-18/`.

**Data acquisition and source probes** — their code is archived (D-040):
`data_audit/`, `candidate_verification/`, `candidate_pdf_extracted.txt`,
`ricerca_dataset_20260915.md`, `source_cards_2026-09-15/`, `jiang_2026-09-15/`,
`nadig_reconcile_2026-09-15/`, `primeflow_2026-09-15/`, `remote_2026-09-15/`,
`remote_catalog_2026-09-15/`, `drive_evidence_2026-09-17/`.

**Retired agent infrastructure** — D-040:
`orchestrator/`, `oracle/`, `grok_verification/`, `catena_2026-09-16/`, `ciclo_giornaliero/`.

## What a submission leaves here

Registered before generating, because the threshold does not move after the score
(CP-0030):
- `reports/prediction_t<NN>_<data>/prediction.json`: the expected band, and the rule to read
  the result by;
- `reports/trial_<data>/submission_texts.md`: the name and description of the upload.

Written while generating and submitting, in `reports/trial_<data>/`:
- `t<NN>_manifest_45_generate_prediction.json` and `t<NN>_generation_diagnostics.json`;
- `t<NN>_manifest_48_package_prediction.json` and `t<NN>_packaging.json`;
- the output of `vcc`, saved as it is: `submit_t<NN>_started.txt`, `submit_t<NN>_raw.json`,
  `submit_<entry>.json`, `status_<entry>.json`.

After the score come `reports/prediction_t<NN>_<data>/comparison.json`, a checkpoint and §0
of `docs/PROGETTO.md`. The latest complete example is t15: `reports/prediction_t15_2026-09-23/`
and `reports/trial_2026-09-24/`.

The owner's authorisations are transcribed in `reports/trial_2026-09-22/autorizzazioni.md`.
Read them, but a new agent confirms in chat before using one.
