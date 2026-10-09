# Cache degli input e preparazione produzione MX

**Misurato il 10 ottobre 2026, Europe/Rome.** Tre test della cache passano:
valori/maschere identici, isolamento dalle mutazioni, limiti ed espulsioni; tre
aggiornamenti AdamW producono output, loss, gradienti e pesi identici al bit su CPU.
Il test usa il vero lettore DATI fissato per hash e `DiskControls`, con soli dati
sintetici. Prova: `ammi_normalized_cache_verified_r1.json`.

Su 2048 cellule sintetiche per 128 geni, 12 letture complete, mediana di cinque
ripetizioni: normalizzazione senza cache 0,569 s; con cache sufficiente 0,079 s;
con cache insufficiente 0,602 s. È una misura del solo percorso degli input:
non comprende encoder appreso, backward o trasferimenti CUDA. Il caso che espelle
continuamente i blocchi è più lento; nessun guadagno cloud è dimostrato.

La cache conserva solo valori normalizzati e maschere immutabili, mai embedding
appresi. Limite: min(512 MiB, un ottavo della RAM disponibile dopo staging), massimo
128 voci; il limite in byte riguarda gli array, non il piccolo overhead Python.
La selezione delle cellule, l'ordine dei blocchi e tutti i parametri scientifici
restano invariati. I pilot in esecuzione non sono stati modificati o rilanciati.

**Implementato, non lanciato:** nuova bozza `production-cells-cache-draft-r1` nella
radice dati. `ammi_cached_production_draft_prepared_r1.json` ne fissa provenienza e
hash. Due test ulteriori verificano gli hash, l'identità di tutti gli input e il
rifiuto effettivo del runner prima di creare output quando manca la lettura dei
pilot: `ammi_cached_production_tests_r1.json`. I due test degli strumenti MX sono
passati; nessun job di produzione è stato avviato.

**Accessi proposti:** `ammi_production_mx_access_plan_r1.json`, 209 file,
10.100.920.946 byte, destinazione unica
`davidmaisterx/ammi-production-cells-17-01a11c35-r1`. Sostituisce la proposta df11.
DATI ha preparato l'emettitore MX con guardia sul consenso specifico; nessun link è
stato emesso. La domanda di consenso per questa produzione è pendente e distinta
dal consenso già acquisito per i quattro pilot. Le fonti native sono state
controllate in lettura; hash dei payload, RAM e disco sul destinatario richiedono
il preflight remoto prima del calcolo. Quota fotografata in
`ammi_quota_preflight_r9.json`, non garanzia di disponibilità futura.

Ultime ricevute locali lette alle 00:19 riportano i due pilot cells ancora RUNNING,
privati, T4, versione 1 e sorgenti corrispondenti. Non attestano il completamento
di un'epoca. Il raccoglitore esistente conserva lo stato terminale quando arriva;
nessun secondo raccoglitore è stato avviato. Mancano ancora lettura comparativa
cells/A0, cells/T0 e cells/none, decisione tecnica di produzione e validazione
indipendente per un'eventuale promozione. Nessun nuovo file AMMI `.vcc` è pronto;
questo resta un pilot con copertura D-053 incompleta.

**Consegna ESM2 separata:** a DATI è stata confermata l'interfaccia del file esatto
in `esm2_production_delivery_r1.json`: ampiezza 1,576 già applicata solo al fallback,
scala di emissione ancora da applicare. La scala 1,5 del generatore congelato è
compatibile; non si riapplica 1,576. Generazione e invio restano di DATI, senza
duplicazioni da questa sessione. La conferma d'interfaccia non è prova di beneficio.
