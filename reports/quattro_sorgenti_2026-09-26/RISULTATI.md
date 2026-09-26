# Quattro sorgenti genome-scale invece di tre: il t20 con HEK293T

26 settembre 2026, pomeriggio. Filone della scheda [R-V2](../../docs/piani/modello-v2.md), dopo che il
canale di magnitudine appreso ([r5](../trasferimento_appreso_2026-09-26/RISULTATI.md)) e il trasferimento
gerarchico ([EB](../trasferimento_gerarchico_2026-09-26/RISULTATI.md)) non hanno passato le loro regole, e
su indicazione del proprietario: usare molti dati insieme. **Proxy contro sorgenti pubbliche tenute fuori,
non punteggi VCC.**

## La prova

Il t20 media K562, CD4 e HCT116. HEK293T (X-Atlas/Orion, stesso studio di HCT116) copre 281 bersagli
del pannello e non c'è. `four_sources_bench.py` confronta, sulle sorgenti tenute fuori che lasciano come
ingressi entrambe le linee Orion (K562 e CD4), la forma del t20 con tre ingressi (`t20like_3`) e con
quattro: `hek_equal` (HEK293T a peso 1) e `hek_half` (le due linee Orion a 0,5 ciascuna, un peso per
studio). Stessi bersagli per tutti i bracci; proxy come r5.

## Regola fissata alle 15:30 del 26/09, prima di eseguire il banco

Su K562 e CD4 tenuti fuori, Δ = 0,36 × ΔPDS_gen − 0,27 × ΔnMAE_gen contro `t20like_3`, con intervallo
bootstrap appaiato sui bersagli. Un braccio passa se Δ > 0 su entrambe, con l'intervallo sopra zero su
almeno una, e nessuna sotto −0,002. Fra i bracci che passano, il candidato t22 è quello con il Δ medio
più alto; la ricetta è quella del t20 con le stesse aggiunte di HEK293T.
