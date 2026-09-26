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

## Regola fissata alle 00:45 del 27/09, prima di eseguire il banco

- `share` **passa** se Δ è positivo su almeno tre delle quattro sorgenti tenute fuori, con l'intervallo sopra
  zero su almeno due, e nessuna sorgente ha l'intervallo interamente sotto −0,002.
- Se passa, il candidato **t23** è il t22 con la quota per gene stimata su tutti gli universi fuori dal pannello
  e la stessa scala a geni rilevabili per contesto; richiede codice nello stadio 100, una previsione registrata
  prima della generazione e il via del proprietario all'invio.
- Se non passa, la quota per gene è chiusa per il trasferimento e il t22 resta il riferimento.
