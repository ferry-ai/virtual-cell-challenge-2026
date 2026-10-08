# DATI-TRANSFER — stato r4

Fotografia dell'8 ottobre 2026, dopo la verifica T delle 19:24:27 UTC (21:24 a Roma).
File posseduti: questa cartella e i suoi output nella radice dati.

**Misurato:** campagna completata, 41/41 unità di produzione e 41/41 T/J,
6/6 ricomposizioni corrette per ciascun regime e 2/2 medie CD4.
Il dispatcher è concluso, senza task residui: `dispatch/r6/finished.json`.
Le nove esecuzioni j1 fallite e le loro prove restano conservate; la conclusione
riguarda le versioni corrette autorizzate, non cancella gli errori precedenti.

Sono congelate le 16 medie di produzione e le 16 con esclusioni target;
gli array sono verificati indipendentemente. Consegna al banco:
[HANDOFF_T2_MEDIE_r2.md](HANDOFF_T2_MEDIE_r2.md).
I due job CD4 autorizzati hanno usato rispettivamente 11.593 e 9.273 target.
T1 resta il candidato di effetti già disponibile; t36 resta riserva storica.
T2 non è ancora un candidato: il fit finale privato è preparato e attende il
consenso già richiesto in chat. Nessun miglioramento comparativo è dichiarato.

| Contratto CRISPRi | Righe | Contesti | Target distinti | Chunk |
|---|---:|---:|---:|---:|
| Produzione | 203.975 | 47 | 18.562 | 1.712 |
| Esclusioni T/J | 163.143 | 47 | 14.786 | 1.366 |

Manifest: `training_release_production_r1.json`, `training_release_T_r1.json`.
Verifiche indipendenti: `training_contract_production_check_r1.json`,
`training_contract_T_check_r1.json`. Passano hash locali, assi, unicità,
esclusioni e masse dei pesi. I chunk remoti richiedono ancora risoluzione dei
mount e verifica nel consumer. Nessun fit su questi contratti è attestato.

[coverage_ledger_r2.json](coverage_ledger_r2.json) collega 100 record del catalogo
a 45 unità di banca. Per 45 record senza collegamento la decisione storica resta
da riverificare: non sono automaticamente 45 nuove fonti biologiche distinte.
Le 41 unità derivate rappresentano 39.209.645 cellule nella somma per unità;
35.191.776 sono nei target che contribuiscono agli effetti di produzione.
Queste somme non sono cellule fisiche uniche o cellule lette da un trainer:
alias, split e ricomposizioni non vanno sommati, e H1 duplica 38.176 controlli
nell'inventario per unità, deduplicati nella ricomposizione.

D-053 resta aperta. Le quattro unità non derivate sono Datlinger 2017/2021
(mapping delle guide irrisolto) e HIPSCI genome-wide fitness/nonfitness
(partizioni da ricomporre e riferimento dei controlli da verificare; soltanto
36/12 controlli riconosciuti dai metadati attuali). KO e CRISPRa sono derivati,
ma restano bracci separati, senza consumer appreso attestato. I contesti extra
non sono stati eliminati per comodità.

L'adattatore di MODELLI-ESTERNI nel commit `303e3612` usa statistiche sufficienti
per target della stessa loss ridge pesata. Quattro fixture rieseguite qui passano,
con errore massimo rispetto al denso 9,99e-16: `adapter_acceptance_r1.txt`.
Questa è parità numerica su dati sintetici, non un fit biologico o un guadagno.
Restano inoltre passati i 15 test scientifici della banca e gli 11 di struttura.
La suite generale precedente ha tre errori per la dipendenza `cell_eval2.config`
mancante; non è dichiarata interamente verde.

Nessun job di questa campagna è ancora attivo; nessuna nuova acquisizione
biologica, acquisto, push Git o submission VCC è stato effettuato qui.
Il limite telefonico di Kaggle mantiene bloccati i due lettori del dataset Xu;
non è stato aggirato. Il pacchetto finale con i piccoli vettori privati resta
fuori dal repository pubblico. I documenti condivisi restano di VALIDAZIONE.
