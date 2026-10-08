# Consegna completa delle medie di produzione e T/J

**Misurato, 8 ottobre 2026:** entrambe le release hanno tutte le 16 fonti e
array scaricati e verificati indipendentemente. Questa consegna completa r1;
non certifica ancora gli effetti del fit finale T2 né un beneficio predittivo.

| Regime | Manifest | SHA256 del file `common.npz` |
|---|---|---|
| Produzione / fonti ammesse nei fold C | [common_release_production_r1.json](common_release_production_r1.json) | `80103235addf13685397bb29bb06fd5851ef7e4a7920cc04570029bf2eac8b02` |
| Esclusioni target T / fonti ammesse nei fold J | [common_release_T_r1.json](common_release_T_r1.json) | `09e63dfe6d48489bf25a740938eec2d09a93529ae05bc64d0d0b52bea8b9c53f` |

I manifest indicano i percorsi assoluti nella radice dati, i denominatori per gene,
le prove dei produttori e gli split. Conservare l'ordine di calcolo e la semantica
del supporto descritti in [HANDOFF_T2_MEDIE_r1.md](HANDOFF_T2_MEDIE_r1.md).
Per C/J escludere integralmente le fonti del lignaggio trattenuto prima delle
statistiche apprese e della predizione. Per T/J usare soltanto la release `T`;
non sostituire un suo vettore con quello di produzione.

È pronta anche la vista CRISPRi del trainer con esclusioni:
[training_release_T_r1.json](training_release_T_r1.json), 163.143 risposte,
18.533 geni, 47 contesti, 14.786 target distinti e 1.366 chunk. La verifica
[training_contract_T_check_r1.json](training_contract_T_check_r1.json) attesta
gli hash dei manifest, l'assenza dei target nascosti, l'unicità target/contesto
e i pesi. Non attesta la lettura degli array remoti né il fit. La vista di
produzione resta a 203.975 risposte, 47 contesti e 18.562 target distinti.

T1 resta disponibile in [candidate_t1_r1.json](candidate_t1_r1.json).
Il fit finale T2 congelato in `final_t2/r1/prepared.json` non è stato avviato:
il consenso aggiuntivo richiesto in chat è ancora pendente. Prima del rilascio
il job dovrà riprodurre esattamente gli hash T1 e attestare consumo, supporto
e hash degli effetti T2. Nessuna generazione cellulare o submission è inclusa.

Il dispatcher `dispatch/r6` è terminato alle 19:22:45 UTC: tutte le unità
autorizzate sono raccolte; nessun runtime della campagna è rimasto occupato.
La scelta comparativa, i documenti condivisi e la promozione restano a VALIDAZIONE.
