# Emettitore privato df11 — preparato, non eseguito

Richiesto da MODELLI-ESTERNI per rendere concreta la futura richiesta di consenso.
L'esecuzione e il lancio restano di MODELLI. **Nessun consenso produzione ricevuto,
nessun locator emesso.**

- [Piano congelato](production_private_payload_plan_r1.json): 135 payload,
  5.387.051.931 byte. SHA256
  `e08ec7c1d41314156e0f0d2118ed3b8f76a2f26a0388571bcc443212ab250e54`.
- [Emettitore](issue_production_private_access_r1.py): verifica hash piano,
  inventario e codice, consenso umano diretto riferito a un job preciso su df11,
  scopo produzione cells seed17, visibilità privata e rischi dei bearer temporanei.
- [Modello di ricevuta](production_private_authorization_template_r1.json):
  campi di consenso falsi e destinatario non compilato; non è autorizzazione.
- [Verifica](production_access_emitter_verified_r1.json): sei test locali superati,
  quindici alterazioni del consenso respinte; la CLI reale con `--issue` e template
  chiuso termina prima dell'import SDK o di chiamate di rete.

Gli 81 payload già presenti nei locator pilot richiedono consenso per il nuovo
scopo. L'emettitore richiede locator nuovi dalle otto sorgenti esatte; non legge
né riusa automaticamente quelli dei pilot. I 18 completion JSON NTC sono già
locali e non fanno parte dei 135 payload.

## Dopo l'eventuale consenso umano

Creare una nuova ricevuta dal modello, riportando la risposta originale e gli ID
di chat/messaggio effettivamente letti; compilare il job privato esatto e i campi
autorizzati. Non promuovere a consenso un messaggio di coordinamento.

Da root repository, il controllo predefinito è offline:

```powershell
.\scripts\py.cmd reports/modelli/dati_transfer_2026-10-08_01a11c34/issue_production_private_access_r1.py --authorization <ricevuta-reale.json> --job davideferrante11/<job-esatto>
```

Per l'emissione aggiungere `--issue --stage <nuova-cartella-sotto-DATA>
--receipt <nuova-ricevuta-nella-cartella-DATI>` allo stesso comando. Lo stage
deve essere nuovo, fuori dal repository; una preparazione parziale fallita non
viene sovrascritta. Non usare il template chiuso come ricevuta reale.

Le credenziali restano isolate per sorgente in sottoprocessi. Gli URL non sono
stampati: vengono salvati sotto DATA in `private_locators.json`, con la stessa
mappa `files[sha256]={bytes,sha256,url}` utilizzata dai consumer esistenti.
La ricevuta pubblica contiene soltanto pin, conteggi e scopo. Errori SDK vengono
redatti, senza riportarne testo o traceback.

L'emettitore non scarica corpi numerici, non modifica ACL/visibilità e non avvia
calcoli. La presenza di un nome nell'output remoto non prova l'hash del corpo:
il consumer deve verificare dimensione e SHA256 di tutti i 135 payload prima
dell'uso. Il test di emissione reale, mount, spazio, hash numerici e decisione
di produzione dopo i pilot restano aperti.
