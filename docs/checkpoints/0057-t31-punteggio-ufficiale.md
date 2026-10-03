# CP-0057 — t31: la media a pesi uguali di più linee pubbliche, ×2, in classifica

- **Data:** 2026-10-04
- **Tipo:** esperimento
- **Redatto da:** Claude Code per Alfredo
- **Revisione umana:** no
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

La media a pesi uguali per gruppo delle linee pubbliche (`net0`, il passo 0 della rete del t30), con ampiezza ×2 e il
generatore del t22, arriva al livello della ricetta in classifica (A, B, C)? È anche il primo punto per verificare se il
banco HepG2 con lo scorer vero ordina i modelli come la gara: lì `net0` stava 0,247 sopra la rete imparata.

## 2. Cosa è stato fatto

- **Registrazione:** previsione e regola il 3/10 alle 21:50 UTC, prima dell'esportazione e della generazione
  ([prediction.json](../../reports/invii/prediction_t31_2026-10-03/prediction.json)). Banda +0,05…+0,15, centro 0,10;
  regola a 0,06, 0,10 e 0,137.
- **Catena locale:**
  - `esporta_abc.py` con `ckpt_step000000.pt` e le 25 chiavi di addestramento come sorgenti; 272 bersagli coperti su 300;
  - stadio 45 `trial-ext-profile` con `--effects-scale 2.0`, il resto come il t22;
  - stadio 48: validatore ufficiale superato, sha256 `36e85e26…`
    ([t31_packaging.json](../../reports/invii/trial_2026-10-03/t31_packaging.json)).
- **Invio:** autorizzato dal proprietario in chat il 4/10 verso le 00:20 ora italiana. Upload come processo separato
  dalle 22:25 alle 22:42 UTC; entry `iJRHcbswOtopr8kDLJuP`, MD5 verificato.

## 3. Cosa si è osservato

- **Punteggio:** stato `published` alle 22:58 UTC, **score_avg +0,078749**, rango 652
  ([status](../../reports/invii/trial_2026-10-03/status_iJRHcbswOtopr8kDLJuP.json)). La media dei sei scalati,
  ricalcolata, coincide ([comparison.json](../../reports/invii/prediction_t31_2026-10-03/comparison.json)).
- **I sei scalati:**

  | Membro | t31 | t30 | t28 |
  |---|---|---|---|
  | PDS | +0,557 | +0,361 | +0,622 |
  | MSE | 0 (grezzo 7,73) | 0 (grezzo 1,04) | 0 (grezzo 5,80) |
  | NMAE | **−0,102** | +0,015 | +0,049 |
  | fedeltà | −0,059 | −0,216 | −0,007 |
  | reach | +0,079 | +0,013 | +0,199 |
  | Jaccard | −0,002 | −0,006 | +0,006 |

- **Differenze:** −0,0625 contro il t22, −0,0661 contro il t28, +0,0509 contro il t30, +0,0080 contro il t11, −0,0288
  contro il t15 (ricetta delle sorgenti genomiche ×2).
- **Regola registrata:** dentro la banda; **ramo c** (0,06–0,10), sotto il centro registrato di 0,10.

## 4. Interpretazione e incertezza

- **Misurato:** il t31 sta 0,051 sopra il t30. Il verso coincide con il banco HepG2 (`net0` sopra `net`), ma la
  grandezza no: sul banco erano 0,247 su una scala diversa. Un solo punto, una sola famiglia.
- **Misurato:** contro il t15, che ha la stessa ampiezza ×2 sulle sorgenti genomiche della ricetta, il t31 perde 0,029.
  Le linee pubbliche rlab non sostituiscono le sorgenti della ricetta su A, B, C.
- **Interpretazione:** l'MSE grezzo più alto di tutti i nostri invii (7,73) e l'NMAE negativo dicono che ×2 è troppo
  sulle medie per questa fonte; insieme reach e fedeltà restano sotto il t28. La fonte porta meno direzione utile, e
  l'ampiezza non lo compensa. Non separabile: sorgenti, stimatore, assenza del cis, 28 bersagli a zero e ampiezza
  cambiano insieme rispetto al t22.
- **Non dice:** nulla su D, E, F; nulla sulle rlab come aggiunta alle sorgenti della ricetta.

## 5. Spiegazione semplice

Abbiamo tolto alla rete la parte che aveva imparato e tenuto solo la media semplice delle risposte misurate in altre
linee cellulari, raddoppiata. Rispetto alla rete il voto sale molto, come il banco locale aveva detto. Ma resta lontano
dalla ricetta: le linee pubbliche indovinano meno bene quali geni cambiano, e alzare il volume fa sbagliare di più le
grandezze senza recuperare le direzioni.

## 6. Conseguenze

- Secondo la regola: **nessun altro invio di questa forma.** L'ampiezza da sola non colma il distacco.
- Il banco HepG2 ha ordinato giusto t31 contro t30, ma non ha un braccio con la ricetta: non può dire dove sta un candidato
  rispetto al riferimento. Per farne un cancello serve il banco della strada B, con la forma del t22 (slug r9 di Davide).
- La ricetta (t22/t28) resta il riferimento.

## 7. Cosa corregge

Nessuna misura precedente. Chiude l'attesa del t31 registrata in
[prediction_t31_2026-10-03](../../reports/invii/prediction_t31_2026-10-03/prediction.json).

## 8. Domanda di comprensione

Perché il t31 ha un PDS vicino a quello della ricetta ma una NMAE negativa, e che cosa dice questo sull'ampiezza ×2?
