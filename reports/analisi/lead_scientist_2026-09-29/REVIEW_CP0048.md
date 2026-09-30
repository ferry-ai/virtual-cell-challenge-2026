# Revisione indipendente di CP-0048

29 settembre 2026. **Verifica in sola lettura del checkpoint e dei risultati
completi seed 0.** Nessun training, scoring cellulare o cambiamento del gate.
Il checkpoint storico non è stato modificato.

**Esito: nessuna correzione numerica o del verdetto necessaria.** Il vantaggio
medio è positivo ma inferiore all'utilità minima preregistrata. Il modello non
è ammissibile al successivo banco cellulare secondo la sua regola seed 0.

Il codice `train_neural_sources.py:116` costruisce la matrice dei coseni fra ogni
previsione e tutte le verità del contesto. La primaria è
`1 - (numero_di_coseni_maggiori_del_proprio + 0,5*pareggi_con_altri)/(N-1)`.
Il coseno del bersaglio corretto è una colonna secondaria distinta. Il lettore
`read_neural_sources.py` usa la colonna `rank`, media i target entro ciascun
contesto, i contesti entro famiglia e infine le cinque famiglie con peso uguale.
La formulazione «delta PDS medio a famiglie equiponderate» di CP-0048 è corretta;
non deve diventare «incremento del coseno medio» nelle sintesi.

Ricontati direttamente da `kaggle_neural_r1/readout_verified_r1/per_target.csv`:

- 6.144 coppie bersaglio–contesto per braccio, **5.049 bersagli distinti**;
- 12 contesti, esattamente 512 coppie ciascuno;
- cinque famiglie: CD4 tre contesti, iPSC tre, K562 tre, Orion due, RPE1 uno;
- delta macro del rango net−transfer **0,0022223326402478804**;
- delta macro del coseno net−transfer **0,002838355814406304**, quantità diversa.

Il verdetto e tutti i delta per famiglia citati coincidono con
`kaggle_neural_r1/readout_verified_r1/verdict.json` e con i punti indipendenti in
`kaggle_neural_r1/independent_points_r1.json`. Gli intervalli citati coincidono con
il reader corretto; non sono stati ricalcolati una seconda volta in questa review.
La correzione del lettore riguarda soltanto il parsing della stringa `null` da
CSV; i training e le predizioni congelate restano quelli originari.

Il `completion.json` originale riporta cinque fold con codice 0; l'ultimo termina
alle **19:24:12.521330 UTC**. Il codice finale 1 e lo stato complessivo `incomplete`
derivano dal reader originario, non da fold mancanti. CP-0048 distingue correttamente
questi fatti e non promuove un notebook terminato male a risultato valido senza
le verifiche successive.

La soglia di utilità è +0,01: **+0,002222 < +0,01** basta a fallire il gate anche
con IC95% sopra zero. Il limite minimo di famiglia, −0,007229, è sopra −0,01;
non è quella condizione a far fallire il candidato. La mancanza di vantaggio sul
cieco, −0,000416, non prova che il modello ignori ogni informazione del contesto.
La distinzione è già presente nel §4 del checkpoint.

Una precisazione di linguaggio per le sintesi future, senza correggere il
checkpoint: il §5 dice «non migliora»; leggerlo come **«non mostra un beneficio
utile in questa implementazione e nel seed 0»**, coerentemente col §4. Non
estenderlo all'equivalenza fra reti o all'inutilità della biologia.

Restano i limiti espliciti del protocollo: PDS relativo al pannello di ogni
contesto, target ripetuti fra contesti, bootstrap originario sui ranghi già
calcolati e condizionato alle cinque famiglie. La diagnostica globale per cluster
è additiva. La replica seed 1 va letta comunque; non sostituisce a posteriori il
seed 0 come corsa primaria e non avvia da sola la produzione.
