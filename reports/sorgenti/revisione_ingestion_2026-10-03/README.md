# Revisione della consegna ingestion e passaggio a Claude1

**Perimetro:** consegna Claude2 del 3 ottobre, aggiornamento del mandato CD4 e regia affidata a Claude1. Codex, sessione `01a10114-058a-7342-9f0e-7942cc43ad6c`. Questa cartella conserva una revisione locale: non certifica acquisizioni o esecuzioni cloud.

## Mandato aggiornato dal proprietario

Il proprietario dichiara **5 TB di capacità su Drive** e chiede di non impoverire CD4 per risparmiare spazio. L'obiettivo è acquisire tutte le cellule idonee dei quattro donatori e delle tre condizioni, con tutti i controlli idonei, le guide, i metadati e l'asse misurato completo. La capacità dichiarata non è una misura dello spazio libero: prima del trasferimento completo verificare occupazione, copie esistenti e dimensione attesa degli output. I 12 file grezzi sono censiti nel piano precedente per circa 1.736 TB decimali.

Distinguere tre livelli: archivio originale, corpus idoneo dopo filtri espliciti, campione del training. `k=10` per guida è soltanto una proposta di tranche iniziale, non un criterio scientificamente convalidato per escludere definitivamente le altre cellule. Conservare conteggi e motivi delle esclusioni; non equiparare cellule senza guida assegnata o multiguida a esempi supervisionati a bersaglio singolo. Campionamento e pesi del training restano una scelta successiva, con split congelati e H1 test chiuso.

L'incarico resta cloud: Colab CPU per ingestion, Kaggle GPU per training, portatile per codice e fixture. Più Colab richiedono partizioni disgiunte e misure di banda/memoria; non garantiscono un'accelerazione proporzionale. Le 617.524 cellule della terza ondata scPerturb già acquisite non vanno riscaricate; il loro uso dipende da modalità, QC, bersagli e ruoli, non dalla sola numerosità.

## Stato della consegna

- **Misurato:** run hub `20261003-141124-vcc-ingestion-resume` conclusa alle 14:20:36 CEST, dopo 545,9 secondi; stesso worktree del run `20261003-115840-vcc-ingestion-expanded`, base `05504a17be7cc59b8e00bf395d605710a847bb0f`.
- **Dichiarato dal worker:** codice scritto ma nessun test o job remoto eseguito. Mancano launcher/preflight completo, adapter CD4, Mixscale e altre sorgenti. Il [rapporto integrale](agenti/claude2_consegna.md) separa queste lacune.
- **Conservato:** [diff originale](agenti/claude2_consegna_originale.patch) e [manifest con hash](consegna_originale_manifest.json). La consegna originale non è stata applicata alla pipeline né al training.
- **Coordinamento:** un nuovo brief per acquisizione completa CD4 è stato preparato in `C:/Users/ferra/agent-hub/control/briefs/vcc-ingestion-complete-cd4-20261003.md`, ma **non inviato**. Il proprietario ha chiesto di lasciare a Claude1 la prosecuzione. Il monitor `segui-claude2-e-verifiche-archivio-vcc` è **PAUSED**; Codex non rilancia il worker.

## Archivio e spazio

La [pulizia precedente](../libera_spazio_2026-10-03/README.md), commit `2c4d242`, ha rimosso 14,517 GiB di copie locali obsolete dopo verifica indipendente Kaggle e ricalcolo SHA256 locale. Il 3 ottobre alle 14:39 CEST sono stati misurati circa 24,29 GiB liberi su C:; il valore cambia con gli altri processi.

La [fotografia dei job](archivio_stato_r1.json) conserva heartbeat, marker, preflight e presenza degli output di 130/131. Un heartbeat prova che il dispatcher li considera attivi, non che i file siano verificati. Senza ricevute remote valide non autorizza ulteriori rimozioni. Il log del singolo job può essere sincronizzato solo alla fine: non dedurre un blocco dal suo silenzio.

## Revisione e correzioni locali

La copia in [corretto/](corretto/) corregge quattro difetti circoscritti: le fasi Orion rifiutano metadati falliti o ricevute incompatibili; la riconciliazione dei bersagli precede l'assegnazione dei fold e rifiuta identità conflittuali; il riuso degli shard è vincolato anche ad asse, specifica e codice; le ricevute persistono attraverso più riprese. Sono modifiche della copia di revisione, non del worktree Claude2 né della pipeline attiva.

**Misurato:** [25 test locali superati](test_corretto_r3.txt), inclusa scrittura/rilettura di un H5AD con il vero writer e due riprese consecutive. Non è una prova di trasferimento cloud né della gestione di milioni di cellule. La [revisione dettagliata](AUDIT.md) distingue difetti corretti e lacune ancora aperte; include i limiti di memoria e i test di rete mancanti. Il controllo dello schema delle ricevute non ha riprodotto un errore: `sum_before` e `sum_after` sono effettivamente forniti dal writer.

Comando delle fixture, dalla radice della repository:

```powershell
.\scripts\py.cmd -m unittest discover -s reports/sorgenti/revisione_ingestion_2026-10-03/corretto -p "test_*.py" -v
```

I percorsi di import della copia sono adattati alla sottocartella `corretto/`: prima di ricollocarla nell'adapter originale, riallineare i percorsi e ripetere i test. La specifica Orion originale resta proposta di campionamento, non attua il nuovo mandato di acquisizione completa. Non lanciare questa copia come se fosse già un job completo.

## Passaggio di consegne

Claude1 diventa l'unica regia. Leggere prima questa revisione e il rapporto del worker; riprendere lo stesso worktree solo dopo controllo delle corse attive e dell'account richiesto dall'utente. Non applicare alla cieca il diff originale. La correzione locale e i test della revisione sono documentati accanto al codice; le verifiche remote rimangono distinte.

Il [prompt completo](PASSAGGIO_CLAUDE1.md) raccoglie mandato, percorsi, stato e prossimi passi.
Le [verifiche finali](VERIFICHE.md) registrano anche la suite generale: tre test dello scorer
passano nella replica nativa; resta la registrazione incompleta della cartella di modelli
di una sessione concorrente, estranea a questa consegna.

Per dichiarare l'ingestion completa servono conteggi di conservazione, identità univoche, provenienza e hash degli input, ricevute per ogni shard, riuso compatibile con asse/configurazione/codice, verifica indipendente delle copie e manifest adottato senza cambiare split. Solo allora il corpus diventa un input di training; solo un confronto preregistrato può dimostrare un miglioramento del modello.
