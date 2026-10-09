# AMMI: passaggi effettivi prima di un eventuale invio

9 ottobre 2026. Stato successivo a `STATO_CHIUSURA_r2.md`; nessun fit AMMI
biologico ancora avviato. Questa nota non autorizza un invio VCC.

## Stato osservato e limiti dell'ETA

Il watcher DATI riporta RUNNING alle 17:23:39 UTC (19:23:39 italiane).
La verifica DATI `df11_progress_snapshot_r2.json`, nella cartella
`reports/modelli/dati_transfer_2026-10-08_01a11c34/`, registra il produttore
ancora attivo, nessun output intermedio esposto e nessun progresso leggibile
dal log live. La cronologia di lancio parte dal primo RUNNING delle 14:50:22
UTC; l'ora effettiva di avvio del container non è esposta. Non si può ricavare
un numero di parti finite né un'ETA dell'intero produttore da questo stato.
Non si interpreta l'assenza di output pubblicati come assenza di lavoro.

Restano da completare e verificare le 12 parti df11. Le 18 parti MX sono già
verificate; i locator dei 105 input derivati sono pronti e hanno superato il
controllo HTTP. I corpi dei file verranno verificati per byte e SHA nel runtime.
Non parte un training con parti mancanti. Nessun nuovo produttore o watcher.

## Preparazione completata mentre gli input sono in corso

`ammi_code_package_r6/manifest.json` congela il codice con misure di durata.
Il pacchetto precedente r5 è conservato. Modello, dati, split, iperparametri,
seme, numero di epoche e guardie sono invariati.

- Bootstrap: risoluzione, download necessari e hash, in
  `ammi_bootstrap_timing.json`. I chunk di risposte risolti successivamente
  sono misurati nella fase responses, non inclusi in questo tempo.
- Fasi anchors, controls, features, responses, inner_baseline, fit ed exports:
  `timing_<fase>.json`, durata monotona e timestamp UTC; eccezioni registrate
  solo per tipo. Le ricevute non contengono URL privati.
- Per ogni epoca: `optimization_seconds` e `epoch_seconds` nella ricevuta
  di training; quest'ultima include checkpoint e guardia. Nessuna estrapolazione
  dei tempi di fixture ai dati biologici.

`combined_tests_r15.txt`: 83 test PASS in 21,240 secondi. Il pacchetto r6
misura 52.033 byte, SHA256
`ae1e9d109bda661f43cfd8facfd2a8dd125ff9bd153b3573a073f391eac328ce`.

`prepare_ammi_readout_v1.py` prepara il banco originale immutato quando sono
disponibili le quattro ricevute. Nessun job di banco è ancora impacchettato
o lanciato. Tre test di preparazione PASS in `ammi_readout_tests_r1.txt`.
La preparazione non certifica accessi remoti né integrità dei payload binari.

## Lettura congelata prima dei risultati

I contesti primari corrispondono ai riferimenti del banco: K562 GWPS per
C-K562; KOLF pan-genome per C-iPSC. Gli altri contesti esportati restano
descrittivi, senza contare la stessa verità come repliche indipendenti.
Le copie di `logo_driver.py`, `bench_core.py` e `metrics.py` restano identiche
al banco VALIDAZIONE. Il supporto del banco originale resta congelato.

Distinzione necessaria: l'ancora AMMI di query esclude sia il lignaggio esterno
sia quello interno; la T0 originale del banco esclude soltanto l'esterno.
Il readout chiama l'ancora annidata **A0**, senza rinominarla T0 originale.
Riporta cells–A0 e cells–none, oltre a cells–swapped e al controllo shuffle.
Mostra separatamente cells–T0 originale e A0–T0 originale. Cells e none devono
avere la stessa ancora per hash. Nessuna ampiezza o soglia adattata ai risultati.
Un solo seme non dimostra stabilità del training; questi confronti restano
sviluppo, non punteggi ufficiali VCC o promozione automatica.

## Stato di produzione e submission

1. **Input e quattro fit:** completare le 12 parti, includerle nei locator dopo
   verifica, costruire i quattro runtime con `build_ammi_runtime_v4.py`,
   impacchettarli, rifare preflight accessi/quote e lanciare nei posti realmente
   disponibili. Verificare CUDA e consumo effettivo prima di dichiarare training.
2. **Confronto:** recuperare ricevute, verificare codice remoto e hash degli
   export, preparare il banco, risolverne gli accessi privati e leggere entrambi
   i fold. Il builder del banco è eseguibile ma il pacchetto finale attende gli
   export. I mount di training non sono automaticamente accessi al banco.
3. **Produzione:** il builder e il ramo runtime esistono e sono testati; le
   ancore di produzione e le NTC ufficiali hanno ricevute DATI. Il runtime
   finale è ancora da costruire: richiede gli NTC di training completi e una
   decisione documentata dopo i confronti di entrambi i fold. I trasferimenti
   autorizzati ai quattro pilot non si estendono implicitamente agli input di
   produzione. Va scelto un runtime con accessi ammessi.
4. **Inferenza e pacchetto:** dopo il fit distinto, ottenere checkpoint e
   predizioni native A/B/C, verificarne ricaricamento, assi, maschere, scala e
   guardie. L'export stage100 è implementato. L'innesto nella ricetta del
   generatore, la generazione delle cellule e il pacchetto di submission non
   sono ancora eseguiti; appartengono al percorso principale DATI/VALIDAZIONE.
5. **Invio:** nessun invio nuovo è stato preparato o autorizzato da questa nota.
   La decisione dipende dai confronti e dai controlli richiesti. ESM2, già
   concluso senza beneficio dimostrato, non viene promosso per accelerare l'invio.

Il tempo residuo dipende da input, training, valutazione e produzione ancora
non misurati. Il watcher DATI raccoglie metadata: non lancia fit e non risveglia
questa chat. Non è stato creato un lanciatore automatico implicito.
