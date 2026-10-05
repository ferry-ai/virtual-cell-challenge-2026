# ARCHIVIO DATI — indice corrente r9

Manifest immutabile `manifest.json`, SHA256 `4a866f404a337baf1ad1b3e9dfa18b609541fbeabd2e790cd6622b4fb4018a1a`. Versioni precedenti conservate.
Account/versioni/percorsi/hash identificano i dati: nessun fallback ai dataset storici.
È un indice di storage, non una release ammessa al fit.

- Grezzi 395,75 GB, HIPSCI inclusa: [fonti e GB](../DATI_DISPONIBILI_r2.md).
- HIPSCI genome-wide: **24/24 parti e entrambe le unioni verificate** in hipsci_verified_r5.
- Norman banca e campioni: `davideferante/vcc-norman-bank-samples-r1`, versione 1 pubblica.
  Byte originali verificati prima del salvataggio; layout e alias espliciti nel manifest.
- iPSC statistiche originali: `davideferante/vcc-tian-ipsc-sample-input-r1`, versione 3 pubblica.
  Pubblicazione verificata dopo una risposta API non valida; nessuna versione dati nuova.
- K562 GWPS e HIPSCI mirato19 ancora aperti nell'ultimo snapshot remaining_open_progress_r6.
- **Copertura dell'intero catalogo e collegamento al trainer ancora aperti.** Verificare
  accessi, hash, assi, maschere, split e consumo effettivo nel runtime prima della chiusura.
  Grok prosegue nella stessa sessione, cartella r2; r1 non adottata dopo difetto BIO riprodotto.
  Nessun fit esteso ancora lanciato. [Verifica r1](../GROK_REVIEW_r1.md).

Riutilizzare i derivati a parità di input, asse, QC, codice e parametri. Un nuovo dataset
aggiunge il proprio adattatore/banca/campioni e una nuova release, senza rifare gli altri.
