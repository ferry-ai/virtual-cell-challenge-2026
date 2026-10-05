# Aggiornamento operativo dei frammenti — 5 ottobre17:20UTC circa

Sette stime per fonte avviate, tutte con ricevuta di accettazione e stato
RUNNING dopo il push in `sourcefits_launch_r1/`: alle cinque iniziali si
aggiungono HepG2 e H1train. `preflight_sourcefits_r2.json` ha verificato
tre job attivi su df11 e nessuno sugli altri account prima dei due nuovi push.
Dispatcher `dispatch_sourcefits_v2.py`: riusa ledger, salta ogni lancio già
registrato, cap5sessioni/account, input/hash e guardia runtime invariati.
Non seleziona CD4 separato per donatore. Pacchetti r4 immutabili.

Jurkat, RPE1 e K562essential sono già `derived` verificati in
`sourcefits_status_r1/verification.json`; non recuperare nuovamente quei
piccoli status. HCT116/HEK293T e GWPS ancora RUNNING nel nuovo preflight.
Sette frammenti non certificano un fit completo o tutta la coperturaD053.

Grok PID9888 stessa sessione r5 è attivo e prepara CD4 congiunto e cloudmix;
nessun `ready_dispatch.json` r5 al controllo. Le righe target non risolte
restano un obbligo adapter aperto, non esclusioni definitive per overlap.
Il contratto completo `training_coverage_r1/expected.json` resta congelato:
non modificarne gli hash perché arrivano nuovi lanci; congelare una nuova
release/ledger snapshot al momento del mix.
