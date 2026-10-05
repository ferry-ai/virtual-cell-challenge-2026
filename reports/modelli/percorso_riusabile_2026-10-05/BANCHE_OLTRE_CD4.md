# Ultimo campionamento CD4 e banche KOLF/Orion

Heartbeat 5 ottobre, dalle 06:42 CEST. Stato tecnico; training esteso non avviato.

**CD4:** `snapshot_samples_r4/state.json` verifica undici unità di campioni
persistenti, 98.060.291.683 byte. Le dodici banche restano quelle verificate
in `snapshot_r11`. D3 Stim8hr, ultimo campionamento, è stato accettato dopo il
preflight sui tre account e produce shard (`samples_live_r5.json`). Tutti i
dodici campionamenti sono ora lanciati: non duplicarli.

Release aggiornata `release_cd4_r4.json`, SHA256
`886b59f756829311bcab776e11ffb8179bb7815aeef194aadcf5d20f5e87d8ed`;
le release precedenti restano intatte. È ancora incompleta per D3 Stim8hr.

**Tre nuovi banchi privati CPU accettati, dai grezzi già ingeriti:**

| Job su davideferrante11 | Cellule | Input esistenti |
|---|---:|---:|
| `vcc-bank-kolf-pan-r1` | 2.659.209 | 2 parti, 133 shard |
| `vcc-bank-orion-hct116-r1` | 3.409.169 | 4 parti, 109 shard |
| `vcc-bank-orion-hek293t-r1` | 4.534.299 | 8 parti, 223 shard |

Ricevute e preflight in `{kolf,hct116,hek293t}_bank_launch_r1/`; codice congelato
in corrispondenti `_bank_stage_r1/`. `snapshot_other_r1` registra lo stato,
`other_banks_live_r1.json` l'avanzamento: KOLF ha superato gli hash e i controlli
iniziali e aggregato cinque shard. I due Orion erano RUNNING ma senza log Python
disponibile al primo controllo: verificarne l'esecuzione effettiva, non dedurla
dalla sola accettazione. Il quarto job sull'account è D3 Stim8hr. Gli input
privati restano presso il proprietario; accesso del terzo account negato nella
prova 403 già registrata, nessuna replica massiva o pubblicazione.

Secondo controllo, `other_banks_live_r2.json` alle 07:06: HEK293T ha emesso
le risorse del runtime (4 CPU, 32,65 GB disponibili); HCT116 non ha ancora
un log disponibile. Verificare quest'ultimo per primo alla prossima supervisione.

**Produttore riutilizzato e corretto:** copia congelata del banco CD4, con
gruppo esplicito (`iPSC`, `HCT116`, `HEK293T`), contesti attesi controllati,
SHA256 di ogni shard prima dei calcoli e guardia sul disco. Conserva statistiche
di popolazione e selezioni annidate, senza pooling di contesti o tagli per
dimensione. Uno shard che mescola identità biologiche viene rifiutato: in caso
di guasto adattare la lettura, non eliminare il contesto. Fixture H5AD passata:
conteggi/campioni invariati, gruppo conservato, rifiuto di alterazione a parità
di dimensione e di un contesto inatteso. È lo stesso codice per tutti e tre.

`kolf_axis_r1.json` e i `prepared.json` Orion verificano l'asse nominale nei
due più dodici lanci d'ingestione congelati. Le ricevute complete precedenti
sono incluse per hash nei nuovi parametri; nessuna nuova ingestione.

**Prossima supervisione:** usare `other_bank_state.py --launches` con i tre
`launch.json` e un nuovo `--out snapshot_other_rN`; recupera solo manifest
dopo COMPLETE, controllando versione/codice, cellule, provenienza e file attesi.
`pipeline_state_r2.py` resta specifico CD4 e non include questi tre job.
Dopo i nuovi banchi servono le loro materializzazioni dei campioni, con i
produttori congelati corretti: il launcher CD4 non va applicato implicitamente.

Questi tre archivi non esauriscono il catalogo. Restano gli altri contesti
idonei, integrazione effettiva nel trainer di release/asse/split/ancore/loss e
resume, e valutazione t28 dei 18 fit preliminari. Nessun miglioramento dichiarato,
nessun invio, cancellazione, pubblicazione o push Git. Automazione attiva.
