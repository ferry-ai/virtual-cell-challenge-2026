# I due NONE avviati; recupero tecnico prima dell'ottimizzazione

9 ottobre 2026. Aggiorna `PERCORSO_INVIO_E_TEMPI_r1.md`: l'attesa degli NTC
non si applica più ai due bracci none. I cells continuano a richiedere tutte
le parti verificate. Restano quattro fit scientifici, non una nuova griglia.

## Emendamento provato

`AMMI_NONE_SENZA_NTC_r1.md` dichiara la separazione fra identificativi di
contesto e matrici NTC. `none_equivalence_r1.json` confronta la revisione con
il codice originale della capsula r6: parametri, gradienti, loss, pesi,
mu_train, copertura e predizioni esatti; guardie reali su fixture e parità del
checkpoint superate. Il registro senza RNA non è utilizzabile da cells.

La prova è stata ripetuta dopo la correzione tecnica del caricatore:
`none_equivalence_r2.json`, PASS, scarti massimi zero. `combined_tests_r17.txt`:
87 test PASS in 22,563 secondi. Nessun beneficio biologico dedotto dai test.

## Lanci e correzioni conservati

I due tentativi di creazione K562 r4 con sorgente di 1,72 MB hanno restituito
HTTP400. Ogni controllo successivo ha trovato il job assente (404), prima
di un nuovo tentativo. La ricompressione senza perdita verifica tutti i
31 membri estratti e riduce i sorgenti a 674/837 KB: entrambe le creazioni
sono state accettate. Il provider non ha restituito un motivo testuale utile;
la dimensione è la spiegazione operativa sostenuta da questo confronto,
non un nuovo limite del servizio certificato da noi.

Le prime corse private r4 risultavano entrambe RUNNING su NvidiaTeslaT4,
versione1, con codice remoto identico (`ammi_c-*_none_status_r3.json`).
Il runtime K562 ha verificato CUDA12.8, Torch2.11.0+cu128, GPU TeslaT4,
15,5 GB GPU liberi, 32,0 GB RAM e 20,9 GB disco liberi. Le due corse sono
poi finite ERROR prima di qualsiasi aggiornamento dei pesi:
`'NoneType' object has no attribute 'loader'`.

Causa verificata: i moduli delle metriche sono impacchettati come asset con
nome SHA senza estensione. `spec_from_file_location` non selezionava un loader.
`ammi_inputs_v3.module` ora usa `SourceFileLoader` esplicito dopo il controllo
di byte e SHA. Il file delle metriche resta invariato. Il test
`test_ammi_hash_module_v1.py` riproduce il caso del nome hash e verifica il
caricamento dell'originale, con BOOT10000 e seme20261008.

Le ricevute remote precedenti sono conservate in
`ammi_c-k562_none_retrieval_r1.json` e `ammi_c-ipsc_none_retrieval_r1.json`;
non sono prove di fit completati. Nessuna guardia scientifica è stata tolta
o reinterpretata. È stata riparata l'importazione prima che la guardia fosse
eseguita. Nuove identità r5 conservano gli output falliti r4.

## Recuperi correnti

- `davidmaisterx/ammi-c-k562-none-17-01a11c35-r5`: accettato alle17:55:46UTC
  (19:55:46 italiane), inizialmente QUEUED.
- `davidmaisterx/ammi-c-ipsc-none-17-01a11c35-r5`: accettato alle17:57:03UTC
  (19:57:03 italiane), RUNNING.

Preparazione corrente: `ammi_c-*_none_prepared_r4.json`. I manifest runtime
stanno fuori Git, nelle cartelle `C-K562-none-r6` e `C-iPSC-none-r6` della
radice dati AMMI; i pacchetti privati compatti sono `C-k562-none-r7-package`
e `C-ipsc-none-r7-package`. Nessun locator privato è stato scritto in Git.
Capsula di codice aggiornata: `ammi_code_package_r8/manifest.json`.

Preflight r6: MX aveva 93.149,744 secondi GPU non prenotati, circa25,87ore,
zero job attivi e pay-to-scale disabilitato. Tutti i18mount non-NTC erano
ammissibili. Nessun acquisto. Le aspettative sul prossimo reset non sostituiscono
la quota misurata. T3/NTC restano su df11; nessun loro job viene interrotto.

## Tempi reali fin qui

Dalle corse r4, preparazione delle risposte: K562186,246s (3,1min),
iPSC472,406s (7,9min). Il bootstrap K562 richiede8,513s; caricamento ancore2,069s,
feature0,276s. Sono tempi di input, non di ottimizzazione né un'ETA del modello.
Per attestare il training servono la ricevuta delle epoche/checkpoint oppure
l'evento di fit completato; GPU configurata e RUNNING non sono sufficienti.

Restano da leggere gli esiti dei recuperi, eseguire cells dopo gli NTC,
confrontare i quattro fit e decidere produzione/integrazione. Nessun invio AMMI
preparato o eseguito; il transfer è seguito separatamente da DATI.
