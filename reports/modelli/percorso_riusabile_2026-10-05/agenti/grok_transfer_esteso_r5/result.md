# Release incrementale r5 — pacchetti pronti, mix non ancora eseguito

Orologio misurato: 2026-10-05T17:32:46Z. Il `ready_dispatch.json` è stato scritto alle 2026-10-05T17:29:01Z e il sorgente dei tre joint è stato riallineato nei pacchetti alle 17:32:46Z (`joint_code_sha256` nel dispatch). Questo worker non ha chiamato Kaggle. `worker_pushed` è false. Nessun punteggio. Il modello lineare non ha optimizer né loss.

## Cosa è eseguibile

Quattro kernel CPU privati, internet spento, in `agenti/grok_transfer_esteso_r5/packages/`:

- `vcc-effects-cd4-rest-joint-r5`
- `vcc-effects-cd4-stim8hr-joint-r5`
- `vcc-effects-cd4-stim48hr-joint-r5`
- `vcc-effects-mix-t25-r5`

`push_now` è false su tutti. Il comando del parent sta in `parent_push_command` di ciascun pacchetto dentro `ready_dispatch.json`. I tre joint montano le banche già salvate (D1–D3 su davideferrante11, D4 su davidmaisterx) e l'asse `davideferrante11/vcc-ingest-code-cd4-r1`. Il mixer monta in cloud i tre joint e i cinque frammenti già accettati. Non serve copiarli in locale.

I joint si pushano quando un censimento mostra uno slot libero su davideferrante11. L'ultima evidenza, non un censimento nuovo, è il preflight del parent con K562 GWPS aperto e quattro ricevute df11 RUNNING, più K562 essential su davidmaisterx. Il tetto è 5 job attivi per account. Il mixer si pusha quando i tre joint e i cinque frammenti hanno un output.

Se Kaggle rifiuta il `kernel_source` di davidmaisterx, il parent condivide quel kernel con davideferrante11 oppure copia la banca sull'account che pusha. D4 resta nel joint.

## Contratto della stima

Per ogni condizione, Rest, Stim8hr e Stim48hr, i quattro donatori entrano in una sola `effects_from_pseudobulk`. Lo shrinkage è quello della media pesata sui donatori. I controlli di un donatore senza il bersaglio restano nel pool. Se una banca pinnata manca, lo stato è `blocked` e non esce una stima sui donatori rimasti.

Lo stack compatto passa la guardia di 6 GiB. Se i quattro compact insieme la superano, il kernel non li carica insieme: fa una chiamata per bersaglio con tutti i donatori e lo stesso pool di controlli. Sulla fixture le due schedule coincidono con la funzione originale. La guardia non è stata abbassata. Una colonna con conteggio diverso da zero dove la maschera è falsa blocca la banca. Le colonne non si tagliano.

`cd4_mix` è `mix` a gamma 0 e reliability 100, raw e shrunk separati, e si costruisce solo con tutte e tre le condizioni. Il mix fra fonti è gamma 1, reliability 100, peso 1. L'ampiezza 1.576 resta nel pin di emissione e non entra nel mix. Cis: 5000 bp, scale 2, file `reports/trasferimento/cis_2026-09-17/k562_neighbour_pairs.csv`, sha256 `d874c305f12e932d2d43eff629ea7d44c8536b7a198868c8fac10007d01dcf8f`. Il path della ricetta `reports/cis_2026-09-17/k562_neighbour_pairs.csv` è assente. Il kernel degli effetti non applica la testa cis.

Il modello salvato dal mixer ha kind `incremental_extended_release`, `fit_admitted` false, le due claims false. Fonti previste in questo primo mix: `cd4_mix`, `orion_hct116`, `orion_hek293t`, `rpe1`, `jurkat_nadig`, `k562_essential`. K562 essential non sostituisce K562 GWPS.

## Frammenti già in corso, non duplicati

Ricevute in `sourcefits_launch_r1`, stato RUNNING al momento della ricevuta, `full_training` false:

- davideferrante11/vcc-effects-orion-hct116-r4
- davideferrante11/vcc-effects-orion-hek293t-r4
- davideferrante11/vcc-effects-rpe1-r4
- davideferrante11/vcc-effects-jurkat-nadig-r4
- davidmaisterx/vcc-effects-k562-essential-r4

Il mixer, fra le statistiche derivate, tiene il file con il massimo `n_rows_kept`. Se due id diversi condividono quel massimo, si ferma. Legge tutte le tabelle BIO di quel file e le altre ricevute restano in `not_used_fold`. Poi ogni fonte ha un voto solo, con mix a gamma 0. I frammenti r4 sono già shrunk per gruppo BIO: il manifest lo segna `aggregated_after_shrink` true. Il joint CD4 lo segna false. Se il frammento non ha il raw, il raw non viene copiato dallo shrunk.

## Verifica

`test_r5_refit.py`: ultima esecuzione, 10 test OK in 0.289s. Confrontano la funzione originale `vcc2026.multisource`, a parità di input.

- Il compact multi-donatore, incluso un donatore solo di controlli, coincide con `effects_from_pseudobulk` sulla matrice intera. La media degli shrunk calcolati donatore per donatore no.
- Lo spill su disco coincide con la stessa chiamata originale.
- Il mix di condizione a gamma 0 coincide con `mix` originale, raw e shrunk separati, e si discosta dalla media uguale e dal gamma 1.
- Un frammento con due tabelle BIO le carica entrambe; nel mix finale la fonte compare una volta.
- ENSG e un simbolo fuori asse restano id di perturbazione. UNASSIGNED e `A+B` sono bloccati, e `A+B` non viene spezzato. `TP53` in hidden globale esce prima della statistica.

Sono fixture. Non sono una prova sulle banche CD4. Il confronto 400×5 non è partito. `observed_result` è null.

## Blocchi nominati, fuori da questo primo mix

Il contratto di copertura resta `training_coverage_r1/expected.json`. Lo sha256 del file `launches_frozen.json` coincide con quello registrato lì. `training_ready` di r10 resta false. Questo dispatch non certifica l'ammissione.

Restano fuori, con motivo: K562 GWPS ancora del parent; Norman, in attesa di una mappa source verificata che separi le singole dalle doppie, senza inventare composti; il token `control` di Tian2021 da verificare nel producer; Tian2019 per il QC; HIPSCI, controlli e ancore già registrati, senza rilancio; l'asse assente su davideferante, che è un accesso tecnico; i KO SCP, stesso stimatore dove è valido, senza inventare chimica o guide; GSE249595 senza guide; HepG2, H1 e i quattro KOLF, non in questo primo mix. I dodici pacchetti r4 per donatore CD4 non vanno usati come stima CD4.

Storage r10, sha256 `7134c13c741e04b1bb90b15f42afd2a50e653454aca17e49005edcad6f2e7fdf`. Asse sha256 `25bfa66715e186bebabce7ac788bbcea47e2bf59ca70be1f8f3a06f2f0e47201`, 18533 geni.
