# t39 — nuovi testi T3 registrati prima della generazione

**Nome:** t39 — T38 transfer + ESM2 sui vuoti

**Descrizione:** Candidato esplorativo: conserva gli effetti del transfer
ampliato T3, già inviato come t38, su tutte le coppie osservate e usa le
predizioni congelate del ridge su embedding proteici ESM2 soltanto nelle
coppie mancanti che il ridge prevede. Nessun nuovo fit. I voti CRISPRi e KO
già presenti in T3 restano invariati. Il riempimento riceve ampiezza 1,576
una volta; emissione come t38 con scala 1,5, dispersione genica a scala 1,
seed 20260912 e 400 cellule per perturbazione e contesto. Il banco precedente
T0+ESM2 non valida questo nuovo ibrido. Nessuna promozione scientifica
anticipata; copertura D-053 ancora aperta.

**Previsione e regola:** [prediction.json](../prediction_t39_t3_2026-10-10/prediction.json),
banda soggettiva 0,125–0,170, delta atteso zero, soglia ±0,005 contro t38;
t36 confronto secondario. Il Lead ha deciso la nuova base prima della generazione.

**Identità del file:** `T3_E2_fallback.npz`, percorso e SHA256 finali pendenti.
DATI li fissa con una ricevuta nuova prima della generazione; non usare
l'hash del precedente `T0_E2_fallback.npz`. Questi testi sostituiscono per
l'esecuzione i precedenti [testi T0](submission_texts.md), che restano conservati.

**Autorizzazione:** messaggio umano al Lead «ok decidi tu, vai e inviamo»;
successivo richiamo «ma la base t36 è vecchia...vabbè dici che ormai dobbiamo
tenere quella?». Il Lead ha annunciato l'uso di T38/T3 con ESM2 nei soli vuoti.
Il candidato T0 precedentemente registrato non è stato generato, secondo il Lead.

**Owner unico:** DATI-TRANSFER per composizione del file, controlli, generazione,
packaging e upload. AMMI continua; nessun invio duplicato.
