# DATI-TRANSFER — stato r6

Fotografia dell'8 ottobre 2026 alle 20:35:36 UTC (22:35:36 a Roma), orologio letto.
Aggiorna [STATO_r5.md](STATO_r5.md), senza modificare le prove precedenti.

**Misurato sulle risposte Kaggle salvate da MODELLI-ESTERNI e lette qui:**
entrambi i lanci corretti sono accettati, versione 1, nessuna sorgente kernel
rifiutata, stato RUNNING:

| Job privato, account `davideferrante11` | Stato letto alle UTC |
|---|---|
| `esm2-production-01a11c35-r4` | 20:34:32 |
| `esm2-t-01a11c35-r3` | 20:34:56 |

Prove nella cartella `reports/analisi/modelli_esterni_01a11c35_2026-10-08/`:
i rispettivi `.launch.json`, `.status_r1.json`, `prepared_production_r4.json`
e `prepared_T_r3.json`. MODELLI-ESTERNI possiede e segue questi fit;
DATI-TRANSFER non ne ha avviati duplicati.

I tentativi precedenti produzione r3 e T r2 si sono fermati al preflight,
prima della risoluzione dei chunk: il packager aveva serializzato percorsi
Linux con separatori Windows. La correzione del proprietario usa percorsi
POSIX e una guardia prima del lancio. I job falliti restano privati;
nessun recupero generale dei loro output, HTML o bundle, perché il bundle
contiene i riferimenti privati. Si recuperano solo ricevute ammesse per nome.

Il trasferimento autorizzato ha destinazione nei soli job privati df11.
I pacchetti e il resolver sono consegnati, ma **RUNNING non attesta ancora
trasferimento completo, verifica dei chunk o training completato**.
Resta da controllare l'uso effettivo di 203.975 righe / 47 contesti in
produzione e 163.143 / 47 in T, oltre agli hash e alle esclusioni congelate.
Non serve un notebook Colab manuale per questo percorso in esecuzione.

`verify_external_consumption.py` è pronto per la verifica indipendente delle
ricevute finali contro la vista originale: identità di tutti i chunk, pesi,
assi, split, inventari letti, codice preparato e prova di equivalenza delle
maschere. Legge solo metadata; non apre chunk o riferimenti privati e non
attesta la correttezza numerica delle predizioni. Tre fixture passano in
`external_consumption_tests_r1.txt`, compresi rifiuto di contesti persi,
pesi/esclusioni cambiati e ricevute con identità alterata. L'esecuzione
sulle ricevute reali resta pendente.

T2 è già completato e verificato: [CONSEGNA_T2_r1.md](CONSEGNA_T2_r1.md).
La consegna T2, il consenso specifico e gli strumenti di accesso sono nel
commit locale `d463df59`, 29 file confrontati byte per byte senza differenze.
Nessun push effettuato. Il candidato di effetti non è un invio VCC;
la promozione scientifica e l'ammissione della scala esterna restano a
VALIDAZIONE. t36 resta riserva; D-053 conserva le lacune nominate in r5.

Il controllo documentale r7 passa. Il r6 precedente conserva tre segnalazioni
su file dell'altra sessione creati durante il controllo: il checker esegue
due scansioni distinte (`scripts/31_check_docs.py`, `covered_paths` e
`check_coverage`), perciò una nuova creazione tra le scansioni può apparire
non coperta anche quando la riga della cartella esiste. Non sono stati
cambiati i registri condivisi. Restano i tre errori storici della suite
generale dovuti a `cell_eval2.config` mancante, documentati in r4.
