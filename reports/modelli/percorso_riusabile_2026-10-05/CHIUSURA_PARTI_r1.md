# Prima parte nuova persistente — 5 ottobre

`snapshot_parts_r1/state.json`: KOLF p0/3 completo e verificato per codice salvato,
versione privata stabile, ricevuta, identità banca, conteggi, maschere e presenza
di ogni file atteso. Recuperata soltanto la ricevuta, nessuna matrice trasferita.
L'intera unità KOLF rimane incompleta finché p1 e p2 non chiudono e l'unione passa.

`other_sample_progress_r5.json`: le altre otto parti sono RUNNING; le quattro sui
nuovi account hanno eventi reali di avanzamento. HEK293T p2–p5 non ancora lanciate.
Nessun errore nuovo rilevato. Non ripetere CD4, banche o parte KOLF già conclusa.

`partition_state.py --out <nuovo_snapshot> --previous snapshot_parts_r1/state.json`
riusa la verifica già salvata, recupera soltanto ricevute delle nuove chiusure e
rifiuta duplicati fra account, deriva di identità o conteggi incoerenti.
Quando tutte le parti sono verificate applica `verify_union`; non confonde una
parte completa con l'intera unità. La verifica integrale dei file avviene ancora
nel consumer; il training non ha ancora consumato queste matrici.
