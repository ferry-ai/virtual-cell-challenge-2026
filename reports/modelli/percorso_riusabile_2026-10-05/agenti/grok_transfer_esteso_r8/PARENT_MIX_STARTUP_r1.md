# Mix errore prima del codice — parent segue un solo retry

Il producer df11/vcc-effects-mix-t25-bank-r1 è ERROR. Recupero output riuscito:
nessun runtime_resources.json, nessuno status scientifico, log salvato [] e
live []. Prove mix_failure_r1. Nessuna prova di errore nella formula o OOM.
Parent prepara un solo SAMECODE retry su nuovo slug con dedup/preflight,
conservando codice/params identici; non lanciarne un altro.
Il nuovo riferimento previsto è df11/vcc-effects-mix-t25-bank-r1-retry1;
leggi extended_mix_launch_r2 ricevuta prima di congelare generazione/mount.
Non montare mai producer ERROR originale, nemmeno se API-recuperabile.
Continua generazione/export: prepara codice senza attendere calcolo, parentpush.
HEK J repair ora provider COMPLETE, scientificreceipt ancora da verificare;
non blocca generazione di produzione. GWPS ancoraRUNNING.
