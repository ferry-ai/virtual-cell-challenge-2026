# Due job ESM2 privati avviati — 8 ottobre 2026

**Osservato alle 22:28:51 Europe/Rome:** entrambi i job risultano RUNNING su Kaggle
CPU, versione 1, visibilità privata verificata. Nessuna ricevuta del fit o misura
predittiva disponibile a questa osservazione; i log letti di produzione erano vuoti.

| Job | Vista | Query | Hash del codice remoto verificato |
|---|---|---:|---|
| `davideferrante11/esm2-production-01a11c35-r3` | 203.975 righe, 47 contesti | 300, contesto convenzionale target_only | `48f230e7e6d52cecd01cf2108c40eb75626a58961968a7f794b739368b5d7882` |
| `davideferrante11/esm2-t-01a11c35-r2` | 163.143 righe, 47 contesti | 66 × 47 = 3.102 | `131956052149030514d60b2b874dd399c1608e1ee63d1950a1a01bad0ac2f454` |

I due hash sono identici ai `code_sha256` dei rispettivi `prepared_*.json`.
Ricevute di push e stato in `esm2-*.launch.json` e `esm2-*.status_r1.json`.
24 mount per job accettati, nessun `invalid_kernel_sources`. Preflight r2 ha
osservato df11 con un job, mx con due e df con zero prima del lancio T; la
disponibilità degli account non somma la memoria dei runtime. Colab non verificato
attivo. Nessun job GPU: il calcolo usa CPU e due thread BLAS per processo.

## Percorso del job, non ancora attestazione di completamento

1. Estrae il solo pacchetto autorizzato in una directory nuova sotto `/kaggle/temp`.
2. Applica il validatore comune congelato a codice, metadata, configurazione e
   locatori. Misura RAM/CPU/disco; richiede spazio per lo store float32, tutta la
   cache privata e 2 GiB di margine. Nessun dato privato scaricato sul portatile.
3. Risolve tutti i chunk per contenuto, verifica ogni SHA e dimensione, poi
   applica il validatore completo ai chunk. I locator non entrano nelle ricevute.
4. Acquisisce sul runtime i soli asset ESM2 pubblici fissati e ne verifica i SHA.
5. Verifica assi, identità e maschere di ogni chunk; store `finite_verified`.
6. Smoke reale limitato a 128 righe e 32 geni, con parità contro regressione
   densa; non è misura di generalizzazione e non decide parametri.
7. Fit su tutte le righe e tutti i geni della vista; checkpoint ogni 64 geni e
   heartbeat ogni 45 secondi. Esporta modello, trasformazioni, maschere, generico,
   predizioni native e ricevuta di consumo. Le decisioni sono in HANDOFF_FIT_r1.md.

## Tentativi conservati e limiti

- Preparazione production r1 fermata dal controllo locale: `psutil` assente.
  Nessuna installazione nell'ambiente condiviso. Il job usa ora `/proc` per le
  risorse Linux e NumPy/SciPy come dipendenze scientifiche. Preparazione r2 passa.
- Push production r2 non confermato (codice 1); status 404, nessuna sessione
  eseguibile identificata. Il corpo dell'errore non fu conservato per evitare
  divulgazione di locator. Un placeholder nella lista non è prova di avvio.
- Production r3 usa compressione LZMA: 494.541 byte di codice invece di 1.273.997.
  Stessi input scientifici. Il push è riuscito; **causa del primo rifiuto ignota**,
  non attribuita retroattivamente alla dimensione. Diagnostica successiva oscura
  URL e valori opachi prima di stampare messaggi strutturati.
- Preparazione T r1 fermata prima del lancio: il campo della vista è un riferimento
  allo split, non lo split stesso. T r2 legge e verifica il file congelato indicato
  dalla release, conservandolo nel pacchetto. Nessun filtro sul risultato.

Autorizzazione al trasferimento privato verificata leggendo direttamente nella
chat DATI-TRANSFER il messaggio umano `01a11d1d-cf01-7df2-bd1c-d04b45eb470f`:
«Autorizzo questo trasferimento privato». Destinatario solo df11 privato,
1.164.005.881 byte di produzione e 929.902.301 byte T; nessuna ACL modificata.
Gli URL sono opachi, senza scadenza verificabile: restano segreti in ogni fase.

## Verifica locale

`combined_tests_r6.txt`: 24 test passati; differenza massima fixture circa 1e-15.
`docs_check_r7.txt`: controllo documentale passato, 67 checkpoint, 11 strade.
`repo_tests_r4.txt`: 290 test, tre errori già presenti per `cell_eval2.config`
assente e un errore documentale transitorio durante scritture concorrenti di DATI;
il controllo documentale successivo passa. Nessuna modifica ai documenti condivisi.

DATI-TRANSFER prepara la verifica indipendente del consumo; VALIDAZIONE conserva
scorer, regole di confronto e ammissione alla scala dello stadio 100. Questi job
non modificano la consegna t36 e non costituiscono un risultato favorevole.
