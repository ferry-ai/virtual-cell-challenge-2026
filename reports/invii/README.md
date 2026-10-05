# invii — i nostri invii alla classifica di validazione

Due tipi di cartella, più due riepiloghi:
- **`prediction_t<NN>_<data>/`**: la previsione e la regola di lettura, **registrate prima**
  di generare (`prediction.json`). Dopo il punteggio c'è `comparison.json`, con l'esito letto
  secondo quella regola. Nessuno di questi file si modifica dopo la registrazione.
- **`trial_<data>/`**: una per giorno di lavoro sugli invii. Contiene i testi scritti prima, i
  manifesti degli stadi 45 e 48 e l'output di `vcc` salvato così com'è (`submit_*`, `status_*`).

Procedura e regole: [PROCEDURE §1–2](../../docs/PROCEDURE.md). Indice generale: [../README.md](../README.md).

**In valutazione:** [t36](prediction_t36_2026-10-06/README.md), ricevuto da VCC alle00:56 del6ottobre, entry `JLcMRGExhXKk77XVds7x`, stato launching senza punteggio. La bozza locale t31 non è stata inviata. [Ricevuta e stato](../modelli/percorso_riusabile_2026-10-05/ESECUZIONE_r18.md).

## I punteggi ufficiali in una tabella

Fonte: i `comparison.json` e gli stati salvati. **Questa tabella è la sede unica dei punteggi
ufficiali** (`docs/CLAUDE.md`): si aggiorna dopo ogni punteggio, e il §0 di
[PROGETTO](../../docs/PROGETTO.md) ne riporta solo il massimo osservato e il riferimento. I sei
membri di ogni invio sono nel suo `comparison.json`.

| Invio | Punteggio | Rango | Esito della regola registrata |
|---|---|---|---|
| trial-01 | +0,045929 | 446 | primo invio; conferma il percorso d'impacchettamento |
| t02 | −0,092774 | 764 | ControlModel ×1 + cis: troppe chiamate; serve a risolvere le ancore |
| t03 | +0,019692 | 576 | verifica storica delle ancore/stadio 84; la pretesa conversione esatta è smentita da CP-0050, non validata da questo invio |
| t07 | −0,016004 | 671 | modello lineare condizionato: la previsione del banco non regge per una famiglia nuova |
| t08 | +0,060370 | 547 | K562 + CD4, nuovo migliore |
| t10 | +0,050191 | 570 | t08 senza CD4: non attribuibile per 0,0002 |
| t11 | +0,070777 | 560 | + Orion HCT116: aggiunge informazione, ma sono cambiati anche i pesi |
| t14 | +0,064892 | 564 | ControlModel ×2,5: non attribuibile; la fedeltà scende |
| t15 | +0,107533 | 436 | ampiezza ×2: sopra la banda; D-006 si riapre (D-042) |
| t16 | +0,137627 | 336 | ampiezza ×4: la curva sale ancora |
| t17 | +0,108774 | 448 | + HEK293T sul t15: non attribuibile (R-016) |
| t20 | +0,139676 | 346 | effetti ristretti a 1,576 + cis: non conclusivo contro il t16 |
| **t22** | **+0,141250** | 337 | + HEK293T: non conclusivo contro il t20; **ricetta di riferimento** |
| t24 | +0,142897 | 347 | t22 con un altro seme: D = 0,0016, una sola coppia; il riferimento del t22 diventa 0,14207 |
| t25 | +0,140238 | 361 | t22 con lo stimatore corretto: −0,0010, non conclusivo; la correzione resta |
| t23 | +0,141868 | 366 | t22 con la quota condivisa (conta l'esclusione): +0,0006, non conclusivo; PDS su, membri DE giù (CP-0042) |
| t26 | +0,138721 | 384 | t25 senza effetti sui geni sotto 5 CPM: −0,0015, non conclusivo; il PDS non sale, i geni poco espressi pesano poco (CP-0045) |
| **t28** | **+0,144845** | 359 | effetti t25 ×1,5 e dispersione per gene ×1: nuovo massimo osservato; +0,004607 contro t25, sotto +0,005: non conclusivo ([CP-0052](../../docs/checkpoints/0052-t28-punteggio-ufficiale.md)) |
| t29 | −0,029625 | 893 | la rete addestrata sulle singole cellule (R-LAB, secondo training, braccio `desc`) al posto degli effetti della ricetta, generatore del t22: sotto la banda, ramo c della regola; PDS grezzo 0,50 contro 0,79 del t22, la rete distingue poco i bersagli ([CP-0055](../../docs/checkpoints/0055-t29-rete-cellulare-punteggio.md)) |
| t30 | +0,135249 | 460 | ibrido selettivo D-056: effetti t25 + w · R della rete del fold HepG2, generazione del t25: −0,004989 contro il t25, ramo b della regola (non conclusivo, a 0,00001 dalla soglia del ramo c); PDS scalato −0,042, fedeltà +0,014, Jaccard +0,002; nessuna promozione ([CP-0064](../../docs/checkpoints/0064-t30-ibrido-selettivo-punteggio-ufficiale.md)) |

Non inviati: t04, t06, t12, t18, t19, t27 (generato e impacchettato il 29/09, tenuto
pronto dal proprietario), t09 e t13 (fermati dalle loro regole), t21 (la sua previsione è citata ma non è nel repository: vedi la
[revisione critica](../analisi/revisione_criticita_2026-09-28/REVISIONE.md), §4).

## Le cartelle, dalla più recente

| Data | Cartella | Nocciolo | Vale? | Peso oggi |
|---|---|---|---|---|
| 2026-10-06 | [prediction_t36](prediction_t36_2026-10-06/) | Record runtime originale e correzione nome richiesta dall'utente; nessuna banda numerica inventata | attuale | Invio esplorativo della release estesa parziale |
| 2026-10-06 | [trial](trial_2026-10-06/) | Manifest packaging, testi e trasferimento del candidato; output CLI quando disponibile | attuale | Nessun score ancora dichiarato |
| 2026-10-06 | [prediction_t31](prediction_t31_2026-10-06/) | Bozza locale con record runtime, mai inviata | storico | Sostituita solo l'etichetta da t36; stessi byte |
| 04/10 | [prediction_t30_2026-10-04/](prediction_t30_2026-10-04/) | Ibrido selettivo D-056: effetti t25 + w · R della rete del fold HepG2 con il selettore congelato; cambia solo la fonte degli effetti rispetto al t25. Registrata alle 08:14 UTC prima della lettura degli effetti ibridi e della generazione; banda 0,125…0,160, regola a ±0,005 contro il t25. Ufficiale 0,135248602, delta −0,004989459: ramo b, non conclusivo; [confronto](prediction_t30_2026-10-04/comparison.json), catena e diagnosi in [diagnosi_t30](../modelli/diagnosi_t30_2026-10-04/README.md) | sì; non conclusivo, nessuna promozione | ★★★ |
| 04/10 | [trial_2026-10-04/](trial_2026-10-04/) | Testi del t30 scritti prima della generazione; effetti t25 rigenerati (stesso sha256 del t25), esportazione `export_abc_r2`, manifesti degli stadi 45 e 48, upload 09:13–09:30 UTC (entry lDMSYUZU5cFYHcRqI0lq, MD5 verificato), status pubblicato e lettore scritto prima; registro in [INVIO_T30.md](trial_2026-10-04/INVIO_T30.md) | sì | ★★★ |
| 01/10 | [prediction_t29_2026-10-01/](prediction_t29_2026-10-01/) | La rete addestrata sulle singole cellule (R-LAB, secondo training, braccio `desc`) con il generatore del t22: cambia solo la fonte degli effetti. Registrata alle 12:06 UTC prima dell'esportazione e della generazione; banda −0,02…+0,10, regola a 0,06 e 0,137. Ufficiale −0,029625, ramo c; [confronto](prediction_t29_2026-10-01/comparison.json) | sì | ★★ |
| 01/10 | [trial_2026-10-01/](trial_2026-10-01/) | Testi del t29 scritti prima della generazione; esportazione, manifesti degli stadi 45 e 48, upload sul Wi-Fi di casa (13:28-15:16 UTC, entry K6Q36uGCaEwQ1wRLmBLp), status pubblicato e lettore del punteggio scritto prima | sì | ★★ |
| 29/09 | [prediction_t28_2026-09-29/](prediction_t28_2026-09-29/) | Effetti t25 ×1,5 e dispersione per gene ×1. Ufficiale 0,144845205, delta t25 +0,004607144: nuovo massimo, sotto la soglia congelata +0,005. Sei membri e media verificati; [confronto](prediction_t28_2026-09-29/comparison.json). Il delta locale +0,028918 non era calibrato, 95/96 target già valutati | pubblicato; non conclusivo | ★★★ |
| 29/09 | [prediction_t27_2026-09-29/](prediction_t27_2026-09-29/) | t25 con l'esclusione del t23 (i 8.247 geni che meno di due universi stimano) senza pesatura né riscalatura; registrato alle 15:45 UTC prima di generare; banda +0,128…+0,150, regola a ±0,005 contro il t25; `esclusione.csv` è la lista 0/1. Generato e impacchettato il 29/09 (sha256 `b4eb8b75…`, manifest in `trial_2026-09-29/`); **non inviato**: il proprietario lo tiene pronto | registrazione; pronto | ★★ |
| 29/09 | [prediction_t26_2026-09-29/](prediction_t26_2026-09-29/) | t25 con effetto 0 sui geni sotto 5 CPM nei controlli del contesto (circa il 70 % dell'energia prevista): registrato alle 12:24 UTC prima di generare; banda +0,134…+0,156, regola a ±0,005 contro il t25. **Esito:** +0,138721, t26 − t25 = −0,0015, non conclusivo; `pds_cosine` −0,0020 grezzo: l'ipotesi registrata (il PDS del t23 dai geni poco espressi) non regge (CP-0045) | sì | ★★ |
| 29/09 | [trial_2026-09-29/](trial_2026-09-29/) | t26 pubblicato dopo ripresa; t27 pronto. t28 caricato alle 22:46 UTC, MD5 verificato e status originale finale published conservato: 0,144845205. Ricevute e cancellazione autorizzata del solo intermedio t26 in INVIO_T28.md; esito in CP-0052, seguito concluso | sì; t28 pubblicato | ★★★ |
| 28/09 | [prova_generale_2026-09-28/](prova_generale_2026-09-28/) | La prova generale del 22 ottobre (azione 3 di R-REV): A/B/C trattati come nuovi, 300 bersagli finti, fino al `.vcc` verificato, senza invio. Protocollo, sei previsioni e 13 difetti attesi dalla lettura del codice, fissati alle 20:00 prima di girare. **Esito (29/09, forma ridotta):** `.vcc` di D/E/F verificato; previsioni 1, 3–6 vere; D1 corretto (CP-0044). D4 (cache sbagliata in silenzio), D9 (riferimento di γ) e gli altri difetti di codice sono corretti il 29/09 pomeriggio con i loro test (RISULTATI, «Correzioni dei difetti»); resta la forma piena | sì; copie di A/B/C, forma ridotta | ★★★ |
| 28/09 | [lezioni_invii_2026-09-28/](lezioni_invii_2026-09-28/) | I nostri invii valutati e la classifica pubblica in soli aggregati: dal t16 nessun cambio supera il rumore del seme; contro la mediana dei primi 100 perdiamo soprattutto sull'MSE (tosato a 0 in tutti i nostri invii) | in parte: l'[audit del 29/09](../analisi/lead_scientist_2026-09-29/AUDIT_SCIENTIFICO.md) ne corregge due letture, il rumore stimato da una sola coppia di semi (§2.2) e il peso della risposta comune sull'MSE (§2.4) | ★★★ |
| 27/09 | [prediction_t25_2026-09-27/](prediction_t25_2026-09-27/) | t22 sulla cache r9 (stimatore senza l'artefatto del pseudoconteggio): +0,140238, −0,0010, non conclusivo | sì | ★★ |
| 27/09 | [prediction_t24_2026-09-27/](prediction_t24_2026-09-27/) | t22 con un altro seme del generatore: D = 0,0016 su una coppia; la soglia ±0,005 resta | sì, come stima grezza di una coppia | ★★★ (il solo dato sul rumore ufficiale) |
| 27/09 | [prediction_t23_2026-09-27/](prediction_t23_2026-09-27/) | t22 con la quota condivisa per gene; inviato il 28/09 con il via del proprietario: +0,141868, t23 − t22 = +0,0006, non conclusivo; `pds_cosine` +0,0109 grezzo, `nmae`, `reach` e Jaccard giù (CP-0042) | sì come registrazione; l'ablazione dice che conta l'esclusione dei geni, non la quota | ★★ |
| 27/09 | [trial_2026-09-27/](trial_2026-09-27/) | Testi, manifesti e pacchetti di t23, t24 e t25; invii di t24, t25 e (il 28/09 sera) t23 | sì | ★★ |
| 26/09 | [prediction_t22_2026-09-26/](prediction_t22_2026-09-26/) | t20 + HEK293T a peso uguale: +0,141250, il migliore; +0,0016 sul t20, non conclusivo | sì | ★★★ (ricetta di riferimento) |
| 26/09 | [prediction_t20_2026-09-26/](prediction_t20_2026-09-26/) | t19 + modulo cis: +0,139676; contro il t16 non si separano restrizione e cis | sì | ★★ |
| 26/09 | [trial_2026-09-26/](trial_2026-09-26/) | Testi, manifesti e invii di t20 e t22 | sì | ★★ |
| 25/09 | [prediction_t19_2026-09-25/](prediction_t19_2026-09-25/) | t16 con gli effetti ristretti a 1,576: registrato, non inviato | storico | ★ |
| 25/09 | [prediction_t18_2026-09-25/](prediction_t18_2026-09-25/) | t16 ad ampiezza 1,576: registrato, non inviato | storico | ★ |
| 25/09 | [trial_2026-09-25/](trial_2026-09-25/) | Testi e pacchetti di t18 e t19, mai inviati | storico | ★ |
| 24/09 | [prediction_t17_2026-09-24/](prediction_t17_2026-09-24/) | t15 + HEK293T a q99 uguale: +0,108774, non attribuibile | in parte: la lettura causale ha i limiti di R-016 | ★ |
| 24/09 | [prediction_t16_2026-09-24/](prediction_t16_2026-09-24/) | t15 ad ampiezza 0,788: +0,137627; grezzi derivati dalle ancore | sì | ★★ |
| 24/09 | [trial_2026-09-24/](trial_2026-09-24/) | t15 inviato; t16 e t17 generati e inviati il 25 dalla catena d'invio | sì | ★ |
| 23/09 | [prediction_t15_2026-09-23/](prediction_t15_2026-09-23/) | t11 ad ampiezza 0,394: +0,107533, sopra la banda; riapre D-006 | sì | ★★ |
| 23/09 | [prediction_t14_2026-09-23/](prediction_t14_2026-09-23/) | ControlModel con gli effetti del t08 × 2,5: non attribuibile, fedeltà in calo | sì | ★ |
| 23/09 | [prediction_t12_2026-09-23/](prediction_t12_2026-09-23/) | t11 + HEK293T: registrato, non generato | storico | ★ |
| 23/09 | [prediction_t11_2026-09-23/](prediction_t11_2026-09-23/) | t08 + Orion HCT116 a pesi uguali: +0,070777 | sì | ★ |
| 23/09 | [prediction_t10_2026-09-23/](prediction_t10_2026-09-23/) | t08 senza CD4: +0,0502; CD4 vale circa +0,010 | sì | ★ |
| 23/09 | [trial_2026-09-23/](trial_2026-09-23/) | t10 inviato; t11 dopo tre tentativi falliti e la ripresa dell'upload; t14 | sì | ★ (lezioni pratiche sull'upload, PROCEDURE §2) |
| 22/09 | [prediction_t08_2026-09-22/](prediction_t08_2026-09-22/) | K562 + CD4, γ = 1: +0,0604, sul bordo superiore della banda | sì | ★ |
| 22/09 | [trial_2026-09-22/](trial_2026-09-22/) | t08 e **le autorizzazioni del proprietario** (`autorizzazioni.md`: invii, Orion, disco) | sì | ★★ (le autorizzazioni vanno riconfermate in chat) |
| 19/09 | [prediction_t07_2026-09-19/](prediction_t07_2026-09-19/) | Previsione dello stadio 84 per il t07: +0,0101 contro un ufficiale −0,0160 | sì | ★ |
| 19/09 | [trial_2026-09-19/](trial_2026-09-19/) | t06 generato e non inviato; t07 inviato | storico | ★ |
| 17/09 | [prediction_t03_2026-09-17/](prediction_t03_2026-09-17/) | Prima previsione registrata (stadio 84) contro il t03 | sì | ★ |
| 17/09 | [trial02_decision_2026-09-17/](trial02_decision_2026-09-17/) | Applicazione meccanica della regola del t02; deviazione dichiarata per il t03 | storico | ★ |
| 17/09 | [trial_2026-09-17/](trial_2026-09-17/) | t02 e t03: gli stati contengono i grezzi che hanno risolto le ancore; t04 mai inviato | sì | ★★ |
| 13/09 | [trial_2026-09-13/](trial_2026-09-13/) | Primo invio (trial-01) e impacchettamento a memoria limitata, con l'istantanea del codice | sì | ★ |
| 12/09 | [trial_2026-09-12/](trial_2026-09-12/) | Primo trial locale: calibrazione annidata dell'ampiezza (0,1974), risorse, convalide | in parte (un file superato, R-011) | ★ |

## Che cosa non si ricava da qui

- **Un intervallo per il singolo invio.** Ogni punteggio è una sola estrazione del generatore;
  il rumore fra due semi è misurato una volta sola (t24 − t22).
- **L'effetto di una scelta su D/E/F.** Ampiezza e sorgenti sono state scelte su A/B/C con
  circa 15 invii: sul set finale, con contesti e bersagli nuovi, vanno ricontrollate.
