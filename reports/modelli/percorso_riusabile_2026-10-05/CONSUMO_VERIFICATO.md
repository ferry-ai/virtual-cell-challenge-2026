# Lettura congiunta verificata e nuove materializzazioni

Heartbeat 5 ottobre 2026, dalle 02:53 CEST. Stato tecnico, nessun nuovo fit.

**Misurato:** `snapshot_r10/state.json` verifica nove banche persistenti: Rest
D1–D4, Stim48hr D1–D4 e Stim8hr D4. Il job D1–D3 Stim8hr risultava ancora attivo;
non certificare le sue tre unità prima della chiusura.

`snapshot_samples_r2/state.json` verifica quattro campioni persistenti, senza
trasferire matrici: D1 Rest, D2 Rest, D4 Rest, D4 Stim8hr. In totale
33.855.360.140 byte. D3 Rest e D4 Stim48hr erano ancora in corso.

**Consumatore concluso e riconciliato:**
`consumer_d1_rest_r1/verification.json` lega codice/versione privata salvata alla
ricevuta `completion/consumer_complete.json`. In 308 secondi ha attraversato
12.091 righe di popolazioni perturbate e tutte le 12.092 righe di campioni,
660.906 cellule del livello 64, inclusi 16.252 controlli. Tutti i 310 file dei
campioni sono stati verificati tramite SHA256 sul runtime; anche i quattro
file effettivamente consumati dalla banca. Zero target mancanti, zero batch
non riconciliati, zero cellule dichiarate usate nella loss. È una prova reale
del collegamento banca/campioni e della lettura cloud, non di training esteso,
generalizzazione o efficacia scientifica. Non ha costruito ancore o modelli.

**Tre nuovi lanci accettati e in avanzamento reale:**
`davideferrante11/vcc-samples-cd4-d{1,2,3}-stim48hr-r1`.
Preflight sui tre account in `samples_preflight_r3.json`, lanci congelati in
`sample_launches.jsonl`, primi shard prodotti in `samples_live_r3.json`.
Gli input privati sono sull'account proprietario; nessuna replica automatica
sugli altri account. La quota osservata ha consentito questi tre lavori pronti.
Non rilanciarli. Stim8hr D1–D3 va materializzato dopo completamento della banca
e verifica degli slot con `launch_samples_r2.py`.

**Identità preservata:** nuova `release_cd4_r2.json`, SHA256
`be37ca5d85fdeec7fff9053fb1071a6485e294a66179cd667c384b5397131223`.
R1 resta intatta. La release r2 registra lo stato sopra, non quello futuro;
contiene ancora derivati incompleti, quindi non autorizza un training completo.

**Asse nominale ricostruito dai produttori:** `bind_ingestion_axis.py` eseguito
su metadati locali esistenti; `axis_binding_r1.json` verifica il codice congelato
dei 24 lanci effettivi e il medesimo SHA256 del CSV di 18.533 nomi unici.
L'ordine è quello che l'ingestione ha codificato come `official_index`.
Il futuro consumatore deve montare il dataset di codice indicato e controllare
quel CSV prima di creare le mappe geni/descrittori. Questa verifica sul runtime
del trainer resta da fare; nessun asse dedotto dal vecchio cubo del pilot.

**Ancora da completare:** campioni residui, riconciliazione del catalogo intero
oltre CD4 e oltre il pilot, integrazione di release/asse/split/ancore/loss e
ricevute di uso effettivo nel trainer anche dopo resume, export e valutazione
t28 dei 18 fit preliminari. Nessuna rete promossa; automazione ancora attiva.
