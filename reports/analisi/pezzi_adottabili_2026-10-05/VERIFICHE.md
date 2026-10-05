# Verifiche della stesura — 5 ottobre 2026

Il catalogo è stato scritto lo stesso giorno delle ricerche. Qui si separa che cosa è stato riaperto mentre si scriveva il report da che cosa resta una pretesa del rapporto di Antigravity o una proposta della sessione.

Orologio della macchina all'inizio della stesura: 2026-10-05 18:05:09 +02:00 (`Get-Date`).

## Ricerche condivise

Tre corse Antigravity in modalità `read`, solo ricerca web, modello non registrato (`model` null in `meta.json`). I testi integrali sono in [agenti/](agenti/).

| Run | Stato | Durata | Caratteri | Brief nell'hub, fuori repository |
|---|---|---|---|---|
| `20261005-132043-predittori` | `failed`, exit code 0, 0 caratteri | 233,3 s | 0 | `predittori-blocchi-2026-10-05.md` |
| `20261005-132632-predittori-web` | `done`, exit 0 | 211,1 s | 6.467 | `predittori-blocchi-web-2026-10-05.md` |
| `20261005-141332-blocchi-reti` | `done`, exit 0 | 171,2 s | 8.977 | `blocchi-qualsiasi-rete-2026-10-05.md` |
| `20261005-153130-blocchi-ovunque` | `done`, exit 0 | 390,5 s | 7.277 | `blocchi-ovunque-2026-10-05.md` |

Il primo errore, copiato da `meta.json`: l'agente non ha prodotto un report perché uno strumento ha chiesto il permesso `command`, che la modalità headless nega da sola. Non si allarga quel permesso.

## Pagine aperte durante la stesura

| Oggetto | Pagina | Che cosa se ne tiene |
|---|---|---|
| STAR | ar5iv HTML di arXiv 2101.11427; scheda ACM del DOI 10.1145/3459637.3481941 | Prodotto elemento per elemento dei pesi condivisi e specifici; autori Sheng, Zhao e coautori, Alibaba; CIKM 2021; in servizio dal tardo 2020 |
| AMMI | Atti 1989, newprairiepress.org `agstatconference/1989/proceedings/22`; PMC6483959 (orzo, equazione con citazione Gauch e Zobel 1990); Frontiers in Physiology 2013, 10.3389/fphys.2013.00044; PDF di Srinivasan su ssca.org.in | Equazione a effetti principali più prodotti. La data 1988 è la citazione in quel PDF, non una pagina 1988 aperta qui. Togliere `β_e` è nostro |
| PLE | ACM DOI 10.1145/3383313.3412236; scheda SciSpace | Tang e coautori, Tencent, RecSys 2020; seesaw. L'arXiv non è stato trovato |
| arXiv 2007.02747 | ar5iv HTML | Non è PLE. È GAG, Qiu, Yin, Huang, Chen, Queensland, SIGIR 2020, DOI 10.1145/3397271.3401109 |
| HorNet | arXiv 2207.14284; GitHub `raoyongming/HorNet` About | NeurIPS 2022; `g^nConv`; licenza MIT sulla pagina About. Formula ricorsiva non ricopiata dal PDF |
| scTenifoldKnk | `plotKO_FAQ.md` e `plotKO_FAQ.html` nel repository `cailab-tamu/scTenifoldKnk` | Non predice il segno; `FC` sempre positivo. Paper Patterns 2022 citato dalla FAQ, non riaperto |
| CellOracle | Nature s41586-022-05688-9; issue GitHub #205 e #239 | L'abstract è su perturbazioni di TF. Le issue sono domande di utenti, senza risposta dei maintainer nel testo letto |
| DeepSEM | Estratto di ricerca del README `HantaoShu/DeepSEM`; abstract Nature Computational Science 2021 | Equazioni corrette nel README; compiti pubblicati GRN, embedding, simulazione. `LICENSE` non letto. PDF non aperto |
| PertAdapt | README `BaiDing1234/PertAdapt`; bioRxiv 10.1101/2025.11.21.689655v1 | Maschera GO e loss adattiva. L'abstract non dice «unseen cellular contexts» |
| sc2Flow | Pagina IJCAI 2026/757 e PDF dei proceedings | Lyu e Luo, Hunan; maschera poi ampiezza; perturbazioni chimiche. Non era nel rapporto Antigravity |
| scDFM | GitHub `AI4Science-WestlakeU/scDFM`; arXiv HTML 2602.07103 | PAD-Transformer, embedding di perturbazione, Norman e Combosciplex. Licenza CC BY 4.0 sulla pagina HTML del paper. Nessuna classe `PerturbationEmbedding` in quelle pagine |
| MLB | arXiv 1610.04325; GitHub `jnhwkim/MulLowBiVQA` About; OpenReview `r1rhWnZkg` | ICLR 2017; autori Kim, On, Lim, Kim, Ha, Zhang. BSD 3-Clause e brevetto pending dichiarati sulla pagina About. Formula matriciale non ricopiata dal PDF |
| FiLM | AAAI DOI 10.1609/aaai.v32i1.11671; PDF su ResearchGate | `γ F + β`. Tenere `β` a zero è nostro |
| Flamingo | PDF NeurIPS 2022, file `960a172bc7fbf0177ccccbb411a7d800-Paper-Conference.pdf` | `y = y + tanh(α) * attention(q=y, kv=x)`, `α` init 0. Query = bersaglio è nostro |
| Guardia e rete | `cellnet.py`, `guards.py`, `train_cellnet.py` nell'ibrido selettivo; S-006 e S-009 in `docs/STRADE.md` | Media dei controlli prima del bersaglio; quota comune, rango, ampiezza; pazienza a controlli consecutivi |

## Non riaperto in questa stesura

GenePert, STATE, Ho e Salimans, Ha–Dai–Le, AdaIN, ControlNet, IP-Adapter, IRM, MoE, regressione a rango ridotto, SKNet, Involution, CBAM, convoluzione dinamica, WeightNet, ODConv, PuLID, FreeU, GenKI, HyperGate, DeepCTR `ple.py`, MultiFlow, e il resto del primo catalogo oltre PertAdapt e scDFM. Restano nel catalogo solo con il grado scritto lì: proposta della sessione, oppure pretesa del rapporto, oppure esclusi.

Le licenze diverse da HorNet (MIT, pagina About), MLB (BSD 3-Clause più brevetto pending, pagina About) e dal paper scDFM (CC BY 4.0, pagina HTML) non sono state lette.
