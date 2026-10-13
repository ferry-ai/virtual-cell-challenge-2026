# Dove sta il margine del punteggio: otto prove sul banco del cubo

13 ottobre 2026, 22:30–23:45 CEST. Claude Code per Alfredo, che ha chiesto in chat di staccarsi dalle ipotesi che ci
tengono bloccati, di usare i dati rielaborati da Davide e di mandare a valutare quello che ha senso.

**Tipo di affermazioni:** misure sul banco del cubo r2 (5 linee tenute fuori, codice di
[guadagno.py](../../modelli/guadagno_appreso_2026-10-05/guadagno.py)). **Non sono punteggi VCC.** I membri DE sono
**proxy nello spazio degli effetti**:
- chiamata se |E| ≥ 0,2 su un gene espresso (CPM ≥ 5);
- verità significativa se |y/se| ≥ 3;
- fedeltà = k / max(n_pred, n_conf), con le definizioni di `cell_eval2` 0.16.0
  (`metrics/direction.py`).

I valori sono nella cartella dei dati, `processed/<nome>_2026-10-13/result.json`.

## Da dove si parte (misurato sul sito e nello scorer)

**Ancore:** `reports/gara/anchors_2026-09-17/anchors.json`. Fotografia delle prime dieci squadre del 16/09:
`reports/gara/leaderboard_2026-09-16/snapshot.md`.

**Il distacco dalle prime dieci sta in MSE e PDS, non nei membri DE:**

| Membro scalato | Prime dieci | `ta 40` |
|---|---|---|
| MSE | 0,15–0,35 | 0 (grezzo 5,7) |
| PDS | 0,72–0,83 | 0,59 |
| nMAE | 0,12–0,28 | 0,08 |
| fedeltà e Jaccard | circa 0,01 | circa 0,01 |

**Dall'MSE normalizzato** (1,0 = prevedere il controllo; la media del contesto vale 0,986, quindi la parte comune è
l'1,4% dell'energia):
- `ta 36` e `ta 38` differiscono solo per l'ampiezza;
- risolvendo 1 − 2cρ + ρ² sui due grezzi si ottiene un **coseno aggregato c ≈ 0,10** e una norma 2,15 volte quella
  vera;
- l'MSE premia solo sotto 0,986, cioè con c ben sopra 0,1: le prime dieci hanno grezzi 0,65–0,85, che corrispondono a
  un coseno di circa 0,4–0,6.

## Le prove (rispetto alla previsione densa di oggi, `all` × 1,576 × 1,5)

| Prova (script) | Idea | Esito sul banco |
|---|---|---|
| [soglia_banco.py](soglia_banco.py) | Chiamiamo troppi geni: tenere solo gli effetti forti | **No.** La verità ha molti geni significativi (mediana 585 per bersaglio, da 96 su K562 a 2.087 su H1). Con soglia 0,5: fedeltà 0,51 → 0,28, Jaccard 0,071 → 0,042, PDS 0,780 → 0,681 |
| [denoise_banco.py](denoise_banco.py) | Ridurre il rumore proiettando sui programmi condivisi (SVD) o contraendo per errore standard | **No.** Rango 20: PDS 0,780 → 0,559. Contrazione: PDS 0,771. L'informazione specifica del bersaglio sta fuori dai programmi |
| [deflate_banco.py](deflate_banco.py) | L'opposto: togliere i primi r programmi condivisi | **No.** r = 1: PDS 0,760; r = 5: 0,714 |
| [ampiezza_banco.py](ampiezza_banco.py) | Ampiezza globale e per bersaglio | **Taratura superata:** da 1,0 a 1,5 riproduce i segni del sito (fedeltà su; nMAE +0,026 contro +0,027 sul sito). Ampiezza 2,0: fedeltà +0,024, nMAE +0,054, quindi circa −0,006 stimato sul sito. Ampiezza per bersaglio ∝ norma: peggio su tutto |
| [tetto_banco.py](tetto_banco.py), [testa_tetto_banco.py](testa_tetto_banco.py) | Tetto sulle magnitudini: le chiamate restano, gli errori grandi di segno costano meno nMAE | Tetto 1,0: nMAE 0,970 → 0,957, PDS 0,780 → 0,775; fedeltà, Jaccard e reach invariati. **Unica prova con valore atteso positivo, circa +0,002 sul sito** |
| [testa_banco.py](testa_banco.py) | Mettere in testa i geni su cui le sorgenti concordano (per il reach) | Reach 0,138 → 0,150, ma nMAE e fedeltà peggiorano: circa −0,004 stimato |
| [affini_banco.py](affini_banco.py) | «Un voto per lignaggio»: solo i gruppi sorgente col basale più simile | **No, e in modo monotono:** PDS 0,594 con 1 gruppo, 0,694 con 2, 0,762 con 5, **0,780 con tutti**. Più sorgenti sono meglio |
| [ivw_banco.py](ivw_banco.py) | Combinare i gruppi con l'inverso della varianza (effetti casuali) | Pari o peggio: PDS 0,775 |

## Che cosa se ne ricava (interpretazione)

1. **La direzione densa del transfer è un ottimo locale** per tutte le trasformazioni semplici provate, e
   l'emissione di `td 28` è vicina al suo ottimo d'ampiezza. Le leve di emissione valgono ±0,005 al più.
2. **Il margine grande** (MSE e PDS delle prime dieci) **richiede una direzione migliore.** Il banco indica una sola
   leva con pendenza chiara: **più dati sorgente** (1 → 9 gruppi: PDS da 0,59 a 0,78).
3. **Ne segue la proposta** (non eseguita): la rete centrata di `ta 40` sopra la banca estesa di Davide, cioè la base
   di `td 38`, che ha più fonti di questo cubo. Gli effetti di quella banca stanno nei dataset Kaggle privati di Davide
   e non sono su questo PC.
4. **Le ipotesi di partenza smentite stasera,** da non riaprire senza un dato nuovo:
   - «chiamiamo troppi geni»: sul banco la verità ne ha centinaia, e sul sito il calo di fedeltà di `ta 38` dice lo
     stesso;
   - «il segnale è rumoroso»;
   - «un voto per lignaggio».

## Invio

`ta 41` = `ta 40` con il tetto a 1,0
([previsione e regola](../../invii/prediction_ta41_2026-10-13/prediction.json),
[esporta_tetto.py](esporta_tetto.py)). Inviato perché il proprietario ha chiesto un tentativo valutato. L'effetto
atteso è piccolo, dell'ordine del rumore di seme. La lettura per membro (nMAE contro PDS) serve a tarare il banco
sulle magnitudini.

Lo script [soglia_effetti.py](soglia_effetti.py) e la modalità `lowrank`/`deflate` di
[esporta_lowrank.py](esporta_lowrank.py) restano come record: sono stati preparati e mai usati per un invio, perché
il banco li ha bocciati.
