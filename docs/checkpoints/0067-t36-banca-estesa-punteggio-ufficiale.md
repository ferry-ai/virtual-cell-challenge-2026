# CP-0067 — t36: massimo osservato sulla banca estesa parziale

- **Data:** 2026-10-06
- **Tipo:** esperimento
- **Redatto da:** Codex
- **Revisione umana:** no
- **Stato:** immutabile
- **Strade:** S-010

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Che risultato dà il transfer t25 con emitter t28 mantenuto, ampliando la banca con
le fonti compatibili pronte al freeze del 5 ottobre? Invio esplorativo richiesto
dal proprietario, senza attendere il banco e senza soglia numerica preregistrata.

## 2. Cosa è stato fatto

Rifit/generazione cloud `davideferrante11/vcc-generate-t28-frozen-bank-r1` versione1,
ricetta e fonti in [record](../../reports/invii/prediction_t36_2026-10-06/prediction.json).
13 nomi registrati, 9 con target sul pannello: K562 storico BULK, CD4 mix,
HCT116, HEK293T, H1 joint e quattro esperimenti KOLF. Quattro cache non contribuiscono
su questo pannello; quattro KOLF non sono quattro linee. Release estesa parziale.
360.000 cellule generate, 300 target × 400 cellule × 3 contesti; emitter t28.

Invio ricevuto alle00:56 locali, entry `JLcMRGExhXKk77XVds7x`, checksum verificato:
[ricevuta](../../reports/invii/trial_2026-10-06/submit_t36_public_receipt.json).
Nome t36 corretto dal proprietario prima upload; bozza t31 mai inviata.
Il [lettore](../../reports/invii/prediction_t36_2026-10-06/read_t36_score.py) legge lo
[status pubblicato](../../reports/invii/trial_2026-10-06/status_JLcMRGExhXKk77XVds7x_0138.json)
e verifica entry, pannello, ancore e media dei sei scalati, senza ricostruzione.

## 3. Cosa si è osservato

**Misurato:** t36 = **0,14724935991548274**, rango432 al controllo; t28 =
0,14484520500645978, differenza **+0,0024041549090229597**.
[Comparison](../../reports/invii/prediction_t36_2026-10-06/comparison.json): stesso
pannello/ancore, sei membri finiti, errore della media0, nessun membro imputato.

| Membro scalato | t36 | Differenza da t28 |
|---|---:|---:|
| PDS | 0,631067 | +0,008759 |
| MSE | 0 | 0 |
| NMAE | 0,071639 | +0,022437 |
| Fedeltà | −0,009521 | −0,002113 |
| Reach | 0,186563 | −0,012150 |
| Jaccard | 0,003750 | −0,002509 |

Fonte di tutti i valori: stesso status e comparison. La MSE scalata resta zero.

## 4. Interpretazione e incertezza

**Misura:** nuovo massimo tra i riferimenti ufficiali registrati, con guadagni PDS
e NMAE compensati da perdite reach, fedeltà e Jaccard.
**Interpretazione:** esito promettente ma descrittivo su un singolo invio; non prova
un beneficio stabile della banca, né di una fonte specifica, né generalizzazione D/E/F.
**Ipotesi:** più fonti possono migliorare alcune componenti del transfer; meccanismo
non isolato. Nessuna banda numerica registrata: nessun ramo pass/fail inventato ora.

## 5. Spiegazione semplice

La stessa ricetta, consultando una biblioteca più ampia, ha ottenuto un voto
leggermente migliore. Questo non dimostra che ogni nuovo libro aiuti, né che tutti
i libri archiviati siano già stati usati.

## 6. Conseguenze

Aggiornare il massimo osservato, senza promozione automatica a riferimento robusto
o nuova decisione D-NNN. Continuare il percorso riusabile e copertura D-053: questa
release non consuma tutti i 395,75 GB; adapter/QC ancora aperti. Banco appaiato su
più semi e split leciti resta il modo per verificare la stabilità, dopo questo invio.

## 7. Cosa corregge

Nessuna misura precedente corretta. Aggiorna il massimo osservato di CP-0052, non
ne riscrive l'esito o la regola. S-010 riceve il primo esito ufficiale di questa
campagna; il vecchio banco e i suoi criteri restano validi nel loro perimetro.

## 8. Domanda di comprensione

Perché +0,002404 e un nuovo massimo non provano che tutta la banca ampliata migliori
il modello, o che ciascuna delle fonti aggiunte abbia aiutato?
