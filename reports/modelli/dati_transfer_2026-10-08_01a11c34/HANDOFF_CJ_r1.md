# Viste C/J — K562 e iPSC

Consegna metadata dell'8 ottobre 2026, dopo le verifiche delle 20:48 UTC.
**Misurato sui metadata congelati:** le quattro viste sono costruite e verificate;
nessun fit C/J, nuova derivazione di effetti o lettura di risposte è stato eseguito.

| Vista | Parent | Righe | Contesti | Esperimenti | Target distinti | Chunk |
|---|---|---:|---:|---:|---:|---:|
| C-K562 | produzione r1 | 192.383 | 45 | 16 | 18.546 | 1.620 |
| C-iPSC | produzione r1 | 182.579 | 23 | 12 | 18.368 | 1.529 |
| J-K562 | T r1 | 153.913 | 45 | 16 | 14.772 | 1.293 |
| J-iPSC | T r1 | 146.039 | 23 | 12 | 14.624 | 1.222 |

I manifest sono `training_release_<vista>_r1.json`; ogni manifest fissa per hash
vista, input, split, parent e codice. I grandi JSON sono nella radice dati,
`processed/dati_transfer_2026-10-08_01a11c34/training_views/<vista>_r1/`.
Le ricevute indipendenti sono `training_contract_<vista>_check_r1.json`.

## Esclusioni e pesi

C riusa gli effetti di produzione dei soli contesti ammessi. J riusa
**esclusivamente** il parent T, derivato escludendo i target nascosti e le loro
componenti prima delle statistiche, delle maschere e dello shrinkage.
Non si ritagliano le risposte nascoste da un fit di produzione già appreso.

Gli effetti sono stimati per contesto con parametri di shrinkage fissati;
rimuovere un altro lignaggio non cambia questi array. Tutti i chunk rimasti
conservano identità, assi, ordine dei target, byte, hash e provenienza. La
verifica indipendente confronta ogni campo con il parent, eccetto `weights`.
I pesi vengono ricalcolati dopo l'esclusione, secondo la medesima policy:
uguale massa per esperimento, poi per contesto, poi per target. La massa
totale è 1 in ogni vista. Tutti i contesti non esclusi dal fold restano presenti.

Le esclusioni dei fold K562/iPSC di v1 e v2 sono state confrontate: lignaggio,
unità, tabelle, sorgenti dei bracci e verità non sono cambiati. Gli split nuovi
puntano al manifest v2. H1 test resta protetta. Le viste conservano anche
`upstream_split`, `effective_split` e il parent per verificare l'ordine delle
esclusioni. In questi file `split_manifest` è un pin; i target nascosti sono
in `effective_split.hidden_targets`.

## Query e supporto

[fold_query_eligibility_r1.json](fold_query_eligibility_r1.json) conserva i target
ammissibili e gli identificativi biologici dei contesti tenuti fuori.
In entrambi i fold C, 299 target del pannello sono visti nel training;
**TMEM104 non lo è**. Non etichettarlo come target visto di C e non rimuoverlo
silenziosamente dal pannello di valutazione: mantenere maschera/ripiego
espliciti secondo il contratto. Nessuna riga training è rimossa per questo.
J prevede i 66 target nascosti preregistrati, tutti assenti dal training;
i 67 target del pannello assenti complessivamente includono anche TMEM104.
L'effettiva disponibilità della verità per ogni query resta a VALIDAZIONE.

## Accessi runtime preparati

Per ogni vista esiste
`C:/Users/ferra/vcc2026-data/processed/dati_transfer_2026-10-08_01a11c34/runtime_access/<vista>_df11_r1/runtime_inputs.json`.
Usare i suoi pin e mount con il resolver; non sostituire il nome del regime
su una vista T. I locator sono solo sottoinsiemi dei riferimenti già autorizzati,
custoditi fuori dal repository. Nessun nuovo riferimento è stato emesso,
nessun dato trasferito da questa preparazione e nessuna ACL modificata.

| Vista | Mount nativi | Chunk privati | Byte privati |
|---|---:|---:|---:|
| C-K562 | 22 | 82 | 1.164.005.881 |
| C-iPSC | 20 | 5 | 53.537.510 |
| J-K562 | 22 | 63 | 929.902.301 |
| J-iPSC | 20 | 5 | 43.760.376 |

Destinazione autorizzata dei riferimenti: soli job privati di
`davideferrante11`. Le ricevute pubblicabili sono
`fold_runtime_access_<vista>_r1.json`, prive di URL sensibili. Questa consegna
non lancia né attesta nuovi job. Validità dei riferimenti e hash dei chunk
devono essere verificati nel runtime effettivo, come per produzione/T.

## Prove e limiti

`build_fold_training_release.py`, `verify_training_contract.py`,
`audit_fold_queries.py`; tre fixture passate in `fold_training_tests_r1.txt`.
Le fixture verificano esclusioni per alias, protezione H1, rifiuto di parent
di produzione per J, assenza dei target hash-nascosti e conservazione di
tutti i contesti ammessi con pesi corretti. Le quattro verifiche reali dei
metadata passano. Gli array non sono stati riletti qui, nessun training C/J
è attestato e D-053 conserva le lacune della release madre.

Precedenti: S-006 e S-011 richiedono di distinguere statistiche del training
e contributo specifico dei target. Questa preparazione non cambia il modello
o il criterio di confronto: rende esplicite le esclusioni prima di qualunque
statistica appresa tra contesti. Un parent, chunk, peso o target escluso non
coerente ferma la verifica; nessun ripiego alla produzione per J.
