# Rifit parziale concluso; generazione preparata

Misurato il 5 ottobre, circa 19:35 UTC. Il retry
`davideferrante11/vcc-effects-mix-t25-bank-r1-retry1` è COMPLETE.
[Codice e versione 1 verificati](extended_mix_completion_r1/verification.json);
[stato scientifico](extended_mix_completion_r1/model/status.json):
`mixed_accepted_gate`, `usable_export=true`, 300 target, 12 fonti registrate.
Non è la copertura completa D-053. Hash delle matrici da verificare nel consumer.

[Inventario del pannello](extended_mix_completion_r1/model/panel_inventory.json):
8 delle 12 fonti hanno almeno un target sul pannello. HepG2, Jurkat, RPE1 e
K562 essential hanno zero target sul pannello e non vanno contate come
contributi effettivi alle predizioni. CD4 mix ha 293 target, HCT116 293,
HEK293T 299, H1 17; KOLF chromatin/metabolic/pan/strong 8/4/282/55.
Questi sono conteggi di disponibilità, non prove di miglioramento o peso non nullo.
Restano le lacune esplicite del manifest; i 395,75 GB archiviati non sono tutti usati.

Grok r8 è terminato, consegna intera in
[result.md](agenti/grok_transfer_esteso_r8/result.md). Nessun nuovo worker avviato.
Pacchetto stage100 → 45 → 48 preparato, ancora non lanciato: manca il mount dei
controlli ufficiali. Il dataset storico del terzo account restituisce 403 sul
consumer df11. [Input privato pronto localmente](generation_controls_r1/launch.json):
tre file originali byte-identici, 661.996.118 byte, destinazione proposta
`davideferrante11/vcc-official-controls-r1`. Nessun upload eseguito.

La revisione automatica ha rifiutato il caricamento perché considera non
specificamente autorizzati questi file e questa destinazione. Non aggirare il
blocco: ottenere l'autorizzazione umana specifica, poi creare una sola versione
privata, verificare READY/accesso, aggiornare il pacchetto parent e lanciarlo.
Prima del lancio correggere in una nuova copia parent `driver.py:208`: la lista
dei voti è ripetuta per A/B/C e provocherebbe un symlink già esistente; usare
l'insieme dei nomi, preservando gli stessi pesi, e aggiornare gli hash embedded.
Verificare nel consumer anche i file vincolati da `checkpoint.json`.
Non rilanciare il mix concluso. Invio VCC esplorativo già autorizzato dopo generazione.

[Percorso per il prossimo training](RIUSO_r1.md): versioni/hash, release nuova,
riuso delle banche compatibili e ricevute del consumo. README precedente conservato;
controllo strutturale documenti passato. Rimangono GWPS, adapter/QC e uso integrale.
