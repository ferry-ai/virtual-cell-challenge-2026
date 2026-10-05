# Identità della banca e protezione dagli input storici

Mandato del proprietario, 5 ottobre: conservare questa ingestione e impedire
che vecchi dataset Kaggle siano scambiati per la banca attuale.

`release_cd4_r1.json` congela i riferimenti delle dodici unità ingerite:
ricevute e SHA256 dei grezzi, sorgenti cloud, identità della trasformazione,
versioni private e hash dei manifest di banca/campioni già verificati.
I derivati ancora in corso restano esplicitamente incompleti. Il file congela
il ramo CD4, non dichiara completo il catalogo o il training.
SHA256 della release r1:
`faefde8db9f205d35c8b781c205040ad778493b8bbfa112023a3a69c3555f114`.

Regola obbligatoria per il nuovo trainer e i suoi launcher: scegliere un release
manifest esplicito e registrarne SHA256 nel run e nel checkpoint. Montare solo
i riferimenti previsti; controllare ricevute e hash dei file effettivamente letti.
Niente ricerca del primo file omonimo, scelta implicita di `latest`, fallback a
un vecchio dataset o resume con input diversi senza una nuova decisione tracciata.
`release_lock.resolve` implementa il rifiuto del mount sbagliato o incompleto;
deve essere collegato al trainer insieme a `training_contract.py`. Non è ancora
una protezione dimostrata nel training esteso, che non è avviato.
Due fixture passate: rifiuto di contenuto storico con nome identico, release
modificata e derivato incompleto senza fallback.

`davideferrante11/rlead-bench-cube-r2` resta identificato come input aggregato
del pilot: non sostituisce questa banca per donatore. Altri dataset storici
restano da riconciliare per provenienza, contenuto, versione e ruolo: l'età
non giustifica scartare una sorgente idonea (D-053), né includerla automaticamente.

Nuove chiusure o nuovi dataset producono un nuovo release manifest, lasciando
immutati i precedenti. Nessun ricalcolo dei derivati invariati. Nessuna rimozione,
sovrascrittura o pubblicazione degli output cloud. I manifest locali sono indici
di recupero: non sono copie di sicurezza delle matrici. La persistenza verificata
finora è quella delle versioni private Kaggle citate nelle ricevute.
