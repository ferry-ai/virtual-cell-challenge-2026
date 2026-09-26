# Atlante: il trasferimento misurato su migliaia di bersagli per linea tenuta fuori

26 settembre 2026, sera. Punto 4 del [piano dell'atlante](../../docs/piani/modello-v2.md) nella scheda
R-V2, su richiesta del proprietario: usare molti dati insieme. **Proxy contro sorgenti pubbliche
tenute fuori, non punteggi VCC.**

## Perché

I banchi del pomeriggio ([r5](../trasferimento_appreso_2026-09-26/RISULTATI.md),
[EB](../trasferimento_gerarchico_2026-09-26/RISULTATI.md),
[quattro sorgenti](../quattro_sorgenti_2026-09-26/RISULTATI.md)) provano su circa 270 bersagli del
pannello per sorgente tenuta fuori: intervalli larghi, e il modello gerarchico stimava le varianze per
gene sugli stessi 270 bersagli. Gli universi genome-wide ([universo](../universo_2026-09-26/RISULTATI.md):
K562 9.866 bersagli, CD4 in estrazione, Orion HCT116 e HEK293T in streaming) permettono di provare il
trasferimento su migliaia di bersagli **fuori dal pannello** per ogni linea tenuta fuori.

## Il banco (`atlas_bench.py`)

Per ogni linea tenuta fuori H, la sua famiglia esclusa da tutto (una linea Orion fuori lascia K562 e CD4):
- **bersagli di prova**: 1.000 bersagli misurati in H e in almeno due sorgenti d'ingresso, estratti con
  seme fisso, nessuno dei 300 del pannello;
- **bersagli di stima**: gli altri bersagli con almeno due sorgenti d'ingresso, fuori dal pannello e
  disgiunti da quelli di prova (al più 6.000). Su di essi, a blocchi, le varianze per gene del modello
  gerarchico (σ² condivisa fra linee, τ² propria della linea; varianza dello SE di CD4 × 2 per i donatori)
  e i programmi di risposta (componenti principali delle risposte di 3.000 bersagli);
- **bracci**, tutti con la testa cis del t20/t22 (prior ristimato senza pannello e senza bersagli di prova):
  `t22like` (la forma del t22: media a pesi uguali degli effetti ristretti, gamma 1, × 1,576);
  `prog_20`, `prog_50`, `prog_150` (la parte trasferita proiettata sui primi k programmi);
  `eb_panel` (media a posteriori con varianze dai soli bersagli di prova, come fa oggi lo stadio 100 sul
  pannello); `eb_atlas` (la stessa, varianze dai bersagli di stima); `share_atlas` (la parte trasferita
  per gene × σ²/(σ² + τ²), la quota della risposta che le linee condividono). Tutti tranne `t22like`
  riportati alla mediana di geni rilevabili di `t22like`;
- **misure** come il banco a quattro sorgenti: PDS, portata e precisione di segno nello spazio degli
  effetti; PDS e nMAE dopo il passo di profilo del trial-01 e uno pseudobulk di 400 cellule (basali A/B/C,
  3 semi ciascuno); Δ = 0,36 × ΔPDS_gen − 0,27 × ΔnMAE_gen contro `t22like`, bootstrap appaiato sui
  bersagli di prova. Il membro `mse` è a zero in tutti i nostri invii
  ([r2](../risposta_comune_2026-09-26/RISULTATI.md)), per questo non entra nel Δ; il rapporto d'energia
  di ogni braccio è registrato.

Prova di funzionamento del codice (non un risultato): alle 19:05 il banco ha girato senza errori su
universi ridotti fatti di pochi blocchi CD4 e K562, nello scratchpad della sessione.

## Regola fissata alle 19:15 del 26/09, prima di eseguire il banco

- **r1** gira sugli universi completi al momento del lancio, almeno K562, CD4 e HCT116, ognuno tenuto
  fuori a turno; con i parametri di default dello script (1.000 bersagli di prova, seme 20260926).
- Un braccio **passa** se il suo Δ è positivo su tutte le linee tenute fuori (su tutte tranne una se sono
  quattro), con l'intervallo sopra zero su almeno due linee, e nessuna linea ha l'intervallo interamente
  sotto −0,002.
- Fra i bracci che passano, il **candidato** è quello con il Δ medio più alto sulle linee. Diventa una
  ricetta (t22 più il braccio, con varianze o programmi stimati sugli universi fuori dal pannello) solo
  con una previsione registrata prima della generazione, e va all'invio solo col via del proprietario.
- Se nessun braccio passa, la forma del t22 resta il riferimento e l'esito è negativo per questi bracci:
  non si rigira r1 con altri parametri per cercarne uno che passi.
- **r2**, con HEK293T quando il suo universo è completo, è una replica: si riporta, non cambia la
  lettura di r1.

**Aggiunta alle 19:19, sempre prima di eseguire il banco:** un braccio in più, `agree_target`, sotto la
stessa regola. È la parte trasferita di `t22like` moltiplicata, bersaglio per bersaglio, per l'accordo fra
le sorgenti d'ingresso: la loro covarianza incrociata diviso l'energia della loro media, sui geni espressi
con i pesi log1p, ristretta verso il rapporto complessivo (pseudo-conteggio pari all'energia del bersaglio
mediano) e limitata a [0, 1]. Motivazione biologica (**ipotesi**): il knockdown di un complesso essenziale
dà risposte condivise fra linee, quello di un regolatore di lignaggio no; dove gli ingressi non concordano,
la linea nuova è meno prevedibile. La prima versione senza restringimento azzerava troppi bersagli e
rompeva la scala a geni rilevabili nella prova su universi ridotti: da qui il restringimento.
