# Banco AMMI: instradamento concreto su df11

9 ottobre 2026. Piano preparato leggendo solo metadati; nessun trasferimento,
locator, modifica di permessi o job eseguito da questo piano.

**Destinazione proposta: banco CPU privato su `davideferrante11`.**
Il preflight `ammi_bank_df11_access_preflight_r1.json`, concluso alle
18:23:44 UTC (20:23:44 Europe/Rome), verifica tutti gli 11 input nativi:
3 dataset originali, 7 kernel originali e il kernel delle ancore AMMI.
Sono tutti accessibili e ammessi. Su MX nove input privati restituiscono403.
La scelta dell'account è quindi definita ora, prima degli output cells.

## Riutilizzo senza nuovi trasferimenti

Gli input originali del banco restano nei mount esistenti. Anche le due
ancore annidate A0 esistono nel job privato df11
`dt-ammi-anchors-01a11c34-r4`: i loro byte/hash coincidono con le ricevute
di parità dei fit none. Non occorre copiarle da MX. L'elenco preciso dei
mount e delle ancore è in `ammi_bank_access_plan_r1.json` e
`ammi_bank_df11_native_sources_r1.json`.

## Soli file che richiedono un nuovo percorso privato

Sorgente `davidmaisterx`, destinazione `davideferrante11`:

| Già prodotto | File relativo all'output del job | Byte |
|---|---|---:|
| `ammi-c-k562-none-17-01a11c35-r5` | `ammi-c-k562-none-17-01a11c35-r5/query_000_native.npz` | 18.286.218 |
| `ammi-c-ipsc-none-17-01a11c35-r5` | `ammi-c-ipsc-none-17-01a11c35-r5/query_000_native.npz` | 17.995.540 |

Totale noto: **36.281.758 byte**, due file. Il piano contiene i rispettivi
SHA256 e tutti gli alias di contesto. I 26 export none hanno soltanto due
contenuti distinti: si trasferisce una copia per hash senza eliminare query.
Gli hash dei payload saranno ricontrollati nel consumer cloud.

Per cells sono elencati ora nel JSON **52 percorsi attesi**: 2 contesti K562
e 24 iPSC, ciascuno native/swapped. Le identità dei due job r5 sono provvisorie
finché fissate dalle ricevute di preparazione; nessun job cells è ancora
avviato. Prima del trasferimento si legano nomi, byte e hash agli output
verificati. Un eventuale swapped fallito produce soltanto la diagnostica,
senza inventare un file valido o richiedere un nuovo fit.

Il nucleo dei confronti primari richiede fino a sei file di predizione:
due none, due cells e due swapped. Per conservare anche tutte le letture
descrittive già previste dal builder, il piano include fino a54 file prima
di deduplicare per hash gli output cells. Non si sceglie quali trasferire in
base ai risultati. La dimensione totale resta ignota finché cells termina;
il percorso e la regola di minimizzazione sono già definiti.

## Trasporto proposto e controlli

Locator temporanei degli export MX dentro il solo pacchetto privato del
banco CPU df11; download direttamente nel cloud. Nessun nuovo dataset,
ACL, pubblicazione, RNA, NTC o checkpoint da trasferire, nessun array sul
portatile. Questo percorso **richiede un consenso specifico**: il precedente
consenso dei 105 derivati e delle 12 parti NTC riguarda gli input dei fit.
Il piano non lo estende e non emette locator.

Il codice originale del banco resta invariato. Un adattatore da verificare
su fixture unirà i mount nativi e i soli export autorizzati in una radice
temporanea, assegnata a `driver.INPUTS`. Il driver cerca già i file per
dimensione e SHA256. Prima del lancio servono prova dell'adattatore, pin
definitivi dei quattro fit, consenso al percorso degli export e preflight
CPU/accessi aggiornato. I contrasti, split e supporti restano quelli congelati.

## Transizione NTC → cells: titolare MODELLI-ESTERNI

All'ultimo heartbeat letto, 18:23:12 UTC (20:23:12 locale), il produttore
NTC df11/r5 è RUNNING e i due manifest finali sono assenti. Il watcher DATI
PID912 resta l'unico raccoglitore/verificatore. Questa chat ha in carico la
sola issuance una tantum già autorizzata, dopo entrambi i manifest e dopo
verifica dell'assenza di `ammi_private_access_with_ntc_r1.json`, poi la
preparazione e il lancio dei due cells su MX con preflight aggiornati.
La responsabilità non viene passata al banco o lasciata implicita; il
watcher attuale non lancia autonomamente i fit e non riattiva questa chat.
