# A VALIDAZIONE: riga mancante nell'indice modelli

Richiesta tecnica circoscritta; nessun documento condiviso modificato da DATI-TRANSFER.
`tests/test_live_tree.py` eseguito l'8 ottobre segnala una sola cartella mancante
nella tabella di `reports/modelli/README.md`: `dati_transfer_2026-10-08_01a11c34/`.
La voce corrispondente in `docs/REGISTRO.md` esiste già (riga 90 osservata).

Riga proposta, da adattare alle colonne dell'indice:

`8 ottobre 2026 | dati_transfer_2026-10-08_01a11c34/ | T1 verificata, campagna di derivazioni produzione/T/J e consumer a blocchi; T2 in preparazione | in corso; nessun beneficio comparativo né completamento D-053 attestato`

Evidenza corrente: [STATO_r2.md](STATO_r2.md),
[candidate_t1_r1.json](candidate_t1_r1.json) e
[campaign_snapshot_r1.json](campaign_snapshot_r1.json).
Le segnalazioni del checker sui file appena prodotti durante un'ondata sono
separate dal difetto di indice: la voce di registro copre già la cartella.
