# df11/r5: avanzamento non osservabile durante l'esecuzione

9 ottobre 2026, osservazione conclusa alle 19:23:11 Europe/Rome.
Tipo: fatti tecnici misurati; scenario temporale condizionato separato.

La [seconda lettura remota](df11_progress_snapshot_r2.json) conferma RUNNING,
versione 1 privata CPU, nessun messaggio di fallimento. L'hash del codice remoto
coincide con quello del lancio: `87520f60c1fd752b51eb3e788c998400701f65e38d5faf13b162bdf7cf7b4670`.
La [prima lettura](df11_progress_snapshot_r1.json) concorda sullo stato.

- Richiesta di lancio: 16:50:07; accettata alle 16:50:15; prima osservazione
  RUNNING alle 16:50:22, come nelle ricevute `neural_launches/r5/df11_ntc/`.
  Questi orari non provano l'istante di avvio effettivo del codice nel container.
- Parti COMPLETE osservabili: **non determinabili**. L'API output restituisce
  zero file durante il run: non significa che siano state completate zero parti.
- Fase corrente: **non determinabile**. Nessun `progress.json`, completion,
  messaggio di fase o log salvato è accessibile ora.
- Log live: due letture limitate, terminate con ReadTimeout dopo 15 e 35 secondi;
  nessun evento ricevuto. Nessun errore del calcolo è stato osservato.
- `last_run_time` nei metadati remoti riporta il 6 ottobre e cambia fra le
  letture, in conflitto con le ricevute del lancio del 9 ottobre. Non è usato
  per stabilire avvio o durata.

Il worker esatto incorporato nel pacchetto r5 è stato letto senza eseguirlo.
Elabora sequenzialmente D1/D2/D3 (nove parti), poi KOLF pan-genome e i due Orion.
Scrive `progress.json` dopo ogni parte, ma non stampa messaggi di avanzamento
e non ha un heartbeat applicativo. Il watcher locale interroga lo stato Kaggle:
il suo RUNNING non misura consumo CPU o avanzamento del worker.

## Scenario temporale condizionato, non ETA del job

Le tre completion D4 conservate in `ntc_ready_manifest_r1.json` misurano
1.218,50, 1.541,88 e 1.368,98 secondi per parte, su CPU con quattro core.
Sono 20,3–25,7 minuti per parte; includono lettura/verifica fonti ed estrazione.

**Solo se** le nove parti CD4 df11 avessero lo stesso costo per parte di D4,
senza ritardo iniziale o rallentamenti, richiederebbero 183–231 minuti in totale.
Usando la prima osservazione RUNNING come riferimento di pianificazione, il
termine delle **sole nove parti CD4** cadrebbe circa fra le **19:53 e le 20:42**.
È un confronto con un altro run, non una misura delle parti df11 già completate.
Differenze di dimensione, I/O, memoria e campioni possono invalidarlo.

Resterebbero KOLF pan-genome, Orion HCT116/HEK293 e l'esportazione Kaggle: tempi
non misurati per questo run. **Non è disponibile un'ETA difendibile dell'intero
job.** Le circa 2 ore e 33 minuti trascorse alle 19:23 sono compatibili con il
costo delle sole nove parti CD4 nello scenario sopra; non provano uno stallo,
ma non consentono neppure di escluderlo.

Nessun job lanciato, interrotto o duplicato; nessuna matrice RNA scaricata.
Il watcher esistente continua. Le 12 parti rimangono escluse dai locator fino
alla verifica delle ricevute e dei pin; restano validi gli accessi già preparati
in [STATO_r15.md](STATO_r15.md).
