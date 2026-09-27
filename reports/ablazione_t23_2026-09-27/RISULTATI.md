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
