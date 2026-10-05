# Prima consegna Grok: verifica del supervisore

Misurato: i 14 test della consegna r1 passano rieseguendoli. Nessun fit o job cloud
lanciato. Il rifiuto degli input non ammessi funziona, ma **non è il percorso
cloud completato** richiesto: il launcher mancante resta un lavoro aperto.

Difetto riprodotto, `grok_context_repro_r1.json`: due contesti BIO diversi, stesso
donatore/condizione, con effetti opposti vengono fusi in una tabella a effetto zero.
`linear_effects.estimate_source` raggruppa solo per condition e conserva solo il
donatore nella chiamata allo stimatore. Studio, contesto e chimica vengono persi.
Correggere prima del fit mantenendo tutte le identità e la gerarchia, con fixture
indipendenti su contesti/studi/chimiche e maschere diverse. Le matrici reali
conservate non sono state alterate o usate da questo adapter.

Ulteriori lavori identificati dal codice: `run_refit` rifiuta sempre il percorso
cloud quando allow_local_fit=False; il solo controllo cloud_params_refused non è
un runtime. La classificazione di tutti i record come unresolved non riconcilia
il catalogo. training_ready=False del manifest di STORAGE è previsto: non è
una misura di inammissibilità scientifica dei dati. Occorre produrre un manifest
di fit nuovo, con prove/ruoli/crosswalk/QC e versioni montabili, non cambiare il flag
in quello di storage. Gli alias CD4 e gli adapter ancora necessari vanno risolti
con evidenze, distinguendo sorgenti nuove da sottocontesti della stessa sorgente.

Il campo union_complete nel primo parser confronta con 'complete', ma gli
snapshot verificati usano 'remote_complete_union_checked': correggere lo schema
nella nuova copia. Non interpretare una convenzione di parser come fallimento dati.
Componenti compound mancanti devono restare bloccanti prima di statistiche/fit,
senza assumere che una stringa opaca sia un singolo gene.

R1 rimane immutabile e non viene adottata per il fit. Proseguire lo stesso worker
Grok in r2, con pin esplicito nuovo, correzioni e preparazione/esecuzione cloud
ammissibile. Non duplicare i job dati. HIPSCI ora24/24 e due unioni verificate
in hipsci_verified_r5/state.json; parent conserva questi output e segue le ultime
due campagne originali. Il training completo richiede comunque catalogo/QC/uso.
