# CP-0056 — t30: punteggio ufficiale della rete sulle sorgenti

- **Data:** 2026-10-03
- **Tipo:** esperimento
- **Redatto da:** Claude Code per Alfredo
- **Revisione umana:** no
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

**Numero:** il CP-0055 è quello di Davide sul punteggio del t29 (`0055-t29-rete-cellulare-punteggio.md`), ricevuto in
chat e non ancora su GitHub; citato in `reports/analisi/t29_diagnosi_2026-10-02/README.md`. Questo checkpoint prende
il numero successivo per non sovrapporsi.

## 1. Domanda

In classifica (A, B, C), quanto vale la rete sulle sorgenti r1? È una rete che pesa effetti misurati in altre linee
usando i profili dei controlli, generata con le impostazioni del t22.

## 2. Cosa è stato fatto

- **Registrazione:** previsione e regola il 3/10 alle 13:55 UTC, prima del voto, dell'esportazione e della generazione
  ([prediction.json](../../reports/invii/prediction_t30_2026-10-03/prediction.json)).
- **Decisione del proprietario:** inviare appena esisteva una rete addestrata, senza aspettare il voto con lo scorer vero
  ([INVIO_T30.md](../../reports/invii/trial_2026-10-03/INVIO_T30.md)).
- **Addestramento:** kernel Kaggle `alfredo2003bit/rete-sorgenti-r1-train`, codice al commit 23d6475, seme 0,
  3.000 passi.
- **Catena locale** ([t30_locale.sh](../../reports/invii/trial_2026-10-03/t30_locale.sh)):
  - `esporta_abc.py` con le sole chiavi di addestramento come sorgenti;
  - stadio 45 `trial-ext-profile` con le impostazioni del t22;
  - stadio 48.
- **Upload:** come processo separato, dalle 16:27 alle 16:43 UTC. Entry `0GRBdx7CEwnmE6dH9AYa`, MD5 verificato.

## 3. Cosa si è osservato

- **Punteggio:** stato `published`, **score_avg +0,027878**, rango 781
  ([status](../../reports/invii/trial_2026-10-03/status_0GRBdx7CEwnmE6dH9AYa.json)). La media dei sei scalati
  pubblicati, ricalcolata, coincide ([comparison.json](../../reports/invii/prediction_t30_2026-10-03/comparison.json)).
- **I sei scalati:**

  | Membro | t30 | t28 |
  |---|---|---|
  | PDS | +0,361 | +0,622 |
  | MSE | 0 | 0 |
  | NMAE | +0,015 | +0,049 |
  | fedeltà | **−0,216** | −0,007 |
  | reach | +0,013 | +0,199 |
  | Jaccard | −0,006 | +0,006 |

- **Differenze:** −0,1134 contro il t22, −0,1142 contro la media t22/t24, −0,0325 contro il t08 (trasferimento non
  amplificato), +0,0575 contro il t29.
- **Regola registrata:** dentro la banda +0,02…+0,13; **ramo c** (sotto 0,06).
- **Misurato prima della generazione e scritto prima del punteggio:** l'ampiezza appresa riduceva gli effetti a un
  |lfc| medio fra 0,005 e 0,007, circa 20 volte sotto il t29. Da lì l'attesa del ramo c (INVIO_T30.md, commit 5b7ab3f).
  - Il fattore era 0,13–0,19 contro il norm-match di 1,14
    ([t30_effects_manifest.json](../../reports/invii/trial_2026-10-03/t30_effects_manifest.json)).
  - Su 300 bersagli, 28 non hanno nessuna sorgente e sono rimasti a zero.

## 4. Interpretazione e incertezza

- **Interpretazione.** Il PDS a +0,36 dice che i bersagli restano distinguibili: gli effetti vengono dallo stesso
  bersaglio misurato altrove. Lo dicono anche il contrasto `same − same_shuf` della strada C r1 (+0,128 su H1) e il
  confronto con il t29, che pesa −0,03 dove questo pesa +0,03.
- **I membri DE sono quasi nulli** perché gli effetti sono minuscoli: pochi geni passano la soglia di espressione
  differenziale. La fedeltà a −0,22 dice che, fra i geni chiamati, il verso sbaglia più spesso della baseline.
  Ipotesi: con effetti così piccoli quelle chiamate sono quasi tutte rumore del generatore.
- **Ipotesi sulla causa principale:** l'ampiezza appresa. Con un coseno di validazione di 0,056 la parte MSE della
  perdita premia effetti piccoli, e la rete ha imparato a ridurli.
- **Non è un confronto attribuibile:** sorgenti, stimatore, pesi e ampiezza cambiano insieme rispetto al t22. Un seme,
  un checkpoint.
- **Il voto con lo scorer vero** (kernel `rete-sorgenti-r1`) arriva dopo questo punteggio e non sposta la regola.

## 5. Spiegazione semplice

La rete deve indovinare come risponde una linea cellulare nuova, copiando con dei pesi le risposte già misurate in
altre linee. Ha imparato *quali* linee copiare, ma anche a dire tutto sottovoce: le risposte escono circa venti volte
più piccole del normale. Lo scorer capisce ancora quale gene è stato spento (PDS discreto). Però non vede quasi
nessun gene cambiare in modo netto, quindi i membri sui geni differenziali valgono quasi zero.

## 6. Conseguenze

- **Per la regola registrata (ramo c):** nessun altro invio di questa rete finché un banco locale a sei membri non la
  mostra almeno al livello del trasferimento semplice.
- **Proposta, non decisa:** prima di un altro invio,
  - togliere o bloccare l'ampiezza appresa, usando solo il norm-match o l'ampiezza della ricetta;
  - oppure usare una perdita a coseno pura;
  - poi confrontare sul banco con lo scorer vero `net` e `net0` contro la ricetta del t22.
- **PROGETTO §0 non cambia:** il massimo osservato resta il t28.

## 7. Cosa corregge

Nessuna conclusione precedente. Precisa l'attesa della previsione del t30: il centro 0,07 supponeva l'ampiezza
naturale. Il limite è stato scritto prima del punteggio, nell'addendum di INVIO_T30.md.

## 8. Domanda di comprensione

Perché il t30 ha un PDS molto migliore del t29 ma un punteggio comunque basso?
