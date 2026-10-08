# Selezione e fonti primarie — 8 ottobre 2026

**Interpretazione:** priorità scientifica PIE; alternativa operativa ESM2 + ridge
mascherata. Nessun modello è promosso. Le metriche pubblicate sono degli autori,
non risultati VCC del nostro progetto. Ricerca in inglese e cinese; i risultati
divulgativi cinesi sono stati usati per trovare nomi, non come evidenza.

## Shortlist

| Candidato e fonte originale | Capacità pertinente | Asset, scala e rischio | Decisione |
|---|---|---|---|
| [PIE, Arc](https://github.com/ArcInstitute/pie) | Target biologico, controlli e memoria degli effetti; generalizzazione C/J dichiarata | Tre teste distinte; dati di training ancora necessari; licenza codice CC BY-NC-SA, pesi con licenza propria | Principale, qualificare inferenza prima dello score |
| [ESM2](https://huggingface.co/facebook/esm2_t33_650M_UR50D) + [GenePert](https://github.com/zou-group/GenePert) | Sequenza proteica per target anche mai perturbati; regressione supervisionata separata | ESM2 non è un predittore di effetti. Implementazione originale ridge, non copia di GenePert. Fit sulle sole righe lecite; non legge il contesto | Alternativa concreta; confronto anche con descrittori GO/STRING già nostri |
| [STATE](https://github.com/ArcInstitute/state) | SE descrive cellule; ST prevede risposte e supporta split di contesti | Checkpoint genetico diverso da Tahoe farmacologico; uscita normalizzata e eventuale decoder da verificare. Licenza non commerciale codice/pesi | Approfondire dopo PIE, non installare SE scambiandolo per ST |
| [GEARS](https://github.com/snap-stanford/GEARS) | Grafo GO per target non osservati, combinazioni | Originale non progettato per cross-cell-type; nostro prototipo non ha ancora grafo reale/training. Uscita espressione, asse specifico del fit, PyG | Conservare encoder; niente rilancio dello stesso prototipo come soluzione pronta |
| [TxPert, Valence](https://github.com/valence-labs/TxPert) | Modello a grafo, esperimenti su nuova perturbazione e nuova linea | Checkpoint pubblici per sottoinsieme dei modelli; i migliori risultati includono grafi proprietari assenti. Output espressione normalizzata; config cross-cell distinta; licenza specifica da leggere prima acquisizione | Nuovo concorrente pertinente, non equivalente alla variante pubblicata migliore |
| [TabICL/TabPFN, Royer Lab](https://github.com/royerlab/tfm-perturbation) | Regressore tabulare preaddestrato con adattamento in-context | [Preprint](https://www.biorxiv.org/content/10.64898/2026.06.28.735106v2) su più scale; pretraining generico non sostituisce split biologici. Asset/licenze per versione, RAM del contesto e assi da qualificare | Seconda alternativa dopo ridge semplice sugli stessi descrittori |
| [PRiMeFlow, Altos](https://github.com/altoslabs/primeflow) | Generatore di distribuzioni, sequenza ESM2 | Corpus pubblico preparato e codice; checkpoint completo della soluzione non verificato. Covariate viste non garantiscono nuova linea; log1p/normalizzazione, guidance e cis implicito richiedono nuovo confronto | Rinvio: cambia emissione, domanda distinta dal miglioramento degli effetti |
| [scDFM, Westlake/Zhejiang](https://github.com/AI4Science-WestlakeU/scDFM) | Attenzione differenziale e flow condizionato alla perturbazione | Norman/ComboSciPlex nei riferimenti, nessuna prova qui di CRISPRi cross-contesto. Pesi/formati/licenza vanno qualificati | Idea di blocco, non vincitore perché il nome contiene differential |
| [PertAdapt](https://github.com/BaiDing1234/PertAdapt) | Adattamento di scFoundation/AIDO.Cell, maschere GO | 19.264 geni nel mask file citato; mapping con 18.533 nostro non automatico. Nuovo gene non implica nuova linea. Pesi di base e dataset necessari | Non priorità rispetto al contrasto ESM2 isolato |
| [GeneGeoFlow](https://arxiv.org/abs/2608.06824) | Geometria spettrale GO/coespressione, residuo condizionato | Paper agosto 2026: Norman e combinazioni farmacologiche; nessuna inferenza nostra o checkpoint verificato. Rete biologica non interpretata come direzione causale | Nuova idea pertinente alla diagnosi GEARS; studio successivo |
| [Arc Stack](https://github.com/ArcInstitute/stack) | Generazione in-context | CP-0051: due bracci falliti; esposizione pretraining limita C rigoroso. Nessuna nuova assunzione concreta per rilanciarlo oggi | Scartare il rilancio invariato, non tutta la famiglia |

## Perché questo meccanismo

Predittore congelato: separa utilità esterna da errori di un nuovo training.
Feature ESM2: rende attribuibile l'incremento alla sequenza, a parità di righe e
regressore. Teacher/distillazione ereditano esposizioni e normalizzazione; non
risolvono leakage. Residuo/gating richiedono errori complementari fuori fold,
altrimenti S-003/S-006. Fine-tuning richiede nuove risorse e split, e non cancella
ciò che i pesi iniziali sanno. Quindi prima predizioni congelate e diagnosi degli
errori; nessuna miscela scelta su test né doppia amplificazione.

## PIE: riscontri tecnici nuovi

Revisione codice letta: `21a526add9ff3a81b4f962d9b16bbae570052c63`.
Piano completo e ricevute metadata: [public_audit_r1.json](public_audit_r1.json).
Modello HF `055c7a2cabdaff5659121c64fa2b609c231fc5be`, fold `hepg2`:
949.595.187 byte, SHA256 `84826d8c3ee76be661c0dcd1abe6c2d410aee9198fd6b243a9203812289616f5`.
È la linea esclusa, non una linea di training. La scelta iniziale è fattibilità,
non selezione fra fold sui risultati. Gli altri tre fold hanno visto questa linea.
[Model card](https://huggingface.co/arcinstitute/PIE_replogle_wdataset).

**Misurato dai piccoli metadata, senza risposte perturbate:** 6.290/18.533 geni
ufficiali coincidono esattamente con l'asse Replogle di 6.642. Zero dei 300 target
del pannello coincide con i target dello stesso dataset; questo non prova J
rispetto a embedding o altri asset e non impedisce query di nuovi target.
La copertura per simboli non è una riconciliazione degli alias. Il fallback e la
copertura devono essere riportati, non valutare solo i geni facili.

**Misurato dal catalogo HF fissato:** piano minimo 45.644.647.954 byte, esclusi
ambiente/software e output. `ncbi_text/embeddings.npy` da solo 43.182.215.296 byte.
Le descrizioni testuali non sono necessarie al lettore d'inferenza e restano fuori
da questo piano. Tutti i file, revisioni, byte, SHA LFS/git blob e URL nel JSON.
Il [lettore](https://github.com/ArcInstitute/pie/blob/21a526add9ff3a81b4f962d9b16bbae570052c63/src/pie/sources/contract.py)
usa mmap: 43 GB disco non equivalgono a 43 GB RAM obbligatori. VRAM e tempi vanno
misurati su batch reali; training 2 H100 non definisce minimo inferenza.

Il [predictor](https://github.com/ArcInstitute/pie/blob/21a526add9ff3a81b4f962d9b16bbae570052c63/src/pie/predict.py)
carica config/statistiche dal checkpoint e memoria dalla config di training anche
quando si sostituiscono i dati di query. L'output parquet contiene una riga per
dataset/contesto/perturbazione, liste sui geni del dataset in metadata `pie`.
L'adattatore è originale e non importa torch o esegue checkpoint.

`p_de`: probabilità di differenziale, non p-value. `lfc_pred`: log2 fold change.
`delta_p_pred`: variazione della media sulla scala preprocessata, discretizzata
nelle uscite della testa; non è lo stesso LFC. [Readout](https://github.com/ArcInstitute/pie/blob/21a526add9ff3a81b4f962d9b16bbae570052c63/src/pie/model/heads.py),
[preparazione](https://github.com/ArcInstitute/pie/blob/21a526add9ff3a81b4f962d9b16bbae570052c63/src/pie/prep/labels.py).
Il preprocessing ufficiale usa CP10k/log1p. [Normalizzazione](https://github.com/ArcInstitute/pie/blob/21a526add9ff3a81b4f962d9b16bbae570052c63/src/pie/process/normalize.py).
Media dei log e log della media sono diversi: convertire la base non ricostruisce
denominatori, pseudoconteggi o rapporti pseudobulk del transfer. Export bloccato
senza evidenza separata del bridge. Nessuna correzione automatica inventata.

## ESM2: alternativa realmente isolabile

Pacchetto Arc fissato: 19.203 target × 1.280 float32; modello originario
`facebook/esm2_t33_650M_UR50D@08e4846e537177426273712802403f7ba8261b6c`;
sequenze umane reviewed UniProt, finestre 1.022 con stride 511 e pooling mean.
[Metadata primaria](https://huggingface.co/datasets/arcinstitute/PIE_sources/blob/cb1aaa4e7655605bdc70a9bd77bbd62016b8c7d7/esm2/meta.json).
Richiede 98.539.820 byte inclusi metadata; **299/300** target del pannello hanno
match esatto, manca TMEM104. Non inventare un vettore zero come dato osservato:
maschera e fallback; alias eventuale solo con fonte/versione.

La matrice attuale del progetto ha già GO/STRING/HGNC/coordinate/DepMap;
ESM2 aggiunge una modalità distinta. `embedding_ridge.py` implementa regressione
pesata con maschere, intercetta e generico stimati solo sulle risposte ammesse;
rifiuta righe escluse. Non è il modello GenePert riprodotto e non prova uso del
contesto. Una ridge su produzione r1 non sarebbe una misura C/J. Il corpus resta
di DATI-TRANSFER, senza duplicare acquisizioni o eliminare contesti D-053.

## Condizioni e ammissibilità

La [licenza PIE](https://huggingface.co/arcinstitute/PIE_replogle_wdataset/blob/055c7a2cabdaff5659121c64fa2b609c231fc5be/MODEL_LICENSE.md)
limita l'uso del modello/derivati a scopi non commerciali e richiede attribuzione
anche per output redistribuiti; distillazione e integrazione sono contemplate nei
derivati. Il testo è stato letto integralmente. Non è stata ottenuta una conferma
specifica di compatibilità con la gara a premi. L'asset repository PIE_sources
non dichiara una licenza nel README consultato: non dedurne automaticamente MIT
dal modello ESM2 originario. Registrare questa lacuna nella decisione d'uso e non
redistribuire gli asset attraverso il repository pubblico.

## Verifica dei contributi precedenti

Grok `pezzi_adottabili_2026-10-05/CATALOGO.md` e i tre originali Antigravity sono
proposte, non misure. Il rapporto Antigravity sui predittori dichiara di non aver
aperto codice/pagine: le attribuzioni cross-contesto e checkpoint non sono ricevute.
Riaperte le fonti originali scDFM/PertAdapt/GEARS: non ne ricavo una prova CRISPRi
su contesti mai perturbati. GenePert usa regressione, non dimostra che una media
di vicini sia equivalente. La correzione Grok sul bias comune resta pertinente:
target × contesto non garantisce media nulla. Il nuovo adattatore non centra o
riscala implicitamente, e conserva le tre uscite PIE separate.
