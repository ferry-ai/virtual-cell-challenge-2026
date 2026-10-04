# Esecuzione banca e primo training ibrido

Mandato del proprietario del 4 ottobre: eseguire banca e preparazione, poi avviare il
training; CPU sui tre account, GPU su davidmaisterx. Nessun invio o push Git.

**Campagna avviata, non risultato scientifico.** Sei job CPU costruiscono le dodici
unità CD4 verificate (21.980.517 cellule): momenti completi, donatori e condizioni
separati, campioni annidati 32/64/128 con libreria/guida conservate. `bank.py` mantiene
medie di proporzioni distinte dai rapporti di somme; `smoke.py` verifica questa
distinzione su un vero file H5AD minuscolo. Gli shard sono vincolati ai manifest già
verificati tramite hash del manifest e dimensione; qui non si ripete la lettura SHA
di tutti i 206 GB. Gli output comprendono hash, copertura e identità dei campioni.

In parallelo `prepare_fit.py` costruisce sul terzo account tre fold C: H1, HepG2,
Jurkat escluse intere. **Primo cohort/pilot sul cubo r2 esistente: 34 tabelle,
10 famiglie prima dell'esclusione, NON catalogo completo né banca CD4 per donatore.**
Ogni tabella e bersaglio ammesso entra nel fit, con esposizione registrata. Le ancore
`all` escludono sia la linea esterna sia quella della riga supervisionata.

Parametri congelati nei lanci: 3.000 passi, batch 64, LR 0,0003, rango 32,
larghezza 64, residuo limitato a 0,5, penalità 0,01, semi di fit 0/1/2;
bracci con/senza contesto. Per questo primo cohort la verità è l'effetto pseudobulk
storico e la loss è MSE mascherata e bilanciata famiglia/studio/contesto/bersaglio:
**non la KL sulle medie cellulari della banca nuova**, che attende integrazione.
I geni non misurati nei controlli hanno una maschera distinta dallo zero.
Nessuna scelta di passi o pesi sulla linea esterna. Nessuna promozione automatica.

`dispatch_training.py` trasferisce privatamente gli input CPU completati al
proprietario della GPU e avvia `train.py`, al massimo due fit GPU della campagna
contemporaneamente. `launches.jsonl` conserva codice congelato, parametri e ricevute;
`transfers.jsonl` conserva i trasferimenti. Gli stati RUNNING non certificano riuscita.
`training_started.json` e `training_done.json`, prodotti sul runtime, distinguono
CUDA effettiva e completamento. Il banco t28 e l'esportatore restano successivi.

Errori di avvio conservati in `errors/`: banca r1 senza import path (corretto r2),
preparazione r1 troppo restrittiva sui NaN dei controlli (corretto r2).
I nuovi pseudobulk CD4, gli altri contesti del catalogo non ancora integrati e il
campionamento cellulare restano necessari per il training esteso richiesto.
