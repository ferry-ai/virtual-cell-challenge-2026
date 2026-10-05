# Resume dello stesso worker: pacchetti eseguibili prima, parent esegue i push

L'utente chiede accelerazione concreta: i 15 slot NON sono occupati. Il worker
r2 PID12704 non esiste più, nessun launches.jsonl, nessun result finale. Esiste
un altro Grok PID5060 estraneo: non toccarlo. Riprendi questa stessa sessione
613a1b58-0807-4abe-8dff-be9b67204552, nessun nuovo subagente. R1/r2 restano
immutabili. Nuovi file solo agenti/grok_transfer_esteso_r3 nel report.
Leggi CLAUDE.md e guide pertinenti. Il parent ha rieseguito i 13 test r2: PASS.
Sono fixture, non prova che i job runtime siano pronti. Non replicare audit/letture
generali. Copia solo i moduli necessari r2 nella nuova cartella e completa il percorso.

Indice CORRENTE cloud_catalog_r10/manifest.json, SHA
7134c13c741e04b1bb90b15f42afd2a50e653454aca17e49005edcad6f2e7fdf.
R8 è superato per nuovi lanci: aggiornare pin/manifest/ammissione con provenance,
non mescolare silenziosamente r8 e r10. Leggi SUPERVISOR_r2/r3 nella cartella r2.
HIPSCI genome-wide e mirato19 chiusi; Norman mountable dataset v1 PUBLIC,
iPSC input v3 PUBLIC. K562 GWPS unico job parent ancora aperto: non duplicarlo.
R10 indice storage, non manifest di fit. Tutto catalogo e aggiunte, oltre 100 r4,
rimane obbligo; classificare ogni lacuna con prove concrete, non solo open generico.

PRIMA consegna urgente: ready_dispatch.json + pacchetti per derivazioni CPU
indipendenti su banche chiuse, con input/versioni/hash/fold/asse completi, comando
esatto e memory/output guard. Parent esegue push da qui: TU NON effettuare push
per evitare collisioni e blocchi di permission auto classifier. Aggiorna status.json
quando pacchetti pronti: parent può lanciare mentre tu prosegui le altre fonti.
Preflight nuovo prima dei push, cap per account, nessun duplicato. Owner accessibile
come origine prima; terzo account solo se accesso input verificato. Le sessioni
separate non sommano RAM. Non abbassare guardie/escludere dimensioni.

Difetti del primo lanciatore da RISOLVERE prima di ready:
- jobs_from_observation non passa held_groups/hidden_targets: per ogni split C/J
  applicare esclusioni globali e componenti prima di statistiche, pooling/shrinkage;
  non produrre unico pack globale poi tagliare dopo. Una sola montatura per source
  può elaborare più fold con input riusato e statistiche separate. Non inventare split.
- cloud_job usa genes=['0','1',...] senza legame ai simboli: congelare/bindare asse
  e hash, coerenti con axis_sha256/official_index conservati, prima del calcolo/fit.
- component_policy assume ogni token senza separatori sia gene singolo: servono
  mapping/evidenze della sorgente; token opachi/UNASSIGNED non diventano geni.
- runtime deve verificare asse/mask/codice/versioni/hash, pseudobulk count_sum per
  BIO/donatore e controlli corretti; file salvati con identità/fold e ricevute effettive.
- completo corpus ammesso prima del fit esteso: derivazioni parziali NON dichiarate
  fit completo. Fonte/condizione/donatore gerarchia senza duplicare voti.

Poi completa le fonti indipendenti ammesse, auxiliary roles e adattatori mancanti,
runtime consumer + trainer reale + freeze release + confronto t25 originale vs
nuova banca a emissione t28 identica 400cellule*5semi appaiati C/J. Nessun beneficio
dalla loss, preregistrazione valida, nessun fallback pilot. I18pilot precedenti
non sono training esteso. Non aspettare K562 per preparare gli altri pacchetti.
Nessun invio VCC, pubblicazione modelli, cancellazione, commit/push Git, altro
worker o Runpod. Pubblicazione necessaria pipeline autorizzata ma parent la gestisce.
Salva relazione completa e status con UTC misurata, comandi/prove e blocker esatti.
Evita ore di pianificazione: prima pacchetti eseguibili e prove piccole indipendenti,
poi estendi. Se compute non lanciabile, fornisci il singolo prerequisito tecnico
da risolvere con percorso/file e azione concreta, non un elenco indistinto.
