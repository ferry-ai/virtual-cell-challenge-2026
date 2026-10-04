# Stato osservato al 4 ottobre 2026, 18:47 CEST

**Misurato, esecuzione:** cinque banchi CPU accettati alle 18:42–18:43 e riletti tutti
`RUNNING` ([ricevuta](stato_banchi_r1.json), [lanci](lanci_banco_r1.jsonl)). H1, HepG2 e RPE1
su `davideferrante11`; Jurkat e K562 su `davidmaisterx`. Nessun risultato scientifico ancora letto.
Protocollo congelato prima dei lanci nel commit `55ae28b`; ogni job monta gli stessi input
del confronto precedente e verifica tutte le dimensioni e gli SHA prima del calcolo.
I manifest e i preflight locali sono nella radice dati, cartella
`processed/ripresa_banco_v2_2026-10-04/dry_<linea>_r2/`; gli snapshot realmente inviati sono
identificati dagli SHA nel registro dei lanci. `dry` è il nome della preparazione, non lo stato del job.

**Dati:** nella [lettura delle 18:41](stato_remoto_r3.json), entrambe le parti `D4_Stim48hr`
e p0 di `D4_Stim8hr` sono COMPLETE. Ancora RUNNING: D3_Stim48hr p0/p1,
D4_Stim8hr p1, D4_Rest p0/p1. `D4_Stim48hr` non è ancora verificata per unità.
Il launcher della sua verifica è pronto nella radice dati, cartella
`processed/ripresa_banco_v2_2026-10-04/verify_d4_stim48hr_r1/`; attende uno slot su `davidmaisterx`.
Le altre verifiche richiedono prima entrambe le parti COMPLETE. Nessun rilancio dei job vivi.

**Incidente ereditato:** registrato [E-20261004-002](../../analisi/lead_scientist_2026-09-29/learning/incidents/E-20261004-002.r001.json).
Il log prova una lettura HTTP incompleta di D3_Rest p1 r1; la causa del trasporto resta ignota.
La verifica indipendente delle 17:07 prova il recupero con p1 r2, non una riparazione generale della rete.

**Risorse e parallelismo:** quote GPU invariate (nessuna GPU accesa); RAM e disco effettivi saranno
nella ricevuta di ciascun kernel, che si arresta sotto 8 GiB disponibili. Non si sommano fra sessioni.
Il terzo account configurato è accessibile ma non monta gli output privati dei due account usati.
Gli input dei cinque banchi sono già disponibili sugli account assegnati. Colab: heartbeat `queue`
fermo al 3/10 19:57 UTC e `queue2` al 3/10 22:11 UTC, quindi nessun runtime attivo verificato;
non è una diagnosi della causa né una richiesta di spostare calcolo sul portatile.

**Controlli:** quattro test originali del banco e quattro nuovi test di maschere, target nascosti e hash passati.
Controllo documentale passato. Suite completa: 290 test, 289 passati e un controllo dell'indice
ha incrociato la nuova cartella ancora non tracciata all'avvio della suite; rieseguiti dopo il commit
tutti gli 11 test dell'albero, passati. Il primo tentativo nel sandbox aveva anche tre errori di accesso
allo scorer; il secondo, nel venv con accesso completo, non ne ha.

**Prossimo passo:** rileggere stati remoti; recuperare preflight, risorse, manifest degli effetti e
`paired.json` dei cinque banchi soltanto a fine job; verificare `kernel_done.json` e applicare la regola
senza modificarla. Avviare le verifiche CD4 quando parti e slot lo consentono. La chiusura dei dati
non dimostra uso effettivo nel training e il pilot non soddisfa da solo D-053.
Push Git e invii restano non autorizzati. Nessun monitor automatico di lancio è stato installato.
