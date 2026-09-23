# CP-0030 — Il t10 (t08 senza CD4): +0,050; CD4 porta circa 0,010 dei 0,014 guadagnati dal t08, ma la regola scritta prima dà esito non attribuibile

- **Data:** 2026-09-23
- **Tipo:** esperimento
- **Redatto da:** agente (Claude Opus 5.5)
- **Revisione umana:** no. Invio autorizzato come ablazione (`reports/trial_2026-09-22/autorizzazioni.md`).
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Il t08 (+0,0604) ha battuto trial-01 (+0,0459) cambiando gli effetti per tre ragioni insieme
([CP-0029](0029-t08-punteggio-ufficiale.md) §4):
- CD4 aggiunto;
- centratura γ = 1;
- stimatore K562 grezzo quasi-Poisson.

Quanto del guadagno viene da CD4?

## 2. Cosa è stato fatto

- **Ricetta** `configs/recipes/t10.json`: identica al t08, senza CD4. Stessa cache (stadio
  98, r3), stesso stimatore, γ = 1, ampiezza 0,197, generatore di trial-01, seme 20260912. I
  28 bersagli che K562 non copre restano senza effetto, come in trial-01.
- **Previsione e regola di lettura** registrate prima della generazione
  (`reports/prediction_t10_2026-09-23/prediction.json`):
  - banda +0,040…+0,060;
  - ≤ 0,050: CD4 porta almeno due terzi del guadagno;
  - ≥ 0,056: il guadagno viene soprattutto da stimatore e centratura;
  - altrimenti non attribuibile.
- **Generazione e impacchettamento** con gli stadi 45 e 48: 26 controlli superati,
  contenuto identico bit per bit (`reports/trial_2026-09-23/t10_packaging.json`).
- **Invio** alle 00:04 UTC del 23 settembre. Output verbatim in
  `reports/trial_2026-09-23/submit_JvksJS5r08YNOP6jfP4Q.json` e `status_JvksJS5r08YNOP6jfP4Q.json`.

## 3. Cosa si è osservato

**Misurato — il punteggio.** **+0,050191**, rango 570, dentro la banda registrata.

**Misurato — i grezzi dei tre invii con lo stesso generatore**
(`reports/prediction_t10_2026-09-23/comparison.json`):

| membro | trial-01 | t10 (solo K562) | t08 (K562 + CD4) |
|---|---|---|---|
| `pds_cosine` | 0,6870 | 0,6938 | 0,7103 |
| MSE | 1,2313 | 1,2970 | 1,1524 |
| NMAE | 0,9849 | 0,9804 | 0,9774 |
| fedeltà | 0,4580 | 0,4610 | 0,4594 |
| `reach` | 0,0980 | 0,0913 | 0,1099 |
| Jaccard | 0,0291 | 0,0293 | 0,0304 |

**Misurato — scomposizione descrittiva del guadagno del t08** (+0,0144 su trial-01):
- **CD4 (t08 − t10): +0,0102.** Migliora PDS (+0,017), MSE (−0,145), `reach` (+0,019),
  NMAE e Jaccard; peggiora di poco la fedeltà (−0,002).
- **Stimatore e centratura (t10 − trial-01): +0,0043.** Migliorano di poco PDS (+0,007),
  NMAE e fedeltà; peggiorano MSE (+0,066) e `reach` (−0,007).

## 4. Interpretazione e incertezza

**Esito della regola scritta prima: nessuna delle due letture è sostenuta.** Il t10 sta a
0,0502, sopra la soglia di 0,050 per 0,0002. La regola va applicata com'è scritta, e la soglia
non si sposta dopo aver visto il numero.

**Descrizione, non verdetto.** La scomposizione attribuisce a CD4 circa il 70% del guadagno. È
anche l'unico fattore che migliora insieme PDS, MSE e `reach`: i tre membri più lontani dalle
prime squadre.

**Incertezza:**
- ogni numero è un singolo invio, senza intervallo, e la scomposizione ignora le interazioni
  fra i fattori;
- con K562 da solo stimatore e centratura portano poco, e non è misurato se con CD4 portino
  di più o di meno;
- i 25 bersagli coperti solo da CD4 contano nel guadagno di CD4: non si separa l'informazione
  nuova sui bersagli già coperti dalla copertura aggiunta.

## 5. Spiegazione semplice

Abbiamo tolto CD4 dal nostro miglior invio e lasciato tutto il resto uguale. Il voto è sceso
da 0,060 a 0,050, poco sopra il 0,046 di partenza. Quasi tutto il miglioramento veniva quindi
dai linfociti T. Avevamo però scritto prima che per dirlo con sicurezza serviva scendere a
0,050 o sotto: siamo a 0,0502, e lo lasciamo scritto così.

## 6. Conseguenze

- CD4 resta nelle ricette. D-039 non si riapre.
- **Il prossimo passo sono altre sorgenti per lo stesso bersaglio.** CD4 è l'unico fattore
  che ha migliorato PDS, MSE e `reach` insieme. Il t11 (+ Orion HCT116) è generato con la
  regola registrata prima (`reports/orion_2026-09-23/PRIMA_DEI_RISULTATI.md`), poi HEK293T.
- La fedeltà non si muove con nessuno dei fattori provati (0,458–0,461): resta legata al
  generatore. È il fattore del t09 e dei candidati a generatore pulito.

## 7. Cosa corregge

Nessuna conclusione precedente. Precisa [CP-0029](0029-t08-punteggio-ufficiale.md) §4 (attribuzione
aperta) con un secondo punto, senza chiuderla formalmente.

## 8. Domanda di comprensione

Perché aggiungere una sorgente può abbassare la MSE di 0,145 senza che il suo scalato si muova
da zero? E perché è comunque un buon segno?
