# Il t23 smontato: esclusione dei geni, pesatura per gene e riscalatura, una contro l'altra

27 settembre 2026, pomeriggio. Nella scheda [R-V2](../../docs/piani/modello-v2.md), su richiesta della revisione
di codex girata dal proprietario: il t23 mescola più cose, e il banco che lo ha prodotto le confrontava tutte
insieme con il t22. **Proxy contro sorgenti pubbliche tenute fuori, non punteggi VCC.**

## Perché

Il t23 moltiplica, gene per gene, la parte trasferita del t22 per la quota condivisa σ²/(σ² + τ²), poi
riporta il risultato alla mediana di geni rilevabili del t22. Dei 18.533 geni, 8.247 hanno quota 0 perché gli
universi non li sanno stimare, 8.395 hanno quota 1 e 1.891 stanno in mezzo. Il t23 è quindi tre operazioni:
- un'**esclusione** dei geni non stimabili (fra questi i sei geni Y dell'[artefatto del
  pseudoconteggio](../pseudoconteggio_2026-09-27/RISULTATI.md));
- una **pesatura** degli altri;
- una **riscalatura**.

Il [banco sul pannello](../quota_condivisa_2026-09-27/RISULTATI.md) (r1) ha confrontato solo l'insieme con il
t22. Un guadagno del t23 non direbbe quale parte ha funzionato, e non confermerebbe il meccanismo biologico.

## Il banco (`ablation_bench.py`)

Stesso codice di `share_panel_bench.py`: stesse quote, ricalcolate come in r1 e confrontate con quelle salvate;
stessa testa cis, stessi proxy, stessi semi. Cinque bracci per ogni sorgente tenuta fuori:
- `t22like`, la forma del t22;
- `excl`: la parte trasferita con i geni a quota 0 azzerati e tutti gli altri a 1, riscalata ai geni
  rilevabili di `t22like`;
- `excl_noscale`: la stessa esclusione, non riscalata;
- `share`: il braccio del t23 (pesatura, riscalata);
- `share_noscale`: la pesatura non riscalata.

Il Δ è sempre 0,36 × ΔPDS_gen − 0,27 × ΔnMAE_gen, con bootstrap appaiato sui bersagli del pannello. Oltre al
confronto di ogni braccio con `t22like` ci sono tre confronti diretti: `share` − `excl`, `share` −
`share_noscale` ed `excl` − `excl_noscale`.

## Regola fissata prima di eseguire il banco

Un confronto **passa** con la regola del banco sul pannello: Δ positivo su almeno tre delle quattro sorgenti
tenute fuori, intervallo sopra zero su almeno due, nessuna sorgente con l'intervallo interamente sotto −0,002.
Il suo **contrario passa** con la stessa regola a segni invertiti.

- **r1**, sulla cache r5 (quella su cui è costruito il t23) e con gli universi di r1 (K562, CD4, HCT116).
  Replica: `share` contro `t22like` deve dare gli stessi Δ puntuali di r1 del banco sul pannello; se non li
  dà, il banco è sbagliato e non si legge.
- **Esclusione:** `excl` contro `t22like`.
- **Pesatura oltre l'esclusione:** `share` contro `excl`.
- **Riscalatura:** `share` contro `share_noscale` ed `excl` contro `excl_noscale`.

Che cosa se ne fa:
- se l'esclusione passa e la pesatura oltre l'esclusione no, i prossimi candidati usano la sola esclusione
  (il modello più semplice), e l'esito ufficiale del t23, se arriva, si legge come esito soprattutto
  dell'esclusione;
- se la pesatura oltre l'esclusione passa, la pesatura per gene ha un sostegno suo sui proxy;
- per la riscalatura vale il verso che passa; se non passa nessuno dei due, la scelta resta aperta.

**r2**, sulla cache r9 corretta e con gli stessi universi (ancora con il pseudoconteggio costante), è una
replica: dice se lo schema regge senza l'artefatto nelle sorgenti del pannello, e non cambia la lettura di r1.

## r1: esito (misurato, 27/09 alle 14:56)

Uscite in `r1/` (`summary.csv`, `measurements.json`). Replica superata: le quote ricalcolate sono identiche a
quelle salvate da r1 del banco sul pannello per tutte e quattro le sorgenti tenute fuori, e `share` contro
`t22like` ridà esattamente i suoi Δ (−0,0015, +0,0122, +0,0045, +0,0129). Δ = 0,36 × ΔPDS_gen − 0,27 ×
ΔnMAE_gen, intervallo bootstrap appaiato al 95 %:

| Confronto | K562 fuori | CD4 fuori | HCT116 fuori | HEK293T fuori |
|---|---|---|---|---|
| `excl` − `t22like` | +0,0042 (+0,001…+0,007) | +0,0138 (+0,007…+0,020) | +0,0053 (−0,002…+0,012) | +0,0131 (+0,006…+0,020) |
| `share` − `excl` | −0,0058 (−0,011…−0,001) | −0,0016 (−0,004…+0,000) | −0,0008 (−0,004…+0,002) | −0,0002 (−0,003…+0,003) |
| `share` − `share_noscale` | +0,0037 (+0,001…+0,006) | −0,0018 (−0,003…−0,000) | −0,0075 (−0,011…−0,004) | −0,0078 (−0,010…−0,005) |
| `excl` − `excl_noscale` | +0,0008 (−0,000…+0,002) | −0,0021 (−0,003…−0,001) | −0,0066 (−0,009…−0,004) | −0,0072 (−0,009…−0,005) |
| `excl_noscale` − `t22like` | +0,0034 (+0,001…+0,006) | +0,0159 (+0,009…+0,023) | +0,0119 (+0,005…+0,019) | +0,0203 (+0,013…+0,028) |

**Lettura con la regola:**
- **Esclusione: passa.** Δ positivo su quattro sorgenti su quattro, intervallo sopra zero su tre, nessuno sotto
  −0,002. Aiuta anche con K562 fuori, dove il t23 intero non aiutava.
- **Pesatura oltre l'esclusione: non passa**, e non passa nemmeno il suo contrario (negativa su quattro, ma con
  l'intervallo sotto zero solo per K562).
- **Riscalatura: passa il contrario**, per entrambi i bracci: riscalare ai geni rilevabili del t22 peggiora il proxy
  con CD4, HCT116 e HEK293T fuori.

Che cosa ne segue per la regola: i prossimi candidati usano la sola esclusione dei geni non stimabili, e un esito
ufficiale del t23, se arriva, si legge come esito soprattutto dell'esclusione. Sulla riscalatura la regola dice di
non riscalare.

**Cautele:**
- **Interpretazione:** quello che aiuta è togliere gli 8.247 geni che meno di due universi sanno stimare: segnali di
  una sola sorgente, fra cui i geni Y dell'[artefatto](../pseudoconteggio_2026-09-27/RISULTATI.md). Non la quota
  condivisa come meccanismo.
- Il proxy non vede i membri DE del punteggio (portata, fedeltà, Jaccard), e sul punteggio ufficiale alzare
  l'ampiezza ha sempre aiutato (t15 → t16). La preferenza per il non riscalare vale per questo proxy: prima di
  guidare un candidato va messa alla prova ufficiale o su un banco con lo scorer completo.

## r2: replica sulla cache r9 (misurato, 27/09 pomeriggio)

Uscite in `r2/`. Stesse quote (identiche alle salvate), cache del pannello r9 con lo stimatore corretto.

| Confronto | K562 fuori | CD4 fuori | HCT116 fuori | HEK293T fuori |
|---|---|---|---|---|
| `excl` − `t22like` | +0,0044 (+0,002…+0,007) | +0,0153 (+0,009…+0,021) | +0,0041 (−0,003…+0,011) | +0,0143 (+0,007…+0,022) |
| `share` − `excl` | −0,0059 (−0,011…−0,001) | −0,0021 (−0,004…−0,000) | −0,0006 (−0,004…+0,002) | −0,0002 (−0,003…+0,003) |
| `share` − `share_noscale` | +0,0030 (+0,001…+0,005) | −0,0020 (−0,004…−0,001) | −0,0072 (−0,010…−0,005) | −0,0078 (−0,010…−0,005) |
| `excl_noscale` − `t22like` | +0,0038 (+0,001…+0,006) | +0,0175 (+0,012…+0,024) | +0,0107 (+0,004…+0,017) | +0,0215 (+0,014…+0,028) |

La replica conferma r1: l'esclusione guadagna sulle quattro sorgenti; la pesatura oltre l'esclusione è negativa sulle
quattro, e qui con l'intervallo sotto zero per K562 e CD4; riscalare peggiora il proxy con tre sorgenti su quattro.
**Misurato in più:** il guadagno dell'esclusione resta uguale con le sorgenti del pannello corrette, quindi non viene
solo dall'artefatto dei geni Y. **Interpretazione:** aiuta togliere i segnali che una sola sorgente misura.
