# Accessi privati AMMI preparati

9 ottobre 2026, 18:44 Europe/Rome. Tipo: verifica tecnica misurata;
nessuna prova di training o beneficio scientifico.

Il consenso umano originale in MODELLI è registrato in
[ammi_private_access_authorization_r1.json](ammi_private_access_authorization_r1.json):
105 file derivati e, dopo verifica, 12 parti NTC df11, destinazione esclusiva
i quattro fit AMMI privati su davidmaisterx. Nessuna produzione o riapertura T3.

La [ricevuta di preparazione](ammi_private_access_issued_r1.json) fissa i percorsi
e gli hash della mappa privata e del piano mount, entrambi fuori Git sotto
`C:/Users/ferra/vcc2026-data/processed/dati_transfer_2026-10-08_01a11c34/ammi_private_access_r1/issued_r1/`.

- 105 origini, 1.639.694.217 byte, equivalenti a 97 SHA distinti e 1.494.478.569 byte.
- Mappa `private_locators.json`, `status=authorized`, pin del consenso e
  `files[SHA]={bytes,sha256,url}`; nessun URL nei report o nei log.
- `mount_plan.json`: 21 kernel COMPLETE e ammissibili con credenziali davidmaisterx,
  cioè 18 produttori di aggregati e i tre produttori NTC MX r6a/r6b/r7a.
- [Verifica HTTP](ammi_locator_headers_r1.json): 97/97 risposte 200 e lunghezze
  corrispondenti. Risposte streaming chiuse senza leggere il corpo. Primo termine
  codificato nei link: 12 ottobre, 16:40:25 UTC; non garantisce disponibilità futura.

La verifica HTTP **non** ricalcola gli hash dei contenuti. I pin provengono dai
manifest verificati; il consumer verifica integralmente dimensioni e SHA prima
dell'uso. MODELLI ha confermato il ricalcolo dei due hash dei manifest locali.

Il primo tentativo ha preparato otto sorgenti e i mount. Per la nona, le tre
tabelle di validazione avevano suffisso `cache/` nel manifest e percorso reale
`model/cache/` nel produttore. Corretto questo solo prefisso per quella sorgente,
sono stati emessi i tre riferimenti mancanti; nessun dato o pin è cambiato.
La traccia del primo tentativo resta in `preparation_results.json` fuori Git.

Le **12 parti NTC df11/r5 restano escluse**: ultimo heartbeat osservato 16:43:21 UTC,
stato RUNNING. L'osservatore già attivo attende il termine e verifica le ricevute;
non è stato duplicato né è stato interrotto il produttore. Gli input del training
restano incompleti (`complete_training_inputs=false`). I dettagli delle 18 parti
MX già completate rimangono in [STATO_r14.md](STATO_r14.md).

Verifiche locali: piano e consenso esatti, rifiuto di URL non HTTPS o con credenziali,
rifiuto di destinazioni private nel repository, compilazione dei due nuovi script.
Nessuna matrice RNA scaricata sul portatile, nessuna ACL o visibilità cambiata,
nessun job lanciato. D-053 resta aperto.
