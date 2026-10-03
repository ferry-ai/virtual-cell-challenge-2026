# Risorse pubbliche individuate nell'analisi dei vincitori

3 ottobre 2026. Catalogo secondo GENERALIZZAZIONE §2. Risorse consultate sul web, nessun file
di dati acquisito. Si tratta di derivati di sorgenti pubbliche: non contarli come nuovi studi
indipendenti dall'archivio già in costruzione.

| Risorsa | Informazione verificata nella pagina degli autori | Ruolo proposto | Prima dell'uso |
|---|---|---|---|
| [PRiMeFlow VCC Datasets](https://huggingface.co/datasets/altoslabs/primeflow-vcc-datasets) | AnnData compressi, split per ID cellulare, asse di 18.001 geni; H1 training, CD4, K562/RPE1, HepG2/Jurkat, Jiang, McFaline e Feng | Confrontare preprocessing, riconciliare celle e fonti con il nostro archivio; eventuale riproduzione separata | Verificare revisioni, hash, sovrapposizioni e metadati; ricostruire C/J del 2026 anziché riusare split H1 |
| ESM2, nello stesso rilascio | `ESM2_pert_features.parquet`, 595 MB dichiarati, derivato dal support set Arc | Ablation di descrittori congelati rispetto ai blocchi attuali | Copertura, mapping/isoforme, provenienza, licenza, presenza locale prima di qualunque acquisizione |

La card dichiara CC-BY-4.0 e rimanda alle licenze delle sorgenti terze: lo stato qui è
**licenza del pacchetto dichiarata; condizioni dei singoli componenti da verificare**.
La licenza del codice è separata da quella dei dati. Non è stata verificata una catena completa
di diritti per un nuovo utilizzo.

Dimensioni compresse, distinzione dal corpus storico vincente e limiti delle conclusioni sono
nel [rapporto](README.md#4-gestire-i-dati-senza-trasformare-ogni-esperimento-in-un-archivio).
L'assenza dei dati proprietari e la diversa lista di sorgenti impediscono di chiamare il
pacchetto pubblico una copia esatta dell'atlante storico. Le fonti sottostanti già note mantengono
la propria scheda nel [catalogo sorgenti](../../sorgenti/README.md).

Le ricerche per nomi esatti `xTrimoSCPerturb`, `TransPert` e combinazioni `XLearning / VCC / X`
non hanno restituito in questa sessione una ricetta completa verificabile dei primi tre.
Il [resoconto ufficiale Arc](https://arcinstitute.org/news/virtual-cell-challenge-2025-wrap-up)
resta la fonte della loro descrizione. Non si assume che queste implementazioni non esistano.
