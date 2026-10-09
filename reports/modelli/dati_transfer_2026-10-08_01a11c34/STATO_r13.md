# Recupero NTC e consegna neurale — 9 ottobre 2026

Misurato: `neural_inputs_status_r7.json` corregge la fotografia r12:
mx/r4 è ERROR dopo tre parti D4 complete; df11/r5 è ancora RUNNING.
Non è stato interrotto. Le tre parti hanno ricevute e codice remoto verificati
in `ntc_mx_partial_verified_r1.json`: 237.140 candidati prima del merge,
2.157.860.033 byte di file da preservare. Le matrici non sono state scaricate
sul portatile né ancora ricalcolate o verificate numericamente qui.

Il difetto verificato è l'assunzione del lettore che ogni gruppo HDF5 sia
categorico. Il supporto aggiunto legge anche `values/mask`, incluse categorie
nullable, e rifiuta simboli mancanti dichiarati mappati. Undici test passano
(`ntc_cells_tests_r6.txt`), incluso un file scritto realmente da AnnData.
La prova del formato dei file remoti viene registrata dal preflight del nuovo
worker, prima dell'estrazione; la fixture non viene spacciata per quel controllo.
Campionamento, piani, normalizzazione e merge restano invariati.

`neural_inputs_cloud_prepared_r6.json` divide esclusivamente le 15 parti
mancanti in tre job privati CPU mx: r6a (3), r6b (6), r6c (6).
r6a recupera anche i file delle tre parti D4, con verifica integrale di hash e
dimensione nello stesso account, senza ripetere l'estrazione. I riferimenti
temporanei restano nel pacchetto privato fuori repository e log.
Il preflight r3 verifica gli input e gli slot; il controllo dei pacchetti r4
passa. Le ricevute effettive di lancio sono in `neural_launches/r6/`:
un pacchetto preparato non equivale a un job completato.

Il nuovo mandato è `MANDATO_CHIUSURA_ESM2_AMMI_r1.md` del Lead: quattro fit
iniziali, consegna per fold quando completa, preparazione distinta produzione.
Le 19 ancore dei fold restano verificate (`ammi_anchors_verified_r1.json`),
ma non dimostrano disponibilità delle ancore produzione a singola esclusione.

Per inner C-iPSC, PROTOCOLLO_v1 §2 fissa già `k562` BULK (272 bersagli) e
MESSAGGI del 9 ottobre 02:44 fissa il lignaggio K562. Il confronto rimane
inter-studio: nessuna verità nuova scelta dai risultati e nessuna replica
indipendente attribuita al riuso della stessa truth. K562 essential ha zero
bersagli del pannello e mantiene il limite esplicito; i suoi NTC non sono una
prova di partecipazione alla loss sul pannello.

NTC non ancora consegnati come corpus completo; nessun training GPU avviato
da DATI. D-053 resta aperto. Fast e invio T3 rimangono fermi.
Suite repository più recente: `repo_tests_r16.txt`, 290 test, tre errori
`cell_eval2.config` già presenti. Nessuna dichiarazione di suite tutta verde.
