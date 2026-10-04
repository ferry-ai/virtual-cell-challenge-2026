# Prosecuzione: sei banche persistenti e campioni autonomi

5 ottobre, heartbeat successivo al mandato sulla persistenza. Stato tecnico,
nessuna conclusione scientifica né training esteso dichiarato completo.

**Misurato:** `snapshot_r8/state.json` verifica sei unità CD4 complete e persistenti
su Kaggle: D1/D2/D3 Rest e tutti i tre stati D4. Sono 11.013.859 cellule ammesse e
9.623.732.946 byte di artefatti di banca. Sono stati recuperati solo manifest;
nessuna matrice è passata dal portatile. Le sei unità stimolate D1–D3 sono ancora
nei due job CPU originali.

**Implementato e provato su fixture H5AD:** `materialize_samples.py` legge le
selezioni esistenti 32/64/128 senza ricampionare. Salva una matrice CSR di conteggi
per shard, metadati con identità della cellula e indice della riga di banca,
probabilità di inclusione per ciascun livello, maschere e provenienza SHA256.
Ogni cellula scelta viene salvata una sola volta, anche se appartiene a tre livelli.
Non cambia QC, contesto o asse; i geni non misurati conservano la maschera.
I campioni comprendono anche i controlli. La fixture verifica conteggi, identità,
livelli annidati e rifiuto di uno shard grezzo alterato. Un test, passato.

**Lanci accettati, da seguire fino alla persistenza:** `sample_launches.jsonl`:

- davideferrante11: `vcc-samples-cd4-d1-rest-r1`, `vcc-samples-cd4-d2-rest-r1`.
- davidmaisterx: `vcc-samples-cd4-d4-rest-r1`, `vcc-samples-cd4-d4-stim8hr-r1`,
  `vcc-samples-cd4-d4-stim48hr-r1`.
- D3 Rest resta da lanciare; sul primo account due banche sono RUNNING e un
  notebook restituisce 404 sullo stato: il launcher riserva uno slot finché non
  è chiarito. Il terzo account è accessibile, ma la condivisione degli output
  privati necessari non è verificata; nessuna replica massiva automatica.

`samples_preflight_r1.json` registra gli ultimi 20 notebook per account e gli
stati riletti; RAM/disco/CPU sono verificati nei consumatori prima del calcolo.
`samples_live_r1.json` conserva il controllo successivo al lancio. Accettazione
del lancio e RUNNING da soli non provano completamento o persistenza finale.
`samples_live_r2.json` completa la prova di avanzamento: tutti e cinque i job
hanno prodotto almeno uno shard, con quattro CPU e circa 32,6 GB disponibili
all'avvio. Le prime matrici e relative ricevute sono state scritte dopo i
controlli SHA e di identità; il completamento complessivo resta da verificare.

I consumatori montano banca e shard grezzi esistenti, verificano gli hash dei soli
file consumati e salvano gli output sotto `/kaggle/working/samples/<unit>/`.
Non rifanno l'ingestione o i pseudobulk. Le nuove matrici sono un derivato autonomo
per evitare letture ripetute dei grezzi nel trainer. Il limite di 18 GiB di output
è una guardia di capacità, non un filtro di cellule: se scatta, conservare i
parziali e partizionare il lavoro restante, senza dichiarare completamento.

## Prossima azione della supervisione

1. Usare **`pipeline_state_r2.py`**, non r1, per gli snapshot successivi. La r1
   aveva inizializzato il percorso delle credenziali SDK a import-time: dopo aver
   letto Rest sul primo account, il cambio verso il secondo restituiva 403.
   r2 isola ogni account in un processo; `snapshot_r8` prova il recupero da entrambi.
   `snapshot_r7` conserva le ricevute Rest del tentativo interrotto; nessun job era
   fallito o è stato rilanciato per questo errore del supervisore.
2. Seguire anche i cinque job campioni. Dopo conclusione verificare file e
   `complete.json`, copertura dei livelli, input invariati e versione persistente.
   Riutilizzare gli output per nuovi trainer; evitare trasferimenti locali.
3. Lanciare le unità mancanti quando input e slot risultano disponibili:
   `launch_samples.py --launch --state <snapshot-nuovo>/state.json
   --preflight-out <ricevuta-nuova>.json`. Il launcher evita i lanci già accettati;
   un errore richiede diagnosi e revisione distinta, non rilancio cieco.
4. Collegare banca e campioni al trainer e vincolare l'asse nominale dei geni agli
   `official_index` dell'ingestione. Rimangono aperti tutti i contesti oltre CD4
   e il pilot, la riconciliazione del catalogo, i controlli di uso effettivo e
   l'export/valutazione t28. Questi cinque job non chiudono il mandato D-053.

Controlli generali: nel turno precedente la suite generale aveva tre errori per
`cell_eval2.config` mancante in locale; non si ripete l'intera suite su questo
heartbeat né si cambia l'ambiente. Qui si verifica la fixture pertinente e il
registro dei documenti. Nessun invio, pubblicazione o push Git.
