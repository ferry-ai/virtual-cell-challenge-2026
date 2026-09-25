# CP-0037 — Il t16 in classifica: +0,138, nuovo migliore; raddoppiare ancora l'ampiezza migliora soprattutto i membri DE

- **Data:** 2026-09-25
- **Tipo:** esperimento
- **Redatto da:** agente (Claude Opus 5.5)
- **Revisione umana:** no. Invio autorizzato dal proprietario in chat il 24 settembre
  (`reports/trial_2026-09-22/autorizzazioni.md`).
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Il t15 aveva guadagnato +0,037 raddoppiando l'ampiezza degli effetti da 0,197 a 0,394
([CP-0033](0033-t15-ampiezza-doppia.md)). Raddoppiarla ancora, a 0,788, con tutto il resto
invariato, alza ancora il punteggio?

## 2. Cosa è stato fatto

- **Ricetta** `configs/recipes/t16.json`: il t15 con ampiezza 0,788. Stesse sorgenti (K562,
  CD4 `cd4_mix`, Orion HCT116) a pesi uguali, effetti grezzi, γ 1, cache r4, generatore di
  trial-01.
- **Previsione e regola** registrate il 24 settembre alle 11:08 UTC, prima della generazione
  (`reports/prediction_t16_2026-09-24/prediction.json`): banda +0,08…+0,14; t16 − t15 fra
  −0,03 e +0,03; `pds_cosine` grezzo 0,76–0,80, fedeltà 0,47–0,51, `nmae` 0,92–0,98.
- **Generazione e pacchetto** con gli stadi 100, 45 e 48 il 24 settembre
  (`reports/trial_2026-09-24/t16_packaging.json`).
- **Invio** dalla catena `submit_chain.py` alle 00:06 UTC del 25, sha256 verificato prima;
  il server verifica l'md5 e pubblica alle 00:43 UTC (`reports/trial_2026-09-24/submit_t16_started.txt`,
  `submit_t16_raw.json`, entry `qUV1D6QZh2tZ5Z9Vx185`).

## 3. Cosa si è osservato

**Misurato — il punteggio.** **+0,137627**, rango 336 (era 436 col t15). È il nuovo migliore
del progetto: +0,030094 sul t15.

**Misurato — gli scalati pubblicati, e i grezzi derivati.** `vcc status` ha risposto
`not_found` per il t16 (e per il t15) il 25 settembre, servendo solo l'ultimo invio
(`reports/trial_2026-09-24/status_qUV1D6QZh2tZ5Z9Vx185_tentativo1_errore.txt`). I grezzi del
t16 sono quindi **derivati** dagli scalati con le ancore ufficiali; la stessa derivazione sul
t17 riproduce i grezzi pubblicati entro 0,00076 (`reports/prediction_t16_2026-09-24/comparison.json`).

| membro | grezzo t15 | grezzo t16 (derivato) | scalato t15 | scalato t16 | Δ scalato |
|---|---|---|---|---|---|
| `pds_cosine` | 0,7743 | 0,7780 | +0,607 | +0,617 | +0,009 |
| `de_wilcoxon_lfc_nmae` | 0,9503 | 0,9272 | +0,084 | +0,122 | +0,038 |
| fedeltà direzionale | 0,4769 | 0,5029 | −0,119 | −0,032 | +0,088 |
| `reach` | 0,1389 | 0,1744 | +0,067 | +0,107 | +0,040 |
| Jaccard | 0,0325 | 0,0348 | +0,006 | +0,012 | +0,006 |
| `mse` | 1,5794 | non derivabile | 0 | 0 | 0 |

**Misurato — rispetto alla previsione registrata.** Punteggio dentro la banda; t16 − t15 =
+0,0301, appena sopra il bordo +0,03 della banda della differenza; `pds_cosine`, fedeltà e
`nmae` dentro i loro intervalli.

**Misurato — rispetto al banco del 25 settembre.** Il modello del rumore del generatore di
`reports/banco_varianti_2026-09-25/` (commit `2308ee7`, scritto prima del punteggio) prevedeva
per il passaggio 0,394 → 0,788 un aumento del PDS proxy di +0,005…+0,026. Il `pds_cosine`
ufficiale è salito di +0,0037: sotto quell'intervallo. I bracci grezzi di quel modello non
dipendono dal difetto sull'SE di CD4 descritto in [CP-0039](0039-banco-varianti-restrizione.md).

## 4. Interpretazione e incertezza

**Esito della regola scritta prima:** t16 ≥ t15 + 0,005, quindi «la curva sale ancora: il
passo successivo raddoppia di nuovo» (ampiezza 1,576).

**Interpretazione:**
- **Il guadagno viene soprattutto dai membri DE:** fedeltà, `nmae`, `reach` e Jaccard fanno
  insieme +0,171 scalato, `pds_cosine` +0,009. Il PDS è vicino al suo plateau per l'ampiezza,
  come prevedeva il modello del banco; i membri DE no.
- **Fedeltà.** Lo scorer calcola k / max(chiamati, veri DE), con k = chiamati il cui segno
  coincide con quello vero, significativo o no ([CP-0039](0039-banco-varianti-restrizione.md)).
  Con più ampiezza cresce la quota di chiamate prodotte dagli effetti rispetto a quelle del
  generatore, e meno bersagli restano sotto il proprio numero di veri DE. Le chiamate del t16
  non sono state contate con lo stadio 83: è un'interpretazione, non una misura.
- La fedeltà grezza (0,503) resta sotto la linea di base 0,512: la precisione dei segni
  trasferiti è vicina al caso ([CP-0039](0039-banco-varianti-restrizione.md)).

**Incertezza:** un solo invio; nessun intervallo; l'ottimo dell'ampiezza non è noto e può non
valere per D/E/F. I grezzi del t16 sono derivati, con l'errore misurato sopra.

## 5. Spiegazione semplice

Abbiamo spinto le previsioni ancora il doppio. Il riconoscimento di quale gene è stato spento
migliora appena; migliora molto invece il numero di geni che il modello segnala come cambiati
con la direzione giusta, ed è lì che la classifica dava più punti.

## 6. Conseguenze

- **Il t16 è il nuovo riferimento** (+0,137627, rango 336).
- **Per la regola registrata il prossimo passo è l'ampiezza 1,576** sulla ricetta del t16, da
  registrare prima di generarlo (D-042).
- **Le varianti che cambiano la forma degli effetti** (la restrizione di CP-0039) vanno
  confrontate al t16, e devono muovere un numero di geni paragonabile: altrimenti possono
  perdere sui membri DE quello che guadagnano sul PDS.
- Per il set finale l'ampiezza resta un parametro da decidere con i dati di validazione.

## 7. Cosa corregge

Nessuna conclusione precedente. Aggiorna il riferimento di PROGETTO §0: il migliore è il t16.

## 8. Domanda di comprensione

Perché raddoppiare l'ampiezza può alzare di molto la fedeltà direzionale anche se la
precisione dei segni trasferiti non cambia?
