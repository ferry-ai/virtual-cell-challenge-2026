# HEK293T accessibile sui tre account — 5 ottobre

Il proprietario conferma la condivisione del terzo blocco. Verifica positiva
di tutti i nove notebook HEK293T (banca e otto parti grezze) da davidmaisterx
e davideferante: ricevute in `shared_samples_dispatch_r3/`. Nessun nuovo 403.

Quattro push aggiuntivi accettati nel registro comune `other_sample_launches.jsonl`:

- davidmaisterx: HEK293T p2/6 e p4/6.
- davideferante: HEK293T p3/6 e p5/6.

Tutte le tredici parti KOLF/HCT116/HEK293T sono ora lanciate una sola volta,
distribuite sui tre account. Il blocco di condivisione è chiuso. Non confondere
tredici lanci con tredici completamenti: usare `partition_state.py` e verificare
le unioni, senza ripetere ingestion o campionamento.

`other_sample_progress_r6.json`: sei parti COMPLETE e sette RUNNING, incluse
le quattro appena avviate. Le nuove chiusure oltre lo snapshot r2 richiedono
ancora recupero e verifica delle ricevute prima di considerarle pronte.

`snapshot_parts_r2/state.json` riusa KOLF p0 già verificato e recupera soltanto
le nuove ricevute: KOLF p1 e HCT116 p0. Verificate due parti KOLF su tre e una
HCT116 su quattro; HEK293T ancora aperto a quel controllo. Prossimo snapshot
con `--previous snapshot_parts_r2/state.json`, nuovo output e piccoli manifest.
Le matrici restano su Kaggle, senza trasferimenti locali.

Il trainer esteso, il consumo effettivo delle nuove matrici e la valutazione
t28 restano aperti. L'indice globale conserva l'identità della versione r1;
aggiornarlo con una nuova revisione quando le nuove unità chiudono integralmente.
