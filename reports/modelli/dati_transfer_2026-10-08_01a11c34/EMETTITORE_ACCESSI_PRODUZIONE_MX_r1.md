# Variante MX — 10 ottobre 2026

Destinazione richiesta da MODELLI-ESTERNI:
`davidmaisterx/ammi-production-cells-17-01a11c35-r1`.
Supera la proposta operativa df11; i file precedenti restano evidenza storica.

[Emettitore](issue_production_mx_private_access_r1.py) vincolato al
[piano esatto MODELLI](../../analisi/modelli_esterni_01a11c35_2026-10-08/ammi_production_mx_access_plan_r1.json):
**209 payload, 10.100.920.946 byte**, dieci sorgenti. SHA256 del piano:
`2337ee0dfd807c25e68b78bd2ba2a0bcf2ce44bf41a2f4aadb0eeb3ff5c5535c`.
119 hash hanno locator pilot; il loro uso in produzione richiede comunque consenso.

[Riconciliazione](production_mx_emitter_scope_verified_r1.json): tutti gli hash,
byte e percorsi sono nell'inventario originale. L'ancora `production_query` è
un alias già verificato dello stesso hash di `production_without_neuron`.
[Otto test locali superati](production_mx_access_emitter_verified_r1.json), comprese
15 alterazioni respinte, piano reale con consenso sintetico solo in memoria,
destinatario diverso e CLI reale bloccata prima di rete/SDK.

Il [template](production_mx_private_authorization_template_r1.json) è chiuso:
`granted=false`. Nessun consenso reale ricevuto, locator emesso o job lanciato.
Dopo un eventuale consenso umano letto direttamente, MODELLI può creare una
nuova ricevuta con risposta e ID originali, scopo, job, hash di piano e codice.
Il consenso deve includere tutti i 209 payload, i 119 hash pilot e i riferimenti
temporanei di accesso. Non ricavarlo da un messaggio di coordinamento.

Controllo offline dalla root del repository:

```powershell
.\scripts\py.cmd reports/modelli/dati_transfer_2026-10-08_01a11c34/issue_production_mx_private_access_r1.py --authorization <ricevuta-reale.json> --job davidmaisterx/ammi-production-cells-17-01a11c35-r1
```

Solo dopo consenso, aggiungere `--issue --stage <nuova-cartella-DATA>
--receipt <nuova-ricevuta-cartella-DATI>`. Output compatibile
`private_locators.json`, mappa `files[sha256]={bytes,sha256,url}`; URL solo sotto
DATA fuori Git, mai nei log. Credenziali isolate per sorgente; errori provider
redatti. Nessun download dei corpi, modifica di visibilità o lancio è implementato.

Gli hash sono pin attesi: verifica di dimensione/SHA256 dei payload, mount, spazio
e decisione scientifica restano al consumer e a MODELLI. Nessun file dei pilot
attivi è stato modificato. L'emissione reale non è stata collaudata.
