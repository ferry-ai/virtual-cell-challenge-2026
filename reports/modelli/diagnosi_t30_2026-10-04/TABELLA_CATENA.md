# Training → banco → esportazione → generazione: che cosa era uguale e che cosa no

4 ottobre 2026, sessione `ba9b8bcb`. Ogni cella è **letta** dal codice o da una ricevuta, con la fonte nell'ultima
colonna; dove una differenza c'è, la colonna «Differenza» dice se il suo effetto sul punteggio è misurato o resta
un'ipotesi. La rete è quella del fold HepG2, la sola usata nel t30.

Fonti abbreviate: **P** = [protocollo D-056](../ibrido_selettivo_2026-10-04/PROTOCOLLO.md); **HL** =
`ibrido_selettivo_2026-10-04/hybrid_lanes.py`; **EX** = `ibrido_selettivo_2026-10-04/export_abc.py`; **CFG** =
`ibrido_selettivo_2026-10-04/esito/train_hepg2_r1/train/config.json`; **BJ** = `…/esito/lanes_*_r1/laneB/bench/bench.json`
e `laneB.log`; **M** = `reports/invii/trial_2026-10-04/t30_effects_manifest.json`; **M45** = manifest dello stadio 45
del t30 e del t25; **R1–R5** = le ricevute di questa cartella (`esito/chain_t30_r2.json`, `bench_members_r1.json`,
`export_vs_rows_r1.json`, `export_on_line_controls_r2.json`, `panel_vs_rows_targets_r1.json`).

| Voce | Training (fold HepG2) | Banco D-056 (corsie A/B) | Esportazione A/B/C | Generazione t30 | Differenza | Fonte |
|---|---|---|---|---|---|---|
| Fonti delle cellule | 13 unità di 7 gruppi: A549, H1, Jurkat, K562, Neuron, RPE1, iPSC; 3.970.762 cellule ammesse | — (pesi congelati) | — | — | pilot a 8 gruppi dichiarato; CD4T, HCT116, HEK293T solo nelle ancore | CFG, P §0 |
| Fonti dell'ancora / baseline | `all`: nove gruppi del cubo senza HepG2, medie J, ampiezza 1,576 | T = `transfer_all_J`, la stessa regola senza la linea esclusa | ancora: gli stessi nove gruppi; **baseline: effetti t25** (quattro fonti, stimatore con restringimento, testa cis ×2) | effetti t25 + w · R | **R è sommata a una baseline diversa da quella rispetto a cui è definita**; coseno mediano fra t25 e l'ancora passata per la rete 0,71. Misurata la distanza, non il suo effetto sul punteggio | P §4, §13–14; EX; R3 |
| Asse e maschere | 18.533 geni del modello, maschera per studio | geni delle cellule vere della linea: 18.077 (H1), 9.023 (HepG2), 8.259 (RPE1), 8.283 (Jurkat), 7.679 (K562) | 18.533 geni misurati in A, B e C | 18.533 | quattro linee su cinque valutano su meno della metà dell'asse di gara; effetto non misurato | CFG; BJ; M |
| Stimatore di R | — | `eval_shifts.npz`: s(N) − s(A) sulle cellule di valutazione di ogni gruppo (rumore indipendente fra bersagli) | 1.024 estrazioni di 64 controlli **uguali per tutti i bersagli**, una libreria per contesto, seme 20261004 | — | procedura mai passata per il banco; sui controlli di HepG2 dà quota comune 0,61 e ampiezza 0,88 contro 0,23 e 0,42 del banco sulla stessa linea (R4; procedura e bersagli non separati) | HL; EX; P §14.3; R4 |
| Unità | spostamento sulle proporzioni medie (`cell_data.shift`), ln | ln fold change del cubo per T e verità; R nello stimatore della rete | idem; float16 | ln → log2 nello stadio 45 | T del banco è il valore del cubo, non s(A): già sul banco T ≠ s(A) | HL; EX |
| Bersagli corretti | — | righe C della linea esclusa; 70–150 bersagli nella corsia B; **dei 300 del pannello: 0 su HepG2, RPE1 e Jurkat, 15 su H1, 72 (righe) e 6 (corsia) su K562** | 230 su 300; 70 con w = 0 (22 senza righe CRISPRi di training, 48 anche nascosti) | 300 | il banco ha valutato altri bersagli: transfer più grande (RMS mediana 0,120–0,135 contro 0,107), più fonti (6–8 contro 5); i 70 non corretti non ricevono la parte comune | M; R3; R5 |
| Selettore | — | leave-one-line-out (sviluppo), congelato (conferma); stimato su 3.604 righe: H1 72, HepG2 1.743, RPE1 1.789 | lo stesso file congelato (`00758778…`) | — | sulle righe il guadagno fuori fold è +0,4 %, −1,8 %, +0,4 %; su A/B/C l'ingresso `f_log_ratio` è a +1,5…+2,2 deviazioni standard e il 45 % dei bersagli di B e C è fuori dalla fascia 1–99 % dello sviluppo; l'ingresso di espressione vale 0 («non misurato») nel 17–21 % delle righe di quattro linee e mai su A/B/C | selector_final.json; R2; R3 |
| Peso w | — | medio 0,29 / 0,59 / 0,33 / 0,33 / 0,31; fra 0,02 e 0,98 su HepG2 | medio 0,28; fra 0,09 e 0,49 | — | su A/B/C il selettore è quasi una miscela costante | decision.json; M; R3 |
| Ampiezza di R | guardia interna: RMS(R)/RMS(ancora) 0,65 allo stato esportato | RMS(R)/RMS(T) mediano per riga 0,24–0,42 | 0,71 (A), 0,96 (B), 0,96 (C) | — | misurata; due–quattro volte quella del banco | guard.json; R3 |
| Quota comune di R | guardia interna: 0,17 allo stato esportato; arresto oltre 0,5 | 0,07–0,24 per linea | **0,62 (A), 0,69 (B), 0,66 (C)**; quella della correzione aggiunta 0,59–0,67 | — | misurata; **oltre la soglia 0,5 della guardia del trainer**, che all'esportazione non veniva applicata | guard.json; R3 |
| Scala e cis | ampiezza 1,576 nell'ancora | 1,576, nessuna testa cis | t25: 1,576 e testa cis ×2 su 78 coppie | `effects_scale` 1,0 | la testa cis esiste solo nella baseline dell'invio | M; t25_regen manifest |
| Clipping | Δ limitata a ±6 | MSE locale troncata in [0, 1]; gli altri membri no | — | spostamento composizionale log2 tagliato a 6 | MSE scalata = 0 per ogni braccio su ogni linea e sul sito: il membro non informa | bench.py `scale`; R2 |
| Generatore | — | `trial01_cells`, Poisson, **un flusso casuale per braccio** | — | `trial-ext-profile` = lo stesso percorso, **un flusso per l'intero file** | stessa funzione; il rumore di ogni blocco dopo il primo bersaglio cambiato è diverso fra bracci e fra t30 e t25 | HL; scripts/45; R1 |
| Cellule per bersaglio | — | metà A delle cellule vere: mediana **32** previste contro 32 vere | — | **400** | potenza dei test DE molto diversa; non misurato l'effetto | BJ; M45 |
| Controlli | 64 per cellula, propria libreria | pool di 2.048 controlli veri, **gli stessi** per predetto, vero e riferimento DE | 18.400 controlli ufficiali per contesto | profilo basale e librerie dei controlli ufficiali | il pacchetto inviato non contiene controlli (120.000 cellule per contesto = 300 × 400); quali controlli usi il sito dal lato predetto qui non è verificato | BJ; M; M45 |
| Verità e scala dei membri | — | metà profondità (replicato = 1, baseline = 0 locali); chiamate vere mediane 35–40 per bersaglio su H1, HepG2, RPE1 e 6–8 su K562 e Jurkat | — | ancore ufficiali r4 per contesto | il JAC locale ha denominatore (replicato − baseline) 0,05 su K562, 0,12 su Jurkat, 0,16 su HepG2: valori fino a −4,7; su Jurkat e K562 il transfer chiama più geni del replicato (53 e 43 contro 40 e 24 per bersaglio) | BJ; R2 |
| Seme | 0 | banco 2026, generatore 20260912 | estrazioni 20261004 | 20260912 | un solo seme ovunque; nessuna misura del rumore di un braccio | CFG; BJ; M45 |
| Stato della rete | passo 20.000 di 31.022 (miglior controllo interno) | lo stesso | lo stesso (`model.pt` `365bf625…`) | — | nessuna | acceptance.json; R1 |
| Regola di decisione | arresti su guardie interne | media dei sei membri; guardia PDS della corsia A solo sulle linee di conferma | parità a w = 0 sugli array | regola ±0,005 contro il t25 | sul fold esportato la corsia B perdeva PDS (−0,093) e la corsia A anche (−0,039): la media lo copriva | P §8–9; R2 |

## Parità a w = 0 lungo la catena

| Tratto | Esito | Fonte |
|---|---|---|
| Effetti: w = 0 restituisce gli array del t25 | vera in A, B, C | M (`parity_w0_equal_t25`) |
| Effetti t25 rigenerati = quelli del t25 inviato | stesso sha256 `1d3e1dac…` | `t25_regen_effects_manifest.json`, R1 |
| Argomenti dello stadio 45 uguali al t25 salvo i file degli effetti | vero; due opzioni nuove al valore inattivo | R1 |
| Profilo previsto dei 70 bersagli non corretti = t25 | 210 blocchi su 210 identici (spostamento composizionale) | R1 |
| **Cellule dei 70 bersagli non corretti = t25** | **no: 1 blocco su 210 identico** (il solo che precede il primo bersaglio corretto) | R1 |
| Corsia B: `ibrido_w0` = `transfer` | cellule identiche sulle cinque linee | `parity.json` di ogni corsia |

La parità era verificata sugli array degli effetti e, nel banco, su un braccio con effetti identici dall'inizio alla
fine. Non copriva il caso reale: un invio in cui alcuni bersagli cambiano e gli altri no. Lì il flusso casuale unico
sposta il rumore di tutti i blocchi successivi, quindi `t30 − t25` contiene, oltre alla correzione, un cambio di
realizzazione su 899 blocchi su 900. L'unica coppia di semi misurata sul sito vale 0,0016 (t24 − t22).
