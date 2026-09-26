# Trasferimento appreso: un modello che impara come trasferire, gene per gene

26 settembre 2026. Filone della scheda [R-V2](../../docs/piani/modello-v2.md). **Proxy nello spazio
degli effetti contro sorgenti pubbliche tenute fuori, non punteggi VCC.**

## L'idea

La ricetta d'invio media gli effetti delle sorgenti con regole fisse: affidabilità per cellule,
restrizione locale, gamma 1, un'ampiezza. Qui un modello (gradient boosting di scikit-learn) impara
dai dati, per ogni coppia bersaglio–gene, quanto dell'effetto misurato altrove passa al contesto da
predire. Le variabili sono biologiche:
- trasferimento: medie grezza e ristretta, numero di sorgenti, accordo di segno, dispersione, z;
- meccanismo: prior cis, gene del bersaglio;
- rete: associazione STRING;
- contesto: percentile di espressione del gene nel contesto e nelle sorgenti, espressione del bersaglio;
- gene: reattività, risposta comune e sua dispersione nell'universo K562 (senza i bersagli del pannello);
- bersaglio: forza nelle sorgenti.

I profili basali delle sorgenti vengono dai loro controlli (`basal_profiles.py`, file in
`processed/basal_sources_2026-09-26.csv`).

## Esecuzioni

- **r1** (`lct_bench.py`): **non affidabile.** La revisione di codex
  ([agenti/revisione_codex_r1.md](agenti/revisione_codex_r1.md)) ha trovato due perdite di
  informazione. I compiti di addestramento usavano come ingresso le misure della famiglia di prova
  sugli stessi bersagli, e il prior di rete usava gli esiti di altri bersagli di prova. Ha trovato
  anche difetti minori: z di CD4 azzerate, SE di CD4 incoerente nella verità, coorti diverse per la
  precisione.
- **r2** (`lct_bench2.py`): tutto corretto, con fold di bersagli disgiunti dentro l'esclusione per
  famiglia, nessun esito del pannello nella rete, SE di CD4 ricostruito e coorte comune. In più:
  - etichetta centrata per gene (la parte specifica del bersaglio), perché in r1 il modello imparava
    soprattutto *quali geni si muovono in media*, come mostrano le importanze;
  - coefficienti di trasferimento per gene (`gene_beta`).
- **r3** (`lct_bench3.py`): due canali, la direzione dal trasferimento del t20 e il profilo di
  magnitudine dal modello; previsioni salvate. *Risultati sotto, quando pronti.*

## Risultati di r2

| Sorgente fuori | braccio | PDS proxy − t20like | reach proxy − t20like | precisione@200 − t20like |
|---|---|---|---|---|
| K562 | modello appreso (centrato) | −0,113 | +0,004 | −0,010 |
| CD4 | modello appreso | −0,109 | −0,000 | −0,003 |
| HCT116 | modello appreso | −0,136 | **+0,176** | **+0,072** |
| HEK293T | modello appreso | −0,124 | **+0,107** | +0,019 |
| CD4 | β per gene ≥ 0 | **+0,040** (+0,014…+0,064) | −0,001 | −0,001 |
| K562 / HCT116 / HEK293T | β per gene ≥ 0 | +0,004 / −0,012 / −0,007 (intervalli attraverso lo zero) | | |

- **Misurato:** il modello appreso perde molto nel distinguere i bersagli, ma **ordina molto meglio
  quali geni si muoveranno** nelle linee Orion (reach e precisione).
- **Misurato:** i coefficienti di trasferimento per gene aiutano quando si predice CD4 e sono neutri
  altrove.
- **Interpretazione:** la parte specifica del bersaglio viene dalla misura dello stesso bersaglio
  nelle sorgenti; quello che un modello impara bene da molti bersagli è *quali geni rispondono* in un
  contesto. Sono due canali diversi, e r3 prova a combinarli.

## Letteratura e critica degli agenti

- [Critica dell'architettura](agenti/critica_architettura_claude2.md) (claude2): etichette centrate,
  pochi parametri, un pooling a effetti casuali con varianza a posteriori, ampiezza per bersaglio e
  calibrazione separata per membro. Le etichette centrate sono già in r2.
- [Conservazione delle risposte fra linee](agenti/conservazione_risposte_grok.md) (grok): numeri e
  fonti; motiva la prova sullo stato di p53, negativa ([contesti r2](../contesti_2026-09-26/RISULTATI.md)).
- [Dataset 2025–2026](agenti/dataset_2025_2026_antigravity.md) (antigravity): elenco da verificare.
