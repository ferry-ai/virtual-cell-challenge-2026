# MODELLI-ESTERNI — sessione 01a11c35, 8 ottobre 2026

**Stato: componente sperimentale pronto; prova biologica pendente.**
Verdetto attuale: **approfondire**, nessuna adozione giustificata dai soli test.
Responsabile: Codex, chat `01a11c35-6e02-7d20-bd83-d8685a490980`.
Inizio verificato: 17:52 Europe/Rome. Nessun miglioramento predittivo misurato.

## Proprietà e confini

Questa sessione possiede soltanto questa cartella. DATI-TRANSFER possiede banca,
ingestion e trainer; VALIDAZIONE possiede split, scorer, confronto finale e
aggiornamenti condivisi. Nessun loro file viene modificato. Per istruzione esplicita
del proprietario, registro/indice/checkpoint saranno richiesti a VALIDAZIONE.
H1 test resta chiusa. Un test di interfaccia non è una validazione biologica.

## Sequenza

1. Verificare PIE, fold, memoria del training, licenze, asset e semantica output.
2. Congelare proposta comparativa e concordarla con VALIDAZIONE prima dei risultati.
3. Implementare adattatore con assi, maschere, provenance e blocchi di compatibilità.
4. Eseguire test piccoli locali; inferenza reale solo dopo asset e runtime autorizzati.
5. Consegnare componente e predizioni reali se ottenibili, separando fattibilità e utilità.

Riferimento iniziale: release canonica r1 del 7/10, produzione senza validazione
C/J. Nessuna scelta basata su nuovi score. Nuova release richiede nuova corsa,
mai sostituzione degli input durante un confronto.

## Coordinamento e risorse

Il primo messaggio a DATI-TRANSFER è stato rifiutato da auto-review; il proprietario
ha poi autorizzato esplicitamente entrambe le chat. Nessun agente aggiuntivo lanciato.
Drive autorizzato dal proprietario come archivio se lo spazio non basta.
La richiesta esplicita di acquisizione asset e calcolo cloud resta pendente.
Nessun download di pesi/dataset, job cloud, invio o push eseguito dalla sessione.
Il primo inventario per nomi nella radice dati non trova PIE/ESM2; non certifica
l'assenza di copie remote o con nome diverso. Si attende conferma del responsabile.

## Materiale

- **Leggere prima `STATO_r2.md`**: consegna attuale, dipendenze e limiti dei test.
- `ACCORDO_VALIDAZIONE_v1.md`: accettazione del protocollo indipendente prima dei risultati;
  `PROTOCOLLO_r1.md` conserva la proposta preliminare.
- `CANDIDATI.md`: shortlist internazionale, fonti primarie, selezione PIE/ESM2.
- `pie_adapter.py`, `export_stage100.py`: conversione controllata e serializzazione finale.
- `embedding_ridge.py`, `run_embedding_probe.py`: alternativa target-only con maschere;
  `context_ids` distinti dai lignaggi `context_groups`.
- `audit_public.py`, `public_audit_r1.json`: asset fissati, byte, hash e copertura.
- `audit_exposure.py`, `exposure_public_r1.json`: identificativi train/val pubblicati
  per quattro fold; review indipendente ancora necessaria.
- `acquire_assets.py`: acquisizione selettiva riprendibile, non eseguita.
- `test_pie_adapter.py`, `interface_tests_r2.txt`, `interface_tests_r3.txt`:
  prove CPU sintetiche; nuove ricevute conservate con nuova revisione.
- `CONSEGNA.md`: primo contratto di consegna; aggiornamenti in `STATO_r2.md`.
- `repo_tests_r1.txt`, `docs_check_r1.txt`, `docs_check_r2.txt`: verifiche repository,
  inclusi errori transitori e dipendenza scorer mancante, non nascosti.
