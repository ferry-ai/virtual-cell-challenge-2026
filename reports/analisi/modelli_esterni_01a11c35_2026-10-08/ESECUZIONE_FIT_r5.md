# J-iPSC fermo per DNS; cinque fit continuano

Misurato il 9 ottobre 2026, circa 00:27 Europe/Rome. Aggiorna ESECUZIONE_FIT_r4.md
e ACCESSO_J_r1.md senza modificarli. Nessun risultato di validazione scientifica.

## Errore identificato nel trasporto

J-iPSC r5, stesso account e dati privati autorizzati, usa la copia del resolver
`runtime_view_resolver_v2.py` e `private_download_v2.py`. Tutti gli otto moduli
scientifici di r4 coincidono per SHA con r5; vista, righe, pesi, esclusioni,
feature e query restano identici. I nuovi pacchetti hanno preflight e accessi
PASS; il dataset del bundle è privato confermato da API. Le cinque fixture
di trasporto passano (`private_download_tests_r1.txt`).

Il fit r5 è stato accettato e avviato, ma fallisce ancora prima dello store e
del training: tutti e tre i tentativi registrano `URLError`, `reason_type=gaierror`,
`errno=-3`, senza risposta HTTP. **Meccanismo immediato verificato: fallimento
della risoluzione DNS nel runtime**, non un errore di fit o di hash dei dati.
Non è ancora verificato perché quel runtime non risolva il dominio.

API get_kernel conferma `enable_internet=true`, `is_private=true`,
`enable_gpu=false` sia per r4 sia per il diagnostico. Una sola verifica DNS
dal portatile risolve il dominio pubblico www.kaggleusercontent.com a
35.190.26.106; non sono stati aperti link privati o scaricati array RNA.
Questo dimostra una differenza fra ambienti, non la causa infrastrutturale.
Nessuna modifica ai DNS, TLS o controlli di accesso.

Nessun secondo diagnostico avviato. Nessun altro rilancio automatico dopo i
tre tentativi falliti di r5. Il quinto slot df11 è riservato e usato da DATI
per il suo transfer esteso, quindi non viene occupato dal nostro J.

## Fit effettivi, non soltanto stati RUNNING

`live_progress_r4.json` conserva le osservazioni dei log e gli hash dei checkpoint.

| Fit | Geni completati su 18.533 | Ultimo checkpoint UTC 8/10 |
|---|---:|---|
| produzione r4 | 6.208 | 22:26:26 |
| T r3 | 8.704 | 22:27:07 |
| C-K562 r1 | 2.880 | 22:26:37 |
| J-K562 r1 | 6.272 | 22:26:49 |
| C-iPSC r3 | 2.240 | 22:27:06 |

Raccolta finita già avviata per questi cinque job, come documentato in r4.
Per J-r5 si raccolgono solo ricevute e log sanitizzato con la allowlist;
nessun modello o predizione è stato prodotto. Le predizioni future richiedono
verifica tecnica, controllo indipendente del consumo e scoring di VALIDAZIONE.
Nessun beneficio predittivo dichiarato e nessuna promozione.

## Controlli e consegna

Commit del recupero e delle ricevute precedenti: `9e017a73`, senza push.
`docs_check_r13.txt` era PASS; `docs_check_r14.txt` rileva invece il nuovo file
concorrente `reports/invii/prediction_t38_2026-10-09/prediction.json` ancora
non coperto dal registro. Segnalato a DATI; registri condivisi non modificati.
Restano i tre errori ambientali `cell_eval2.config` nei 290 test repository,
documentati in r4. Non è una suite interamente passata.

La copia del trasporto è disponibile a DATI con pin per SHA e test; il resolver
originale condiviso non è stato alterato. L'esito DNS resta una limitazione
operativa aperta, mentre la valutazione scientifica attende i fit reali.
