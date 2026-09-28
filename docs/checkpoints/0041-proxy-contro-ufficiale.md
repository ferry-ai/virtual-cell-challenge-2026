# CP-0041 — Il proxy dei banchi contro le differenze ufficiali: due coppie su quattro non lette, non si sceglie più sul solo proxy

- **Data:** 2026-09-28
- **Tipo:** esperimento
- **Redatto da:** Claude (Opus 5.5, sessione f2abd9a6)
- **Revisione umana:** no
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Dal 25/09 i banchi si leggono sul proxy Δ = 0,36 ΔPDS_gen − 0,27 ΔnMAE_gen, calcolato contro una sorgente pubblica
tenuta fuori. Questo proxy prevede il segno delle differenze ufficiali già misurate? È l'azione 2 della scheda
[R-REV](../piani/revisione-critica.md) e l'incertezza 4 del §4 di [PROGETTO](../PROGETTO.md).

## 2. Cosa è stato fatto

- **Protocollo e regola** fissati alle 18:45 del 28/09, prima di girare, e committati alle 18:46 (`055ecff`) in
  [taratura_proxy_2026-09-28/RISULTATI.md](../../reports/trasferimento/taratura_proxy_2026-09-28/RISULTATI.md).
- **Le coppie:** le quattro a un fattore sopra il rumore del seme: t10 − t08, t11 − t08, t15 − t11, t16 − t15. Le due
  ricette di ogni coppia sono ricostruite esatte da `configs/recipes/` sulle cache dello stadio 98 (r3 per t08 e t10,
  r4 per le altre).
- **La verità:** HEK293T (cache r5), che non entra in nessuna di queste ricette. Letture in più su HCT116, K562 e CD4,
  ciascuna tolta dalle sorgenti di entrambe le ricette.
- **Il codice:** `taratura_proxy.py`, stessi membri di `four_sources_bench.py`, fissati da `tests/test_proxy_banchi.py`.
  Girato alle 19:18–19:28 dalla sessione Claude `f2abd9a6`, senza modifiche:

  ```bash
  scripts/py.cmd reports/trasferimento/taratura_proxy_2026-09-28/taratura_proxy.py \
      --out reports/trasferimento/taratura_proxy_2026-09-28/r1
  ```

## 3. Cosa si è osservato

Tutto in [`r1/summary.json`](../../reports/trasferimento/taratura_proxy_2026-09-28/r1/summary.json), con la tabella
nel §«Esito» del report.

- **Verità HEK293T, 281 bersagli:**
  - t11 − t08: +0,0233 [+0,0160; +0,0303] contro +0,0104 ufficiale. Segno giusto.
  - t15 − t11: +0,0133 [+0,0107; +0,0159] contro +0,0368 ufficiale. Segno giusto.
  - t10 − t08: +0,0055 [−0,0048; +0,0152] contro −0,0102 ufficiale. Non letta; la stima punta dall'altra parte.
  - t16 − t15: +0,0018 [−0,0002; +0,0037] contro +0,0301 ufficiale. Non letta.
- **Regola: non passa.**
- **Descrittivo:**
  - su CD4 il t16 − t15 del proxy è −0,0113 [−0,0137; −0,0088], di segno opposto all'ufficiale;
  - raddoppiare l'ampiezza da 0,394 a 0,788 peggiora l'nMAE del proxy su HEK293T, HCT116 e CD4, mentre il `nmae`
    ufficiale del t16 migliora ([CP-0037](0037-t16-ampiezza-quadrupla.md)).

## 4. Interpretazione e incertezza

- **Misurato:** il proxy legge le due coppie che passano dal PDS (una sorgente in più, il primo raddoppio) e non legge
  la via di CD4 né il secondo raddoppio.
- **Interpretazione:** il secondo raddoppio guadagna nell'ufficiale quasi tutto da fedeltà, `nmae`, `reach` e
  Jaccard (CP-0037), che il proxy non calcola o calcola su un altro insieme di geni.
- **Ipotesi, non verificata:** l'nMAE del proxy va contro quello ufficiale perché si calcola sui geni con |Z| ≥ 3 in
  una sorgente pubblica. Lo scorer lo calcola sui geni DE del contesto di gara, molti di più.
- **Limiti:**
  - una sola verità principale, che non è una linea di gara;
  - quattro coppie;
  - rumore di pseudobulk simulato;
  - ricette ricostruite dalle cache, non dai file inviati.

  Un proxy diverso, per esempio con più membri, potrebbe andare meglio: questa prova non lo dice.

## 5. Spiegazione semplice

Per decidere se una modifica alla ricetta migliora, finora la si provava in casa su una linea pubblica, con un
punteggio semplificato. Qui si è controllato se quel punteggio di casa avrebbe previsto quattro risultati ufficiali già
noti. Ne indovina due. Per gli altri due è come un termometro che segna la stessa temperatura prima e dopo che la stanza
si è scaldata: il cambiamento c'era, lo strumento non lo vede.

## 6. Conseguenze

- **Per la regola scritta prima:** nessun candidato si propone più al proprietario sul solo proxy. Serve il banco
  dell'azione 4 di R-REV, con lo scorer vero sui bersagli del pannello (Colab, avviato dal proprietario).
- **Proposta, da confermare con il proprietario:** i banchi a proxy restano utili per scartare varianti che peggiorano
  il PDS, non per scegliere ampiezza e sorgenti.
- **Le regole già lette sul proxy** (l'encoder, la quota condivisa del t23) non cambiano di esito. Dove da qui in
  avanti un modello «passa» sul solo proxy (per esempio la rete r1, la cui regola si sta leggendo), il passo
  successivo è lo scorer vero, non un invio.
- `docs/DECISIONI.md`: nessuna decisione nuova finché il proprietario non conferma la proposta.

## 7. Cosa corregge

- Chiude l'incertezza 4 del §4 di PROGETTO («se i proxy dei banchi predicano il punteggio ufficiale»): in parte sì, sul
  PDS; non sull'ampiezza né sulla rimozione di una sorgente.
- Qualifica le scelte prese sul proxy dal 25/09
  ([CP-0039](0039-banco-varianti-restrizione.md), il banco a quattro sorgenti del t22): restano valide come
  scarti, non come previsioni di punteggio. Non corregge i loro numeri.

## 8. Domanda di comprensione

Perché un proxy che non vede il guadagno del secondo raddoppio d'ampiezza non può scegliere l'ampiezza per D/E/F?
