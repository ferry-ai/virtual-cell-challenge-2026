# Generazione r8 — pacchetto pronto, invio ancora bloccato

Misurato il 2026-10-05. Questo worker non ha chiamato Kaggle, non ha fatto push e non ha generato cellule. `push_now` è false. Il prodotto da caricare, quando il kernel termina, è un solo `prediction.vcc`.

## Dispatch

Il pacchetto è `packages/vcc-generate-t28-extbank-r1`, slug `davideferrante11/vcc-generate-t28-extbank-r1`. È un kernel CPU privato, senza GPU, TPU o internet. Monta solo `davideferrante11/vcc-effects-mix-t25-bank-r1-retry1`. Il dataset già esistente è `davideferrante11/vcc-ingest-code-cd4-r1`. Il producer in ERROR `vcc-effects-mix-t25-bank-r1` non è un mount: la ricevuta r2 lo marca `supersedes_failed` e il driver rifiuta quella directory.

La ricevuta r2, copiata in `ledger_snapshot`, dice RUNNING alle 2026-10-05T19:17:31Z. Non è stata riletta da Kaggle. Il parent spinge il kernel di generazione solo quando quel mix è COMPLETE e i tre h5ad ufficiali sono attaccati. Il comando sta in `ready_dispatch.json`. Non va lanciato da questo worker.

## Catena e ricetta

La cache votata del mix entra nello stage 100. Ampiezza 1.576 e le coppie cis originali (5000 bp, scala 2, sha256 `d874c305f12e932d2d43eff629ea7d44c8536b7a198868c8fac10007d01dcf8f`) si applicano lì, una volta. Lo stage 45 applica `effects_scale` 1.5 una volta, con dispersione genica accesa e scala 1, 400 cellule, seme 20260912, trial `trial-ext-profile`. Lo stage 48 scrive il `.vcc`. `effects.npz` non è una fonte. I controlli non entrano nella predizione.

La ricetta non è `configs/recipes/t25.json`. Ogni fonte presente in `source_model.json` del mix riceve peso 1 su A, B e C. `cd4_mix` è l'unico voto CD4. `k562_essential` resta con il proprio nome. `k562` è rifiutato. `h1_train` e `h1_val` non sono due voti. La lista concreta esiste solo a mix concluso: il contratto in `prediction_contract.json` è registrato prima della generazione e non contiene una banda di miglioramento.

Lo score ufficiale di riferimento resta 0.14484520500645978. Non è un obiettivo e non è un confronto locale. `local_score`, `loss` e `optimizer` sono null. `training_ready` e `fit_ready` restano false. Il banco a 5 semi non è partito.

## Identità misurata

Pannello `pert_counts.csv`: 300 bersagli, sha256 del file `f57edd7b912ebd718efc7ee9d0f334772513e7cc418d133ce525470e373b3276`, sha256 dei bersagli `c9c4c9a69f76afd4507e9a7619fe9925c19ff34e5878c7854493683b23bea5ca`. Asse `gene_names.csv` locale e copia `kaggle_code_cd4_r1`: stesso sha256 `25bfa66715e186bebabce7ac788bbcea47e2bf59ca70be1f8f3a06f2f0e47201`, 119295 byte. Coordinate: sha256 `065906f739094c6ae572d21c0b14e7b8f2d4daa0284cdb68864ed27b9caba34c`.

Controlli locali, da attaccare prima del push. Non esiste uno slug di dataset nel catalogo letto, e questo worker non li carica.

| File | Byte | sha256 |
|---|---:|---|
| context_A.h5ad | 224973316 | `f22e71968487d3da9402769dcd0c73a47851fad4cd7dd25510283c923031fe3e` |
| context_B.h5ad | 210966111 | `41557555b3febf6db19fd930b4dd7db88941840077bf985d14dfff959c782380` |
| context_C.h5ad | 226056691 | `e090e7c7cfdd0006f689214ba38ba0cd2669578e89c9bc325b65f0bd940c02e0` |

Guardie non abbassate: RAM 6 GiB se la misura c'è, disco di output 10 GiB, riserva stage 45 di 10 GiB e stage 48 di 6 GiB. Il run completo chiede circa 17 GiB liberi; è una nota, non una soglia più bassa. Nove controlli di identità, contratto e adapter, sono passati. `scripts/31_check_docs.py` termina OK, 64 checkpoint, e non chiede una riga di registro.

## Inventario, dopo il pacchetto

`sourcefits_status_r9` ha 11 righe derived e verified. Sono `h1_train` e `h1_val` (un solo transfer id `h1`) più HepG2, Jurkat, K562 essential, i quattro KOLF ammessi (pan è access1), HCT116 e RPE1. I tre joint CD4 in `cd4_joint_status_r3` sono derived e diventano un solo `cd4_mix`. Il pan access1 è pubblico, versione 1, sha256 del codice `59a73c1c608f28cfe76ab3dfd593db010b2c336411a3146a7937b8e5b06d5f6a`, come `public_kolf_pan_r1/consumer_verified.json`.

`orion_hek293t` in r9 è `partial_output_budget`, verified false, ammissione `if_exact` nel mix. Non viene aggiunto a mano. Il repair HEK non è fra i `kernel_sources` del mix retry né del kernel di generazione. Il kernel GWPS del parent non è un mount di questa generazione.

`adapters_r8.py` rifiuta HIPSCI, Tian 2021, Tian 2019, SCP, KO, A549, Norman e GSE249595. Ogni rifiuto è un gap tecnico: nessuna esclusione per dimensione o overlap, nessuna mappa inventata. Non è un secondo mix.

H1 joint, dalla ricevuta `h1_joint_completion_r1`, è derived, 72 split, `fit_ready` false. Lo snapshot r7 si ferma a sourcefits r8 e al preflight r5; questa ondata congela r9, r3, il completamento H1 e le due ricevute del mix.
