# Accesso privato J-iPSC: esito del singolo diagnostico

Misurato il 9 ottobre 2026, circa 00:13 Europe/Rome. Nessuno score scientifico.

Il proprietario ha autorizzato un solo diagnostico nella risposta alla domanda
`call_617ab433f8a74ae79fbdf3ada3933036`, item 0: «Sì, autorizzo il singolo job
diagnostico». Il precedente rifiuto dell'auto-review è stato rispettato fino a
questa autorizzazione. Scope: primo blocco CD4 D1 Rest già previsto per J-iPSC,
16.238.339 byte; lettura e hash remoti, nessun training o RNA sul portatile.

Il push è accettato, versione 1, senza sorgenti rifiutate. Kaggle ha derivato
l'identità dal titolo, non dall'id richiesto nella metadata:

- richiesto: `davideferante/esm2-j-ipsc-access-01a11c35-r1`;
- effettivo, verificato con list e status:
  `davideferante/esm2-j-ipsc-private-access-diagnostic`.

È un unico job, non due tentativi. La prima interrogazione dell'id richiesto
non trovava il kernel; non è stata interpretata come mancato lancio né ritentata.
Per i futuri pacchetti mantenere titolo uguale allo slug, come nei fit.

Stato provider COMPLETE, ma **accesso FAIL**: `URLError`, nessun codice HTTP.
Il file atteso è `effects/context000_chunk00000.npz`, dal produttore
`davideferrante11/dt-all-d1-rest-01a11c34-tj2private`, SHA-256
`d9b357c4779d8ae2dbb19b18d6f4da3396388f9f858260542faae427ad24052b`.
Non sono stati ottenuti dimensione e hash effettivi. Questo non distingue DNS,
TLS, timeout o altro errore di connessione e **non prova un link scaduto**.
L'audit dei soli metadati di DATI trova tutti i 987 locator coerenti; non prova
che siano leggibili dal runtime destinatario.

Output recuperati con filtro esatto `^diagnostic\.json$`, oltre al log separato
del proprio job, fuori Git:
`C:/Users/ferra/vcc2026-data/external_models/01a11c35/cloud_results/J-iPSC-access-diag-r1/`.
Nessun URL, notebook, bundle o array RNA recuperato. I pacchetti privati e i
locator restano fuori Git; nessuna pubblicazione.

J-iPSC r4 era già fallito in `resolve_all_chunks`, prima dello store e del fit;
il diagnostico riproduce un errore di accesso sul primo input. La correzione
successiva proposta riguarda soltanto robustezza e diagnostica del trasporto,
nel fit J già autorizzato. Nessun altro diagnostico autorizzato o avviato.
