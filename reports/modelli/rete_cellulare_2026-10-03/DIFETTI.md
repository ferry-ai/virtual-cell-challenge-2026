# I difetti dell'audit dell'1/10 nella versione 2 della rete cellulare

Fonte: [NOTA_TRAINING](../../analisi/lead_audit_2026-10-01/NOTA_TRAINING.md), [REVISIONE](../../analisi/lead_audit_2026-10-01/REVISIONE.md)
§2.1–2.6 e [AGGIORNAMENTO_R3](../../analisi/lead_audit_2026-10-01/AGGIORNAMENTO_R3.md). Per ciascun difetto: com'è
registrato qui (riprodotto, corretto, non applicabile, non verificabile), dove sta la correzione e quale test la prova.
I test sono in questa cartella e girano con `..\..\..\scripts\py.cmd -m unittest <modulo>`.

| Priorità | Difetto (audit) | Stato | Correzione | Prova |
|---|---|---|---|---|
| P1 | Pesi della loss normalizzati nel batch: K562 GW al 32,61% invece del 16,67% (2.2) | **riprodotto e corretto** | `cell_data.hierarchical_weights`: ogni gruppo di linea pesa uguale e, dentro il gruppo, ogni studio; pesi solo sulle unità attive; loss divisa per il batch nominale (`train_cellnet.train`) | `test_v2_units.Weights`: su epoche intere quote esatte 1/G; la composizione dei batch non cambia l'obiettivo; con la normalizzazione della versione 1 il gruppo grande supera il 50%. `coverage.json` riporta le quote effettive |
| P1 | Serbatoio dei controlli: dopo il tetto di 2.048 per contesto nessuna libreria HepG2 tiene 64 controlli; fusione dipendente dall'ordine (2.3) | **corretto** | `cell_data.pool_quotas`, `pool_hash`, `bottom_k`: per libreria i controlli con l'hash minore di (seme, chiave cellula), almeno min(n, ctrl_k) per libreria; `draw_controls_lib` registra se una cellula esce dalla sua libreria | `test_v2_units.Reservoir` (quote, indipendenza dall'ordine, inclusione uniforme, estrazioni), `test_v2_stages.test_reservoir`; `qc.json` → `reservoir`, `coverage.json` → `control_draws` |
| P1 | Split instabili al cambiare del corpus e ruoli assegnati prima del QC (2.1, 2.6) | **corretto** | gruppi di linea interi (`--line-groups`, `--holdout-group`), fold per hash della chiave riconciliata come il banco R-LEAD (`--hidden-fold`, `target_keys.py`), classi ricalcolate dopo l'ammissione (`classify_held`) | `test_v2_units.Folds` (stesse fold del banco, stabili quando il corpus cresce), `test_v2_stages.test_classes_after_qc` (il controesempio G2: C prima del QC, J dopo) |
| P1 | `unknown` non addestrato come risposta generica (2.4) | **riprodotto e corretto** | braccio `generic` con la stessa capacità e gli stessi batch, senza alcuna informazione sul bersaglio; l'identità resta diagnostica | `test_v2_stages.test_generic_arm_learns_its_unknown_row`: la riga `unknown` del braccio generico si muove, quella del braccio identità solo per il weight decay (il difetto, che resta, misurato) |
| P1 | Gradiente del gate nullo sotto il clamp: il gate chiuso non si riapre (AGGIORNAMENTO_R3) | **riprodotto e corretto** | `cellnet.gate_logs`, `mixture_loglik`: log-sigmoid dei logit, nessun clamp | `test_pi_floor.Gate`: il controesempio dell'audit (pi = 10⁻⁸) dà −(e−1)·10⁻⁸ con la nuova formula e un segno positivo con la vecchia. Collasso registrato prima del training: `pi_q50` < 10⁻³ (PROTOCOLLO §6) |
| P2 | La baseline appresa riceve gradiente dalle perturbate (2.5) | **non corretto, registrato** | invariato: l'ablazione chiesta (baseline empirica, solo controlli, congiunta) è un esperimento a sé, non una correzione | — |
| P2 | Valutazione sui 400 gruppi più grandi, il 79% da uno schermo (3.1) | **corretto per il pilot** | tutti i gruppi C e J della linea esclusa; T stratificato per chiave e scelto per hash (`--eval-max-groups-t`); esportazione degli spostamenti per il banco | `test_v2_stages.test_exports` |
| — | Righe d'identità casuali per i bersagli mai addestrati (osservato scrivendo il pilot) | **corretto** | embedding dei bersagli inizializzati a zero: un bersaglio J non riceve un vettore casuale | — |

Ciò che non è stato verificato: l'effetto delle correzioni sull'apprendimento reale. Lo diranno il pilot e i suoi
confronti.
