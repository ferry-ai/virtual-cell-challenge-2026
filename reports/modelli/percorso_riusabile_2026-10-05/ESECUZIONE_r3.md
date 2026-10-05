# Stato operativo — 5 ottobre17:30UTC circa

Nove stime per fonte avviate, deduplicate in `sourcefits_launch_r1/`:
alle sette si aggiungono H1val e KOLFchromatin, accettate/RUNNING.
Preflight dei tre account `preflight_sourcefits_r3.json`:3attivi df11 prima
dei2push; mx/terzo liberi, ma gli input di questa coda sono sul proprietario df11.
La nuova preparazione CD4joint del worker deve risolvere accesso fra account.

Cinque fonti `derived` con codice salvato identico al pacchetto e versione1:
H1train, HepG2, Jurkat, RPE1, K562essential. Prova incrementale
`sourcefits_status_r2/verification.json`; status precedenti riusati.
Nessuno split bloccato per budget. H1train non ha token bloccati;
HepG2/Jurkat/RPE1 ne hanno217, K562203: identità target da risolvere prima
di ammettere tutti i dati, senza esclusione per overlap con asse di espressione.
Le matrici di effetti NON sono state riscaricate o certificate qui:
il consumatore deve verificarne gli hash. ProviderCOMPLETE non prova il modello.

`source_fit_state_v1.py --preflight <nuovo.json> --out <nuovo_dir> --previous sourcefits_status_r2/verification.json`
verifica soltanto chiusure nuove e riusa ricevute con prova del codice.
`dispatch_sourcefits_v2.py <nuovo_preflight.json>` riempie slot con non-CD4
ancora pronti (KOLFmetabolic/strong/pan-genome), dopo preflight fresco tutti3.
Mai passare tutte le righe JSON del ledger come job: alcuni sono snapshot.

Grok PID9888/r5 ancora attivo, ha scritto joint e mixer e sta correggendo
il carico CD4 affinché non tenga quattro matrici compact contemporaneamente
in RAM. Nessun ready_dispatch r5 al controllo. NON interrompere/duplicare.
R4 è congelato; i suoi CD4 separati e mixer tables[0] NON adottati.

Obiettivo invariato: esattamente transfer t28, sola banca variabile, tutte
le fonti/BIO scientificamente ammissibili e nuova release congelata prima mix.
Archivio r10/43unità/395,75GB non certifica consumo o copertura completaD053.
Contratto `training_coverage_r1/expected.json` immutato; nuovi ledger vanno
congelati in una nuova release. Nessun fit esteso completo/confronto ancora.
