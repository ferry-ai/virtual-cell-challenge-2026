# invii — i nostri invii alla classifica di validazione

Due tipi di cartella, più due riepiloghi:
- **`prediction_t<NN>_<data>/`**: la previsione e la regola di lettura, **registrate prima**
  di generare (`prediction.json`). Dopo il punteggio c'è `comparison.json`, con l'esito letto
  secondo quella regola. Nessuno di questi file si modifica dopo la registrazione.
- **`trial_<data>/`**: una per giorno di lavoro sugli invii. Contiene i testi scritti prima, i
  manifesti degli stadi 45 e 48 e l'output di `vcc` salvato così com'è (`submit_*`, `status_*`).

Procedura e regole: [LAVORO §1–2](../../docs/LAVORO.md). Indice generale: [../README.md](../README.md).

## I punteggi ufficiali in una tabella

Fonte: i `comparison.json` e gli stati salvati. La tabella completa per membro è in
[PROGETTO §0](../../docs/PROGETTO.md).

| Invio | Punteggio | Rango | Esito della regola registrata |
|---|---|---|---|
| trial-01 | +0,045929 | 446 | primo invio; conferma il percorso d'impacchettamento |
| t02 | −0,092774 | 764 | ControlModel ×1 + cis: troppe chiamate; serve a risolvere le ancore |
| t03 | +0,019692 | 576 | verifica fuori campione delle ancore e dello stadio 84 |
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

Non inviati: t04, t06, t12, t18, t19, t23 (pronto, aspetta il via), t09 e t13 (fermati dalle
loro regole), t21 (la sua previsione è citata ma non è nel repository: vedi la
[revisione critica](../analisi/revisione_criticita_2026-09-28/REVISIONE.md), §4).

## Le cartelle, dalla più recente

| Data | Cartella | Nocciolo | Vale? | Peso oggi |
|---|---|---|---|---|
| 28/09 | [lezioni_invii_2026-09-28/](lezioni_invii_2026-09-28/) | I nostri invii valutati e la classifica pubblica in soli aggregati: dal t16 nessun cambio supera il rumore del seme; contro la mediana dei primi 100 perdiamo soprattutto sull'MSE (tosato a 0 in tutti i nostri invii) | sì; il rumore viene da una sola coppia di semi | ★★★ |
| 27/09 | [prediction_t25_2026-09-27/](prediction_t25_2026-09-27/) | t22 sulla cache r9 (stimatore senza l'artefatto del pseudoconteggio): +0,140238, −0,0010, non conclusivo | sì | ★★ |
| 27/09 | [prediction_t24_2026-09-27/](prediction_t24_2026-09-27/) | t22 con un altro seme del generatore: D = 0,0016 su una coppia; la soglia ±0,005 resta | sì, come stima grezza di una coppia | ★★★ (il solo dato sul rumore ufficiale) |
| 27/09 | [prediction_t23_2026-09-27/](prediction_t23_2026-09-27/) | t22 con la quota condivisa per gene: registrato, generato, **non inviato** | sì come registrazione; l'ablazione dice che conta l'esclusione dei geni, non la quota | ★★ |
| 27/09 | [trial_2026-09-27/](trial_2026-09-27/) | Testi, manifesti e pacchetti di t23, t24 e t25; invii di t24 e t25 | sì | ★★ |
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
| 23/09 | [trial_2026-09-23/](trial_2026-09-23/) | t10 inviato; t11 dopo tre tentativi falliti e la ripresa dell'upload; t14 | sì | ★ (lezioni pratiche sull'upload, LAVORO §2) |
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
