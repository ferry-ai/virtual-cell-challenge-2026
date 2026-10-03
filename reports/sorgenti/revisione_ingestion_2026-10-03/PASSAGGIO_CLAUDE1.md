# Prompt di passaggio a Claude1

Prendi tu la regia unica dell'ingestion e dell'archivio. Codex ha sospeso la propria automazione `segui-claude2-e-verifiche-archivio-vcc` e non ha rilanciato Claude2 dopo la consegna del 3 ottobre alle 14:20 CEST. Non duplicare worker, dispatcher o job già attivi.

Leggi `CLAUDE.md`, poi `reports/sorgenti/revisione_ingestion_2026-10-03/README.md` e le evidenze della revisione. La cartella conserva il rapporto integrale e il diff originale di Claude2, hash dei file, correzioni locali e fotografia dei job archivio. Distingui codice scritto, test locali, job avviati, dati acquisiti e copie indipendentemente verificate.

## Indicazioni del proprietario

- Drive ha **5 TB di capacità dichiarata**: non fissare un tetto definitivo di 10 cellule per guida per risparmiare spazio. L'obiettivo CD4 è acquisire tutte le cellule idonee dei quattro donatori e delle tre condizioni, con controlli, guide e metadati. Campione iniziale e bilanciamento del training sono scelte separate. Prima del trasferimento completo misura spazio libero e copie già presenti; non assumere 5 TB liberi. Mantieni provenienza e inventario delle esclusioni, senza assimilare cellule multiguida/non assegnate a supervisione singola.
- Colab CPU per ingestion; Kaggle GPU per training; portatile solo sviluppo e fixture. Usa blocchi riprendibili e output distinti. Valuta più Colab su partizioni indipendenti dopo aver misurato banda, RAM e tempi di lettura/conversione/scrittura/verifica. Nessun dato pesante sul portatile.
- Riusa la terza ondata scPerturb già acquisita (617.524 cellule); separa KO/CRISPRi/CRISPRa e conta i gruppi che insegnano ogni bersaglio **dopo** QC e split. Più cellule della stessa linea non equivalgono a più linee indipendenti. Jiang e Mixscale sono la stessa sorgente.
- Prosegui autonomamente nell'incarico già autorizzato, controlla e risolvi le discrepanze anche coordinando gli agenti. Le correzioni utili alle sessioni future vanno in codice con test, report e sedi canoniche. Mantieni gli split congelati e H1 test chiuso; non promuovere dati o modelli da un semplice rapporto del worker.

## Claude2: dove riprendere

Run concluso: `20261003-141124-vcc-ingestion-resume`, seguito di `20261003-115840-vcc-ingestion-expanded`. Worktree:

`C:/Users/ferra/agent-hub/runs/20261003-115840-vcc-ingestion-expanded/claude2/wt`

Il codice originale è in `reports/sorgenti/ingestione_espansione_2026-10-03/` dentro quel worktree. Il rapporto indica che shell/rete erano negate dal confine headless: il worker non ha eseguito test o ingestion. Non aggirare i permessi; esegui tu le verifiche autorizzate.

Il brief aggiornato è già scritto ma **non inviato**:

`C:/Users/ferra/agent-hub/control/briefs/vcc-ingestion-complete-cd4-20261003.md`

Integra nel prossimo messaggio a Claude2 gli esiti della revisione Codex, evitando di fargli rifare correzioni già pronte. Controlla prima con `hub.py status` che nessun altro seguito sia partito, e con `doctor` l'account richiesto dal proprietario nella chat. Il registro hub ha una vecchia identità attesa: non confondere il suo avviso `wrong-account` con l'identità effettiva e non modificare login o configurazioni globali.

Mancano ancora una pipeline completa con launcher/preflight, acquisizione CD4 completa, conversione Mixscale e verifica remota. Non mettere in coda la consegna Orion originale senza correzioni e test. La copia corretta è materiale di revisione da integrare deliberatamente; non è già attiva nella pipeline.

## Archivio e pulizia

Codex ha liberato **14,517 GiB** di vecchie matrici r1/r2, con hash locali confrontati con prova Kaggle indipendente; commit `2c4d242`, evidenze in `reports/sorgenti/libera_spazio_2026-10-03/`. Nessun'altra cancellazione è stata fatta in questa revisione.

I job Colab `130_archivio_verify_b_r1.sh` e `131_archivio_verify_a_r1.sh` sono partiti alle 14:00 CEST e hanno preflight PASS. Alla fotografia delle 14:40 CEST l'ultimo heartbeat era delle 14:30:55 CEST con entrambi in esecuzione; nessun `.done`, output `out_a_r1` e `out_b_r1` esistenti ma ancora senza ricevute visibili. Rileggi lo stato attuale, non trattare questa fotografia come un monitor dal vivo.

Percorsi Drive: `G:/Il mio Drive/vcc2026/runs/jobs/dispatcher.log`, `runs/queue/`, `runs/archivio_verify_2026-10-02_r1/`. Una volta ottenute ricevute indipendenti valide, prosegui la pulizia già autorizzata soltanto sulle copie senza dipendenze attive, con verifica locale e ricevuta della rimozione. Non interrompere o duplicare i job sulla sola base del log individuale non sincronizzato.

Chiudi il passaggio confermando lo stato dei worker e dei job, le correzioni integrate e il prossimo blocco concreto. Mantieni tu il monitoraggio periodico richiesto dal proprietario.

Leggi anche `VERIFICHE.md`: 25 fixture ingestion e 11 controlli strutturali passati; i tre errori di visibilità dello scorer nel sandbox passano nella replica nativa. La suite generale segnala ancora i file della cartella concorrente `reports/modelli/rete_ancorata_2026-10-03/` non registrati: completa indice e registro alla consegna di quel lavoro e ripeti il controllo documentale. Codex ha lasciato intatti quei file.

Nota Git: il commit concorrente `54405b2`, pur avendo titolo sul pilot lane B, ha incluso anche i 23 file ingestion preparati da Codex nell'indice condiviso. Il codice è già conservato lì; non riapplicare tutto il diff né attribuirlo a una validazione del pilot. La cronologia è stata preservata. Usa preparazione isolata e commit con percorsi espliciti per evitare nuovi incroci.
