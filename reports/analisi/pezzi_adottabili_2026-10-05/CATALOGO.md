# Pezzi che possiamo fare nostri — 5 ottobre 2026

**Tipo:** proposta e interpretazione. Non è una misura nuova, non è un punteggio VCC, non cambia la ricetta.

**Perimetro.** Modelli e blocchi letti il 5 ottobre 2026, in questa sessione, di cui si può copiare un pezzo nel residuo della rete ancorata al transfer congelato. Entra chi ha un'equazione o un modulo che obbliga il bersaglio a entrare nel residuo. Resta fuori chi sostituirebbe la ricetta, chi porta pesi addestrati sulle risposte di perturbazione, e chi è rimasto un nome senza pagina aperta.

**Che cosa «fare nostro» vuol dire qui.** Si riscrive l'equazione nel nostro residuo, con attribuzione. Non si importa un checkpoint, non si copia un repository intero, non si impilano i blocchi. Un candidato si prova da solo contro l'ancora congelata a pesi uguali. Se non regge la discriminazione dei bersagli, si passa al successivo.

Le pagine riaperte durante la stesura sono elencate in [VERIFICHE.md](VERIFICHE.md). Dove una formula non è stata riletta sul paper, è segnata come proposta nostra o come pretesa del rapporto di Antigravity.

## Il difetto che il pezzo deve chiudere

Nella rete dell'ibrido selettivo (`reports/modelli/ibrido_selettivo_2026-10-04/cellnet.py`) i controlli sono ridotti a un vettore prima che il bersaglio entri nel calcolo: in modalità `mean` si somma il profilo (righe 375–379), in modalità `cells` si fa la media degli embedding (riga 382). Il residuo è poi `delta_out(delta_low(h))` (riga 413). `delta_out` è un `Linear` dal rango a tutti i geni, pesi e bias a zero all'inizio (righe 341–345). Con il guadagno fisso la previsione è ancora più questo delta (righe 417–418).

Un lineare libero, con il contesto già mediato, può ignorare il bersaglio e imparare uno spostamento uguale per tutti. È il meccanismo ipotizzato in [S-006](../../../docs/STRADE.md): togliendo la media sui bersagli, il PDS risale e la parte specifica non aggiunge. [S-009](../../../docs/STRADE.md) è il primo tentativo di correzione vincolata: in gara il t30 è 0,135249, sotto il t25 (CP-0064). La guardia già nel codice non va reinventata. `guards.py` misura, sulle coppie di validazione interne, il rango di discriminazione dello spostamento contro l'ancora, il rapporto di ampiezza e la quota comune `||media di R||² / media di ||R||²`. `train_cellnet.py` si arresta quando un braccio viola una condizione per `--guard-patience` controlli di fila. La soglia di default della quota comune nel codice è 0,5 (`guards.py`, `breaches`).

## Precedenti

| Voce | Che cosa ha già mostrato | Come un pezzo di questo catalogo se ne distingue |
|---|---|---|
| S-001 | La rete al posto del transfer, inviata (t29), perde | L'ancora resta. Il pezzo è solo il residuo |
| S-002 | Lo stato cellulare aiuta contro il profilo medio, e perde comunque il PDS contro il transfer | Non si rimette una testa libera dal rango a tutti i geni |
| S-006 | La correzione appresa è in gran parte uno spostamento comune | Il residuo nuovo non ha un termine che il contesto produce da solo |
| S-007 | Guadagni per gene, bilineare e rete sul pseudobulk dai controlli medi: nessun beneficio | Un prodotto bersaglio × contesto non è quel bilineare già provato: lì la correzione partiva dai controlli medi |
| S-008 | Encoder, cancelli, rete dei contesti, relazionale, rete sulle sorgenti, Stack | Si copia un'equazione, non un'altra architettura intera |
| S-009 | Ibrido v1: testa comune, guadagno fisso, penalità, selettore. Banco locale poi t30 sotto il transfer | La testa comune resta un ramo di training. Non è il residuo esportato |

Il segnale precoce resta quello di S-006 e della guardia v5: discriminazione, ampiezza, quota comune. Una loss contrastiva che allontana i residui può essere soddisfatta da uno spostamento comune più un rumore piccolo specifico del bersaglio. Non è il primo cambiamento.

## Ordine proposto

Un blocco alla volta. L'ordine è una proposta, non un risultato.

### 1. AMMI, senza l'effetto principale del contesto

**Verificato in stesura.** L'AMMI (additive main effects and multiplicative interaction) scompone una tabella genotipo × ambiente. La forma letta su una pagina PMC di orzo primaverile, che cita Gauch e Zobel 1990, è:

`y_ge = μ + α_g + β_e + Σ_n λ_n γ_gn δ_en + Q_ge`

La stessa scomposizione — media, scarto del genotipo, scarto dell'ambiente, assi moltiplicativi, residuo — è nella pagina degli atti 1989 su newprairiepress.org (`agstatconference/1989/proceedings/22`). Un PDF di Srinivasan ospitato da ssca.org.in attribuisce il modello a Gauch 1988, Zobel et al. 1988 e Gauch 1992: quella data 1988 è una citazione nel PDF, non una pagina del 1988 aperta qui. Frontiers in Physiology, 2013, lo scrive `μ_ij = μ + G_i + E_j + Σ_k b_ik z_jk + ε_ij`.

**Che cosa copiare.** `α_g` è l'ancora congelata: l'effetto principale del bersaglio, già stimato dal transfer. `β_e` è l'effetto principale del contesto: è lo spostamento comune, e si toglie. Il residuo che si impara è la somma dei prodotti. Per un contesto nuovo, il punteggio `δ_e` si ricava dai soli controlli di quel contesto. Ricavarlo dalle risposte di knockdown del contesto di test è leakage.

**Limite, interpretazione.** L'ANOVA classica vuole la matrice completa bersaglio × contesto sui contesti di training. Un contesto mai osservato non si ottiene rifittando quelle rese. La previsione è una regressione fattoriale: i punteggi del contesto nuovo sono funzione dei controlli, non un asse stimato sulle risposte assenti. Non si importa codice di prove agronomiche. Il denso G×E del CIMMYT che Antigravity ha messo al posto di questa equazione è un MLP con bias (`h = σ(Wh + b)` nel suo rapporto): quel bias è di nuovo lo spostamento comune.

### 2. STAR, prodotto dei pesi, solo sul residuo

**Verificato in stesura.** Xiang-Rong Sheng, Liqin Zhao e coautori, Alibaba, CIKM 2021. arXiv [2101.11427](https://arxiv.org/abs/2101.11427), DOI 10.1145/3459637.3481941. Il testo HTML di ar5iv dice che la rete di ogni dominio è il prodotto elemento per elemento dei pesi della rete condivisa e dei pesi della rete specifica di quel dominio, e che dal tardo 2020 il modello è in servizio nel display advertising di Alibaba. L'abstract arXiv parla di miglioramento medio 8,0% di CTR e 6,0% di RPM: è il loro numero di produzione, non un nostro banco.

**Che cosa copiare.** Sul solo residuo, `W(bersaglio) = W_condiviso ⊙ W_specifico(e_bersaglio)`. `W_specifico` parte da zero, così il residuo parte da zero e l'ancora non viene moltiplicata via. Se `W_specifico` diventa costante fra i bersagli, la quota comune della guardia lo ferma.

**Limite.** L'inizializzazione a zero e il fatto di non toccare l'ancora sono nostri. Nel paper le due reti, condivisa e specifica, formano l'intero predittore. La licenza del codice non è stata letta.

### 3. PLE, un esperto condiviso sottratto e uno specifico

**Verificato in parte.** Hongyan Tang e coautori, Tencent. Progressive Layered Extraction, RecSys 2020, DOI [10.1145/3383313.3412236](https://doi.org/10.1145/3383313.3412236). L'abstract ACM descrive la separazione esplicita fra componenti condivise e componenti specifiche del compito, e il fenomeno «seesaw»: un compito migliora a spese di un altro. Numeri loro, sul raccomandatore video di Tencent: +2,23% di view-count e +1,84% di watch time rispetto ai modelli multi-task dello stesso confronto.

**Correzione.** L'arXiv `2007.02747` citato da Antigravity non è questo paper. Aperto il 5 ottobre, quella pagina è GAG, Qiu, Yin, Huang e Chen, University of Queensland, SIGIR 2020, DOI 10.1145/3397271.3401109. L'identificativo arXiv di PLE non è stato trovato in questa stesura. L'equazione `y_k = Σ softmax(W_k · x)_i E_i(x)` è segnata «inferred» nel rapporto: non è stata copiata da una pagina del paper.

**Che cosa copiare, proposta.** Uno strato solo. Un esperto condiviso, letto e sottratto. Un esperto specifico, il cui cancello vede solo il bersaglio. Non un esperto per gene, non la pila intera. Il cancello può mettere tutta la massa sull'esperto condiviso: per questo PLE viene dopo STAR. Il percorso `ple.py` in DeepCTR, nominato in sessione, non è stato riaperto.

### 4. HorNet, il cancello calcolato dal bersaglio

**Verificato in stesura.** Yongming Rao, Wenliang Zhao, Yansong Tang, Jie Zhou, Ser-Nam Lim, Jiwen Lu. NeurIPS 2022, arXiv [2207.14284](https://arxiv.org/abs/2207.14284). Il `g^nConv` è una convoluzione gated ricorsiva: interazione spaziale di ordine alto, adattata all'input. Repository [raoyongming/HorNet](https://github.com/raoyongming/HorNet): la pagina About vista oggi dichiara licenza MIT.

**Che cosa copiare.** Il cancello, e lo si calcola dall'embedding del bersaglio. Il contesto già mediato non è l'input che decide il cancello. I pesi ImageNet e la spina dorsale intera restano fuori. L'equazione ricorsiva del paper non è stata ricopiata dal PDF in questa stesura: si parte dall'abstract e dal repository, e si rilegge la formula prima di scrivere il modulo.

### 5. Una rete regolativa dai soli controlli, dopo che un prodotto tiene il PDS

Tre versioni, una sola, e solo come maschera o come intervento su un'equazione lineare. Nessuna è un predittore di delta con segno da importare.

**scTenifoldKnk.** Repository [cailab-tamu/scTenifoldKnk](https://github.com/cailab-tamu/scTenifoldKnk). La FAQ `plotKO_FAQ.md`, riletta oggi, risponde no alla domanda se `plotKO` indichi salita o discesa: i valori `FC` vengono da un test chi-quadro e sono sempre positivi; sono un'ampiezza, non una direzione. La FAQ cita il paper su Patterns, 2022. **Si copia una maschera di quali geni si muovono. Il segno resta all'ancora.** La pagina del paper non è stata riaperta: il dettaglio «si azzera la riga del gene nella adiacenza» resta da rileggere prima di implementare. Costruire la rete dai controlli del contesto di test è ammesso. Usare le risposte di perturbazione del test no.

**CellOracle.** Nature 2023, [s41586-022-05688-9](https://www.nature.com/articles/s41586-022-05688-9). L'abstract, riletto oggi, descrive perturbazioni in silico di fattori di trascrizione a partire da dati wild-type, con una rete regolativa e la propagazione del segnale. Le issue GitHub #205 (6 luglio 2024) e #239 (22 ottobre 2025) sono domande di utenti: il simulatore, nella loro lettura della documentazione, è pensato per i TF. Non sono una risposta dei maintainer. **Copre i regolatori con archi uscenti, non ogni bersaglio CRISPRi.** Non si importano pesi, compresi quelli di zebrafish. La licenza del codice non è stata letta.

**DeepSEM.** Hantao Shu e coautori, Nature Computational Science 2021, doi 10.1038/s43588-021-00099-8. Repository [HantaoShu/DeepSEM](https://github.com/HantaoShu/DeepSEM). Il README, nel testo restituito dalla ricerca, corregge le equazioni del paper in `X = X W^T + Z`, `H_Z = (I − W^T)^{-1} Z`, e una loss con attesa su `Z`, KL e penalità L1 su `W`. I compiti pubblicati nel README sono inferenza della rete, embedding e simulazione di scRNA realistici. **Un knockout virtuale, ottenuto fissando il gene e togliendo la sua equazione, sarebbe un uso nostro di quel SEM lineare, non un risultato che loro hanno pubblicato.** Il file `LICENSE` c'è; il suo testo non è stato letto. Il PDF di Nature non è stato aperto.

## Stessa famiglia del prodotto: non un secondo esperimento in parallelo

Questi pezzi chiudono lo stesso buco di STAR. Se ne prova uno se il precedente è fermo, non insieme.

**Prodotto di Hadamard a basso rango (MLB).** Jin-Hwa Kim, Kyoung Woon On, Woosang Lim, Jeonghee Kim, Jung-Woo Ha, Byoung-Tak Zhang. arXiv [1610.04325](https://arxiv.org/abs/1610.04325), ICLR 2017. Repository [jnhwkim/MulLowBiVQA](https://github.com/jnhwkim/MulLowBiVQA), in Lua: la pagina About vista oggi dichiara BSD 3-Clause e un brevetto pending sul prodotto elemento per elemento per il visual question answering. Si legge quel brevetto prima di distribuire un modulo che lo implementa. **Proposta nostra, formula non ricopiata dal PDF:** tre mappe lineari senza bias, prodotto elemento per elemento fra la proiezione del bersaglio e la proiezione del contesto, proiezione finale a init zero. Il repository non si copia. Un gist PyTorch in cui `nn.Linear` tiene il bias di default non è il blocco: quel bias è lo spostamento.

**FiLM, solo la scala.** Ethan Perez, Florian Strub, Harm de Vries, Vincent Dumoulin, Aaron Courville, AAAI 2018, DOI [10.1609/aaai.v32i1.11671](https://doi.org/10.1609/aaai.v32i1.11671). Formula letta sul PDF in ResearchGate: `FiLM(F | γ, β) = γ F + β`. **Si tiene `γ` del bersaglio. `β` resta zero:** nell'equazione pubblicata è il termine additivo. La licenza del repository `ethanjperez/film` non è stata verificata.

**Un solo cross-attention con cancello alla Flamingo.** Alayrac e coautori, NeurIPS 2022. Nel PDF della conference, la figura del blocco è `y = y + tanh(α) * attention(q=y, kv=x)`, con `α` inizializzato a 0, così all'inizio il ramo nuovo non sposta il modello congelato. **Proposta nostra:** la query è il bersaglio, chiavi e valori sono le cellule di controllo, e questo blocco sostituisce la media in `context()`. Si prova dopo che un prodotto tiene il PDS, da solo. Il nome «gated cross-attention» che Antigravity ha messo su IP-Adapter è il cancello di Flamingo; IP-Adapter, nel rapporto, è un cross-attention disaccoppiato. I pesi DeepMind non si importano. La classe `GatedCrossAttentionBlock` di `lucidrains/flamingo-pytorch` non è stata riaperta in questa stesura.

**Guida senza classificatore, sul ramo già presente.** Il residuo esportato è `f(contesto, bersaglio) − f(contesto, vuoto)`. Il ramo vuoto è `common()` in `cellnet.py` (righe 423–428), oggi escluso dalla previsione esportata. Se la differenza è costante fra i bersagli, la quota comune la ferma. Anno e arXiv di Ho e Salimans non sono stati riaperti in questa stesura: il rapporto di Antigravity segna il 2021 come non verificato.

**Iperrete di lettura.** Proposta della sessione: l'embedding del bersaglio genera la matrice di uscita, a init zero; una matrice costante fra i bersagli è di nuovo lo spostamento. Il paper di Ha, Dai e Le e il repository `g1910/HyperNetworks` non sono stati riaperti mentre si scriveva questo report. Resta in lista come idea, non come equazione verificata.

## Pezzi biologici, senza i loro pesi

**PertAdapt.** Repository [BaiDing1234/PertAdapt](https://github.com/BaiDing1234/PertAdapt), README riletto. Adattatore sopra scFoundation e AIDO.Cell: attenzione mascherata dalla somiglianza di Gene Ontology (il peso va a −∞ se la coppia di geni non condivide un termine GO; il README indica `go_mask_19264.npz`) e una loss adattiva fra geni sensibili e geni insensibili alla perturbazione. bioRxiv [10.1101/2025.11.21.689655](https://www.biorxiv.org/content/10.1101/2025.11.21.689655v1): l'abstract parla di perturbazioni genetiche non viste, regime a pochi dati e perturbazioni multiple. **La frase di Antigravity «tested unseen cellular contexts» non è in quell'abstract.** Si può copiare la maschera GO e l'idea della loss. I pesi dei foundation model restano fuori.

**scDFM, solo il modo in cui la perturbazione entra nell'attenzione.** Chenglei Yu, Chuanrui Wang, Bangyan Liao, Tailin Wu, Westlake e Zhejiang. arXiv [2602.07103](https://arxiv.org/abs/2602.07103), ICLR 2026 nel titolo del repository [AI4Science-WestlakeU/scDFM](https://github.com/AI4Science-WestlakeU/scDFM). La pagina HTML dichiara licenza CC BY 4.0 per il paper. Il PAD-Transformer condiziona la velocità al contesto di controllo e a un embedding di perturbazione, con attenzione mascherata da un grafo di geni e attenzione differenziale fra controllo e perturbazione. Il README nomina Norman e un sottoinsieme Combosciplex di Sci-Plex. **Non è una prova di contesto nuovo per CRISPRi.** Si lascia fuori il flow matching intero e ogni checkpoint. Una classe di nome `PerturbationEmbedding` non compare nelle pagine riaperte: non va citata come modulo trovato. La licenza del codice non è stata letta.

**sc2Flow, maschera poi ampiezza.** Non è nel rapporto di Antigravity: è stato aggiunto in verifica. Hanwen Lyu e Jiawei Luo, Hunan University, IJCAI 2026, DOI [10.24963/ijcai.2026/757](https://www.ijcai.org/proceedings/2026/757). Predice risposte a perturbazioni chimiche (Sci-Plex3 nel abstract): prima la maschera binaria dei geni espressi, poi il livello quantitativo. Il loro «mean prediction bias» è la tendenza dei regressori a dare la media fra cellule, sotto farmaci. È un parente del nostro spostamento comune, non la stessa misura. **Si copia la separazione maschera / ampiezza. Il modello chimico e i suoi pesi restano fuori.** I farmaci non diventano il grosso del training.

**Memoria dei delta dei vicini, stile GenePert.** Proposta della mattina, paper non riaperto in questa stesura. Dove l'ancora ha poco supporto, il residuo è una media non parametrica dei delta reali di training dei vicini del bersaglio in un embedding di gene (GenePT o un descrittore già nostro). Nessun checkpoint. Va scritto come protocollo a parte, con i precedenti sopra, prima di qualsiasi corsa.

## Letti oggi e non da copiare

| Nome | Perché resta fuori |
|---|---|
| STATE (Arc) | Sostituirebbe il transfer. Un checkpoint di perturbazione addestrato su studi che includono le linee del nostro banco non è una generalizzazione. Il paper non è stato riaperto in questa stesura; la conclusione è quella della sessione |
| MultiFlow | Terzo nella classifica di Antigravity del primo catalogo. Pagina non riaperta. Non entra finché non si sa se chiede ATAC e se il campo di velocità è specifico del bersaglio |
| scELMo, scDisInFact, DynPerturb, UNAGI, veloAgent, SLIM, CoupleVAE, UniPert, CaLMFlow | Nel primo rapporto, quasi tutti senza modulo nominato nello snippet. Licenze e pesi spesso «not named». Non verificati |
| T2I-Adapter | Nel terzo rapporto l'equazione inferita è `F_frozen + α · Adapter(C)`. È il percorso additivo che già abbiamo |
| MTDL denso, CIMMYT, G3 2018 | L'inquadramento G×E è quello di AMMI. Lo strato che Antigravity ha scritto ha il bias |
| AdaIN | Nel secondo rapporto l'equazione non c'è. In sessione si era detto che la media di stile è lo spostamento. Pagina non riaperta: non si copia |
| ControlNet | Le zero-convolution proteggono il modello congelato al passo 0. `delta_out` è già a init zero e può comunque ignorare il bersaglio dopo il training |
| IRM | È una loss. Se l'ambiente della penalità è il bersaglio, la penalità premia chi lo ignora. Pagina non riaperta |
| MoE / Switch | Utile solo se il router vede il bersaglio e non il contesto già mediato. L'URL `t5x` del rapporto non è il paper del 2017. Non riaperto |
| Regressione a rango ridotto | Il rapporto la data 2022, non verificato. Non riaperta |
| SKNet, Involution, CBAM, convoluzione dinamica, WeightNet, ODConv | Una famiglia: i coefficienti del kernel devono dipendere dal bersaglio. Provarne tre è lo stesso esperimento. Il rapporto attribuisce SKNet e Involution a Tsinghua; quelle pagine non sono state riaperte, quindi l'affiliazione resta non verificata e i due arXiv di ODConv (`2201.05046`) e WeightNet (`2002.11983`) non sono confermati |
| PuLID, FreeU | Lezioni nominate in sessione (una loss di allineamento; uno split fra frequenze). Pagine non riaperte. Non precedono il prodotto |
| GenKI, HyperGate | URL ed equazioni segnati «inferred» da Antigravity. Non aperti |
| Modelli farmaco–bersaglio (BACPI, DeepDTA e simili) | Secondari: i farmaci non devono dominare il training. Pagine non riaperte in questa stesura |

## Che cosa non è stato fatto

Nessun modulo è stato scritto in `cellnet.py`. Nessun training, nessun banco, nessun invio, nessun push. Le licenze sono dichiarate solo dove una pagina aperta oggi le mostra: HorNet MIT, MLB BSD 3-Clause più brevetto pending, paper scDFM CC BY 4.0. Le altre restano non verificate.
