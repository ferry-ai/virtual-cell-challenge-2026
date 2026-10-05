# Mappa del progetto — VCC 2026

**Perimetro:** lo stato del progetto VCC e la sua direzione (§0), il problema (§1), le fasi (§2),
che cosa sappiamo e non sappiamo (§3–§4), le criticità note (§5). Chi arriva legge il §0; il resto
quando il compito lo chiede. **Fonti:** i checkpoint, i report e le schede citati accanto a ogni
affermazione: questa pagina instrada e riassume, non è evidenza. **Si aggiorna:** il §0 dopo ogni
invio valutato e quando cambia la direzione, riscritto e non allungato; §3–§5 quando un risultato
cambia una conclusione. Il testo tolto resta in `docs/storico/`: le
[sezioni 3–4 del 28/09](storico/PROGETTO_sezioni_3_4_2026-09-28.md) e il
[§0, §6 e §7 del 30/09 mattina](storico/PROGETTO_sezioni_0_6_7_2026-09-30.md), il
§0 del 3/10 sera nel [consolidamento](storico/consolidamento_2026-10-03/INDICE.md).

## 0. Oggi — 4 ottobre 2026, l'ibrido D-056 passa il banco ma il t30 non migliora il t25

**Il riferimento resta la ricetta t22**, quattro sorgenti a peso uguale (K562 GWPS, CD4 in tre stati, HCT116,
HEK293T) con lo stimatore t25 corretto; t22/t24 danno una media osservata di **0,14207**; il massimo è t28,
**0,144845**, non conclusivo ([CP-0052](checkpoints/0052-t28-punteggio-ufficiale.md)). Il t29, rete r2 `desc` al posto
del transfer, è negativo ([CP-0055](checkpoints/0055-t29-rete-cellulare-punteggio.md)). Punteggi:
[indice degli invii](../reports/invii/README.md).

**Un solo piano operativo, [R-LEAD](piani/strategia-scientifica.md), su due binari (D-054).**
**Direzione dal 4/10 ([D-056](DECISIONI.md#d-056--transfer-con-correzione-neurale-selettiva)):**
transfer congelato e correzioni neurali pesate da un selettore di beneficio validato; in assenza di evidenza,
ritorno al transfer.

- **Modello.** L'**ibrido selettivo D-056 v1** passa le regole congelate sia in sviluppo (H1, HepG2, RPE1) sia in
  conferma (Jurkat e K562): T + w · R batte il transfer sui sei membri locali in cinque linee escluse su cinque
  (+0,006…+0,074). Il punteggio di banco del §9 è 0,134 contro 0,090 del transfer
  ([CP-0062](checkpoints/0062-d056-ibrido-selettivo-esito-banco.md), [S-009](STRADE.md)). È la prima rete sulle
  cellule che migliora il transfer su linee escluse, con un seme e un corpus pilot a 8 gruppi; in scala locale, non
  sul sito. Il **t30** (effetti t25 + w · R della rete del fold HepG2) vale **0,135249**, −0,004989 contro il t25:
  ramo b della regola registrata, non conclusivo e non un miglioramento; perde PDS (−0,042 scalato)
  ([CP-0064](checkpoints/0064-t30-ibrido-selettivo-punteggio-ufficiale.md)). Il banco non aveva valutato il candidato inviato: baseline diversa, correzione per due
  terzi comune ai bersagli e più ampia all'esportazione, perdita di PDS già visibile sul fold esportato. La causa non
  è isolata ([diagnosi](../reports/modelli/diagnosi_t30_2026-10-04/README.md)); il v1 non è un candidato per D/E/F. Rifatto su 5 semi e 400 cellule
  per bersaglio, il guadagno di banco è +0,013 di media (non +0,044), e il fold esportato perde PDS in modo netto
  ([CP-0065](checkpoints/0065-d056-confronti-e-rumore-del-banco.md)). Il banco v2 t28 a 400 cellule × 5 semi è ora concluso:
  superano la regola con guardia PDS 4/5 linee su all, solo Jurkat su prod; HepG2 perde PDS su entrambe,
  RPE1 su prod ([CP-0066](checkpoints/0066-banco-v2-t28-cinque-linee.md)). Diagnosi su linee già di sviluppo, nessuna promozione. Il pilot v4
  (correzione libera) resta negativo ([CP-0061](checkpoints/0061-pilot-v4-esito-tre-linee.md)).
- **Fonti del transfer:** su Jurkat e K562 più tabelle aggregate battono le fonti della ricetta (+0,07…+0,14 locali).
  Nessun candidato di solo transfer è ammesso, perché il banco di quelle due linee è sotto 0,100 ([S-010](STRADE.md)).
- **Dati, mandato non negoziabile D-053:** tutte le linee e i contesti idonei entrano nel percorso principale,
  qualunque sia l'esito del pilot; archivio completo, aggregati e campioni cellulari restano distinti e l'uso
  effettivo si verifica ([vincolo](GENERALIZZAZIONE.md#21-copertura-integrale-vincolo-non-negoziabile)). Esecuzione in
  [R-LAB](piani/piano-giorno-2026-09-30.md), inventario riconciliato e lacune in [R-DATI](piani/dati-affidabilita.md).

**Che cosa vale (misurato).** Le correzioni del transfer dai controlli medi non danno beneficio, semplici o con una
rete sul pseudobulk, e sui sei membri vince il transfer ([CP-0056](checkpoints/0056-banco-contesto-c-j.md),
[CP-0057](checkpoints/0057-p4-dieci-gruppi-pseudobulk.md)); nel pilot v2 lo stato delle cellule aiuta rispetto al
profilo medio ma la rete resta sotto il transfer; la v3 r1 è un pilot
incompleto per difetti tecnici ricostruiti esattamente, non una bocciatura
([diagnosi](../reports/modelli/rete_ancorata_v4_2026-10-03/diagnosi_r1/DIAGNOSI.md)). La prima correzione neurale
che batte il transfer su linee escluse è quella pesata dell'ibrido D-056 (CP-0062), nel banco locale. Sul sito il
guadagno non è comparso (t30, CP-0064). Esiti e fonti per area in
[AMBITI §4–5](AMBITI.md#5-modelli-appresi-e-generalizzazione).

**Riserve e traguardo.** K562 è già vista dalle reti r2/r3; H1 train/val è nel corpus, H1 test resta chiusa e non si
usa per debug. La consegna D/E/F (dati il 22/10, invii fino al 5/11) richiede la prova generale a forma piena
([R-REV](piani/revisione-critica.md), [S-INVII](piani/invii-finale.md)) anche se resta il transfer.

### Coordinamento e decisioni aperte

- La sessione che lavora su R-LEAD si registra nella sua intestazione con macchina, commit, file e output; lo stato
  scritto in una scheda non prova che un job sia vivo. Le guide prima di questa riscrittura sono nello
  [storico del consolidamento](storico/consolidamento_2026-10-03/INDICE.md).
- **Autorizzazioni:** il 4/10 notte il proprietario ha autorizzato la sessione `2b35612c`, per il mandato D-056 e solo
  per essa, a procedere senza conferme. L'autorizzazione copre training, banchi, download, gestione dei job negli
  account configurati, commit e push dopo verifica, e invii in grading dei candidati con banco ≥ 0,100 secondo una
  regola precisa ([autorizzazioni](../reports/invii/trial_2026-09-22/autorizzazioni.md#mandato-d-056-e-invii-autonomi-notte-del-4-ottobre-r-lead-sessione-claude-2b35612c)).
  Acquisti e servizi a pagamento restano esclusi. Per le sessioni successive valgono le regole precedenti: invii e
  push si chiedono.
- Uso di ulteriori dati della stessa linea e verifica esterna della licenza Orion restano decisioni distinte;
  identità fuori dalla repo pubblica.
- La preregistrazione t21 citata ma assente resta [R-020](REGISTRO.md#r-020--evidenza-citata-ma-assente-dal-repository),
  non va ricostruita dopo il risultato.

La pubblicazione si verifica confrontando commit locale e remoto aggiornato. Worktree, scratchpad e infrastruttura
hanno il proprio stato in [AGENTI](AGENTI.md).

## 1. Il problema

Bisogna prevedere come cambia l'espressione genica di una cellula quando si spegne uno
di 300 geni, in tre tipi cellulari (A, B, C) mai visti prima. Della gara riceviamo solo
le cellule **non perturbate** dei tre contesti: 18.400 cellule ciascuno. Nessun esempio
di perturbazione, in nessuno dei tre. Si chiama previsione *zero-shot*: bisogna
imparare altrove e trasferire qui.

La classifica finale dipende solo dal set finale, su tre contesti diversi (D, E, F) e
300 perturbazioni nuove, rilasciato il 22 ottobre 2026. Le sottomissioni chiudono il
5 novembre 2026. Formato, metriche e setup: `README.md`.

## 2. Dove siamo

| Fase | Stato | Evidenza |
|---|---|---|
| Ambiente, CLI, dati di controllo, contratto di sottomissione e di punteggio | fatto | [SOTTOMISSIONE.md](SOTTOMISSIONE.md) §1–2 (`da-verificare` per §3 e §6: R-015), `reports/gara/scorer_2026-09-12/vcc2026_contract.json` |
| Impacchettamento in memoria limitata (stadio 48) | fatto: 0,52 GiB di picco contro i 33,5 di `vcc prep` | [CP-0005](checkpoints/0005-packaging-streaming-trial01.md) |
| Ancore ufficiali di cinque membri su sei | fatto; come conversione dei grezzi aggregati non sono esatte ([CP-0050](checkpoints/0050-credibilita-score-e-riserva.md)): un punteggio si legge dai sei scalati pubblicati (PROCEDURE §2, punto 7) | [CP-0021](checkpoints/0021-ancore-ufficiali-e-troppe-chiamate.md), `reports/gara/anchors_2026-09-17/` |
| Pipeline a singola cellula su Colab: K562 letto per intero, `ControlModel`, DE veloce identico allo scorer, banchi a sei metriche | fatto | [CP-0020](checkpoints/0020-singola-cellula-cis-generatore.md), [CP-0021](checkpoints/0021-ancore-ufficiali-e-troppe-chiamate.md) |
| Trasferimento dello stesso bersaglio da quattro sorgenti genome-scale (K562, CD4, Orion HCT116 e HEK293T) | ricetta del t22; ultimi cambi della media piccoli, ma ampiezza e generatore non confinati | §0, [audit 29/09](../reports/analisi/lead_scientist_2026-09-29/AUDIT_SCIENTIFICO.md) |
| Universi genome-wide: tutti i bersagli di ogni sorgente, non solo i 300 del pannello | fatti per K562, CD4, HCT116, HEK293T (corretti il 27/09), KOLF2.1J, A549, VIPerturb-seq, 19 linee HIPSCI | [sorgenti](../reports/sorgenti/README.md) |
| Banco con lo scorer vero su un contesto pubblico tenuto fuori (HepG2) | r1 fatto il 27/09: descrittivo | [banco HepG2](../reports/generatore_e_banchi/banco_hepg2_v2_2026-09-26/RISULTATI.md) |
| Modelli su molti contesti (modello a cancelli, rete, encoder, Tahoe T1) | nessuno passa la sua regola; stato di R-V2 nella [scheda](piani/modello-v2.md) | [modelli](../reports/modelli/README.md) |
| Contesti A/B/C: saggio 10x Flex, impronte genetiche | misurato; le identità di linea restano ipotesi | [CP-0028](checkpoints/0028-cd4-sorgente-flex-trasferimento.md) |
| Generatore, cioè la fedeltà direzionale | trial-01 in tutti i migliori invii; `ControlModel` (t14) non attribuibile, la fedeltà scende | `reports/generatore_e_banchi/dispersion_2026-09-23/` |
| Esperimenti in pseudobulk dell'11–19/09; orchestratore e catena di cicli | chiusi il 23/09, codice archiviato; la base di lancio degli agenti di oggi è fuori dalla repo ([AGENTI](AGENTI.md)) | [storico](../reports/storico/README.md), [ARCHIVIO.md](ARCHIVIO.md) |
| Set finale D/E/F | esce il 22 ottobre; invii fino al 5 novembre; prova generale fatta in forma ridotta ([CP-0044](checkpoints/0044-prova-generale-22-ottobre.md)), non in forma piena | [PROCEDURE.md](PROCEDURE.md) §7 |

## 3. Che cosa sappiamo e guida le scelte

Solo ciò che pesa sulle scelte di oggi, con il tipo di affermazione. La tabella delle misure
del 12–17 settembre è in [storico](storico/PROGETTO_sezioni_3_4_2026-09-28.md).

**Sul punteggio ufficiale**
- **Misurato.** Raddoppiare l'ampiezza vale +0,037 da t11 a t15 e +0,030 da t15 a t16; nel
  secondo passo `pds_cosine` sale appena, mentre fedeltà, `nmae`, `reach` e Jaccard fanno insieme
  +0,171 scalato ([CP-0033](checkpoints/0033-t15-ampiezza-doppia.md),
  [CP-0037](checkpoints/0037-t16-ampiezza-quadrupla.md)). D-006 è superata da D-042.
- **Misurato.** Dal t16 i cambi a un fattore valgono +0,0012 (t17 − t15), +0,0020 (t20 − t16),
  +0,0016 (t22 − t20), −0,0010 (t25 − t22); il solo seme vale +0,0016 (t24 − t22)
  ([lezioni](../reports/invii/lezioni_invii_2026-09-28/RISULTATI.md)).
- **Misurato.** La `mse` ufficiale grezza dei nostri invii segue 1 + E/4786 (scarto massimo 0,048
  su sei invii) ([risposta comune](../reports/trasferimento/risposta_comune_2026-09-26/RISULTATI.md)).
  Tutte le prime 100 squadre hanno la `mse` scalata positiva; in tutti i nostri invii è tosata a 0.
  **Inferenza condizionata**, non misura: che le previsioni siano quasi ortogonali agli effetti
  veri e che nessuna ampiezza porti la `mse` sopra il suo zero. Il fit indica eccesso di energia,
  ma non identifica il coseno con la verità; la lettura operativa è che lo shrinkage globale da solo
  ha poche prospettive per la `mse` ([audit del 29/09](../reports/analisi/lead_scientist_2026-09-29/AUDIT_SCIENTIFICO.md), §2.5).
- **Misurato**, nel t24: `pds_cosine` scalato 0,636, il 74 % della media; la fedeltà direzionale
  scalata −0,054, vicino alla linea di base ([confronto](../reports/invii/prediction_t24_2026-09-27/comparison.json)).
  Nel t28 la fedeltà scalata sale a −0,007, +0,051 sul t25 ([CP-0052](checkpoints/0052-t28-punteggio-ufficiale.md)).
- **Misurato.** Aggiungere sorgenti per lo stesso bersaglio alzava `pds_cosine` quando l'ampiezza
  era bassa: CD4 +0,0102 ([CP-0030](checkpoints/0030-t10-attribuzione-cd4.md)), HCT116 +0,0104
  con i pesi cambiati insieme ([CP-0031](checkpoints/0031-t11-punteggio-orion.md)); HEK293T non si
  distingue né sul t15 né sul t20.
- **Misurato dagli organizzatori**, nelle note dello scorer: sul pannello val A circa 340 geni DE
  per bersaglio in media, il 12–30 % dei bersagli con meno di 10; la fedeltà conta il segno giusto
  anche sui geni non significativi nel vero ([CP-0039](checkpoints/0039-banco-varianti-restrizione.md)).
- **Misurato.** Il generatore di trial-01 fa centinaia di chiamate spurie per bersaglio a effetto
  nullo; con `ControlModel` sono quasi zero ma la fedeltà scende (t14,
  [CP-0032](checkpoints/0032-t14-controlmodel-fedelta.md)). Chi non chiama geni prende fedeltà 0
  (D-035).

**Sui dati e sul trasferimento** (proxy su sorgenti pubbliche, non punteggi VCC)
- **Misurato.** I profili di knockdown di linee diverse si somigliano poco: coseno mediano 0,02–0,03
  fra linee e laboratori diversi, circa 0,07 fra linee dello stesso laboratorio, 0,16 fra due
  esperimenti della stessa linea, 0,20–0,25 fra stati delle stesse cellule CD4. Confondono linea,
  laboratorio, protocollo e rumore ([atlante](../reports/trasferimento/atlante_2026-09-26/RISULTATI.md)).
- **Misurato.** Il segno della miscela delle altre sorgenti coincide con quello della sorgente
  tenuta fuori nel 51–56 % dei geni più mossi; con i bersagli scambiati si arriva già al 53,8 %, e
  «sempre su» fa il 63,6 % ([CP-0034](checkpoints/0034-audit-segni-e-ampiezza.md)).
- **Misurato.** Riponderare sorgenti, bersagli o programmi (EB, programmi, accordo per bersaglio,
  somiglianza basale, p53, trasferimento appreso) non batte la media a pesi uguali; aiuta invece
  togliere i geni che una sola sorgente stima ([trasferimento](../reports/trasferimento/README.md)).
- **Misurato.** Lo stimatore pseudobulk leggeva un gene senza conteggi come indotto (geni Y delle
  donatrici CD4): corretto con `min_expected` (cache r9, universi `_me1`)
  ([pseudoconteggio](../reports/sorgenti/pseudoconteggio_2026-09-27/RISULTATI.md)).
- **Misurato.** La gara è letta in 10x Flex, a sonde; **anche CD4 è GEM-X Flex v1**, verificato nelle
  12 righe dei metadati originali. La ricetta usa quindi già una sorgente Flex per 293 bersagli.
  Il ponte K562 VIPerturb–Replogle (metà Flex contro metà 0,110; Flex contro 3' 0,030) riguarda
  quella coppia, non tutte le sorgenti ([audit e fonte](../reports/analisi/lead_scientist_2026-09-29/AUDIT_DATI.md)).
- **Misurato.** I bersagli del pannello sono knockdown di forza tipica (percentile mediano 0,54 nel
  K562) e nessuno è nei pannelli *essential*; i banchi su bersagli essenziali misurano effetti più
  forti e più trasferibili di quelli del pannello ([atlante](../reports/trasferimento/atlante_2026-09-26/RISULTATI.md)).

**Sui modelli per contesti nuovi**
- **Misurato nei modelli del 27–28/09.** Dove battono il contesto cieco non battono quello
  scambiato; in quelle corse la perdita sulla famiglia esclusa sale dopo 50–100 passi.
  Non estendere quella curva a r2/r3 cellulari: hanno [esiti e diagnosi propri](../reports/modelli/README.md).
  Nessuna rete è stata promossa; t29 aggiunge un esito ufficiale negativo (CP-0055).
- **Misurato**, su HepG2 con lo scorer vero: la forma t19 batte la t16 (+0,026); raddoppiare la t19
  non è distinguibile da zero; la testa cis non si vede; Jaccard negativo in ogni braccio
  ([banco HepG2](../reports/generatore_e_banchi/banco_hepg2_v2_2026-09-26/RISULTATI.md)).
- **Ipotesi.** Le identità di linea di A/B/C sono sostenute da marcatori, impronte genetiche e
  da un confronto con espressione e numero di copie DepMap già svolto il 24/09. Il materiale
  resta fuori dalla repository pubblica; non è una conferma degli organizzatori
  ([audit del 29/09](../reports/analisi/lead_scientist_2026-09-29/AUDIT_DATI.md), §6).

## 4. Che cosa non sappiamo ancora

Le incertezze aperte al 28 settembre. Fra parentesi il numero che avevano nel vecchio §4
([storico](storico/PROGETTO_sezioni_3_4_2026-09-28.md)).

1. **Quanto sono grandi gli effetti da prevedere nei contesti di gara** (3). Le note degli
   organizzatori danno circa 340 geni DE per bersaglio in A; nessuna nostra misura li stima.
   L'essenzialità riguarda la sopravvivenza, non l'ampiezza della risposta (CP-0002).
2. **Se ampiezza e sorgenti scelte su A/B/C valgano per D/E/F** (2). Sono state scelte sul
   punteggio ufficiale di A/B/C con circa 15 invii; l'ottimo dipende dal generatore e dal numero
   di geni DE, che cambiano con contesto e pannello.
3. **Quanto rumore ha il punteggio ufficiale.** Una sola coppia di semi (t24 − t22 = 0,0016): da
   una sola osservazione, l'intervallo al 95 % per la deviazione standard della differenza va da
   circa 0,0007 a circa 0,05 (calcolo nella revisione critica, §3).
4. **Se i proxy dei banchi predicano il punteggio ufficiale.** Δ = 0,36 ΔPDS − 0,27 ΔnMAE non vede
   fedeltà, reach, Jaccard e MSE. **Misurato il 28/09** ([CP-0041](checkpoints/0041-proxy-contro-ufficiale.md)):
   sulle quattro differenze ufficiali sopra il rumore ne legge due con il segno giusto (una sorgente
   in più, il primo raddoppio); non legge la via di CD4 né il secondo raddoppio. Per la regola
   scritta prima, non si sceglie più un candidato sul solo proxy. Resta aperto se un proxy con più
   membri farebbe meglio.
5. **Se il contesto letto dai controlli sia utilizzabile** (nuovo). Ogni prova finora dice di no;
   con 4–13 contesti di poche famiglie, e laboratori e piattaforme confusi con le linee, non è
   ancora una risposta.
6. **Quanto pesino piattaforma e studio**, e se una mappa gene per gene aiuti su bersagli tenuti
   fuori. CD4 è già Flex; il ponte descrittivo VIPerturb–Replogle riguarda due studi K562 e
   non isola l'effetto della chimica ([audit](../reports/analisi/lead_scientist_2026-09-29/AUDIT_DATI.md)).
7. **Quali linee siano D/E/F, e se esistano Perturb-seq pubblici di quelle linee** (5, 7). Per
   A/B/C il percorso «stessa linea» è già stato esplorato in materiale riservato: un dataset
   mirato è stato provato e non adottato per il debole segnale specifico del bersaglio. Questo
   non chiude la ricerca di fonti ulteriori; identità e confronti restano fuori dalla repo pubblica.
8. **Se l'asse genico ufficiale sia ricostruibile in identificatori Ensembl** (4): contraddizione
   aperta, scheda [R-004](REGISTRO.md#r-004--docsrevisione_analisi_2026-09-11md).
9. **L'efficienza di knockdown nei contesti di gara** (8), non disponibile.
10. **Se la licenza CC-BY-NC-SA-4.0 di Orion sia compatibile con le regole della gara** (9).
    Ammessa negli invii per decisione del proprietario, non verificata con gli organizzatori.
11. **Quale backend DE usi il server** (10): localmente il DE veloce coincide con il percorso scanpy
    dello scorer (D-037); lo scarto fra backend non è misurato.
12. **Se un ricampionamento dei controlli sia ammesso** (13): D-017, non risolta e non urgente.
13. **Se la pipeline regga il 22 ottobre** (nuovo): la prova generale è fatta in forma ridotta
    ([CP-0044](checkpoints/0044-prova-generale-22-ottobre.md)), non in forma piena; con un
    pannello nuovo cambiano la risposta media tolta da γ = 1 e i bersagli coperti.

Le altre incertezze del vecchio elenco sono chiuse o assorbite: (1) le ancore di cinque membri
non sono identificate per contesto: le ancore aggregate del 17/09 non convertono esattamente
i grezzi ([CP-0050](checkpoints/0050-credibilita-score-e-riserva.md)); (6) la co-espressione non predice l'effetto
su HepG2; (11), (12) e (21) sono superate dalla scelta dell'ampiezza sul punteggio ufficiale
(D-042); (14) il limite di `vcc prep` è aggirato dallo stadio 48; (15)–(19) sono linee chiuse con
il codice archiviato; (20) le copie su Drive sono state lette.

## 5. Criticità note

Dalla [revisione critica del 28 settembre](../reports/analisi/revisione_criticita_2026-09-28/REVISIONE.md),
che le argomenta con le fonti:

1. **La direzione gene per gene è debole e i membri del punteggio si compensano**. Il fit energia–MSE
   indica eccesso di energia, ma non dimostra saturazione di ogni ampiezza o generatore:
   [correzione del 29/09](../reports/analisi/lead_scientist_2026-09-29/AUDIT_SCIENTIFICO.md).
2. **Le decisioni precedenti sono state prese anche su un proxy di due membri su sei**, contro verità
   pubbliche rumorose, con regole «positivo su 3 linee su 4» che hanno poca potenza e molti
   confronti in parallelo.
3. **Il rumore del punteggio ufficiale è stimato su una coppia**, e i parametri della ricetta sono
   stati scelti su A/B/C: sul set finale vanno ricontrollati, non trasferiti.
4. **Piattaforma e normalizzazione**: sorgenti di saggi diversi, con CD4 già Flex; i profili basali
   sono normalizzati su insiemi di geni diversi. La media dei CPM per cellula può inoltre differire
   molto dalla composizione aggregata che il generatore Poisson conserva.
5. **Il codice di ricerca sta nei report**: molte volte il codice vivo, quasi tutto senza test, e in
   parte importato da altri banchi per percorso; misure e mappa in
   [reports/README.md](../reports/README.md), «Il codice di ricerca che sta qui».
6. **Evidenza citata ma assente dal repository**: la revisione del 28/09 ne contava cinque; quattro
   sono state recuperate e committate il 28/09, resta la previsione del t21, probabilmente mai
   scritta ([registro, R-020](REGISTRO.md#r-020--evidenza-citata-ma-assente-dal-repository)).

## 6. Percorso di lettura

Non c'è più un percorso di lettura qui: l'unico è la tabella dei compiti di [CLAUDE.md](../CLAUDE.md),
che per ogni compito dice che cosa leggere e dove fermarsi. Il percorso scritto fino al 30/09 è nella
[copia storica](storico/PROGETTO_sezioni_0_6_7_2026-09-30.md).

## 7. Come si tiene aggiornato questo sistema

Le regole di scrittura dei documenti stanno in un posto solo, [docs/CLAUDE.md](CLAUDE.md): la sede
di ogni informazione, quando si scrive un checkpoint, come si corregge un documento. Il controllo
da eseguire prima di chiudere è in [CLAUDE.md](../CLAUDE.md), «Before you finish».
