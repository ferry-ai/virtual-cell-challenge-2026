# Retry del mix dopo errore di avvio — 5 ottobre 19:20 UTC circa

Misurato: il primo mix provider ERROR senza runtime_resources, senza status
scientifico e con log salvato/live entrambi []. [Diagnosi](mix_failure_r1/diagnosis.json).
Non c'è prova di errore della formula, RAM o dati: causa provider non esposta.

Un SOLO SAMECODE retry accettato/RUNNING, con codice e parametri byte-identici:
**davideferrante11/vcc-effects-mix-t25-bank-r1-retry1**,
[ricevuta](extended_mix_launch_r2/vcc-effects-mix-t25-bank-r1-retry1.json).
Originale conservato, supersedes_failed esplicito; non montarlo nei consumatori.
Nessuna statistica riuscita ricalcolata. Nessun secondo retry senza diagnosi nuova.
[Preflight](preflight_mix_retry_r1.json) verifica i tre account prima del retry.

HEK J:A549:f4 riparato/derived, [status](hek_repair_completion_r1/status.json).
H1 e gli altri frammenti verificati invariati. GWPS ancora RUNNING.
Il retry conserva il mix di produzione già preparato, senza attendere il banco.

Grok r8 PID20016 continua la generazione .vcc, con compattazione della stessa
sessione osservata; nota PARENT_MIX_STARTUP_r1 informa l'alias. Nessun pacchetto
di generazione consegnato al controllo. [Invio diretto](INVIO_DIRETTO_r1.md)
autorizzato resta prioritario appena mix ed export reali pronti.
