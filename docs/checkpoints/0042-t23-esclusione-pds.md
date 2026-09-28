# CP-0042 — Il t23 in classifica: +0,1419, non conclusivo; il PDS sale di dodici volte il rumore del seme, i membri DE scendono

- **Data:** 2026-09-29
- **Tipo:** esperimento
- **Redatto da:** Claude (Opus 5.5, sessione f2abd9a6)
- **Revisione umana:** no
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Il t23, cioè il t22 con la parte trasferita pesata gene per gene per la quota di risposta condivisa fra linee, alza il
punteggio ufficiale? Per l'[ablazione](../../reports/trasferimento/ablazione_t23_2026-09-27/RISULTATI.md), del t23 conta
l'esclusione degli 8.247 geni che meno di due universi sanno stimare (quota 0), non la pesatura: un suo esito si legge
come esito dell'esclusione.

## 2. Cosa è stato fatto

- **Registrato prima:**
  - la previsione e la regola, il 26/09 alle 23:14 UTC
    ([prediction.json](../../reports/invii/prediction_t23_2026-09-27/prediction.json));
  - i testi, il 27/09 alle 01:15 ([submission_texts.md](../../reports/invii/trial_2026-09-27/submission_texts.md)).
- **Generato e impacchettato** il 27/09: stadi 100, 45 e 48 sulla cache r5, come il t22.
- **Via del proprietario** in chat il 29/09 alle 00:04 ora italiana, trascritto in
  [autorizzazioni](../../reports/invii/trial_2026-09-22/autorizzazioni.md).
- **Invio:** `submit_trial2.py`, con lo sha256 dell'archivio ricontrollato contro il report dello stadio 48 (`2805aea8…`).
  - Upload dalle 22:05 alle 22:37 UTC del 28/09, md5 verificato dal server.
  - Stato salvato subito:
    [submit_t23_raw.json](../../reports/invii/trial_2026-09-27/submit_t23_raw.json),
    [status_JvKSI2yE5zdnw4Agghvy.json](../../reports/invii/trial_2026-09-27/status_JvKSI2yE5zdnw4Agghvy.json).
- **Letto con la regola:** [comparison.json](../../reports/invii/prediction_t23_2026-09-27/comparison.json).

## 3. Cosa si è osservato

- **Media:** +0,141868, rango 366 al momento del punteggio. Sta nella banda registrata (+0,12…+0,165).
- **Rispetto ai riferimenti:**
  - t23 − t22 = +0,0006, dentro la banda della differenza (−0,010…+0,015);
  - contro la media t22/t24 (0,14207), −0,0002.
- **Membri grezzi, t23 − t22** (fra parentesi t24 − t22, cioè il solo seme):

| Membro | t23 − t22 | Solo il seme |
|---|---|---|
| `pds_cosine` | **+0,0109** (0,7977, il più alto dei nostri invii) | +0,0009 |
| fedeltà | +0,0031 | −0,0006 |
| `de_wilcoxon_lfc_nmae` | **+0,0099** (peggiore) | −0,0020 |
| `reach` | **−0,0085** | +0,0052 |
| Jaccard | −0,0018 | +0,0000 |
| `mse` | −0,136 (scalato 0) | −0,003 |

- **Scalati:** `pds` +0,0250, `nmae` −0,0172, fedeltà +0,0105, `reach` −0,0098, Jaccard −0,0047, `mse` 0.
- Tutti i membri stanno dentro le bande registrate; `nmae` ne sfiora il bordo.

## 4. Interpretazione e incertezza

- **Per la regola:** non conclusivo entro la risoluzione. Il t22 resta il riferimento per l'attribuzione; la quota
  condivisa resta candidata per il banco con lo scorer vero.
- **Interpretazione, non verificata:** l'esclusione affila la discriminazione fra bersagli (il PDS sale di circa
  dodici volte quello che il seme da solo lo muove). Nello stesso tempo la parte trasferita muove meno geni DE e ne
  sbaglia di più l'ampiezza, e le due cose si compensano nella media.
- **Incertezza:**
  - l'unità di rumore del seme viene da una sola coppia (t24 − t22);
  - la differenza del PDS è grande rispetto a quella coppia, ma non ha un intervallo;
  - il t23 cambia anche la scala per contesto (riportata ai geni rilevabili del t22) e la pesatura: il membro che sale
    non si attribuisce alla sola esclusione senza un invio a un fattore.

## 5. Spiegazione semplice

Il t23 butta via, dalla previsione, i geni su cui le linee pubbliche non sanno dire nulla di affidabile. Il risultato è
che la previsione riconosce meglio quale knockdown è quale (il PDS sale), ma prevede meno geni cambiati, e con misure
meno precise. Il voto medio resta uguale perché un guadagno paga una perdita.

## 6. Conseguenze

- **Nessun cambio del riferimento:** resta la ricetta del t22.
- **Ipotesi per il prossimo candidato**, da registrare con la sua regola prima di generare: tenere l'esclusione (il
  guadagno di PDS) e recuperare i membri DE, per esempio con un'ampiezza che riporti `reach` al livello del t22.
  Dopo [CP-0041](0041-proxy-contro-ufficiale.md) il proxy non può scegliere questa ampiezza: serve il banco con lo
  scorer vero (azione 4 di R-REV), oppure un invio a un fattore dichiarato come tale.
- Dal t16 i cambi della **media** stanno nel rumore del seme
  ([lezioni](../../reports/invii/lezioni_invii_2026-09-28/RISULTATI.md)); qui si muove di molto un **membro**. Anche il
  t25, che cambiava lo stimatore, aveva mosso `pds_cosine` oltre il seme, ma all'ingiù (−0,0047 grezzo,
  [confronto](../../reports/invii/prediction_t25_2026-09-27/comparison.json)). Una modifica della direzione, non
  dell'ampiezza, può quindi spostare il PDS ufficiale; va provata a un fattore.

## 7. Cosa corregge

Nessuna conclusione precedente. Aggiunge il primo esito ufficiale all'[ablazione del
t23](../../reports/trasferimento/ablazione_t23_2026-09-27/RISULTATI.md), che resta un banco a proxy.

## 8. Domanda di comprensione

Perché un punteggio medio invariato non basta a concludere che il t23 non abbia cambiato nulla?
