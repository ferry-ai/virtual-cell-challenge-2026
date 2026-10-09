# Consegna NTC parziale e produzione — 9 ottobre 2026

Tipi di evidenza: codice e ricevute misurati; completamento dell'intero corpus
non ancora avvenuto. Ultimo stato remoto: `neural_inputs_status_r11.json`.

## Disponibile

- `davidmaisterx/dt-ntc-inputs-01a11c34-r6a`: COMPLETE. Tre nuove parti,
  21 contesti e 13.654 candidati; `ntc_mx_r6a_verified_r1.json` verifica
  codice remoto, piani, sorgenti dichiarate, copertura e pin dei tre file per parte.
- Nello stesso r6a: tre parti D4, 237.140 candidati, recuperate da r4 ERROR
  senza riestrazione. `ntc_mx_restored_verified_r1.json` verifica la ricevuta
  di copia e rehash cloud dei 12 file, complessivamente 2.157.860.033 byte,
  e l'identità delle tre completion originali.
- `davideferrante11/dt-official-ntc-01a11c34-r1`: COMPLETE. A/B/C hanno
  2.944 controlli ciascuno (46 identificativi × 64). `official_ntc_verified_r1.json`
  verifica codice e ricevute. Il denominatore è la somma della riga X nativa
  fornita, prima di allineare: la profondità biologica oltre l'asse fornito
  non è disponibile. Non sostituisce `obs.depth_native` dei dati di training.
- Le 19 ancore dei fold restano in `ammi_anchors_verified_r1.json`.

Nessuna matrice NTC è stata scaricata sul portatile. Il consumatore deve
verificare dimensioni e hash dei file cloud prima dell'uso. Il PASS di ricevute
e codice non viene presentato come rehash locale delle matrici.

## Contratti

`ammi_ntc_runtime_contract_r2.json` mantiene le 30 parti di estrazione e i
47 contesti; separa produttore, codice originale per parte e destinazione di
storage. Per i due fold servono attualmente le stesse 27 parti/44 contesti.
HepG2/Jurkat/RPE1 non hanno bersagli di pannello per la loss: l'estrazione
generale resta attiva, il loro mancato uso nel fit resta dichiarato.

`official_ntc_contract_manifest_r1.json` indicizza il contratto esteso spostato
fuori Git senza cambiare un byte. `official_ntc_prepared_r1.json` conserva il
percorso storico precedente allo spostamento; il suo hash resta corretto e il
payload cloud non cambia. A/B/C restano anonimi.

`panel_anchor_requests_production_r1.json` è il contratto separato per
produzione: 10 ancore che escludono il solo lignaggio della riga, query T0
completa e confronto esatto con la ricetta originale a tre contesti.
Il primo job si è fermato prima del calcolo per `--contexts A` contro ricetta
`A,B,C`; r2 passa tutti i contesti effettivi, senza modificare ricetta o fonti.
`davideferrante11/dt-ammi-production-01a11c34-r2` è RUNNING nell'ultimo check.

## Difetto risolto e blocco residuo

Il vecchio lettore assumeva che tutti i gruppi HDF5 fossero categorici.
Undici test passano con il fix, compreso roundtrip AnnData, categorie nullable,
maschera malformata e simbolo mancante dichiarato mappato. La verifica cloud
reale di r6a ha letto 10 file con `nullable-string-array` e 59 categorici;
le tre parti hanno poi completato l'estrazione. Il worker ora verifica gli
schemi prima dell'estrazione, senza ammettere RNA prima degli hash sorgente.

r6b, r6c e df11/r5 restano RUNNING: nessun fold viene dichiarato pronto senza
le sue parti richieste. df11 non è stato interrotto. Accesso ai risultati
privati fra account va verificato nel runtime effettivo; un file locale di pin
non dimostra montabilità. MODELLI possiede caricamento CSR a blocchi e training.
Nessun fit GPU o nuovo invio è stato lanciato da DATI. Fast e T3 restano fermi.

D-053 resta aperto: contesti estratti, contesti usati dalla loss e catalogo
completo non sono la stessa evidenza. I test specifici passano; la suite di
repository r16 conserva i tre errori preesistenti `cell_eval2.config`.
