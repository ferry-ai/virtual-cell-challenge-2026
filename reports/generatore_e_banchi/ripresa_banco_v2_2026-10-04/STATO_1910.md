# Stato della ripresa al 4 ottobre 2026, 19:10 CEST

**Misurato:** i cinque banchi CPU sono avviati; H1, HepG2, RPE1 e Jurkat r1 e
K562 r2 risultano RUNNING nella [lettura remota](stato_1902_r1.json).
K562 r2 è ancora RUNNING nella [lettura successiva](stato_1907_r1.json).
Nessun nuovo risultato scientifico è stato letto. RUNNING non dimostra che lo scoring
sia già iniziato o che il preflight sia passato: le ricevute si recuperano a fine kernel.

**Riparazione tecnica:** K562 r1 ha superato il preflight remoto completo, poi si è
fermato nell'esportazione prima dello scoring. Un controllo aggiunto dal launcher
rifiutava i bersagli privi di supporto nella baseline di produzione, che invece sono
legittimi e devono emettere cellule di baseline in entrambi i bracci. La
[correzione preregistrata](EMENDAMENTO_K562.md), congelata nel commit `9cad688`, mantiene
tutti i bersagli, maschere, effetti e regole. Rilancio r2 accettato alle 18:57 CEST,
registrato in [lanci_banco_r1.jsonl](lanci_banco_r1.jsonl). Il tentativo r1 resta conservato;
incidente [E-20261004-003](../../analisi/lead_scientist_2026-09-29/learning/incidents/E-20261004-003.r001.json).
Sei test piccoli di preparazione/riparazione passati. Gli altri controlli della sessione
sono descritti nello [stato precedente](STATO_1847.md), che resta una fotografia storica.

**CD4:** [riconciliazione delle ricevute](copertura_cd4_r1.json): 10 unità su 12 verificate,
con conteggi confrontati alla specifica e SHA delle ricevute. D3_Stim48hr e D4_Stim48hr
hanno tutte le verifiche indipendenti positive, inclusa la rilettura degli SHA degli shard.
D4_Stim8hr: verifica avviata alle 19:00, osservata RUNNING.
D4_Rest: entrambe le parti COMPLETE; verifica indipendente avviata dopo tale riscontro,
con ricevuta in [lanci_verifiche_r1.jsonl](lanci_verifiche_r1.jsonl).
La chiusura di tutte le parti non basta per dichiarare le ultime due unità verificate.

**Risorse:** tutti questi job sono CPU. Nessuna GPU usata e quote invariate.
Non servono ulteriori sessioni Colab per i job già avviati; i vecchi heartbeat Drive
non permettono di affermare che Colab sia attivo. La prossima fase del corpus ampliato
richiederà una nuova misura di risorse e accessi. Il banco usa il pilot a otto gruppi:
non è una prova di copertura D-053 o di uso del corpus ampliato nel training.

**Ripresa operativa:** rileggere gli stati remoti; a fine job scaricare ricevute,
preflight, risorse, manifest degli effetti e risultati dei banchi. Verificare uscita e
integrità prima di applicare il protocollo congelato `55ae28b`, senza selezionare
automaticamente un fold da esportare. Recuperare `source_complete.json` delle ultime
due verifiche CD4 e rieseguire `reconcile_cd4.py --out <nuovo-file>` per il bilancio
a 12 unità. Restano da preparare i gemelli compatti e gli accessi fra account per il
prepasso ampliato; l'ingestione non dimostra uso effettivo nel training.
Nessun nuovo training, invio o push Git. Nessun monitor automatico è stato installato.
