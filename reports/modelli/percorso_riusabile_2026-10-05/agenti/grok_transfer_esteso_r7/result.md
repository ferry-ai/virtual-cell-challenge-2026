# r7 — pool prima dello shrink, pannello t25

Misurato il 2026-10-05. `test_r7_pool.py`: 7 test PASS, incluso un joint H1 su due banche sintetiche confrontato con `effects_from_pseudobulk`. `launch_r7.py` ha scritto tre pacchetti alle 2026-10-05T19:00:09Z. `worker_pushed` false. Kaggle non è stato chiamato. r1–r6 non sono stati modificati.

## Cosa cambia rispetto a r6

r6 non è il refit identico. `one_vote` e `collapse_fragment` combinavano tabelle già shrunk. r7 rifiuta una media post-shrink e un doppio voto. H1 resta una fonte: `h1_train` e `h1_val` mettono insieme le righe `count_sum`, i controlli identici una volta sola, poi una chiamata `effects_from_pseudobulk(condition=None)`. `training_vote` false è il peso unico dei due sotto-contesti. H1 test resta fuori.

Il test sintetico usa lo stesso input della funzione originale in `vcc2026.multisource`. La media 0,5 degli shrunk separati non coincide. L'adattatore coincide, anche il port locale. Lo spill per bersaglio, con tutti i controlli in ogni chiamata, coincide con la chiamata unica. Ipotesi non misurata sul cloud: le banche H1 ripetono gli stessi controlli; il joint lo verifica sui byte, non lo assume.

## Pannello

Misurato `raw/controls/pert_counts.csv`: 300 bersagli, sha256 del file `f57edd7b912ebd718efc7ee9d0f334772513e7cc418d133ce525470e373b3276`, sha256 del pannello `c9c4c9a69f76afd4507e9a7619fe9925c19ff34e5878c7854493683b23bea5ca`. È il pannello della cache r9 e dello stadio 100. Proiettare una statistica completa su quel pannello coincide con la chiamata diretta `targets=panel`. Il centraggio gamma 1 sull'unione dei bersagli non coincide: il mixer proietta prima del mix di condizione e prima del centraggio. I bersagli fuori pannello restano inventario in `panel_inventory.json`, non entrano nel modello t28. L'asse di espressione resta intero. Un simbolo sul pannello resta un id di perturbazione anche se non è una colonna dell'asse.

Indici locali H1, non le righe cloud: train 150 di cui 13 sul pannello, val 50 di cui 4, nessun simbolo in comune. Gli altri 183 restano inventario.

## Pacchetti

Il parent può spingere ora, dopo il proprio preflight:

1. `davideferrante11/vcc-effects-h1-joint-r7`. Input: `vcc-derivatives-rlab-h1-vcc2025-trainval` e l'asse `vcc-ingest-code-cd4-r1`. Non i kernel di effetti `h1-train-r4` e `h1-val-r4`.
2. `davideferrante11/vcc-effects-hek293t-j-a549-f4-r7`. Solo lo split `J:A549:f4`, stessa partizione e stesse guardie 6 GiB / 10 GiB. Non sostituisce la statistica di produzione HEK.

`davideferrante11/vcc-effects-mix-t25-r7` ha `push_now` false. Va spinto quando il joint H1 è COMPLETE con shrunk, raw e se. Monta Rest, Stim48hr, Stim8hr `retry1`, HepG2, Jurkat, K562 essential, KOLF chromatin, metabolic `retry1`, strong `retry1`, RPE1, HCT116, HEK293T, il joint H1 e la riparazione HEK. Pan `access1` è atteso ma non montato. Gli slug falliti non sono in `kernel_sources`.

Dodici id logici. L'unico gruppo con due tabelle è H1. Le quattro banche KOLF restano quattro fonti. CD4 resta tre joint di condizione e poi gamma 0. `k562_essential` non sostituisce `k562`.

## Ricevute usate, senza nuovo polling

CD4 Rest e Stim48hr erano già derived. Stim8hr `retry1` è derived: 4 donatori, 12129 bersagli (`cd4_joint_status_r3`). Metabolic `retry1` e strong `retry1` sono derived: 72 split, 6 statistiche, nessun `blocked_output` (`sourcefits_status_r8`). In `preflight_joint_progress_r5` pan `access1` e il GWPS K562 erano ancora RUNNING. `preflight_joint_progress_r4` è precedente ai retry KOLF. Le copie alias-resolved stanno in `ledger_snapshot/`.

## Non affermato

`fit_ready` false. `fit_admitted` false. `comparison_started` false. `local_score` null. Loss e ottimizzatore non esistono per questo modello lineare. Nessun beneficio di score. Ampiezza 1,576 e cis 5000 bp scala 2 restano negli stadi 100 e 45, una volta. Il banco 400×5 non è partito: l'uguaglianza dell'adattatore è sintetica; il joint H1 sul `count_sum` cloud non è ancora stato eseguito. Il catalogo D-053 non è completo.

Lacune tecniche, non esclusioni scientifiche: GWPS ancora aperto; pan `access1` ancora in corsa; composti Norman; controllo Tian 2021 senza mappa; QC Tian 2019 non verificato; partizioni HIPSCI già registrate e non rilanciate; SCP, KO, A549 e le guide GSE249595 senza statistica in questo pacchetto; accesso tecnico all'asse per `davideferante`.
