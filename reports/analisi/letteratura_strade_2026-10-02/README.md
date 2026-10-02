# Letteratura, classifica e strade per i 20 giorni che restano

2 ottobre 2026, sera, Claude Code per Alfredo (sessione `42343bb9`). Richiesta: mettere ordine, raccogliere la
letteratura pertinente e proporre le strade più promettenti. Il set finale esce il **22 ottobre**; gli invii chiudono
il **5 novembre**.

**Che cosa è questa pagina.** Una revisione con fonti, più tre letture nuove ma leggere:
- la classifica pubblica di validazione del 2 ottobre;
- il codice dello scorer installato (`cell_eval2` 0.16.0);
- l'indice PyPI dello scorer.

Nessun training, nessun invio e nessun download di dati. Le strade del §5 sono **proposte da decidere**, non un
protocollo: ognuna va registrata prima di misurarla, come da regola del progetto.

**Quanto ho letto delle fonti.** Di diverse fonti ho letto solo l'abstract o la pagina dell'editore, non il testo
completo. La colonna «Letto» del §3 lo dice per ognuna. L'articolo su *Cell* della gara 2026 ha risposto 403.

## 1. In dieci righe

1. **Il punteggio.** Il nostro massimo è +0,145 (t28); il riferimento della ricetta t22 è +0,141.
   - Rango 100: 0,216. Rango 20: 0,257. Primo: 0,432.
2. **Da dove viene il divario col rango 100 (+0,075):**
   - circa 43% dalla MSE, che noi abbiamo sempre tosata a 0;
   - circa 33% dal PDS;
   - circa 18% dalla reach.
3. **La causa più probabile della MSE a 0.** Le descrizioni pubbliche dei primi 300 parlano spesso di un **emettitore a
   due momenti**:
   - il profilo aggregato (pseudobulk, letto da MSE e PDS) è regolato da solo;
   - le singole cellule (lette dai test di Wilcoxon: nMAE, fedeltà, reach, Jaccard) sono regolate a parte.

   Il nostro generatore ha un solo momento: l'amplificazione ×1,576 che aiuta i membri DE gonfia la MSE (grezza 3,06
   contro circa 0,8 al rango 100). Lo scorer permette la separazione: il pseudobulk somma i conteggi, il Wilcoxon legge
   i ranghi per cellula (§4).
4. **La letteratura del 2025–2026 è concorde:** nessun modello profondo batte in modo affidabile il trasferimento lineare
   o la media fra contesti.
   - Molina e Zhang (2026): l'interazione bersaglio × linea porta circa il 21% dell'energia, è riproducibile solo a
     metà e nessun modello la prevede zero-shot.
   - Due squadre VCC 2026 con codice pubblico si fermano a 0,137–0,139 col solo trasferimento: è il nostro stesso
     plateau.
5. **Che cosa significa per R-LEAD.** Non ci si deve aspettare il salto dalla rete. Può valere come correzione o per i
   bersagli scoperti, solo se la misura di discriminazione lo mostra.
6. **Lo scorer ufficiale ha una versione 0.18.0,** pubblicata il 1° ottobre; noi usiamo la 0.16.0. Gli organizzatori
   chiudono attivamente le «leve del sottomettitore» (#247, #348 nelle note del codice). **Prima di costruire sul
   doppio momento** va letta la differenza fra le due versioni.
7. **La classifica finale è su D/E/F,** non su A/B/C. Molte squadre in alto hanno 40–80 invii su A/B/C: ciò che vale è
   il metodo che si trasferisce, non i parametri tarati su A/B/C.

## 2. Dove siamo, membro per membro

Grezzo / scalato. Il t22 viene dal CP-0055; i ranghi dalla classifica del 2 ottobre, 22:40 CEST (script
[`leggi_classifica.py`](leggi_classifica.py)).

| | PDS | MSE norm. | nMAE | fedeltà | reach | Jaccard | media |
|---|---|---|---|---|---|---|---|
| t22 (nostro) | 0,787 / 0,634 | 3,06 / 0 | 0,927 / 0,120 | 0,497 / −0,052 | 0,195 / 0,131 | 0,036 / 0,014 | 0,141 |
| rango 100 | 0,853 / 0,782 | 0,803 / 0,195 | 0,927 / 0,122 | 0,511 / −0,005 | 0,267 / 0,212 | 0,026 / −0,012 | 0,216 |
| rango 20 | 0,854 / 0,786 | 0,697 / 0,306 | 0,886 / 0,188 | 0,517 / 0,015 | 0,287 / 0,235 | 0,033 / 0,007 | 0,257 |
| rango 1 | 0,897 / 0,881 | 0,322 / 0,702 | 0,782 / 0,364 | 0,555 / 0,147 | 0,458 / 0,429 | 0,057 / 0,070 | 0,432 |

**Lettura.**
- **MSE.** La MSE normalizzata vale 1 quando si prevede il controllo. Lo scalato diventa positivo appena il pseudobulk
  previsto è più vicino al vero del controllo: sulla classifica, scalato ≈ 0,48 − 0,37 × grezzo per i grezzi sotto 1.
  Noi siamo a 3: tre volte l'errore del «non fare niente».
- **PDS.** Il PDS non dipende dalla scala, ma dipende dalla direzione del profilo aggregato. Anche lui guadagna se il
  momento aggregato è pulito: ad esempio togliendo la parte comune a tutti i bersagli, che non discrimina.
- **I membri DE** (nMAE, fedeltà, reach) sono già vicini al rango 100: lì l'amplificazione ha funzionato.

## 3. La letteratura, per tema

### 3.1 La gara e le sue metriche

| Fonte | Che cosa dice | Che cosa implica per noi | Letto |
|---|---|---|---|
| [VCC 2026, *Cell* 2026](https://www.sciencedirect.com/science/article/pii/S0092867426009311) e [annuncio Arc](https://arcinstitute.org/news/virtual-cell-challenge-2026) | Sei linee CRISPRi, Flex, zero-shot; metriche scalate con 0 alla media del contesto e 1 a una replica; «misurare la capacità che si trasferisce» | Il criterio è la replica: nessun membro premia un'ampiezza oltre il vero | pagina Arc; articolo 403 |
| [Dietro i dati, Arc](https://arcinstitute.org/news/behind-the-data-virtual-cell-challenge-2026) | Bersagli con knockdown mediano ≥ 80%; 400 cellule per bersaglio; circa 20.000 UMI per cellula; circa 50.000 controlli per esperimento; fra le sei linee ci sono cellule staminali, linee immortalizzate e tumorali | Il gene bersaglio scende sempre molto (testa cis sicura); i bersagli sono selezionati per efficacia, non per forza della risposta | sì |
| Note nel codice di `cell_eval2` 0.16.0 (`catalog.py`, `metrics/delta.py`) | Pseudobulk = log1p dei conteggi **sommati** per gruppo, normalizzati a 5·10⁴; MSE con correzione del rumore di campionamento limitata (#247, #348); DE di Wilcoxon per cellula a CPM | Profilo aggregato e distribuzione per cellula sono separabili (§4). Gli organizzatori chiudono le leve una a una | sì, codice |
| [Distanze e scala nel PDS, arXiv 2511.16954](https://arxiv.org/abs/2511.16954) | Il PDS dipende molto dalla distanza e dalla scala; col coseno tende a un coseno sui segni | Col coseno ufficiale contano direzione e segno del profilo aggregato, non l'ampiezza | abstract |
| [VCC 2025, i vincitori](https://arcinstitute.org/news/virtual-cell-challenge-2025-wrap-up) | 1° BioMap (scFoundation più frequenza DEG e media come feature), 2° XLearning (FCN su pseudobulk più ESM-2, residui), 3° TransPert (sole statistiche riassuntive fra linee più scala lineare per il PDS); premio generalista ad Altos (flow matching) | Anche nel 2025 vincono ibridi statistici. Il terzo posto è il parente più stretto della nostra ricetta | sì |

### 3.2 Modelli profondi contro modelli semplici

| Fonte | Che cosa dice | Implicazione | Letto |
|---|---|---|---|
| [Ahlmann-Eltze, Huber, Anders, *Nat. Methods* 2025](https://doi.org/10.1038/s41592-025-02772-6) | Cinque foundation model e due reti non battono baseline lineari né la media | Ogni rete va confrontata con trasferimento e media, come già fa il protocollo | abstract |
| [Systema, Viñas Torné et al., *Nat. Biotechnol.* 2025](https://brbiclab.epfl.ch/projects/systema) | I punteggi alti sono spesso variazione sistematica (perturbato contro controllo) e non effetto specifico | È esattamente il difetto del t29: profilo comune, PDS 0,503 | pagina |
| [Diversity by Design, arXiv 2506.22641](https://arxiv.org/abs/2506.22641) e [«DL *do* outperform», bioRxiv 2025](https://www.biorxiv.org/content/10.1101/2025.10.20.683304.full.pdf) | Con metriche pesate sui DEG la media perde; la perdita WMSE riduce il collasso sulla moda | Perdita da usare se si addestra ancora una rete: pesare i geni DE e non la MSE piatta | abstract |
| [PerturBench, arXiv 2408.10609](https://arxiv.org/abs/2408.10609); [benchmark «in the wild», arXiv 2604.27646](https://arxiv.org/abs/2604.27646) | In condizioni severe le prestazioni crollano. Unire dataset alla cieca può peggiorare. I lineari catturano il trend globale ma non l'effetto fine | Coerente coi nostri CP: aggiungere sorgenti aiuta solo dove coprono il bersaglio | abstract |
| [Valutazione bloccata, arXiv 2608.00152](https://arxiv.org/abs/2608.00152) | Su VCC un modello va bene in distribuzione e fallisce il trasferimento (ρ −0,14 e −0,27); il numero di cellule confonde la magnitudine | Il metodo del progetto (registrare prima, riserva intatta) è quello giusto | abstract |
| [Modelli tabulari (TabPFN, TabICL), Palla et al., bioRxiv 2026](https://biorxiv.org/content/10.64898/2026.06.28.735106) | Su pseudobulk battono PRESAGE, scGPT, scLAMBDA e STACK | Candidato economico per un residuo per gene, se ci fosse tempo; non prioritario | abstract |

### 3.3 Trasferimento fra contesti (il cuore del 2026)

| Fonte | Che cosa dice | Implicazione | Letto |
|---|---|---|---|
| [Molina e Zhang, bioRxiv 2026](https://www.biorxiv.org/content/10.64898/2026.07.24.740459v1) | Risposta = globale + linea + effetto conservato β + interazione γ. Su quattro schermi CRISPRi: β porta il 30% dell'energia, γ il 21% ma riproducibile solo a metà. La parte globale si ricava dall'espressione dei controlli. Modelli lineari o MLP «allineati alle componenti» battono lo stato dell'arte | **La guida più diretta per la gara.** Prevedere bene β (trasferimento) e la parte globale; non investire su γ | abstract |
| [Entrata VCC 2026 con codice (yashnil)](https://github.com/yashnil/virtual-cell-generalization) | Stessa scomposizione. β 80,8% riproducibile, γ 49,5%. I prior di annotazione crollano fuori (r da 0,51 a 0,02–0,06). Fusione a pesi uguali: 0,139, rango 370; generatore, riponderazione e nuove sorgenti non hanno migliorato | Replica indipendente del nostro plateau, con le stesse conclusioni | README |
| [Entrata VCC 2026 con codice (MMatinGerami)](https://github.com/MMatinGerami/zero-shot-perturbation) | Correlazione corretta per il rumore fra linee circa 0,47. Rinormalizzare la media delle sorgenti (direzione del consenso, norma delle singole) migliora la fedeltà. Correggere per la profondità del knockdown peggiora. 0,137 | Il «tetto del trasferimento» è vicino; il margine sta nell'emissione e nella parte comune | README |
| [TxPert, arXiv 2505.14919](https://arxiv.org/abs/2505.14919) (Valence/Recursion) | Grafi di conoscenza per perturbazioni e linee non viste | Utile per i bersagli senza sorgente (J), non per quelli coperti | abstract |
| [LPM, *Nat. Comput. Sci.* 2025](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC12638242/) | Perturbazione, lettura e contesto come assi separati | Stessa idea di R-LEAD; non mostra contesti davvero nuovi a livello di gara | abstract |
| [STATE (Arc), bioRxiv 2025](https://www.biorxiv.org/content/10.1101/2025.06.26.661135) e [Stack (Arc), bioRxiv 2026](https://www.biorxiv.org/content/10.64898/2026.01.09.698608.full.pdf) | Modelli enormi degli organizzatori; Stack fa in-context learning su cellule | In classifica le entrate scGPT/State stanno intorno a 0,16–0,17; da noi Stack A/B è stato negativo (29/09) | abstract |

### 3.4 Dati

| Fonte | Ruolo | Note |
|---|---|---|
| [Replogle et al., *Cell* 2022](https://doi.org/10.1016/j.cell.2022.05.013) | K562 genome-wide e RPE1 | già nella ricetta |
| [Nadig et al., *Nat. Genet.* 2025 (TRADE)](https://pmc.ncbi.nlm.nih.gov/articles/pmid/40513557) | HepG2, Jurkat; un bersaglio tipico muove circa 45 geni, un essenziale oltre 500 | banco HepG2; il pannello di gara è più vicino agli «essenziali» per numero di DE (circa 340 in A) |
| [X-Atlas/Orion, bioRxiv 2025](https://www.biorxiv.org/content/10.1101/2025.06.11.659105v1) | HCT116 e HEK293T genome-wide; l'abbondanza di sgRNA fa da dose | già nella ricetta (licenza NC-SA, §4 PROGETTO punto 10) |
| [Zhu et al. (Marson), bioRxiv 2025](https://www.biorxiv.org/content/10.64898/2025.12.23.696273.full.pdf) | CD4 genome-scale **Flex**, quattro donatori | già nella ricetta |
| Jiang et al. 2025 (A549, HT29, MCF7, BxPC3, HAP1), VCC 2025 H1, KOLF2.1J, HipSci, VIPerturb-seq, LINCS L1000 | citati nelle descrizioni della classifica | H1 della gara 2025: decisione aperta del proprietario |
| [Illumina Billion Cell Atlas](https://www.statnews.com/2026/01/13/illumina-billion-cell-atlas-ai-drug-development/) | CRISPR su oltre 200 linee, non pubblico | probabile vantaggio del primo in classifica («iCell»); per noi inaccessibile |

### 3.5 Biologia del CRISPRi

Il CRISPRi spegne anche i geni il cui promotore è vicino a quello del bersaglio (promotori bidirezionali,
[Isoform Perturb-seq](https://isoform-specific-perturb-seq.readthedocs.io/en/stable/scripts/3_analysis_scripts/5_genekd_neighbouring_gene_expression.html)).
Un'entrata in classifica dichiara una regola misurata sull'H1 2025: tetti di −0,22 log2 fra 2 e 10 kb e di −0,12 fra 10
e 50 kb dal TSS. Vale per ogni contesto, quindi si trasferisce a D/E/F.

## 4. Che cosa fanno i primi, dalle loro descrizioni pubbliche

Sono dichiarazioni degli autori, non verificate; le entrate sono anonimizzate qui.
- **Due momenti.**
  - «DE moment» per le cellule, «pooled/bulk moment» per il pseudobulk, con ampiezze diverse (dichiarate: «log2fc
    amplitude» 0,75–1,5, «bulk amplitude» 0,30–0,50).
  - Varianti: «16 carriers», «carrier fraction», «sampling-refund ratio» portato a 0,95.
  - Un'entrata riporta la MSE grezza scesa da 5,1 a 1,68 cambiando solo l'alfa del momento aggregato, da 0,55 a 0,25.
- **Ripartizione dell'ampiezza per accordo fra sorgenti:** ampiezza aggregata per bersaglio proporzionale a A¹ ×
  m^−0,875, con A l'accordo fra sorgenti e m la magnitudine, tagliata in [0,33; 3] a energia totale costante. Si
  ritrova in almeno tre entrate fra il 18° e il 201° posto.
- **Rimozione del modo comune** per contesto («common subtract 0,5», «centred per context»), e rinormalizzazione alla
  norma originale del bersaglio dopo la fusione.
- **Legge cis dei vicini** (§3.5) e prior cis appreso.
- **Perdite allineate allo scorer** nelle poche reti dichiarate: InfoNCE sui bersagli per il PDS, MSE relativa, L1,
  teste di segno e di DE.
- **Le sorgenti** sono quasi le stesse nostre: K562 GWPS, Orion, CD4, KOLF, HipSci, VIPerturb, L1000, H1 2025.

**Lettura.** Il metodo dei primi 100 è in gran parte **la nostra ricetta più un'emissione migliore**, non un modello
diverso. Il primo (0,432, rango 1) è probabilmente fuori portata: dati privati su centinaia di linee. Il blocco
0,28–0,30 contiene più righe con membri identici (stesso pacchetto da account diversi): non va preso come riferimento
di metodo.

## 5. Le strade, in ordine di guadagno atteso per giorno di lavoro

Ogni strada:
- si prova prima sui banchi locali con lo scorer vero (HepG2 tenuto fuori, K562 dell'azione 4);
- ha una regola registrata prima;
- arriva alla classifica solo se il banco la conferma.

Le stime di guadagno sono **ordini di grandezza** ricavati dal §2, non previsioni registrate.

| # | Strada | Perché | Guadagno possibile sulla media | Costo | Rischio |
|---|---|---|---|---|---|
| 0 | **Leggere `cell_eval2` 0.18.0** (diff con 0.16.0) | Se chiude la separazione dei momenti, la strada 1 cambia | — | 1 ora; serve l'ok al download del pacchetto | nessuno |
| 1 | **Emettitore a due momenti:** pseudobulk con ampiezza ridotta e direzione pulita, cellule con l'ampiezza attuale | Il 43% del divario col rango 100 è MSE; noi abbiamo il ×1,576 su entrambi i momenti | da +0,02 a +0,05 (MSE scalata da 0 a 0,1–0,3) | 2–4 giorni: generatore, test, banco | che lo scorer finale lo chiuda; zona grigia se si usano cellule «portatrici» con profondità estreme (§6) |
| 2 | **Ampiezza per bersaglio dall'accordo fra sorgenti e rinormalizzazione dopo la fusione** | Alza PDS e reach senza energia in più | da +0,005 a +0,02 | 1–2 giorni, codice del trasferimento esistente | sovradattamento ad A/B/C; si sceglie sui banchi |
| 3 | **Modo comune:** togliere dal momento aggregato la parte comune ai 300 bersagli e sostituirla con una stima del modo comune del contesto | Il PDS cresce se la parte comune non discrimina; la MSE se il modo comune è giusto (la parte globale si prevede dai controlli, Molina e Zhang) | da +0,005 a +0,02 | 2 giorni | stimare il modo comune è esso stesso un trasferimento |
| 4 | **Legge cis dei vicini (2–50 kb)** | Si trasferisce a ogni contesto; piccola ma sicura | +0,001–0,003 | mezza giornata | basso |
| 5 | **Prontezza per D/E/F:** prova generale piena, identificazione delle linee dai controlli il 22/10, ricerca di sorgenti della stessa linea, catena di 24 ore | Il set finale è l'unico che conta; con 2 invii al giorno e upload di ore, una catena lenta costa invii | evita perdite | 2–3 giorni (più 17 GB liberi) | alto se non si fa |
| 6 | **R-LEAD a tempo limitato:** solo se la discriminazione `ident` sulla classe C supera 0,65; poi come correzione del trasferimento o per i bersagli scoperti | La letteratura dice che γ non si prevede; la rete serve dove il trasferimento manca | incerto; probabilmente piccolo | già in corso; più un kernel di valutazione | basso se resta a tempo |
| — | **Non consigliato:** fine-tuning di STATE, scGPT o Stack; reti più grandi; nuove sorgenti alla cieca | Letteratura e classifica concordi | — | — | — |

**L'ordine dipende dalla strada 0.** Se la 0.18 lascia aperta la separazione, la 1 è la priorità e le 2–4 si innestano
sul momento aggregato. Se la chiude, le 2–4 restano e la MSE si attacca solo con la direzione (3).

## 6. Regole e correttezza

- **Il regolamento** ammette qualunque strategia e qualunque dato pubblico (pagina Arc).
- **Il doppio momento:** fra le leve che gli organizzatori hanno chiuso nel codice (#247, #348), alcune erano proprio
  sul rumore di campionamento del pseudobulk.
- **Un emettitore onesto:** cellule plausibili, profondità nel range del controllo, pseudobulk che è la previsione
  migliore dell'aggregato. È una previsione di due quantità vere: la media e la distribuzione.
- **Un emettitore con poche cellule a profondità estrema,** costruite solo per spostare la somma, sfrutta lo scorer e
  può essere chiuso o giudicato sleale.
- **Proposta:** solo la versione onesta. Se il dubbio resta, una domanda agli organizzatori sul forum prima di un
  invio.
- **L'invio su D/E/F** resta, come sempre, con l'ok esplicito di Alfredo.

## 7. Calendario proposto

| Giorni | Che cosa |
|---|---|
| 3–4 ott | Strada 0. Lettura del training r1 e, con l'ok, della discriminazione. Registrazione del protocollo della strada 1 |
| 5–9 ott | Strada 1 sui banchi locali; 2 e 4 in parallelo. Un solo invio di conferma se il banco passa |
| 10–14 ott | Strada 3; scelta dei parametri **stabili** fra A/B/C e banchi, non i massimi di A/B/C |
| 15–21 ott | Strada 5: prova generale piena, catena di 24 ore, sorgenti candidate per linee nuove; R-LEAD chiusa o integrata |
| 22 ott – 5 nov | Set finale: identificazione, produzione, 2 invii al giorno con previsione registrata, scelta finale |

## 8. Decisioni per Alfredo

1. L'ok a scaricare `cell_eval2` 0.18.0, un pacchetto pubblico, per leggerne le differenze.
2. Se perseguire la strada 1, e in quale forma (§6).
3. Se condividere questa pagina con Davide e la lead, che lavorano sul generatore (stadio 45).
4. Il repository è pubblico, e questa pagina descrive la nostra strategia per i prossimi 20 giorni: se pusharla subito o
   tenerla locale fino al 5 novembre.
