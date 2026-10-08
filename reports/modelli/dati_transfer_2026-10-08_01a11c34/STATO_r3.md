# DATI-TRANSFER — stato r3

Fotografia misurata alle 2026-10-08T18:50:22.407238+00:00; le ricevute successive possono aumentare i conteggi.

T1 è pronta: 16 fonti, effetti A/B/C verificati e consegnati. t36 resta riserva storica.
Nessun miglioramento comparativo è attestato qui; la lettura finale appartiene a VALIDAZIONE.

La produzione ha **41/41 unità con ricevuta verificata**. Le esclusioni T/J hanno
**26/41** ricevute a questa fotografia. La somma per unità è
39,209,645 cellule rappresentate e 35,191,776
cellule nei target che contribuiscono agli effetti: non sono conteggi di cellule fisiche
uniche, né cellule lette o usate da un trainer cellulare. H1 ricompone e deduplica i controlli.
Le ricomposizioni corrette hanno 6/6 ricevute di produzione e
5/6 T/J. Prova: [campaign_snapshot_r2.json](campaign_snapshot_r2.json).

Il contratto CRISPRi completo della campagna di produzione contiene 203.975 righe,
18.533 geni, 47 contesti e 1.712 chunk: [training_release_production_r1.json](training_release_production_r1.json).
CD4 conserva i contesti di donatore/stato e HIPSCI i cloni; H1 e i blocchi K562 sono
ricomposti. KO e CRISPRa restano bracci separati. Il consumer deve ancora risolvere i
mount per hash e attestare il fit: il manifest da solo non dimostra apprendimento.

T2: i due job delle medie CD4 sono completati e verificati (11.593 target in produzione,
9.273 con esclusioni). K562 bulk riusa 9.866/7.838 target e riproduce esattamente tutti i
272 target condivisi con T1; [k562_bulk_common_r1.json](k562_bulk_common_r1.json).
La riduzione locale K562 ha richiesto 31,64 s e 199.929.856 byte di picco RAM.
Il pacchetto del fit finale è congelato in [final_t2/r1/prepared.json](final_t2/r1/prepared.json),
ma il lancio richiede ancora il consenso chiesto in chat. Il pacchetto numerico privato
è fuori dal repository. Il runtime deve riprodurre T1 esattamente prima di produrre T2;
una media mancante o non supportata su un gene votato blocca la release.

La r1 delle ricomposizioni ha fallito nell'avvio della cartella temporanea.
Log H1 e HIPSCI, correzione e test completo sono conservati in `joint/diagnosis*`
e `test_joint_runtime.py`. L'utente ha autorizzato nove rilanci privati: r2 immutabile.
Il dispatcher corrente è `dispatch/r6`, con uno slot per account non allocato da noi.
Gli account mantengono RAM separata; nessuna somma delle RAM è usata per dimensionare un job.

Kaggle ha esaurito la pubblicazione giornaliera di notebook sull'account principale:
i nuovi job sono privati, sullo stesso account. Il dataset Xu privato è stato creato,
ma entrambi i lettori restano senza accesso: il servizio richiede verifica telefonica
anche per aggiungere collaboratori. Prova: `private_share_xu_r1/verification.json`.

D-053 resta aperta: Datlinger 2017/2021 richiedono crosswalk di guida con provenienza;
HIPSCI genome-wide fitness/nonfitness richiede una strategia verificata per i controlli;
le fonti del catalogo esterne alla banca attesa non sono ancora riconciliate integralmente.
Nessun fit cellulare, nuova acquisizione biologica o invio VCC è stato effettuato qui.

File posseduti: soltanto questa cartella e i suoi output nella radice dati.
VALIDAZIONE ha aggiornato indice e registro; i documenti condivisi restano di sua proprietà.
Richiesta pronta: consumare T2 solo dopo la ricevuta finale e usare le medie T/J congelate
prima delle statistiche del fold; niente media di produzione nei fold T/J.
