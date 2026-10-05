# Progresso operativo — 5 ottobre18:05UTC circa

Misurato: [HCT116 è derived](sourcefits_status_r5/verification.json),72split,
6statistiche, nessun fold bloccato da budget. Otto sourcefit ora derived;
HEK293T resta partial_output_budget già segnalato, ricevuta riusata senza recuperi.
Token917HCT/HEK da riconciliare, hash matrici nel consumer ancora obbligatori.

Due nuovi fit autorizzati accettati/RUNNING, nel ledger sourcefits_launch_r1:
df11/vcc-effects-kolf-metabolic-r4 e mx/vcc-effects-kolf-pan-genome-r4.
Undici sourcefit complessivi più i tre joint CD4, tutti3 RUNNING nel
[preflight](preflight_joint_progress_r2.json). Nessuno è il mix finale.
Pan assegnato a mx libero: [accesso producer](kolf_cross_access_r1.json)
verificato sui due account alternativi. Codice/parametri originali r4 invariati,
solo proprietario metadata cambiato; wrapper risorse runtime conservato.
KOLFstrong resta pronto ma input derivato privato df11, inaccessibile agli altri
account al controllo; attendere slot o risolvere accesso senza reingestione.

Grok PID19956/r6 sta lavorando nella stessa sessione, non ancora ready_dispatch.
Parent gli ha comunicato nuove chiusure/lanci; nessun secondo worker.
source_fit_state_v2.py riusa anche ricevute parziali salvate/code-verified e
registra lanci successivi allo snapshot come non osservati. Tentativo r4 aborted
per snapshot precedente al lancio KOLF, NON errore dei job cloud. Prova valida r5.
Accessi pubblici, copertura e mandato restano [ESECUZIONE_r4](ESECUZIONE_r4.md).
Nessun training esteso finale o risultato di confronto ancora dimostrato.
