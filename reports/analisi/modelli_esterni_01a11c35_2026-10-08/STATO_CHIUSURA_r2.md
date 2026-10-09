# Chiusura: ESM2 letto, AMMI attende gli ultimi input

Snapshot del 9 ottobre 2026, heartbeat DATI delle 16:40:08 UTC. Integra
`STATO_CHIUSURA_r1.md`; non sostituisce le ricevute originali dei risultati.

## Misurato

ESM2 resta concluso: `RISULTATI_CHIUSURA_ESM2_r1.md` e
`esm2_closure_verified_r1.json`. L'aggiunta al riferimento T0 non dà un
miglioramento risolto dal confronto congelato. Nessun nuovo fit ESM2 previsto.

AMMI ha 18 parti NTC verificate; le 12 del produttore
`davideferrante11/dt-ntc-inputs-01a11c34-r5` risultano ancora RUNNING.
Nessun fit AMMI biologico avviato: il requisito sugli input resta bloccante.
Le quattro condizioni restano C-K562/C-iPSC × cells/none, seme 17, due epoche.
Il codice cloud congelato resta `ammi_code_package_r5/manifest.json`.

Il consenso umano `call_e5b26037196f4edaa64eb31c16676c61` è già salvato in
`autorizzazione_trasferimenti_AMMI_r1.json`. DATI-TRANSFER ha confermato la
ripresa della preparazione dei locator privati per i 105 derivati; aggiungerà
le 12 parti solo dopo verifica. Il vecchio stop T3 non viene usato per
interrompere questo nuovo lavoro autorizzato. Nessun T3 riavviato.

## Implementato e verificato su piccoli esempi

`collect_ammi_evidence_v1.py` recupera soltanto metadata da job terminali:
ricevute di training, export, parità nulla, checkpoint e diagnostiche.
Non scarica log, codice contenente locator, RNA, NTC o array di predizione.
Controlla identità del fit, due epoche con guardie superate, hash della ricevuta
di training, copertura delle query native, scala e coerenza delle ricevute.
Accetta un fallimento della sola diagnostica swapped conservando il nativo.

Il suo stato positivo è deliberatamente
`METADATA_PASS_BINARY_HASH_AND_READOUT_PENDING`: non verifica ancora il codice
remoto, gli hash dei payload binari né il beneficio scientifico. Questi restano
passi obbligatori del banco cloud prima di interpretare i contrasti.
Il programma non è stato eseguito su output biologici inesistenti.

`ammi_evidence_tests_r1.txt`: quattro test PASS, 0,559 secondi. Coprono
esclusione di file fuori perimetro, ricevuta alterata, predizione o diagnostica
mancante, conservazione del nativo senza promozione. Nessun cambiamento al
modello, al protocollo o al pacchetto di training congelato.

## Da eseguire dopo la consegna completa degli input

Verificare la ricevuta finale DATI, costruire i quattro pacchetti, rifare il
preflight di accessi e quote e lanciare i fit privati autorizzati. Recuperare
quindi le evidenze e verificare codice e payload nel banco; leggere cells–T0
e cells–none su entrambi i fold prima della decisione sul fit di produzione.
Una guardia o un controllo tecnico superato non è una prova di miglioramento.
Copertura D-053 completa non dichiarata. Nessun invio VCC o push Git.
