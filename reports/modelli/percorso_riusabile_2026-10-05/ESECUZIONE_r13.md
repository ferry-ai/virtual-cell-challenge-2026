# Riuso del K562 originale; fonti e maschere prima del freeze

5 ottobre, dopo20:45UTC. Stato operativo solo [R-LEAD](../../../docs/piani/strategia-scientifica.md).
Mandato umano: aggiungere quanto possibile fino23:30 Europe/Rome, poi rifit/generazione
per invio entro02 come obiettivo, senza attendere un confronto predittivo.

K562 t25/t28 originale già pronto: 28.104.995byte,272target×18.533geni,
SHAa37c78ce1f7c13a3fc145e75e64f2ccead555ec8e38a656d671903ed4fd7218f.
Confronto esatto con parita_sha256 del27/9, non K562essential né nuovo ricampionamento.
[Provenienza](k562_reuse_r1/preparation.json). Dopo rifiuto iniziale auto-review, umano
ha autorizzato SPECIFICAMENTE cache28MB+Gencode1,7MB e controlli662MB nelle due
destinazioni private df11/vcc-k562-t25-cache-r1 e df11/vcc-official-controls-r1.
[K562 caricato](k562_reuse_r1/dataset_create_r1.json),
[controlli caricati](generation_controls_r2/launch.json). Nessuna pubblicazione.

Tre lanci effects-only falliti, con causa conservata: bootstrap senza workingdir
su sys.path, importanndata inutile nel fit, poi guardiaSE KOLFchromatin. I primi due
non hanno calcolato statistiche; fix2 ha attraversato il controllo di tutti gli hash
del checkpoint del mix, poi si è fermato prima stage100.
[Recupero del log e guardia](k562_reuse_r1/failure_fix2/retrieval.json).
Non rilanciare fix2 né attribuire questi ERROR a OOM/dati persi.

Difetto adapter r4: _scatter copia anche geni control_mean<1e-6, dove il core mette
zeri raw/shrunk e talvoltaSEnan; originale AxisTable.from_source li lascia NaN.
[Riproduzione indipendente](../../analisi/riconciliazione_banca_2026-10-05/axis_adapter_repro.json).
La correzione deve ripristinare la maschera originale, non inventareSE o togliere guardie.
Il provider COMPLETE del vecchio mix non certificava ancora questa parità.

Grok stessa sessione613a1b58-0807-4abe-8dff-be9b67204552: r9 interrotta per comunicare
la prova, r10 ripresa come unico worker PID21672. [Mandato integrale](agenti/grok_transfer_esteso_r10/prompt.md).
Prepara derivati production-only sul pannello per HCT/HEK/4KOLF, con banche esistenti e
stessa soglia/estimator; poi ulteriori fonti compatibili. Parent verifica/pusha, no nuova
ingestion. Dati vecchi A549/RPE1/HIPSCI/Southard/ViPerturb localizzati nella
[ricognizione metadata](../../analisi/riconciliazione_banca_2026-10-05/old_derivatives_inventory.json);
presenza non basta ad ammetterli. Il producer singlecellK562 resta separato e non duplicato.

Generazione parent preparata con codice auto-contenuto, un solo voto perfonte attraverso
A/B/C, K562 esplicito, hash del checkpoint econtrols. Dipendenzeanndata/zstandard fissate,
nessun upgrade numpy/scipy/pandas/h5py, versioni runtime da registrare.
[Pacchetto preparato](generation_parent_r1/ready_deps.json), non ancora lanciato.
Serve integrare i successori corretti delle fonti prima del lancio, senza montare ERROR.
Il freeze è una nuova release dichiarata; non si aggiungono fonti durante generazione.

Riconciliazione:80pin e43unità inventory/storage, zeroerrori/differenzebyteGit in
[checkr4](../../analisi/riconciliazione_banca_2026-10-05/check_r4/verification.json).
Ledger storico recuperato e fissato inexpectedr2; storico completo conservato.
Copertura integrale/QC/adapter, dedup biologico e confronto appaiato restano aperti.
