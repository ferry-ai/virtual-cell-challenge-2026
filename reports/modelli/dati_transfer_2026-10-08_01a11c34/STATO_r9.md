# DATI-TRANSFER — 9 ottobre 2026, 00:54 Europe/Rome

Ora letta dall'orologio UTC. Stato misurato; sostituisce r8 per l'avanzamento.

Il fit T3 è completato e verificato. La ricevuta
`extended_transfer/r1/fit_completion_r1/verification.json` attesta i 22 chunk KO
previsti, 12 contesti, 5 voti di studio/linea e tutti i 34 bersagli supportati.
Il controllo nullo riproduce T1 byte per byte; nessuna modifica fuori dai
bersagli KO. I tre effetti hanno SHA256
`b8c61f6da684f6c28107199469ac42ef030a4644176371b9723ae6e3f863f6a6`.
Identità e ruoli sono in `candidate_t3_r1.json` e `coverage_t3_r1.json`.

Il primo job ha fallito **dopo il fit**, all'argomento CLI della generazione.
Il recupero privato `davideferrante11/dt-t3-generate-01a11c34-r2`, versione 1,
riusa gli effetti congelati senza rifare il fit. Lancio accettato alle
22:39:48 UTC. Il log live mostra A completato e B 151/300 dopo 679 secondi;
la generazione completa richiede A/B/C, 300 bersagli e 400 cellule per bersaglio.
I log statici vuoti durante RUNNING non erano evidenza di mancato avvio.
Lo stream ha terminato due volte con ChunkedEncodingError; questo è un errore
del collegamento di osservazione, non una ricevuta di fallimento del job.

Una copia difensiva ulteriore è stata preparata per un sospetto sui percorsi
Linux, **non confermato dall'esecuzione reale**. Non è stata lanciata e ora il
launcher la blocca (`generation_recovery/r2/NOT_LAUNCHED_r1.json`).

La previsione t38 e la regola ±0,005 contro t36 restano quelle congelate prima
del fit. VCC whoami alle 22:38:21 UTC consentiva l'invio, senza upload pendenti.
Non è ancora stato scaricato né inviato un prodotto t38. DATI-TRANSFER mantiene
la corsia di invio esclusiva assegnata dal Lead per questo candidato.
`collect_t38_generation.py` verifica il produttore e tutte le ricevute prima del
download; `t38_submission.py` verifica il file locale e consente una sola entry.
I cinque test offline delle guardie di consegna passano (`t38_delivery_tests_r1.txt`).

Limiti scientifici: nessun punteggio T3 misurato, nessuna promozione e nessuna
copertura D-053 completa dichiarata. Il ledger conserva CRISPRa, mapping,
controlli insufficienti, soglie cellulari, QC storico ed esperimenti già
rappresentati come ruoli/esclusioni espliciti; non sono stati tagliati contesti
per rispettare l'orario. T3 non incorpora i fit ESM2 ancora in corso.

Verifiche del repository: `repo_docs_check_r13.txt` PASS. La suite completa ha
eseguito 290 test con tre errori per `cell_eval2.config` assente e un errore
d'indice t37/trial 8 ottobre; quelle due righe sono ora presenti nell'indice,
ma la verifica mirata va ancora ripetuta. Non si registra la suite come PASS.

Per VALIDAZIONE: registrare l'esito operativo della generazione e poi l'eventuale
score con la regola già congelata. L'incidente tecnico è descritto in
`generation_incident_r1.json`; le cartelle t38 sono già nel registro condiviso.
