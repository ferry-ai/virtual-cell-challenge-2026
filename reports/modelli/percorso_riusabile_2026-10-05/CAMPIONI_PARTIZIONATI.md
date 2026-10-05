# Campioni delle tre nuove banche — 5 ottobre

Implementato e provato su fixture: `materialize_partition.py` riusa il
materializzatore verificato, senza ricampionare. Ripartisce gli shard globali
per resto della divisione: KOLF 3 parti, HCT116 4, HEK293T 6. Ogni cellula e
riga mantiene la propria identità; ogni parte dichiara conteggi locali e globali.
`verify_union` rifiuta parti mancanti, duplicate, provenienze diverse e conteggi
non riconciliati. Due test passati, incluso H5AD → banca → matrice e alterazione
dei grezzi. La ricomposizione reale resta da verificare dopo le chiusure.

Il frazionamento riduce il rischio del limite disco di output; non costituisce
una misura anticipata della compressione. Restano attive le guardie su RAM e
disco e il limite di 18 GiB per parte. Nessuna cellula viene esclusa per spazio.
Un eventuale errore richiede conservare il tentativo e suddividere solo il lavoro
non recuperabile, non ripetere l'ingestione o modificare le selezioni.

`launch_other_samples.py` prepara 13 pacchetti immutabili; cinque push accettati
in `other_sample_launches.jsonl`: HCT116 p0/p1, HEK293T p0/p1, KOLF p0.
Otto parti restano da lanciare agli slot liberi. Nuova esecuzione dello stesso
launcher con `--launch --state snapshot_other_r2/state.json --preflight-out`
e un percorso nuovo salta tutti i tentativi già registrati. Un errore non viene
rilanciato automaticamente sopra il precedente.

Il preflight interroga tutti e tre gli account. Questi input privati sono montati
dal proprietario davideferrante11; il terzo account ha accesso negato misurato
in `third_input_access_r1.json`; accesso dell'altro account a queste sorgenti non
provato. Nessuna condivisione o copia massiva nuova. Capacità Colab non verificata
in questo giro. Le risorse effettive vengono scritte in `environment.json`.

`sample_partition_progress.py` registra stati e gli ultimi eventi dei log senza
scaricare matrici. Alla chiusura recuperare solo le ricevute, verificare versione
privata/codice/file presenti e unione delle parti. Le matrici restano montabili
dal cloud; il consumer deve verificarne gli hash e gestire tutte le parti.
Il lettore corrente di una singola unità non è ancora integrato per questa unione.

Nessun nuovo training, valutazione o risultato scientifico in questo passo.
Continuare anche la copertura delle altre linee, l'integrazione trainer e la
valutazione t28 dei fit preliminari. Le banche e i dodici campioni CD4 già chiusi
non vanno rilanciati. Nessun push Git.
