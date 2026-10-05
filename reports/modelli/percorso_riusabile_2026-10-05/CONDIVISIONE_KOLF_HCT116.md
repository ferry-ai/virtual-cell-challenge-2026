# KOLF e HCT116 condivisi e distribuiti — 5 ottobre

Il proprietario ha reso pubblici i primi due blocchi di notebook e lo ha
confermato in chat. Le verifiche in `shared_samples_dispatch_r2/` dimostrano
accesso agli output di tutte le otto sorgenti necessarie da entrambi gli account
consumatori: due banche, due parti KOLF e quattro parti HCT116. I precedenti 403
sono superati per queste sorgenti. I file consumati vengono verificati per hash
nel runtime; i riferimenti e le selezioni congelate rimangono quelli originari.

Quattro nuovi push accettati nel registro comune `other_sample_launches.jsonl`:

- davidmaisterx: HCT116 p2/4 e KOLF p1/3.
- davideferante: HCT116 p3/4 e KOLF p2/3.

Con le cinque parti già avviate su davideferrante11, tutte le sette parti
KOLF/HCT116 sono state lanciate, più due parti HEK293T. Restano le quattro
parti HEK293T p2–p5, dopo l'accessibilità del terzo blocco di nove notebook.
Non ripetere parti già registrate. Il completamento richiede ricevute e unione
delle parti, non soltanto stato RUNNING.

`dispatch_shared_samples_r2.py` aggiunge `--units` al dispatcher precedente,
per consentire il lancio delle sole sorgenti già condivise. Identità e codice
del materializzatore invariati. Per HEK293T usare `--units orion_hek293t
--launch --out <nuova_cartella>`; verifica tutti gli input e gli slot prima
di spendere quota, con deduplicazione per banca/unità/parte fra account.

La pubblicazione è eseguita dal proprietario sul sito. Non ho ripetuto
ingestione, trasferito matrici o modificato i permessi tramite API. Training
esteso e integrazione dei lettori restano aperti.
