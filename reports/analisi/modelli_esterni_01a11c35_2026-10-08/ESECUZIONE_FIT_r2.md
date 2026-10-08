# Correzione del pacchetto Windows → Linux

**Corregge lo stato provvisorio di ESECUZIONE_FIT_r1.md.** I job production r3 e
T r2 hanno raggiunto il runtime ma si sono fermati in preflight, prima del resolver
e della lettura delle risposte. Stato ERROR verificato con API. Ricevute recuperate
per whitelist in `failure_production_r3.json` e `failure_T_r2.json`, con heartbeat
e log omonimi; nessun HTML, notebook, codice o bundle remoto recuperato.

**Meccanismo accertato:** `Path('/kaggle/temp/...')` costruito su Windows viene
serializzato con backslash. Su Linux quel nome è relativo: l'estrazione finiva
sotto working e il validatore rifiutava i percorsi dichiarati non assoluti.
Il controllo ha impedito consumo e fit, ma non l'avvio della sessione.

`prepare_cloud_fit_v2.py` usa `PurePosixPath` per tutte le destinazioni Linux.
`check_private_package.py` legge il pacchetto effettivo, senza eseguirlo né
stampare il payload: verifica radice scratch assoluta, coerenza di ogni path con
l'estrazione, byte/SHA di tutti gli input e compilazione dei moduli. Le tre fixture
di `test_package_paths.py` riproducono separatori Windows, contratti discordanti e
contenuto mutato; il pacchetto corretto deve passare.

Nuovi pacchetti: `prepared_production_r4.json` e `prepared_T_r3.json`.
Entrambi hanno PASS in `package_check_production_r4.json` e
`package_check_T_r3.json`, 13 input. Nuovi job con nomi e output distinti;
ricevute di lancio/stato nei file `esm2-production-01a11c35-r4.*` e
`esm2-t-01a11c35-r3.*`. Nessuna modifica di dati, pesi o parametri scientifici.
La correzione locale non viene chiamata verifica remota finché il nuovo preflight
non produce la propria ricevuta PASS.

**Gestione dei locator:** nei job falliti il bundle era finito in working.
Il job e i suoi output restano privati. Non recuperarne output generali, HTML,
notebook o source, che possono contenere il pacchetto e riferimenti riservati.
Le ricevute sicure sono state spostate nella radice di questa cartella conservando
i byte, per rientrare nella copertura del registro; nessun file di evidenza eliminato.
La nuova radice corretta è sotto `/kaggle/temp`, fuori dagli output da recuperare.
Anche nei nuovi job, l'HTML generato automaticamente può includere il codice
privato: il recupero rimane una whitelist di ricevute e artefatti scientifici.

**Risorse realmente osservate nei due runtime:** 4 CPU, RAM disponibile circa
32,7 GB, disco libero circa 1,15 TB nel filesystem. Non è una promessa sulla quota
degli artefatti persistenti. I soli output del fit/checkpoint sono molto più piccoli
dello store temporaneo. Nuovo preflight slot r3: df11 zero job, mx uno, df zero.

La diagnostica del primo push non confermato resta di causa ignota. I due errori
preflight qui documentati hanno invece causa riprodotta e una guardia dedicata.
Nessuna misura predittiva e nessuna promozione derivano da queste prove operative.
