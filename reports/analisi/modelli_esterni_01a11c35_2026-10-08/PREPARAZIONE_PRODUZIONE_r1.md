# Produzione AMMI: preparazione eseguita, accessi in attesa del proprietario

9 ottobre 2026. Aggiorna la preparazione descritta in `STATO_CHIUSURA_2243_r1.md`;
non attesta nuovi risultati o un fit di produzione avviato.

## Pronto

- Draft completo, con gate deliberatamente chiuso:
  `ammi_production_draft_prepared_r1.json`. Il vero runner lo rifiuta prima di
  creare output: due test PASS in `ammi_production_draft_tests_r1.txt`.
- Quattro strumenti dedicati al solo job
  `davideferrante11/ammi-production-cells-17-01a11c35-r1`: packaging, lancio,
  controllo remoto e raccolta metadati. Ricevuta
  `ammi_production_tools_prepared_r1.json`; due ulteriori test PASS in
  `ammi_production_tools_tests_r1.txt`. Scientific runner e codice dei pilot
  rimangono identici. Il packager rifiuta la ricevuta pending prima di leggere
  accessi privati; il launcher non può inviare un pilot o un altro account.
- Piano esatto `ammi_production_access_plan_r1.json`, riconciliato per hash e
  byte con il draft:135payload,5.387.051.931byte,81aggregati da davideferante e
  54file di18partiNTC da davidmaisterx. Le18completionJSON sono già incorporabili
  localmente e non richiedono download. Gli81file già usati nei pilot richiedono
  consenso anche per questa destinazione/scopo.
- Preflight delle22:49:23sorgenti native accessibili, nessuna respinta:
  `ammi_production_access_preflight_r1.json`. Quota precedente fresca:
  7.335,844secondi GPU liberi df11, senza acquisti. La durata reale del fit non
  è ancora misurata; la quota non giustifica un'ETA.
- DATI ha preparato e testato l'emettitore, senza usarlo:
  `reports/modelli/dati_transfer_2026-10-08_01a11c34/production_access_emitter_verified_r1.json`.
  Piano esatto SHA256 `e08ec7c1d41314156e0f0d2118ed3b8f76a2f26a0388571bcc443212ab250e54`.
  Sei test e15mutazioni del consenso respinte. Nessun nuovo locator emesso.

## Ancora necessario

Richiesto al proprietario il consenso specifico ai135payload nel solo job
privato df11, tramite link temporanei e con verifica integrale in cloud,
senza RNA sul portatile o acquisti. Il consenso ai quattro pilot non è stato
esteso per deduzione. L'emettitore resta bloccato fino alla risposta originale.

Rimangono anche i due CELLS terminali, la verifica delle loro guardie, la lettura
effettiva CELLS−A0/T0/NONE e la decisione tecnica motivata. Non viene richiesto
il banco a sei membri come nuovo prerequisito al solo fit tecnico; nessun esito
tecnico equivale a promozione scientifica o submission.

Il comando `plan_ammi_cells_delivery_v1.py` è pronto a congelare i file primari
native/swapped dalle due ricevute terminali, senza scaricarli. Mantiene tutte
le altre rotte descrittive e i fallimenti diagnostici. La scelta dei contesti
primari deriva dal piano congelato precedente ai risultati. Non è stato
eseguito perché le ricevute terminali mancano ancora.

Alle22:50 entrambi i fit risultavano RUNNING; gli ultimi eventi misurati erano
la baseline interna iPSC completata22:33:57 e K562 completata22:43:05
(`ammi_c-*_cells_progress_r2.json`). Nessun tempo finale di training misurato.
La raccolta terminale resta affidata alla continuazione PID22492; nessun
collector, banco o lancio duplicato.
