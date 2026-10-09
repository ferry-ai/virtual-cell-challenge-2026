# Ripresa: sei fit conclusi, rete contestuale r2 implementata su fixture

9 ottobre 2026, 12:46 Europe/Rome (orologio locale letto). Stato misurato,
non un risultato predittivo. Ricezione della ripresa verificata nel messaggio
umano `01a11fec-686c-7641-8b4a-37d5337aa2dd` della chat Lead.

## A VALIDAZIONE

Accetto per i fit C la regola indicata nei vostri MESSAGGI delle11:25:
T0 dove il transfer predice, ridge come ripiego dove non predice. Nessuna
miscela scelta dopo i numeri. La scelta è scritta anche in PROTOCOLLO_AMMI_r2.md,
che distingue questa ridge dal successivo esperimento additivo AMMI.

I sei fit risultano COMPLETE; T e J-K562 erano già raccolti e verificati.
I quattro nuovi recuperi sono nella radice esterna:
`C:/Users/ferra/vcc2026-data/external_models/01a11c35/verified_cloud_outputs_resume_r4/`.
Dentro ogni cartella `<job>/<job>/fit/native_predictions.npz`:

| Job | SHA256 della predizione registrato in complete.json |
|---|---|
| esm2-j-ipsc-01a11c35-r1 | 2569481ba352e2c749f89613cb28eee077d6d2f76359b0ad21ce493bc8b74990 |
| esm2-c-k562-01a11c35-r1 | 00b9d2d8286c5818633c09243d8e7146a56877804426d1b1647005513f831638 |
| esm2-c-ipsc-01a11c35-r3 | 6ada81fc8befcc336a6bd1b0658ac0e01ac89cac01f9a6fcd573f41915fdadc0 |
| esm2-production-01a11c35-r4 | 7bde4f1432a0cb9273a497c643237f91a74c667532309d48720a1186dbb3a1c0 |

Alla scrittura sono materializzate e hash-match le predizioni J-iPSC, C-K562
e produzione; C-iPSC e i quattro modelli sono ancora in download. **Non è
ancora un PASS tecnico completo**: quello richiede i file `.verified_resume_r4.json`
con assi, tutte le celle predette, maschere e reload del modello verificati.
Non leggere le partial e non confondere uno SHA atteso con un file verificato.

DATI ha verificato indipendentemente il consumo di tutti e sei i fit:
`../../modelli/dati_transfer_2026-10-08_01a11c34/esm2_*_consumption_verified_r1.json`.
Copertura di queste viste, non D-053 completa; nessuna misura nuova di beneficio.

Per AMMI: PROTOCOLLO_AMMI_r2.md e ADDENDUM_AMMI_r2_coverage.md recepiscono
le sette condizioni. Opzione(a), T0 panel-only; nessun refit che riammetta
l'inner. DATI ha congelato17 richieste di ancore outer+inner(+lignaggio riga).
La baseline outer-only esistente resta confronto distinto. Sono richieste
le ancore numeriche e la guardia disc95 del banco per il fold interno:
MODELLI non ne introduce una variante omonima.

## A DATI-TRANSFER

`ammi_context.py`: encoder individuale dei controlli, proiezione ESM2 e decoder.
`ammi_contract_v2.py`: pesi globali uguali per lignaggio/contesto/riga; obiettivo
che media i geni validi per riga; audit delle epoche; mappa di controlli scambiati;
quota comune della previsione intera; export ancorato con parità byte al residuo zero.
`ammi_train_v2.py`: trainer isolato a due epoche, gruppi di contesto senza
duplicare gli NTC per ogni target; CUDA obbligatoria salvo fixture minuscole.
Resta da collegare il wrapper biologico ai vostri input/ancore verificati e
alla guardia interna di VALIDAZIONE, poi preflight del pacchetto concreto.

Il callback della guardia non è una guardia implementata sui dati reali.
L'engine esige ricevute degli input, ma è il wrapper a dover verificare tutti
i loro hash e la provenienza prima della chiamata. Nessun training biologico
AMMI, nuovo job GPU o pubblicazione è avvenuto.

## Verifiche e stato operativo

14 fixture AMMI PASS (`ammi_tests_r3.txt`);56 test della cartella PASS
(`combined_tests_r10.txt`). Testano perdita mascherata, masse, gradienti,
reproducibilità, differenza cells/mean, invarianza none ai controlli, swap,
guardie, assi e parità nulla al byte. Non misurano beneficio biologico.
Controllo documentale r17 PASS; suite repository r7 ancora in esecuzione.
La r6 conserva3 errori ambientali cell_eval2.config e il precedente difetto
documentale già corretto, senza nasconderli.

Trasporto: dopo la sospensione del portatile, i collector notturni non avevano
recuperato questi quattro fit. I retry CLI hanno avuto SSL intermittente e
timeout600s. `collect_cloud_fit_v4.py` separa paginazione e download, usa una
allowlist esatta e HTTPS streaming con timeout; URL e log remoti non vengono
persistiti. Il recupero è in corso, non si attribuisce una causa remota non
misurata. Nessun fit già concluso è stato rilanciato.

Verdetto scientifico invariato: approfondire. Il segnale T è finora specifico
delle iPSC; J-K562 non dimostra generalizzazione. J-iPSC e C attendono la lettura
indipendente. Nessuna promozione, nessuna nuova submission, t36 resta la consegna.
