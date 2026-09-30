# Revisione indipendente tramite hub

29 settembre 2026, 18:22 UTC. Il proprietario ha offerto esplicitamente Grok e
Claude2 della base di lancio come risorse aggiuntive facoltative. Brief pronto in
`BRIEF.md`, sola lettura, compiti disgiunti sui due modelli neurali.

**Osservato con `hub.py doctor`, senza chiamare modelli:** Grok risulta senza login;
Claude2 riporta `wrong-account` rispetto a `expect_account` del registro dell'hub.
Non sono stati cambiati account o permessi, e nessun worker dell'hub è stato avviato.
Il lavoro continua con i tre sottoagenti della sessione corrente. Questa verifica
non è una revisione scientifica eseguita né un'approvazione dei modelli.

Alle 18:26 UTC, dopo che il proprietario ha esplicitamente autorizzato l'account
attuale di Claude2 e indicato Grok come collegato, è stato richiesto l'avvio reale
in modalità `read` del run `20260929-202639-vcc-lead-neural-review`. L'hub ha
confermato la creazione del processo in background. Questo non dimostra ancora
che entrambi i worker siano autenticati o che abbiano prodotto un rapporto.

Alle 18:35 UTC la verifica del run ha trovato Claude2 terminato con codice 1:
`You've hit your session limit · resets 9:20pm (Europe/Rome)`. Non ha prodotto una
revisione. Grok risultava ancora in esecuzione. Il messaggio del doctor non va quindi
interpretato come prova che l'account Claude2 sia inutilizzabile per autenticazione;
il blocco osservato nel tentativo reale è il limite di sessione. Nessun cambio di login.

Grok ha concluso in 19 minuti e 26 secondi. Il suo testo originale è conservato in
`GROK_R1.md`: revisione statica, senza test eseguiti né risultati dei banchi letti.
Non ha individuato un ulteriore errore fatale nel regime C; ha segnalato limiti
del bootstrap, diluizione della baseline da fallback e possibili spiegazioni del
guadagno diverse dalla biologia del contesto. Queste sono osservazioni da verificare,
non certificazioni del modello. I file di training letti sono confrontati con gli
hash del payload remoto; il lettore finale corretto resta l'emendamento separato.

Il 29/09 il primo nuovo lancio Claude2 per Stack è stato bloccato dal controllo
automatico: il consenso sull'account non era considerato consenso esplicito a
condividere contenuti del repository. Nessun worker è partito da quel tentativo.
Il proprietario ha poi autorizzato espressamente gli otto file di
`stack_review_packet_r1/` (81.240 byte, codice/piano/note, senza matrici o credenziali).
Una copia isolata fuori dal repository è stata fornita in modalità di sola lettura
al run `20260929-213819-vcc-stack-packet-review-r1`, avviato alle 19:38 UTC.
Il brief vieta letture fuori dal pacchetto.

La revisione è terminata dopo 20 minuti e 22 secondi; testo originale in
`CLAUDE2_STACK_R1.md`, SHA256
`5ef40073a49bd5cab14ff0c2b7d84c6e395111e47b7d4f34ba9cecc70afa00e7`.
È una lettura statica degli otto file e del codice Arc pubblico, senza esecuzione
né accesso agli outcome. L'autore conferma il contratto prompt/query e segnala
rumore del controllo sintetico condiviso, perdita di massa misurata fuori dal
supporto comune, distinzione maiuscole/minuscole e limiti dell'estensione a
produzione. Il protocollo di conferma dichiara già l'inferenza condizionale a
profili e controlli fissi; tre semi Poisson non replicano il modello GPU.
I rilievi restano da verificare individualmente: non sono una certificazione di
qualità, né una ragione per cambiare il criterio dopo aver visto gli score.
