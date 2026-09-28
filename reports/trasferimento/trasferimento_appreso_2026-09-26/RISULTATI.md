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
  magnitudine dal modello; previsioni salvate in `processed/lct_r3_predictions_2026-09-26`.
- **r4** (`generator_check_r3.py`): le stesse previsioni passate per il modello del passo di
  profilo del generatore del trial-01 e per uno pseudobulk di 400 cellule (basali di A, B, C,
  semi 1–3), per vedere se il guadagno di r3 sopravvive al rumore delle cellule.

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

## Risultati di r3: due canali

`t20_rw<a>` = t20like × (|previsione del modello centrato| / la sua media sui geni del
bersaglio)^a, riportato alla mediana dei geni rilevabili di t20like (così il confronto non premia
un'ampiezza diversa). Differenze da t20like, intervalli bootstrap al 95 % sui bersagli
([summary.csv](r3/summary.csv)):

| Sorgente fuori | braccio | PDS proxy | reach proxy | precisione@200 | rapporto di errore quadratico |
|---|---|---|---|---|---|
| K562 | rw 0,25 | **+0,007** (+0,001…+0,015) | +0,007 (+0,001…+0,014) | −0,000 | 1,08 → 1,13 |
| CD4 | rw 0,25 | **+0,018** (+0,010…+0,028) | +0,000 | +0,001 | 1,26 → 1,34 |
| HCT116 | rw 0,25 | **+0,012** (+0,003…+0,021) | +0,004 (+0,001…+0,007) | +0,004 (+0,001…+0,007) | 1,26 → 1,39 |
| HEK293T | rw 0,25 | **+0,017** (+0,008…+0,028) | +0,003 (+0,000…+0,005) | +0,003 (−0,000…+0,005) | 1,46 → 1,67 |
| K562 / CD4 / HCT116 / HEK293T | rw 0,5 | +0,003 / +0,028 / +0,019 / +0,026 (K562 attraverso lo zero) | | | fino a 2,36 |
| K562 / CD4 / HCT116 / HEK293T | rw 1 | −0,017 / +0,030 / +0,019 / +0,027 (tre intervalli attraverso lo zero) | | | 6,4–13,3 |
| K562 / CD4 / HCT116 / HEK293T | segno del t20, modulo del modello | −0,037 / −0,002 / +0,000 / −0,015 | | | |

- **Misurato:** con esponente 0,25 il PDS proxy sale su tutte e quattro le sorgenti tenute fuori,
  ogni intervallo sopra lo zero, e reach e precisione non scendono. Esponenti più alti guadagnano di
  più dove il t20like è debole (CD4, Orion) ma perdono su K562 e allargano gli intervalli.
- **Misurato:** prendere dal modello il modulo intero (solo il segno dal t20) perde: il modello
  serve come correzione del profilo, non come sostituto.
- **Misurato:** il rapporto di errore quadratico sale (la magnitudine si concentra su meno geni a
  pari geni rilevabili). Col punteggio mse ufficiale già a zero dopo la scala, questo membro non
  può scendere; al miglior riscalamento il rapporto di t20like e di rw 0,25 resta fra 0,998 e 0,9997.

## Risultati di r4: attraverso il modello del generatore

PDS sul pseudobulk generato, differenze da t20like ([generator_check.csv](r4/generator_check.csv)):

| Sorgente fuori | rw 0,25 | rw 0,5 |
|---|---|---|
| K562 | **+0,010** (+0,004…+0,016) | +0,011 (+0,001…+0,022) |
| CD4 | **+0,009** (+0,003…+0,015) | +0,009 (−0,001…+0,020) |
| HCT116 | **+0,008** (+0,000…+0,015) | +0,007 (−0,006…+0,020) |
| HEK293T | **+0,009** (+0,002…+0,016) | +0,008 (−0,004…+0,021) |

- **Misurato:** il guadagno sopravvive al rumore delle cellule; con 0,25 ogni intervallo resta sopra
  lo zero, con 0,5 il guadagno medio è simile e tre intervalli su quattro attraversano lo zero.
- **Scelta** (fra tre esponenti provati, dunque con un poco di selezione): **0,25** per il candidato
  d'invio t21, implementato nello stadio 104.
- **Interpretazione, da non promuovere:** i contesti ufficiali distano dalle sorgenti di
  addestramento più di quanto le sorgenti pubbliche distino fra loro (altre linee, chimica Flex): il
  guadagno ufficiale può essere più piccolo di quello qui misurato, o assente.

## r5: banco isolato come chiede l'audit

L'[audit di codex](../audit_piani_dati_2026-09-26/RISULTATI.md) (§4, revisione R-019 del registro)
ha trovato che in r2–r4 i centri delle sorgenti e delle etichette erano calcolati prima degli split,
e che un compito di addestramento poteva usare come ingresso la famiglia tenuta fuori. Il primo
t21 costruito dallo stadio 104 (`effects_t21_2026-09-26`, non inviato) aveva inoltre un difetto
biologico: il ripeso moltiplicava anche la testa cis e il gene del bersaglio (vicini a promotore
bidirezionale come AIMP1 per TBCK da −3,4 a −12,5 in ln; gene del bersaglio da −2,5 a −8,5 di
mediana), dosi che il generatore poi taglia a ±6 in log2. `lct_bench5.py` (r5) corregge il banco
(esclusione della famiglia di prova da etichette, ingressi e centri; centri sui soli bersagli di
training; arresto anticipato validato su bersagli interi) e confronta anche il ripeso della sola
parte trasferita (`rw_tx`, testa cis e gene del bersaglio lasciati come sono). Regime C: il
bersaglio è misurato in altri contesti; K562 tenuto fuori non è una linea nuova (prior dall'universo
K562).

**Regola fissata alle 14:48 del 26/09, prima di leggere r5.** Il t21 si genera con `rw_tx0.25`
se, sulle tre sorgenti la cui linea è nuova (CD4, HCT116, HEK293T), la differenza di PDS attraverso
il modello del generatore da t20like è positiva con l'intervallo sopra zero in almeno due, e l'nMAE
proxy non peggiora di oltre 0,01 in nessuna. Altrimenti oggi non si genera nessun t21 con lo
stadio 104, e `rw_all0.25` non si usa in ogni caso (difetto biologico sopra).

### Risultati di r5

Differenze da t20like, intervalli bootstrap al 95 % sui bersagli ([summary.csv](r5/summary.csv)).
PDS e nMAE "gen" sono misurati dopo il modello del generatore; per l'nMAE più alto è peggio.

| Sorgente fuori | braccio | PDS proxy | PDS gen | nMAE gen | energia |
|---|---|---|---|---|---|
| K562 (linea non nuova) | rw_tx 0,25 | +0,012 (+0,004…+0,020) | +0,012 (+0,005…+0,019) | +0,027 (+0,018…+0,039) | 1,58 |
| CD4 | rw_tx 0,25 | +0,011 (−0,002…+0,023) | +0,007 (−0,001…+0,015) | +0,017 (+0,014…+0,020) | 1,54 |
| HCT116 | rw_tx 0,25 | +0,011 (+0,000…+0,021) | +0,004 (−0,004…+0,011) | +0,046 (+0,037…+0,056) | 1,76 |
| HEK293T | rw_tx 0,25 | +0,015 (+0,006…+0,024) | +0,008 (+0,001…+0,016) | +0,051 (+0,041…+0,061) | 1,68 |
| CD4 / HCT116 / HEK293T | rw_tx 0,5 | | +0,004 / −0,002 / +0,005 (attraverso lo zero) | +0,040 / +0,103 / +0,112 | 3,6–4,1 |
| tutte | rw_all 0,25 | come rw_tx 0,25 entro 0,003 | come rw_tx 0,25 entro 0,001 | come rw_tx 0,25 entro 0,001 | 1,66–1,97 |

- **Esito della regola:** sulle linee nuove il PDS attraverso il generatore ha l'intervallo sopra
  zero solo su HEK293T (uno su tre), e l'nMAE proxy peggiora di +0,017…+0,051 su tutte e tre.
  **Il t21 con lo stadio 104 oggi non si genera.**
- **Misurato:** con il banco isolato il guadagno di PDS attraverso il generatore sulle linee nuove
  scende da +0,008…+0,009 (r4) a +0,004…+0,008, e due intervalli su tre attraversano lo zero. Il
  guadagno più grande resta su K562, la sola linea di cui il modello conosce i prior.
- **Misurato:** con l'arresto anticipato validato su bersagli interi i modelli si fermano a 30–100
  iterazioni per K562 e CD4 (in produzione erano 600 con la validazione su righe a caso), 99–426
  per Orion: la parte specifica del bersaglio si impara poco su bersagli nuovi.
- **Misurato:** a parità di geni rilevabili il ripeso concentra l'energia (1,5–1,8 volte), e sui
  geni significativi della verità l'errore assoluto cresce: è il limite indicato dall'audit (§4.3).
- **Interpretazione:** il canale di magnitudine sposta la discriminazione di poco e la paga in
  errore sulle ampiezze. Riportarlo alla stessa energia del t20 lascerebbe il PDS com'è (il coseno
  non dipende dalla scala) e ridurrebbe i geni rilevabili: senza lo scorer vero (banco F2) non si
  sa quale dei due effetti prevalga sui membri DE ufficiali. Lo stadio 104 resta nel codice come
  strumento sperimentale, fuori dalla pipeline d'invio.
- Il ripeso della sola parte trasferita e quello di tutte le voci danno numeri quasi uguali: il
  difetto biologico del primo t21 non spostava i proxy, perché il generatore taglia a ±6 in log2.

## Letteratura e critica degli agenti

- [Critica dell'architettura](agenti/critica_architettura_claude2.md) (claude2): etichette centrate,
  pochi parametri, un pooling a effetti casuali con varianza a posteriori, ampiezza per bersaglio e
  calibrazione separata per membro. Le etichette centrate sono già in r2.
- [Conservazione delle risposte fra linee](agenti/conservazione_risposte_grok.md) (grok): numeri e
  fonti; motiva la prova sullo stato di p53, negativa ([contesti r2](../contesti_2026-09-26/RISULTATI.md)).
- [Dataset 2025–2026](agenti/dataset_2025_2026_antigravity.md) (antigravity): elenco da verificare.
