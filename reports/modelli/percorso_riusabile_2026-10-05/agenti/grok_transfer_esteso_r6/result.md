# Mixer di produzione r6

Misurato il 2026-10-05T18:26:02Z. `worker_pushed` false. `kaggle_called` false. `fit_ready` false. `fit_admitted` false. `all_compatible_admitted` false. `claims_complete_training` false. Confronto 400×5 non avviato: `local_score` null. Lo score ufficiale trascritto 0.14484520500645978 non è il banco locale.

Otto fixture in `test_r6_refit.py` PASS. La statistica di produzione è l'identità di split condivisa dalle ricevute C con fold nullo e gruppo tenuto diverso dalla linea. Il massimo di `n_rows_kept` non seleziona. Il manifesto dei 72 split è vincolato prima dei mount. I joint CD4 non votano come effetti di validazione C/J.

## Pacchetto da lanciare

`packages/vcc-effects-mix-t25-r6/`, slug `davideferrante11/vcc-effects-mix-t25-r6`. CPU, privato, senza GPU e senza internet. Asse `davideferrante11/vcc-ingest-code-cd4-r1`. Il comando per il genitore è in `ready_dispatch.json`. `push_now` false.

Dodici mount, tutti richiesti tranne HEK (`if_exact`): i joint Rest, Stim8hr e Stim48hr; H1 train e val; HepG2; Jurkat; K562 essential; KOLF chromatin; HCT116; RPE1; HEK293T. Stim8hr è `davideferrante11/vcc-effects-cd4-stim8hr-joint-r5-retry1`. La ricevuta dice che il primo slug Stim8hr non ha prodotto output scientifico: non è montato e non va rilanciato.

Il mixer scrive la cache nello schema di `save_table` e `effects.npz` del mix gamma 1. Ampiezza 1.576, cis 5000 bp scala 2 e `effects_scale` 1.5 non sono applicati qui. Restano, una volta sola, negli stadi 100 e 45. Loss e optimizer non esistono per questo modello lineare.

## Non rilanciare

GWPS K562, i tre joint, i sourcefit già accettati, Norman iPSC, HIPSCI targeted19, KOLF metabolic, KOLF strong, pan-genome r4 e pan-genome access1.

`kernel-metadata-when-remaining-kolf-exact.json` aggiunge solo metabolic, strong e `davidmaisterx/vcc-effects-kolf-pan-genome-r4-access1`. Si usa quando quei tre output hanno shrunk, raw e se. L'output bloccato di pan r4 non vota. access1 è già accettato e risultava RUNNING, con l'asse `davidmaisterx/vcc-ingest-code-cd4-r1` nel payload: non è stato duplicato.

## Azioni aperte

Il genitore lancia il mixer quando i tre output joint sono COMPLETE. HEK vota solo se l'identità di produzione ha shrunk, raw e se; lo split `J:A549:f4` resta assente, non zero. Metabolic e strong sono `if_exact` e non montati: la ricevuta li vedeva RUNNING o senza stato provider. K562 essential non sostituisce K562: GWPS è ancora il kernel aperto del genitore.

Lacune tecniche, non esclusioni: singoli Norman senza mappa compound inventata; token control di Tian non mappato; QC Tian 2019 non verificato; partizioni HIPSCI non in questo mixer; SCP/KO/A549 senza adattatore in questo pacchetto; guide GSE249595 assenti; l'account terzo non ha il dataset dell'asse. Gli snapshot consumati sono in `ledger_snapshot/`, compreso `sourcefits_status_r6__verification.json`. Gli stadi 100 e 45 non sono stati eseguiti.
