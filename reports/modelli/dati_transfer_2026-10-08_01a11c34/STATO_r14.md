# Consegna delle 18 parti MX e attesa df11

9 ottobre 2026, controllo remoto delle 18:10 Europe/Rome in
`neural_inputs_status_r16.json`. Tipo: risultati tecnici misurati, non beneficio.

**Completate e consegnate:** 18 parti NTC di davidmaisterx, 35 contesti e
460.940 candidati prima del merge globale; indice unico
`ntc_ready_manifest_r1.json`. Sono ospitate dai kernel COMPLETE r6a, r6b e r7a.
Sette parti già complete sono state copiate e rihashate nello stesso account,
senza ripetere l'estrazione. Le ricevute e il codice produttore sono verificati;
il consumatore ricalcola gli hash delle matrici prima del training. Non sono
state scaricate matrici RNA sul portatile.

**Resta in esecuzione:** df11/r5, 12 parti e 12 contesti. Non è stato interrotto.
I fold richiedono le stesse 27 parti/44 contesti e nessuno è ancora completo.
`ammi_ntc_runtime_contract_r3.json` mantiene tutte le 30 parti generali,
separa codice produttore e storage e fissa il lettore immutabile in
`ntc_normalization_r1/ntc_cells.py`. Normalizzazione e merge hanno lo stesso
AST della versione precedente; il campionamento resta 64 per strato.

## Recupero Tian verificato

Il banco congelato escludeva controlli con conteggi nulli sull'asse comune.
L'estrattore ora applica la stessa ammissione usando la maschera comune
ricostruita da metadati e assi sorgente; la normalizzazione usa sempre
`obs.depth_native`, e le maschere di feature esportate restano quelle sorgente.
I piani e i CSV congelati non cambiano. Le ricevute reali confermano:

| Sorgente | NTC grezze | Ammesse | Escluse come nel banco |
|---|---:|---:|---:|
| Tian2019 iPSC | 10.687 | 10.401 | 286 |
| Tian2019 neuron | 15.580 | 15.083 | 497 |

Dodici test mirati passano (`ntc_cells_tests_r7.txt`). Il campo storico
`NTC_cells_read` delle due completion r7a indica le **517 cellule esportate**;
per verificare l'ammissione sono state lette anche le righe RNA di tutte le
26.267 NTC grezze, zero righe perturbate. Le ricevute restano immutate:
questa precisazione evita di confondere cellule esportate e letture per QC.
Il codice futuro esplicita separatamente i due contatori.

## Produzione pronta sul lato ancore e controlli

`production_anchors_verified_r1.json`: PASS per 12 output, cioè 10 ancore
senza il lignaggio della riga, query completa e riferimento della ricetta
originale. Fonti effettivamente consumate, hash, assi e maschere verificati.
La query e l'effetto A della ricetta originale hanno hash identico
`08fdfd2803fe97753b71324665aad61ccf658f4f014785a5cae8563c3c354c57`.
Il confronto è con la ricetta congelata, non una dichiarazione di parità con
un vecchio file di produzione non recuperato.

`official_ntc_verified_r1.json`: 8.832 controlli A/B/C, 2.944 ciascuno;
denominatore pari alla somma dell'intera X ufficiale fornita, prima di allineare.
La profondità biologica oltre l'asse disponibile non è nota. Produzione e pilot
restano distinti; nessun fit finale viene dichiarato eseguito.

## Accesso privato residuo

`ammi_private_access_plan_r1.json` misura 105 file necessari non accessibili
nativamente a davidmaisterx: 1.639.694.217 byte di chunk, ancore e truth,
provenienti da davideferrante11 e davideferante. I producer già utilizzabili
restano montati direttamente; gli ESM2 sono gli stessi asset pubblici acquisiti.
Mancano dimensioni e hash dei 12 blocchi NTC df11. Nessun trasferimento fra
account o locator è stato emesso; MODELLI attende il piano completo per
un'eventuale unica estensione di consenso. Staging di un chunk di risposta
alla volta, NTC in CSR, nessuna matrice densa globale.

Commit locale precedente: `7776d9df`, senza push. Controllo documenti r16 PASS;
suite generale r16 con i tre errori preesistenti `cell_eval2.config`.
Nessun training GPU lanciato da DATI, nessun invio T3 riaperto. D-053 resta aperto.
