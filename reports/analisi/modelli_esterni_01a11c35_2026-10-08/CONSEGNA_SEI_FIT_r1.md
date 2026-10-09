# Sei fit ESM2 recuperati e verificati

9 ottobre 2026, verifiche complete entro le12:56 Europe/Rome. Aggiorna
HANDOFF_RETI_r2.md: non rimangono modelli o predizioni da recuperare.
**Verdetto: approfondire; nessuna promozione scientifica.**

## Consegna a VALIDAZIONE e DATI

Manifest unico: `completed_fits_handoff_r1.json`,10955byte,
SHA256 `715dc24a9c5136f3f2cfa69a7c13ecaf22ea8780b2fe20f315a159c9462b8d3c`.
Contiene percorsi assoluti, byte e hash di modello/predizioni, pin delle ricevute
tecniche e della verifica indipendente di DATI per ognuno dei sei fit.

| Vista | Righe consumate | Contesti | Query consegnate | Esito tecnico/consumo |
|---|---:|---:|---:|---|
| Produzione |203975|47|300|PASS/PASS|
| T |163143|47|3102|PASS/PASS|
| C-K562 |192383|45|299|PASS/PASS|
| C-iPSC |182579|23|299|PASS/PASS|
| J-K562 |153913|45|66|PASS/PASS|
| J-iPSC |146039|23|66|PASS/PASS|

Asse di risposta18533geni. Produzione ha una query senza ESM2, dichiarata e
mascherata; nessuna feature mancante nelle query degli altri fit. Controllate
tutte le celle predette, gli assi, le maschere, la finitezza sul supporto,
gli hash di modello e ricevute; il reload riproduce le righe prefissate,
inclusa quella senza feature in produzione. Nessuna risposta RNA di training
è stata scaricata o usata dal verificatore locale. DATI attesta consumo e
split contro le viste congelate; nessun D-053 completo dichiarato.

I nuovi file nativi si trovano sotto
`C:/Users/ferra/vcc2026-data/external_models/01a11c35/verified_cloud_outputs_resume_r4/`;
T e J-K562 conservano i percorsi precedenti in `verified_cloud_outputs/`.
Le ricevute `.verified_resume_r4.json` sostituiscono lo stato intermedio
`PREDICTIONS_PASS_MODEL_RELOAD_PENDING` senza riscriverlo.

**Richiesta a VALIDAZIONE:** leggere ora C-K562, C-iPSC e J-iPSC; i percorsi
e SHA richiesti nei MESSAGGI delle11:25 sono tutti nel manifest. Regola C
accettata prima dei nuovi numeri: T0 dove predice, ridge come ripiego dove
non predice. Nessuna miscela selezionata dopo la lettura. La produzione non
è un fold C e non dimostra generalizzazione su nuovi contesti.
Registrare questa consegna nei documenti condivisi di vostra proprietà.

## Significato dei risultati già noti

La ridge legge la descrizione ESM2 del bersaglio e fornisce la stessa risposta
per tutti i contesti. Nel test T ha riconosciuto meglio i bersagli nelle iPSC;
negli altri quattro lignaggi il confronto con le previsioni scambiate non
mostra un segnale specifico risolto. J-K562 non migliora questa conclusione.
Questi sono risultati di VALIDAZIONE già pubblicati in RISULTATI_ESM2_T.md,
non nuovi punteggi prodotti da questa consegna.

Intuizione: il modello sembra aver imparato soprattutto come reagisce una
famiglia cellulare molto rappresentata. È un'ipotesi, non la prova che sappia
prevedere qualsiasi cellula. J-iPSC permette ora di vedere che cosa rimane
quando quella famiglia non viene mostrata nel training. Il banco deve ancora
leggere questo nuovo file: la correttezza tecnica non anticipa il suo risultato.

## Rete contestuale e dipendenze concrete

PROTOCOLLO_AMMI_r2.md, ADDENDUM_AMMI_r2_coverage.md, ammi_context.py,
ammi_contract_v2.py e ammi_train_v2.py: specifica e motore isolato implementati.
Ricepite le sette condizioni: stessa ancora T0 panel, esclusioni outer+inner
e del lignaggio della riga, controlli individuali, confronto con media e senza
contesto, scambio dei controlli sul modello addestrato, tre semi cells/none,
masse per lignaggio e quota comune di ancora/residuo/previsione.

14 fixture AMMI e56 test totali PASS; commit locale `deaadcb2`, senza push.
Non è ancora un training biologico. Mancano estrazione numerica NTC e ancore,
wrapper con verifica completa dei pin e collegamento alla guardia interna del
banco. DATI ha preparato i pacchetti CPU; la loro presenza non prova esecuzione
o accesso remoto. I contesti senza target panel sono lacune esplicite, non
supervisione fittizia. Nessun nuovo job GPU è stato lanciato in questa ripresa.

## Recupero e verifiche repository

I quattro recuperi v4 hanno richiesto circa707,906,1010 e970secondi per
J-iPSC, C-K562, C-iPSC e produzione (durata ricostruita da UTC iniziale della
ricevuta e mtime finale); tutti oltre il timeout600s del precedente collector.
Questo spiega perché quel limite era insufficiente per i tempi osservati;
gli errori SSL intermittenti precedenti hanno causa remota non identificata.
v4 ha completato14file per fit, senza errori di trasporto registrati, tramite
allowlist, paginazione e HTTPS streaming. Nessun URL firmato conservato.
I tentativi e le ricevute precedenti restano disponibili; nessun fit rilanciato.

Controllo documentale r18 PASS. Suite repository r7:290 test,3 errori per
`cell_eval2.config` mancante; nessun altro fallimento. Il precedente errore
di forma del protocollo non ricompare. Non si dichiara la suite globale PASS.

Il candidato di consegna resta t36. Nessuna pubblicazione, push remoto o
submission è stata effettuata da questo lavoro.
