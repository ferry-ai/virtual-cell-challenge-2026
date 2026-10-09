# Riuso NTC: dati presenti, contratto cambiato e adattatore incompleto

9 ottobre 2026. DATI-TRANSFER. Audit di metadata, ricevute e codice; nessuna nuova
estrazione, nessuna modifica al produttore in corsa, nessuna matrice reale letta.

**Conclusione:** i dati erano conservati e il riuso del transfer era dimostrato.
Il percorso canonico verificato consumava aggregati, non i campioni cellulari.
AMMI ha aggiunto un contratto di selezione e normalizzazione diverso, senza un
adattatore già verificato verso i campioni conservati. Presentare questo divario
come «mancano i dati» è errato. Il beneficio del passaggio a 64 NTC per strato
non è stato misurato: è una scelta di protocollo, non una necessità biologica
dimostrata né una conseguenza automatica di D-053.

## Che cosa esisteva e cosa si riusa

- Il [consumer canonico](../banca_canonica_2026-10-07/consumer/runtime.py)
  dichiara `BANK_FILES = count_sum.npz, mask.npz, rows.csv, complete.json`.
  Le righe NTC alimentano gli effetti. La [prova di riuso](../banca_canonica_2026-10-07/fit/riuso_r2.json)
  riguarda questo percorso: non prova il consumo di cellule da un encoder.
- La banca documenta 189,20 GB di campioni 32/64/128 persistenti, allora non
  consumati dal trainer canonico. Per le **12 parti attualmente attese**, le
  ricevute precedenti attestano **129.510.075.411 byte di matrici campionate**,
  comprensive di controlli e perturbazioni, non solo NTC.
- Il nuovo [inventario verificato](ntc_reuse_catalog_r1.json) riconcilia tutti i
  **1.739 shard sorgente** delle 12 parti con i riferimenti conservati nei vecchi
  campioni. Nessuno manca da questa catena di provenienza. Questo controllo di
  ricevute non è una nuova verifica remota delle matrici.

| Parti attese | Shard distinti | Popolazione NTC nella banca |
|---|---:|---:|
| CD4 D1–D3, tre condizioni ciascuno | 1.274 | 702.395 |
| KOLF pan-genome | 133 | 146.747 |
| Orion HCT116 | 109 | 165.777 |
| Orion HEK293T | 223 | 218.838 |
| Totale | 1.739 | 1.233.757 |

Gli shard hanno almeno 258.447.639.607 byte noti; i 131 shard D3 Stim48hr hanno
hash e numero di cellule ma dimensione non riportata nel piano locale. Non
tratto questo minimo come una misura dei byte effettivamente letti dal job.

## Perché il vecchio campione non è identico all'input AMMI fissato

La specifica [AMMI r2](../../analisi/modelli_esterni_01a11c35_2026-10-08/PROTOCOLLO_AMMI_r2.md)
e il suo [addendum](../../analisi/modelli_esterni_01a11c35_2026-10-08/ADDENDUM_AMMI_r2_coverage.md)
prescrivono fino a 64 cellule **per strato** library/batch/guides, profondità
nativa e maschere per sorgente. Il vecchio `NestedSampler` distribuiva il
limite 32/64/128 **per unità biologica e bersaglio** fra gli strati, elevandolo
al loro numero quando necessario per non perderne nessuno. Sono diversi anche
seme e chiave di priorità: `20261004` contro `esm2-ammi-ntc-r1`.

La nuova selezione preserva la specifica corrente. Non è dimostrato che sia
migliore. Usare ora i campioni precedenti richiederebbe un emendamento esplicito,
con nuova identità della selezione e confronto coerente tra i bracci.

Il [contratto neurale](neural_input_contract_manifest_r2.json) registra inoltre
`materialized_sample_has_depth=false`. Il materializzatore conserva
`source_sha256`, `source_row`, `cell_key`, `bank_row`, strato e probabilità di
inclusione, ma non `depth_native`; applica già ai conteggi la maschera della
riga di banca. La somma sui 18.533 geni allineati non ricostruisce in generale
la profondità nativa. Neppure ripristinare il denominatore restituisce geni
eventualmente rimossi dalla maschera comune della banca.

## Recupero dai metadata: possibile, con limiti precisi

[ntc_depth_metadata.py](ntc_depth_metadata.py) implementa il join per
`source_sha256 + source_row + cell_key`, con controlli NTC, identità biologica,
strato e profondità positiva/finita. Legge solo `obs`; non apre `X`. Richiede
che il chiamante abbia verificato la versione sorgente contro la ricevuta
congelata. **Non effettua autonomamente quella verifica integrale** e non
recupera conteggi eliminati dalle maschere.
Un eventuale hash integrale fresco del file HDF5 leggerebbe anche i byte che
contengono RNA: l'assenza di accessi a `X` non equivale a zero I/O sull'intero
file se il chiamante deve ancora autenticarlo. Tale costo va separato dal join
dei metadata e non nascosto nella promessa di riuso.

La fixture [test_ntc_reuse.py](test_ntc_reuse.py) passa su un HDF5 che non contiene
alcun dataset `X`: recupera il denominatore corretto e rifiuta cellula perturbata,
identità sorgente errata e duplicati. È una prova dell'adattatore, non una
materializzazione reale dei 12 gruppi. Le tabelle shard dei campioni e gli `obs`
reali non sono stati scaricati in questo audit; il numero di vecchi NTC per
livello non è ricavabile dai soli totali delle ricevute `complete.json`.

Si possono quindi riusare conteggi campionati, provenienza e selezioni esistenti,
aggiungendo un piccolo sidecar dei denominatori da metadata, **se** il protocollo
ammette quella selezione e quelle maschere. Non è un sostituto byte-identico
del bundle AMMI corrente.

## Duplicazioni ed inefficienze: distinzioni verificate

- Nessuno dei 1.739 hash sorgente è duplicato fra le 12 parti; nessuno compare
  nelle sorgenti delle 18 parti NTC già completate. Non emerge una parte intera
  corrente eliminabile come doppione di quelle 18.
- I controlli H1 condivisi sono già deduplicati dal pianificatore: usa train,
  esclude la copia val. Le stesse NTC non vengono estratte per ogni fold o seme.
- È invece ripetuto l'accesso a sorgenti che il vecchio percorso aveva già letto.
  Nel payload **effettivamente lanciato r5**, verificato contro gli hash di
  `neural_inputs_cloud_prepared_r5.json`, `selection` verifica integralmente ogni
  sorgente; `extract` ripete la verifica per le sorgenti con cellule selezionate.
  Il costo di queste riletture non è una necessità scientifica. Non abbiamo un
  profilo temporale che ne quantifichi il peso sul ritardo corrente.
- Il worker r5 elabora le 12 parti in sequenza e non stampa progressi. Il `print`
  finale del runner sta nel ramo CLI, non nel `run()` importato dal worker.
  `progress.json` viene aggiornato dopo ogni parte nel filesystem del job, ma
  non è esposto dalle osservazioni remote effettuate prima del termine. Questo
  è un difetto di osservabilità del nuovo worker, non prova di stallo.

## Correzione minima, stato di attuazione

**Implementato localmente:** [ntc_reuse_catalog.py](ntc_reuse_catalog.py) registra
18 bundle completi con ricevute verificate e 12 parti assegnate al produttore
attivo. La chiave include hash delle sorgenti, righe/identità NTC, asse genico,
selezione, normalizzazione e versione del lettore. Esclude percorso, nome del
job, fold e seme del training. Le decisioni sono `REUSE_AFTER_CONSUMER_HASH_CHECK`
oppure `AWAIT_ACTIVE_PRODUCER`; nessun rilancio automatico. I tre test passano:
spostare un file non invalida la cache, cambiare la scienza sì, e un produttore
attivo non genera una seconda estrazione.

**Dati già persistenti:** i 18 bundle sono output dei produttori verificati;
l'indice li riferisce, non li ricopia. Prima del consumo resta obbligatorio
verificare i byte e gli hash dei file numerici. L'integrazione del nuovo indice
nel consumer di MODELLI non è ancora attestata da una ricevuta di training.

**Al termine corrente:** il watcher DATI raccoglie/verifica le 12 parti e scrive
`ntc_df11_terminal_verified_r1.json` e `ntc_ready_manifest_r2.json`. MODELLI ha
confermato un worker distinto, PID9048, che attende quelle sentinelle, gestisce
la sola issuance autorizzata e i due fit cells. Non lo duplico. Il catalogo si
rigenera con `--ready ntc_ready_manifest_r2.json --out ntc_reuse_catalog_r2.json`.

**Da integrare prima di una futura estrazione, senza toccare r5:** eventi JSON
con flush a inizio/fine parte, sorgente verificata, shard metadata visitato e
NTC estratti; checkpoint immutabili per parte e ripresa dai soli mancanti.
Separare tempo di verifica, metadata, lettura e scrittura. Verificare ogni
contenuto una volta per snapshot immutabile del runtime, riusando quella
verifica nelle fasi successive; non abolire il controllo d'identità.

La cache evita nuove derivazioni sui prossimi fit compatibili. Il sidecar depth
è una via di riuso dei vecchi campioni da qualificare con un protocollo
esplicito, non un cambio silenzioso dei fit AMMI già autorizzati.

## Precedenti e limite della conclusione

S-005 distingue un limite del percorso operativo da un fallimento del modello;
S-007 richiede di non confondere media di cellule trasformate e trasformazione
della media. Nessun nuovo risultato biologico o chiusura D-053 è dedotto qui.
**Segnale precoce e arresto:** sorgente, asse, selezione, maschera o normalizzazione
diversi impediscono il riuso come input equivalente; una cache non verificata
non è dichiarata pronta e una parte attiva non viene rilanciata.
