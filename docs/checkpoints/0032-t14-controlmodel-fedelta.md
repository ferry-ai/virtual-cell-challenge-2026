# CP-0032 — Il t14 in classifica: +0,065; ControlModel all'ampiezza scelta per le chiamate è non attribuibile per la sua regola, e la fedeltà scende invece di salire

- **Data:** 2026-09-24
- **Tipo:** esperimento
- **Redatto da:** agente (Claude Opus 5.5)
- **Revisione umana:** no. Esecuzione sul portatile e invio autorizzati dal proprietario in chat,
  il 23 settembre.
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Con gli stessi effetti del t08, sostituire il generatore di trial-01 con `ControlModel`,
all'ampiezza che produce abbastanza chiamate, migliora il punteggio ufficiale? E in
particolare la fedeltà direzionale, che in tutti gli invii precedenti è rimasta sotto la base?

## 2. Cosa è stato fatto

- **Regola** scritta prima dei piloti: `reports/dispersion_2026-09-23/PRIMA_T14.md`.
- **Sede.** Per scelta del proprietario il lavoro è girato sul portatile invece che su Colab
  (`reports/dispersion_2026-09-23/T14_IN_LOCALE.md`). I job 044 e 045 sono stati tolti dalla
  coda.
- **Piloti** su 20 bersagli per contesto (`reports/dispersion_2026-09-23/t14_pilots/`):
  - a effetto nullo 0 chiamate mediane in A, B e C;
  - la regola sceglie l'ampiezza 2,5.
- **Effetti:** quelli del t08. Il punto 2 della regola li avrebbe cambiati con quelli del t11
  solo se il t11 avesse vinto prima dell'avvio del job. Il job è partito alle 18:00Z, il t11 è
  stato pubblicato alle 18:25Z.
- **Previsione registrata prima** della generazione completa
  (`reports/prediction_t14_2026-09-23/prediction.json`):
  - banda +0,02…+0,12;
  - fedeltà grezza attesa 0,48–0,58;
  - regola di lettura contro il t08.
- **Generazione** con lo stadio 76: 360.000 cellule in 35 minuti
  (`reports/trial_2026-09-23/t14_generation.json`). Lo stadio 83 conta 136,5 / 213 / 218
  chiamate mediane in A / B / C, per il 43–52% «in su»
  (`reports/prediction_calls_2026-09-23/t14/`).
- **Impacchettamento** con lo stadio 48 (`reports/trial_2026-09-23/t14_packaging.json`), dopo
  aver liberato disco con l'autorizzazione del proprietario
  (`reports/trial_2026-09-22/autorizzazioni.md`).
- **Invio** alle 00:05Z del 24 settembre. Il server verifica l'md5 e pubblica alle 00:35Z. Output
  verbatim in `reports/trial_2026-09-23/submit_QiuBir8wNfqDnVdDxqTB.json` e
  `status_QiuBir8wNfqDnVdDxqTB.json`.

## 3. Cosa si è osservato

**Misurato — il punteggio.** **+0,064892**, rango 564, entry `QiuBir8wNfqDnVdDxqTB`,
dentro la banda registrata. Il t08 aveva +0,060370, il t11 +0,070777.

**Misurato — i sei grezzi** (`reports/prediction_t14_2026-09-23/comparison.json`):

| membro | t08 | t11 | t14 | t14 − t08 | scalato t08 | scalato t14 |
|---|---|---|---|---|---|---|
| `pds_cosine` | 0,7103 | 0,7392 | 0,6827 | −0,0276 (peggio) | +0,466 | +0,402 |
| `expr_mse_unbiased_capped_norm` | 1,1524 | 1,1290 | 2,1298 | +0,9775 (peggio) | 0 (tosato) | 0 (tosato) |
| `de_wilcoxon_lfc_nmae` | 0,9774 | 0,9774 | 0,9384 | −0,0391 (meglio) | +0,039 | +0,103 |
| fedeltà direzionale | 0,4594 | 0,4582 | 0,4473 | −0,0121 (peggio) | −0,178 | −0,217 |
| `reach` | 0,1099 | 0,1129 | 0,1871 | +0,0773 (meglio) | +0,035 | +0,121 |
| Jaccard | 0,0304 | 0,0298 | 0,0233 | −0,0070 (peggio) | −0,000 | −0,020 |

**Misurato — la fedeltà grezza è 0,4473.** È sotto l'intervallo previsto (0,48–0,58) e sotto il
t08 (0,4594).

**Misurato — le ancore reggono su un settimo punto.** Riproducono gli scalati pubblicati con uno
scarto massimo di 0,0016 (stesso file, campo `anchor_check_on_t14`).

## 4. Interpretazione e incertezza

**Esito della regola scritta prima.** t14 − t08 = +0,0045, dentro ±0,005:
**non attribuibile**.

**Descrizione, non verdetto.** Rispetto al t08 il cambio di generatore e di ampiezza:
- **perde** in `pds_cosine` (−0,028 grezzo), in Jaccard e in fedeltà;
- **guadagna** in `nmae` e in `reach`.

I saldi quasi si compensano.

**Contraddetto — la fedeltà non è governata dalle sole chiamate spurie del generatore.**
[CP-0029](0029-t08-punteggio-ufficiale.md) §4 lo leggeva così, e la mappa ne traeva che si
sarebbe spostata cambiando il generatore. Qui le chiamate spurie sono quasi zero, e quelle
rimaste seguono gli effetti previsti; la fedeltà però scende. Due letture restano aperte, e i
dati aggregati non le separano:
- sui geni che chiamiamo, il segno dei nostri effetti trasferiti concorda con i contesti
  ufficiali meno della metà delle volte;
- con meno chiamate dei geni veri di molti bersagli, la fedeltà vale `k / n_conf` e paga il
  silenzio, come prevede D-035. Il nostro `n_conf` per bersaglio non è osservabile.

**Incertezza:**
- rispetto al t08 sono cambiati due fattori insieme, generatore e ampiezza;
- un solo invio, senza intervallo;
- il t14 non usa Orion.

## 5. Spiegazione semplice

Abbiamo cambiato il modo di fabbricare le cellule, usando un modello che imita le cellule di
controllo senza inventare differenze. Abbiamo anche alzato l'intensità degli effetti, finché il
confronto con i controlli mostrava abbastanza geni cambiati.

Il voto è quasi quello di prima: 0,065 contro 0,060. Andiamo meglio nell'indovinare quanto
cambiano i geni, peggio nel distinguere un gene spento dall'altro. La direzione dei cambiamenti
non migliora: il problema non era solo il rumore del vecchio generatore.

## 6. Conseguenze

- **Il t11 resta il riferimento** (+0,070777).
- **La leva della fedeltà non è il solo generatore.** L'ipotesi «generatore pulito, fedeltà
  migliore» non è sostenuta. Un candidato `ControlModel` con gli effetti del t11 perde priorità,
  perché paga in `pds_cosine`.
- **Il t15 separa l'ampiezza.** È il t11 con ampiezza doppia e con il generatore di trial-01.
  Mostrerà se `nmae` e `reach` salgono anche lì, e se `pds_cosine` regge.
- **La direzione degli effetti diventa la domanda.** Serve una misura del segno degli effetti
  trasferiti sui geni chiamati, per bersaglio: nello spazio degli effetti fra sorgenti, e con
  i banchi su cellule vere.

## 7. Cosa corregge

- [CP-0029](0029-t08-punteggio-ufficiale.md) §4, l'interpretazione «[la fedeltà] è governata
  dalle chiamate spurie del generatore»: senza chiamate spurie la fedeltà scende.
- La mappa (`docs/PROGETTO.md` §0) diceva che in questa famiglia la fedeltà si sposta cambiando
  il generatore: si è spostata, ma verso il basso.

## 8. Domanda di comprensione

Perché togliere centinaia di chiamate sbagliate può abbassare la fedeltà invece di alzarla?
