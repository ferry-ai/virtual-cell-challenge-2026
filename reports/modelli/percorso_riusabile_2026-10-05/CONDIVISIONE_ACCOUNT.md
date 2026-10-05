# Condivisione degli input — 5 ottobre

Autorizzazione del proprietario in chat: condividere ora gli input fra i tre account;
anche pubblicamente se necessario. Preferenza operativa: condivisione privata.
Il browser integrato è autenticato come davidmaisterx. Chrome, autenticato dal
proprietario come davideferrante11, non è disponibile al controllo di questa chat.
Nessuna modifica dei permessi ancora eseguita.

`shared_samples_plan_r1/required_access.json` elenca i 17 notebook necessari:
tre banche e quattordici parti grezze. Condividere con davidmaisterx e davideferante
in lettura dal proprietario davideferrante11, tramite Share → Collaborators.
Non serve rifare login o ingestion sugli account consumatori.

`dispatch_shared_samples.py` prepara otto parti, quattro per account; codice
identico ai pacchetti già congelati. Con `--launch --out <nuova_cartella>` verifica
gli accessi a tutti gli input e gli slot prima dei push. Riconosce i tentativi già
registrati per identità banca/unità/parte anche fra account, nel registro comune
`other_sample_launches.jsonl`. Non usare più `launch_other_samples.py` dopo la
distribuzione: quel launcher storico distingue gli slug, non le identità fra account.

`other_sample_progress_r2.json`: i primi cinque job RUNNING con eventi reali di
materializzazione. Le otto parti aggiuntive sono preparate, non lanciate.
