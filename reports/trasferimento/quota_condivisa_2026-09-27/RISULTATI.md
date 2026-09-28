# Quota condivisa per gene, sul pannello: il braccio più vicino dell'atlante, provato dove conta

27 settembre 2026, notte. Seguito del banco dell'[atlante](../atlante_2026-09-26/RISULTATI.md) nella scheda
[R-V2](../../docs/piani/modello-v2.md). **Proxy contro sorgenti pubbliche tenute fuori, non punteggi VCC.**

## Perché, e con quale cautela

Nell'atlante r1 nessun braccio ha passato la regola. Il più vicino è stato `share_atlas`: la parte trasferita
del t22 moltiplicata, gene per gene, per σ²/(σ² + τ²), la quota della risposta che le linee condividono,
stimata sugli universi genome-wide fuori dal pannello; +0,008 e +0,009 con l'intervallo sopra zero con CD4 e
HCT116 tenuti fuori, −0,0002 con K562 tenuto fuori. Questa è un'**ipotesi nuova suggerita da quel
quasi-passaggio**, non una rilettura di r1: la si prova su bersagli che l'atlante non ha mai usato (i 300 del
pannello, esclusi da ogni stima), con una regola fissata prima, e la si legge sapendo che è stata scelta dopo
aver visto r1.

## Il banco (`share_panel_bench.py`)

Per ogni sorgente del t22 tenuta fuori (K562, CD4, HCT116, HEK293T; la sua famiglia esclusa da tutto, quindi
una linea Orion fuori lascia K562 e CD4):
- la quota per gene viene dagli universi delle altre famiglie (K562, CD4, HCT116; HEK293T non è ancora
  completo), su al più 6.000 bersagli fuori dal pannello misurati in almeno due, con il codice dell'atlante;
  niente della sorgente tenuta fuori;
- `t22like`: la forma del t22 sulla cache del pannello (media a pesi uguali delle sorgenti del t22 meno la
  famiglia tenuta fuori, gamma 1, × 1,576, testa cis);
- `share`: la parte trasferita per la quota, riportata alla mediana di geni rilevabili di `t22like`, più la
  stessa testa cis (lo stesso braccio di r1);
- misure come il banco a [quattro sorgenti](../quattro_sorgenti_2026-09-26/RISULTATI.md), Δ = 0,36 × ΔPDS_gen
  − 0,27 × ΔnMAE_gen, bootstrap appaiato sui bersagli del pannello.

## Regola fissata prima di eseguire il banco

Scritta prima del lancio e pubblicata alle 00:25 del 27/09 (commit a434379), prima di qualunque risultato. La prima versione diceva «00:45»: un orario stimato invece che letto, corretto qui con quello del commit; il testo della regola non è cambiato.

- `share` **passa** se Δ è positivo su almeno tre delle quattro sorgenti tenute fuori, con l'intervallo sopra
  zero su almeno due, e nessuna sorgente ha l'intervallo interamente sotto −0,002.
- Se passa, il candidato **t23** è il t22 con la quota per gene stimata su tutti gli universi fuori dal pannello
  e la stessa scala a geni rilevabili per contesto; richiede codice nello stadio 100, una previsione registrata
  prima della generazione e il via del proprietario all'invio.
- Se non passa, la quota per gene è chiusa per il trasferimento e il t22 resta il riferimento.

## r1: esito (misurato, 27/09 alle 00:51)

Uscite in `r1/` (`summary.csv`, `measurements.json`, la quota usata per ogni sorgente tenuta fuori in
`share_<sorgente>.npy`). Δ = 0,36 × ΔPDS_gen − 0,27 × ΔnMAE_gen di `share` contro `t22like`:

| Tenuta fuori | Bersagli | Δ | Intervallo 95 % | ΔPDS (effetti) | Energia rispetto a `t22like` |
|---|---|---|---|---|---|
| K562 | 271 | −0,0015 | −0,0067…+0,0040 | +0,000 | 0,59 |
| CD4 | 292 | +0,0122 | +0,0053…+0,0189 | +0,038 | 0,35 |
| HCT116 | 265 | +0,0045 | −0,0033…+0,0122 | +0,020 | 0,42 |
| HEK293T | 278 | +0,0129 | +0,0049…+0,0212 | +0,051 | 0,42 |

**Lettura con la regola: passa.** Δ positivo su tre sorgenti su quattro, intervallo sopra zero su due (CD4 e
HEK293T), nessuna sorgente con l'intervallo interamente sotto −0,002 (K562 arriva a +0,004). La quota
mediana per gene è 1 in ogni prova; i geni sotto 0,5 sono il 24 % (varianze senza K562), 16 % (senza CD4)
e 9–10 % (senza le Orion). Candidato **t23**, come dice la regola.

- **Misurato:** il guadagno viene dalla discriminazione (PDS nello spazio degli effetti +0,02…+0,05 dove passa),
  con l'nMAE quasi fermo; a parità di geni rilevabili l'energia scende a 0,35–0,59 di quella di `t22like`.
- **Cautela:** l'ipotesi è stata scelta dopo aver visto l'atlante r1; il pannello è indipendente dall'atlante,
  ma il risultato va letto come una prima conferma, non come una misura definitiva. Proxy, non punteggi VCC.
