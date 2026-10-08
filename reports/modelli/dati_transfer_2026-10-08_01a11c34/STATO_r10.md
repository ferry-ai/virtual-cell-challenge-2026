# DATI-TRANSFER — 9 ottobre 2026, 01:34 Europe/Rome

Ora misurata con l'orologio UTC. Questa fotografia aggiorna r9; non è un esito finale.

Il proprietario ha precisato in questa chat: **upload terminato entro le 02:00**,
con refit parziale ammesso come ripiego. Il mandato è registrato in
`deadline_fallback_authorization_r1.json`. T1/T2 hanno effetti disponibili, ma
non è disponibile un loro `.vcc` già generato: cambiare effetti non abbrevierebbe
la generazione e il trasferimento.

T3 scientifico resta invariato e verificato. Il recupero r2 ha generato tutte
le 360.000 cellule e fallito dopo, cercando `manifest.json` invece del nome reale
`manifest_45_generate_prediction.json`. Il file era sul disco temporaneo e non
compare nell'inventario esportato: `generation_recovery/r1/output_inventory_after_failure.json`.

Il tentativo r4 senza compressione si è fermato al preflight. Il controllo
aggiunto richiedeva 64 GiB sulla cartella di output, che in r5 misura 19,50 GiB;
il disco temporaneo separato misura invece 1069,92 GiB. Il vecchio controllo
confondeva la destinazione finale con quella degli intermedi. Non è stata
avviata una generazione nel tentativo r4.

È ora RUNNING `davideferrante11/dt-t3-generate-01a11c34-r5`, versione 1,
con gli stessi effetti, seed e parametri, compressione intermedia **LZF lossless**,
nome del manifest corretto e conservazione del file generato in caso di un
errore successivo. Codice e prova: `generation_recovery/r4/prepared.json` e
`t38_storage_tests_lzf_r1.json`. Il test verifica dati CSR, assi ed etichette
identici. Il log live mostra A e B completati e C 126/300 a 860 secondi.

Per rispettare l'orario è pronta una corsia di **upload diretto cloud → VCC**:
`cloud_delivery/r1/plan.json`, `cloud_t38_delivery.py`, `package_upload_t38.py`.
La chiave VCC resta locale; il runtime privato riceve soltanto il riferimento
temporaneo per scrivere un singolo oggetto della singola entry. Nessuna nuova
entry è ancora stata creata in questa fotografia. Tre test offline delle
guardie passano: `cloud_upload_tests_r2.txt`.

Se lo stadio 48 rifiuta la stima di disco sulla cartella di output, la corsia
recupera le cellule già generate e impacchetta sul disco temporaneo capiente,
senza rifare fit o generazione. Resta obbligatoria la verifica del formato,
del payload bit per bit e del checksum remoto prima dell'avvio dello scoring.

DT-5 di VALIDAZIONE è recepito **senza cambiare candidato o soglia**:
`reports/invii/prediction_t38_2026-10-09/addendum_DT5_r1.json` dichiara le 6.722
coppie sostenute soltanto dal KO, sulle quali il peso normalizzato 0,25 si
semplifica. Non si interpreta quel peso come limite globale all'effetto.
Nessun punteggio T3, miglioramento o copertura D-053 completa è ancora misurato.
