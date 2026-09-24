# Banco a sorgente esclusa: varianti della ricetta del t15, prima di spendere invii

25 settembre 2026, notte. **Proxy nello spazio degli effetti su sorgenti pubbliche, non
punteggi VCC.** Per ogni sorgente tenuta fuori (K562, CD4 `cd4_mix`, Orion HCT116, Orion
HEK293T) gli effetti del pannello si prevedono dalle sorgenti delle **altre famiglie**
(le due linee Orion non si predicono fra loro) con `vcc2026.multisource.mix`, come fa lo
stadio 100; la sorgente esclusa fa da verità con i suoi effetti grezzi. Cache
`processed/multisource_2026-09-23_r5`, hash negli output.

## I due proxy, e perché questi

Le note interne dello scorer installato (`cell_eval2` 0.16.0) dicono come si calcolano i
membri; da lì:
- **PDS proxy.** `pds_cosine` confronta il delta pseudobulk previsto con i delta veri di tutti
  i bersagli, per coseno, nello spazio `log1p` dei pseudobulk normalizzati a 5·10⁴
  (`bulk_target_sum` in `configs/vcc2026.yaml` del pacchetto), con tutti i 300 geni del
  pannello esclusi, e dà 1 − rango/(n − 1). Il proxy fa lo stesso sugli effetti, con il peso
  x/(1 + x) che quel `log1p` dà a un effetto piccolo (x = 0,05 × CPM del contesto ufficiale).
- **Proxy della fedeltà.** Lo scorer conta k = geni chiamati il cui segno coincide con quello
  vero, **che il gene vero sia significativo o no**, e divide per max(chiamati, veri DE). Il
  proxy prende i primi N geni per |effetto previsto| fra quelli ≥ 5 CPM nel contesto (il
  filtro DE dello scorer) e misura la quota di segni giusti.

**Misurato dagli organizzatori, nelle note dello scorer** (`competition.py`, `metrics/de.py`,
`metrics/direction.py`): sul pannello val A ci sono 102.786 coppie bersaglio–gene
significative (circa 340 per bersaglio, in media); il 12–30% dei bersagli ha meno di 10 geni
DE e il 46–61% meno di 40; un invio che incolla i controlli ha fedeltà 0,001, quindi quasi
nessun bersaglio ha zero geni DE e il silenzio non paga.

## Risultati

**1. Varianti del mix (`analyze.py`, `r1/`).** Media sui pesi di A, B e C.

| Sorgente esclusa | t15 (grezzi, γ 1) | ristretti k 4 (cache) | γ 0 | consenso | bersagli rimescolati |
|---|---|---|---|---|---|
| CD4 | 0,668 | 0,681 | 0,662 | 0,666 | 0,501 |
| K562 | 0,756 | 0,777 | 0,753 | 0,757 | 0,455 |
| HCT116 | 0,688 | 0,701 | 0,681 | 0,688 | 0,505 |
| HEK293T | 0,658 | 0,674 | 0,657 | 0,658 | 0,496 |

La precisione dei segni sui primi 200 geni resta fra 0,506 e 0,533 in ogni variante, contro
~0,50 con i bersagli rimescolati. In spazio effetti i primi 800 geni sono "su" per il 41–51%:
lo sbilanciamento all'81–86% delle chiamate del t15 viene dal generatore, non dagli effetti.

**2. Forza della restrizione (`shrink_sweep.py`, `r2/`).** Effetto = grezzo × z²/(z² + k),
z = grezzo/SE. Guadagno del PDS proxy sui grezzi:

| Sorgente esclusa | k 1 | k 4 | k 16 | k 64 | k 4, media a varianza inversa |
|---|---|---|---|---|---|
| CD4 | +0,007 | +0,014 | +0,023 | +0,030 | −0,001 |
| K562 | −0,011 | +0,008 | +0,028 | +0,041 | 0,000 |
| HCT116 | +0,026 | +0,047 | +0,070 | +0,083 | +0,044 |
| HEK293T | +0,069 | +0,090 | +0,111 | +0,123 | +0,093 |

**3. Filtro dei bersagli difficili (`gating.py`, `r3/`) — respinto.** Il PDS proxy per
bersaglio è coerente fra sorgenti escluse diverse (Spearman 0,46–0,70 in `r1/`), e il 20–30%
dei bersagli sta sotto 0,5. Una stima annidata, che non vede la sorgente esclusa, lo prevede
solo in parte (Spearman 0,33–0,42). Azzerare i bersagli stimati sotto soglia **fa perdere**
PDS, o lo lascia uguale, in tutte le sorgenti e a ogni soglia 0,3–0,6 (fra 0,000 e −0,087):
molti bersagli stimati male si trasferiscono comunque sopra 0,5.

**4. Con il rumore del generatore (`noise_sim.py`, `r4/`).** Il delta previsto passa per un
modello del generatore: rumore di Poisson della media di 400 cellule a 20.000 UMI, poi il
`log1p` a 5·10⁴. È un **modello**: ignora sovradispersione, dimensioni di libreria e
l'eccesso di zeri che produce le chiamate Wilcoxon.

| Sorgente esclusa | grezzi 0,197 | 0,394 (t15) | 0,788 (t16) | 1,576 | k 16, q99 del t15 | k 64, q99 del t15 |
|---|---|---|---|---|---|---|
| CD4 | 0,636 | 0,656 | 0,661 | 0,660 | 0,678 | 0,682 |
| K562 | 0,664 | 0,713 | 0,739 | 0,745 | 0,740 | 0,755 |
| HCT116 | 0,637 | 0,664 | 0,675 | 0,674 | 0,712 | 0,722 |
| HEK293T | 0,617 | 0,638 | 0,646 | 0,643 | 0,712 | 0,718 |

- **Calibrazione:** da 0,197 a 0,394 il proxy sale di +0,020…+0,049; il `pds_cosine` ufficiale
  da t11 a t15 è salito di +0,035. Stesso verso e stesso ordine di grandezza.
- **Previsione per il t16** (registrata qui prima del suo punteggio): il proxy sale ancora di
  +0,005…+0,026 da 0,394 a 0,788, e si ferma oltre.
- **Ristretti con k 64 all'ampiezza che dà il q99 del t15** (0,229): +0,026 / +0,042 / +0,058 /
  +0,080 sul t15, e sopra anche ai grezzi alla loro ampiezza migliore. Raddoppiare quel q99 non
  aggiunge nulla.

## Interpretazione e limiti

- **Interpretazione:** negli effetti delle sorgenti la maggior parte dei geni è rumore (il
  mediano |Δ|/SE sta sotto 1, `docs/PROGETTO.md` §3), e il coseno sui grezzi ne è dominato;
  restringere verso zero gli effetti poco sostenuti rende più riconoscibile ogni bersaglio.
- **Non dimostrato:** che il guadagno arrivi al punteggio ufficiale. La verità qui è una
  sorgente pubblica rumorosa, non A/B/C; gli altri membri (chiamate, `nmae`, `reach`,
  fedeltà) dipendono dalla forma degli effetti ristretti, che il proxy non misura.
- La precisione dei segni resta vicina al caso in ogni variante: la fedeltà non si risolve
  cambiando il mix, ma solo con previsioni di segno migliori.
- Confronti esplorativi multipli, senza intervalli; tre semi di rumore in `r4/`.

## Proposta

Registrare come prossimo candidato la ricetta migliore letta dopo t16 e t17, con gli effetti
ristretti a k 64 al posto dei grezzi e l'ampiezza scelta con la regola del q99, un fattore
alla volta. Serve un'opzione nuova dello stadio 100 (oggi legge solo `raw` o lo `shrunk` della
cache, che per le sorgenti pseudobulk non coincide con k 4 ricalcolato). La soglia di lettura
va scritta prima del punteggio.

Riproduzione: `scripts/py.cmd reports/banco_varianti_2026-09-25/<script>.py --out <cartella nuova>`.
