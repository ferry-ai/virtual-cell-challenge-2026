# Dataset acquisiti, trasformati e realmente usati nei modelli

29 settembre 2026. **Audit misurato su file, manifest e codice eseguito.**
Non è stato avviato training o letto alcun array grande per questa ricognizione.
La risposta alla domanda «abbiamo addestrato il modello con tutti i dataset,
decine di linee e centinaia di GB di cellule?» è **no**. L'acquisizione è più ampia
del training; l'ingestione di conteggi non equivale ad addestramento cellulare.

## Catena di prova, non conteggio di nomi nel catalogo

[`training_copertura_r1/inventory.json`](training_copertura_r1/inventory.json)
collega, per ogni contesto r2, manifest della sorgente, indice e SHA, input
materiale, righe aggregate e conteggi train/validation/refit/test per i cinque
fold effettivi. Generato da [`training_coverage_inventory.py`](training_coverage_inventory.py).

[`runtime_binding.json`](training_copertura_r1/runtime_binding.json) verifica
nuovamente **16 piccoli file con SHA esatto per ciascuno dei cinque manifest
remoti**, inclusi assi, contesti, indici, prior e manifest dataset. I tre array
grandi sono legati per dimensione e manifest, non rehashati: questa limitazione
è esplicita anche nei manifest remoti. Script:
[`verify_training_input_binding.py`](verify_training_input_binding.py).

Il catalogo del 26 settembre contava **195 file locali e 77 accessioni citate**,
non 77 dataset validati. Oggi `external` contiene 330 file, 69.252.639.289 byte:
tra questi ci sono metadata, script, annotazioni, conteggi e duplicati logici,
non 330 studi. Non include raw su Drive, né gli enormi shard Orion letti in
streaming. La lista delle 77 accessioni rimane nel JSON con la sua provenienza;
un'accensione citata non prova download, derivato o ingresso nel training.

## Produzione: quattro tabelle di effetti, nessuna rete nuova promossa

La ricetta [`t25.json`](../../../configs/recipes/t25.json), SHA256
`c74df9a994c3accc1d7bbe53ab16b0739168737cadc21bb6fff92a18499ef50a`,
usa `k562`, `cd4_mix`, `orion_hct116`, `orion_hek293t`, più la componente cis.
Sono quattro sorgenti di effetti dello stesso bersaglio, con CD4 aggregata
fra stati. Non è un training con tutte le cellule e non include automaticamente
le sorgenti della ricerca. Il candidato generatore t28 riusa quegli effetti:
cambiare emissione/dispersione non amplia i dataset perturbativi del modello.

I controlli ufficiali entrano nel basale e nel generatore; non forniscono
etichette perturbative di addestramento. Non si pubblica qui alcuna associazione
fra contesti ufficiali e identità biologiche.

## Rete source-attention: dodici contesti di effetti, cinque famiglie

Dataset r2 SHA256
`2e59376b103dc6578b9a52e3c37c655207567ecc0375481bc5e3560e7fb8b32a`:
109.586 righe aggregate, 19.265 bersagli nominali, 13.248 geni conservati;
8.717.981.535 byte di file elencati nel manifest. I file `raw.npy`, `shrunk.npy`
e `se.npy` contengono **effetti stimati e incertezza**, non cellule raw:
la parola `raw` significa effetto prima dello shrinkage.

1.000 righe A549 knockout sono serializzate ma escluse dal codice
`usable = ... modality == "crispri"`. Restano **108.586 righe CRISPRi di dodici
contesti**. Le righe sono un pool disponibile: il training campiona minibatch
di 16 per massimo 1.000 passi per fit. I manifest non conservano l'elenco delle
righe effettivamente estratte per ogni gradiente, quindi non si può attestare
che tutte siano state etichette supervisionate. Il calcolo dei centri visibili
usa invece le righe ammesse. È una distinzione tra disponibilità, uso come
sorgente e apparizione in un minibatch, non una nuova misura di efficacia.

| Dataset / contesto r2 | Righe di effetti serializzate | Materiale effettivo a monte e disponibilità | Ruolo nella rete corrente |
|---|---:|---|---|
| Replogle K562 genome-wide | 9.866 | Pseudobulk locale 374.587.922 B; originale cellulare su Drive 65.830.941.948 B | Training/sorgente o holdout K562 |
| Replogle K562 essential | 2.057 | Pseudobulk locale 79.766.954 B | Stessa famiglia K562, non una nuova linea |
| VIPerturb K562 Flex | 6.614 | Somme locali p1 500.067.773 B, derivate dal file `genome_wide_filtered.rds`; 326.247 cellule rappresentate | Stessa famiglia K562; prefiltraggio della sorgente dichiarato |
| Replogle RPE1 | 2.393 | Pseudobulk locale 95.350.546 B | Training/sorgente o holdout RPE1 |
| CD4 Rest | 12.063 | File pseudobulk locale comune ai tre stati, 44.566.657.140 B | Famiglia CD4 interamente esclusa nel suo fold |
| CD4 Stim8hr | 12.135 | Stesso studio e file; stato, non linea aggiuntiva | Come sopra |
| CD4 Stim48hr | 12.103 | Stesso studio e file; stato, non linea aggiuntiva | Come sopra |
| Orion HCT116 | 16.438 | 109 shard, 46.576.484.789 B letti in streaming secondo manifest; somme/effetti persistiti | Famiglia Orion; filtro `pass_guide_filter == 1` |
| Orion HEK293T | 17.270 | 223 shard, 79.683.336.248 B letti in streaming secondo manifest | Stesso studio, seconda linea; holdout insieme a HCT116 |
| KOLF2.1J | 10.985 | Somme locali 6.875.416.408 B; 2.659.209 cellule rappresentate nel manifest | Famiglia iPSC, non tutti i genotipi HIPSCI separati |
| HIPSCI genome-wide fitness | 2.147 | RNA counts gzip locale 1.445.924.890 B; somme 168.203.782 B | Linee in pool, una tabella a giorno 3 |
| HIPSCI genome-wide non-fitness | 4.515 | RNA counts gzip locale 1.748.940.996 B; somme 368.728.210 B | Linee in pool, altra libreria/giorno 6 |
| A549 Cas9 KO | 1.000 | Somme locali 595.100.652 B; 606.075 cellule rappresentate | Nel file, **zero righe train/refit/test** della corsa CRISPRi |

Le dimensioni sono byte decimali; quelle dei raw indicano un file o flusso,
non il volume passato al modello. Per KOLF, VIPerturb e A549 il materiale locale
direttamente verificato sono le somme: non si attesta che l'originale cellulare
temporaneo remoto sia ancora disponibile. Per Orion i byte sono quelli
storicamente applicati, non una presenza corrente di tutti gli shard sul disco.

Dodici contesti **non sono dodici linee indipendenti**: tre sono esperimenti
K562, tre sono stati CD4, due sono pool HIPSCI; Orion contiene due linee in
un solo studio. La famiglia iPSC unisce KOLF e i pool HIPSCI anche per la
sovrapposizione della linea KOLF nei pool. È una scelta di isolamento prudente,
non una ricostruzione delle decine di linee come esempi distinti.

| Famiglia tenuta fuori | Pool train prima della scelta passi | Pool refit finale | Target-contesto test |
|---|---:|---:|---:|
| K562 | 56.341 | 90.049 | 1.536 |
| CD4 | 53.748 | 72.285 | 1.536 |
| Orion | 56.341 | 74.878 | 1.024 |
| iPSC | 57.231 | 90.939 | 1.536 |
| RPE1 | 72.485 | 106.193 | 512 |

Sono cinque modelli per seed con holdout differenti, non un modello finale
addestrato contemporaneamente su tutti e dodici i contesti. I due semi hanno
terminato la valutazione; nessun fit di produzione source-attention è stato
promosso. Codice pertinente: [`train_neural_sources.py`](train_neural_sources.py),
[`neural_sources.py`](neural_sources.py), protocollo e hash nei manifest remoti
collegati dal JSON.

## Materiale acquisito che non è entrato in questa rete

| Materiale già disponibile | Prova concreta | Uso / mancato uso dimostrato e limite del motivo |
|---|---|---|
| **HIPSCI mirato per 19 linee** | RNA gzip locale 4.480.969.391 B; somme `targeted_p2` 1.320.184.528 B; **19 universi locali, 7.900 righe con effetti**, da 194 a 444 per linea | Tutti assenti dal registry r2 e dai cinque training manifest. Non è corretto dire «non acquisiti». Il disegno storico proponeva E2 per linea; non ho trovato una decisione che dimostri un rifiuto predittivo o motivi l'omissione dalla nuova rete. È una lacuna d'integrazione, non evidenza che non servano |
| HIPSCI genome-wide vecchi `_me1` | Derivati ancora presenti | Versione scartata esplicitamente per pochissimi NTC per pool; r2 usa `_ua1` con unassigned + NonTarget come negli autori. Il controllo può contenere perturbazioni non assegnate e attenuare gli effetti |
| Southard Hs27 | Somme p2 locali 273.802.640 B e universo di effetti | Assente da r2; CRISPRa, diversa modalità. L'assenza è misurata; non prova inutilità per un modello multimodale futuro |
| A549 | Somme ed effetti completi sopra | Esclusione CRISPRi/KO esplicita nel codice, non mancanza di dati |
| Mixscale | ZIP DE locale, cartella 324.112.833 B; audit 218 target, sei linee e cinque stimoli | Analisi di pattern/trasferimento precedenti; non presente nel registry r2. Nel catalogo la lacuna era basali/controlli appaiati e guide, non numero di target insufficiente |
| DLD-1 | LFC Low1/Low2 e SE Low1 locali, cartella 459.147.355 B | Audit e confronto su supporto parziale, non training r2. Non estendere conclusioni dal supporto parziale a tutti i geni |
| Screening mirato multi-guida già auditato | 144 raw nei manifest, 3.753.694.370 B; derivati H5AD rimossi ma codice e report conservati | Non training r2; pilot precedente con copertura limitata e dipendenze fra guide. Nuovo test predittivo preparato, **nessuna ingestione/fit nuova eseguita** |
| HepG2 | Raw locale 850.590.740 B e copia Drive | Truth dei banchi generatore/Stack; NTC usati come input. Risposte perturbate non nel predittore corrente; ciò non rende il benchmark mai visto storicamente |
| DepMap, STRING, GENCODE | File locali; manifest/annotazioni/prior | Descrittori basali, rete e coordinate, non etichette addizionali di knockdown. Non contarli come nuovi schermi perturbativi |
| Tahoe | Quattro metadata e **un solo shard** da 100.651.927 B | Non è il dataset Tahoe100M completo; non entra nel training r2. Nessun divieto generale dedotto dalla modalità farmacologica |
| H1 gara 2025 | Quattro CSV locali, 121.719 B complessivi | Assi/pannelli, non una matrice RNA acquisita in quel percorso |
| Altre accessioni del catalogo | 77 menzioni tracciate, con riferimenti storici | Una menzione non consente di assegnare bytes, qualità o ruolo. Non risultano nel registry attivo; l'audit non inventa una motivazione scientifica per ogni voce non riconciliata |

Per le 19 linee HIPSCI, «19 linee» descrive linee/genotipi iPSC nello stesso
tipo cellulare, non 19 tessuti. Non ho trasformato automaticamente i prefissi
degli identificativi in un conteggio di donatori: serve la corrispondenza
metadata esplicita. Gli effetti sono già sufficientemente materializzati da
rendere concreta una prova futura per genotipo/linea; non sostengono che sia
stata eseguita in questa sessione.

Fonti di ruolo e cautela: [audit catalogo 26/09](../audit_piani_dati_2026-09-26/RISULTATI.md),
[HIPSCI](../../sorgenti/universo_hipsci_2026-09-27/RISULTATI.md),
[dataset r2](../../modelli/rete_contesti_r2_2026-09-28/RISULTATI.md),
[nuovi universi](../../sorgenti/universo_nuovi_2026-09-27/RISULTATI.md).
Le righe dei vecchi report che parlavano di universi ancora mancanti sono
superate dall'inventario corrente; le ragioni non documentate restano ignote.

## Stack non colma questa differenza

Stack ha usato un modello esterno preaddestrato, senza fine-tuning sui nostri
archivi. Il pilot usa dodici prompt K562 con fino a 128 cellule per target,
512 controlli sorgente e 512 controlli destinazione, dentro un bundle di circa
32 MB. Questo è inferenza condizionata; non significa aver addestrato Stack
con tutte le centinaia di GB raccolte dal progetto. Il contenuto del pretraining
esterno non è stato ricostruito o verificato come holdout del nostro test.

**Conclusione verificata:** sono stati elaborati anche grandi archivi e milioni
di cellule per costruire somme ed effetti, ma la nuova rete ha imparato da una
selezione di rappresentazioni aggregate. La richiesta di utilizzare sistematicamente
tutti i dataset e le linee raccolte non è stata soddisfatta; i 19 universi HIPSCI
già pronti sono l'esempio più concreto della distanza fra dati disponibili e
dataset effettivamente passato al training.
