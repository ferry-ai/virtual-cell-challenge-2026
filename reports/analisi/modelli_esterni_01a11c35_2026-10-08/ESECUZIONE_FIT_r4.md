# Cinque fit effettivi e accesso J-iPSC ancora incompleto

Misurato il 9 ottobre 2026, circa 00:11 Europe/Rome. Aggiorna lo stato di
ESECUZIONE_FIT_r3.md, conservato. Le misure riguardano l'esecuzione, non il
beneficio predittivo. Fonte: `live_progress_r3.json`, estratti dei log remoti.

| Fit | Account | Geni di risposta completati su 18.533 |
|---|---|---:|
| produzione r4 | davideferrante11 | 5.120 |
| T r3 | davideferrante11 | 7.104 |
| C-K562 r1 | davideferrante11 | almeno 1.856 |
| J-K562 r1 | davideferrante11 | 4.544 |
| C-iPSC r3 | davidmaisterx | almeno 640 |

C-iPSC r3 ha risolto tutti i 1.529 blocchi della vista: 182.579 righe, 23
contesti, 24.933.790.309 byte verificati e 1.114.426.892 byte trasferiti
privatamente. È entrato nel full_fit. La prova di uso finale richiede ancora
le ricevute complete e il verificatore indipendente di DATI-TRANSFER.

Il proprietario ha esteso il consenso ai trasferimenti privati aggiuntivi
H1/K562 verso C e CD4/HepG2/Jurkat/HCT116/HEK293T/RPE1/H1/K562 verso J,
domanda `call_d00b2526c23e4a11b662023128fe9811`, item 0. Il piano esatto e
l'audit dei consensi sono della chat DATI-TRANSFER. Nessun dato è stato reso
pubblico. Nessun RNA è stato scaricato sul portatile.

## J-iPSC: tentativi e cause distinte

- r2: mount privati di un altro account inaccessibili, verificato e descritto
  nella r3 di questo rapporto. Guardia `source_access_preflight.py`.
- r3: push rifiutato HTTP 400, codice sorgente oltre 1 MB per i locator
  incorporati. Nessun fit. Guardia di dimensione nel launcher v5.
- r4: sorgente breve e bundle in dataset privato; bootstrap e preflight
  riusciti, errore in `resolve_all_chunks` alle 21:56:52 UTC. Nessun fit.
  Dataset `davideferante/esm2-j-ipsc-01a11c35-r4-private-bundle`, privato
  verificato dall'API, 859.214 byte. Pin in `prepared_J-iPSC_r4.json` e
  `private_bundle_upload_r1.json`. Il codice scientifico resta invariato.
- diagnostico singolo autorizzato: URLError sul primo blocco, senza codice
  HTTP; dettagli e limiti in `ACCESSO_J_r1.md`. Non confondere COMPLETE del
  notebook con riuscita dell'accesso o del training.

Il quinto slot df11 resta riservato da DATI al nuovo transfer esteso e alla
generazione. Non si rilancia J su quello slot. Nessuna ottimizzazione o
interruzione dei cinque fit esistenti.

## Raccolta e verifiche

Il raccoglitore finito dei quattro job df11 resta in corso; un secondo
processo nascosto raccoglie soltanto C-iPSC r3 (`terminal_collection_ipsc_r1.process.json`).
Entrambi scaricano la allowlist di output scientifici fuori Git e applicano
`verify_fit_outputs.py`; non lanciano job, non pubblicano e non fanno scoring.
Dipendono dalla permanenza dei processi locali, senza garanzia dopo spegnimento.

Test: `combined_tests_r8.txt` 32 PASS; `dataset_bundle_tests_r1.txt` 5 PASS
(include tre test di pacchetto precedenti). `repo_tests_r5.txt`: 290 test,
tre errori per la dipendenza ambientale `cell_eval2.config` assente, già
osservata; non dichiarati come suite passata. `docs_check_r13.txt` PASS
strutturale. Nessuna modifica alle dipendenze condivise.

## Conclusione scientifica ancora aperta

Non sono disponibili score indipendenti di questo componente. I fit usano
le viste congelate, tutte le loro righe e i contesti previsti, con esclusioni
C/T/J; questa copertura non chiude D-053 per l'intero catalogo. Nessun nuovo
dato viene inserito a corsa iniziata. La nuova copertura estesa appartiene a
DATI e a un confronto distinto. Nessuna promozione o invio per rispettare
una scadenza. Restano la scala nativa, il limite target-only e il fallback
esplicito per TMEM104. Decisione: approfondire, validazione ancora pendente.
