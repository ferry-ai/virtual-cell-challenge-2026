# Decisione di invio t28 — 29 settembre 2026

Decisione del lead prima dell'upload, su richiesta esplicita del proprietario di inviare appena possibile. Autorizzazione già ricevuta e ribadita nella chat; riferimento: `autorizzazione_lead_2026-09-29.md`.

**Si invia t28 come esperimento ufficiale della ricetta congelata**, non come modello già dimostrato competitivo. La previsione e le soglie in `../prediction_t28_2026-09-29/prediction.json` restano invariate. Il valore atteso soggettivo non è un intervallo calibrato.

Il contenitore da 4.161.126.400 byte ha superato la convalida ufficiale, la verifica del payload e il SHA256 integrale dal portatile: `0d70ba92d68817b46383b11c53d513a41c85329230b9ff5524ac51f7bd110b32`. Ricevuta: `t28_in_place_validation_r1/validation.json`, 21:42:04 UTC. L'upload usa direttamente il file su Drive e verifica nuovamente l'integrità prima della chiamata ufficiale.

L'audit [SCORE_CREDIBILITA](../../analisi/lead_scientist_2026-09-29/SCORE_CREDIBILITA.md) non trova errori aritmetici bloccanti nel banco. Il delta +0,028918 è però un indice locale: 95/96 target della conferma erano già valutati storicamente, i controlli sono condivisi fra stima e scoring, e le ancore aggregate non ricostruiscono esattamente gli score ufficiali. La conferma è interna alla selezione odierna, non indipendente dall'intera ricerca. La MSE grezza peggiora; il risultato ufficiale userà tutti e sei i membri pubblicati senza omissioni.

Il candidato contiene il trasferimento da quattro sorgenti, amplificazione ×1,5 e dispersione stimata dai controlli. Non contiene la rete sperimentale né Stack. Non realizza ancora il training con tutti i dataset e le molte linee disponibili: questa lacuna viene resa prioritaria nel piano successivo.

Questa decisione non attesta un upload completato. Fanno fede le ricevute CLI in `t28_direct_attempt_r1/` e lo status ufficiale dell'entry; non si modifica la ricetta o la soglia dopo aver letto lo score.
