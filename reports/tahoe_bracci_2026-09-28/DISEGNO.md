# Bracci Tahoe: imparare come cambia una risposta fra contesti

28 settembre 2026. Stato: **proposal**, codice verificato su dati sintetici;
nessuna estrazione remota e nessun risultato di modello in questo lavoro.

## Due ruoli separati

**interpretation.** I DMSO descrivono lo stato iniziale della linea: servono
all'encoder basale e come riferimento della risposta. Da soli non insegnano
come una perturbazione cambia al cambiare del contesto. I bracci farmacologici
offrono interventi ripetuti fra linee: permettono una supervisione della
dipendenza della risposta dal basale. Non diventano etichette CRISPRi per il
solo fatto di avere un bersaglio annotato in comune.

**hypothesis.** La variazione fra contesti appresa sui farmaci contiene una
componente trasferibile al knockdown. T1 verifica il primo passaggio dentro
Tahoe; T2 cerca evidenza del ponte. Nessuno dei due dimostra da solo un
miglioramento nella gara, né la generalizzazione congiunta a bersagli e
contesti nuovi prevista da D-044.

## Quanto sappiamo dai file locali

**measured**, lettura offline dei quattro parquet in
`C:/Users/ferra/vcc2026-data/external/tahoe100m/metadata/`:

| File | Byte su disco | Righe e significato |
|---|---:|---|
| `gene_metadata.parquet` | 1.326.799 | 62.710 token genici |
| `drug_metadata.parquet` | 40.475 | 379 farmaci |
| `sample_metadata.parquet` | 65.636 | 1.344 campioni, 14 piastre, 380 etichette incluso DMSO |
| `cell_line_metadata.parquet` | 19.040 | 1.000 annotazioni, 102 nomi/ID di linea distinti |
| Totale | 1.451.950 | Non sono conteggi di cellule |

**measured.** I controlli sono 28 campioni DMSO, due per piastra; tutti i
1.344 valori `drugname_drugconc` sono stati analizzati con il parser. L'asse
ufficiale contiene 18.533 geni; 18.150 simboli sono presenti nella tabella
Tahoe, 383 assenti. La copertura effettiva dopo `min_expected` sarà inferiore.
I quattro metadati non contengono il numero di cellule per campione, né byte
di espressione per campione, né una mappa campione–shard. Questi conteggi
non sono ricavabili dalle medie QC.

**interpretation.** Le 102 linee annotate non provano 102 linee nei conteggi.
Il contesto del mandato e la card riportata in
`../tahoe_dmso_2026-09-28/LAYOUT.md` parlano di 50 linee: la discrepanza va
risolta con gli ID osservati durante l'estrazione. Non si usa 50 come
dimensione di array né si assumono tutte le combinazioni linea/farmaco/dose.

**measured — lettura di evidenza precedente, non nuova verifica della fonte.**
`LAYOUT.md` trascrive dalla card 95.624.334 cellule, 337.644.770.670 byte
compressi e 1.693.653.078.843 byte logici per l'espressione completa. Questi
totali non sono stati riverificati qui e non stimano i byte dei 73 farmaci.
Il mandato riporta su shard 1031 1.364 DMSO in tre row group su 29:
non si riesegue questa misura e non la si estrapola ad altri campioni.

**proposal.** Registrare nel manifest i byte effettivamente ricevuti, le
dimensioni delle shard lette, le cellule esaminate e quelle selezionate per
campione. `selected_samples` identifica solo i campioni selezionati osservati
in quella shard, non tutti i suoi campioni. Mantenere la scansione `drug`
di ogni row group; le altre colonne si leggono solo nei gruppi positivi.
Non stimare traffico come frazione dei campioni moltiplicata per 338 GB.

**interpretation — dimensionamento.** Una somma float64 sui 62.710 token
occupa 501.680 byte per gruppo, senza overhead. Il codice accumula i gruppi
in memoria e ne impila le somme per il NPZ: il picco supera quindi la sola
matrice finale. Il lead deve dimensionare la RAM dal numero di gruppi
osservati nel pilot; il numero di cellule non determina questo costo.

## Selezione ed effetti

**measured.** `choose_drugs.py` ha usato
`C:/Users/ferra/vcc2026-data/processed/universe_k562_2026-09-26/index.csv`,
9.866 bersagli, SHA256 nel manifest. Ha scritto `selection/drugs.csv`:
73 farmaci, 72 con un solo simbolo annotato presente in quell'universo,
261 campioni farmacologici più 28 DMSO. Quattro candidati controlli positivi:
Bortezomib (proteasoma), Belinostat (HDAC), AZD-8055 (mTOR), AT7519 (CDK).
Tre appartengono anche al gruppo dei 72. Nessun candidato BET trovato nei
campi MOA; nessuna annotazione BRD nei bersagli. Ogni riga del CSV conserva
motivazione, bersaglio, MOA, ruolo e indice sorgente. La scelta dei controlli
è alfabetica entro meccanismo, riproducibile e indipendente dalle risposte.

**interpretation.** «Un solo simbolo nei metadati» non significa farmaco
selettivo, né necessariamente inibitore: agonisti e annotazioni incerte vanno
separati nel banco T2. L'intersezione con bersagli umani CRISPRi è il controllo
operativo dei simboli; non è una nuova curazione HGNC o farmacologica.
La risposta forte dei controlli è una **hypothesis**, da verificare con
ampiezza e replicabilità. L'overlap seleziona la vista T2, non limita il
valore di altri farmaci per T1 (D-044).

**measured — implementazione e selftest.** `extract_arms.py` conserva somme
float64, numerosità e libreria su tutti i token, per linea/piastra/farmaco/dose.
La dose proviene dal `sample` della cellula: parsing letterale della tupla,
unità conservata, controllo di corrispondenza farmaco e piastra. Le stringhe
farmaco originali, anche con spazi finali, restano intatte. Include sempre
DMSO; rifiuta di pubblicare un NPZ se un braccio non ha il controllo della
stessa linea e piastra. Un sottoinsieme di shard non garantisce il pairing:
se manca, serve una nuova estrazione con copertura maggiore.

**measured — implementazione e selftest.** `arms_effects.py` richiama
`vcc2026.multisource.effects_from_pseudobulk` (`src/vcc2026/multisource.py:92`),
lo stesso usato dagli universi. Farmaco+dose è il target, piastra il donor;
ogni linea viene elaborata separatamente. La funzione confronta ogni piastra
con il proprio DMSO e media i log-effetti con pesi cellulari del braccio,
gene per gene fra le piastre informative. Non confronta somme di piastre
diverse prima di calcolare l'effetto. Default: `min_expected=1`, almeno
10 cellule per braccio e per controllo, pseudo 0,5 costante, phi 0,2.
La libreria include tutti i geni Tahoe, prima della mappatura sull'asse.
Si conserva la prima occorrenza del simbolo in ordine di token, come
`corpus_tahoe.py`; duplicati non vengono sommati come se fossero geni diversi.
L'output include `raw`, `shrunk`, `se`, unità logaritmo naturale e piastre
usate. Geni assenti o senza evidenza rimangono NaN. `min_control_frac=0`
evita che la maschera interna a bassa frazione diventi uno zero misurato.

## T1: differenze tra contesti su molte linee

**proposal.** Congelare gli ID effettivi, i criteri QC, i fold e i semi prima
di leggere le risposte di test. Se sono disponibili 50 linee, lavorare su
quelle 50, lasciando fuori due linee intere per fold e altre linee per
validation. Se il numero osservato è diverso, dichiararlo e registrare
nuovamente il protocollo prima del training. Ripetere su coppie predefinite;
ogni confronto riguarda lo stesso farmaco e la stessa dose nelle due linee.
Le risposte delle linee di test, su tutte le piastre e dosi, sono nascoste.
Solo i loro DMSO sono input. È regime C, non J.

**proposal.** Confrontare un modello regolarizzato basale × farmaco/dose con
un modello cieco al contesto, la risposta media del farmaco nel training e
lo scambio dei basali. Stessi geni e stessi dati ammessi per tutti. Pesi
genici, encoder, normalizzazione, selezione geni, iperparametri e arresto
si apprendono solo nel training/validation. Per dichiarare linee nuove
escluderle anche dal pretraining dell'encoder; una variante con pretraining
sui loro DMSO va dichiarata transduttiva e riportata separatamente.

**measured — lettura del codice.** E2 è `e2_diagnostics` in
`../rete_contesti_2026-09-27/train.py:542`: per perturbazione correla, con
pesi genici, differenza predetta e osservata fra due contesti, dopo aver
sottratto a ciascun gene la differenza media sulle perturbazioni di test.
Così un semplice template di linea non basta. Riporta media, bootstrap,
permutazione delle corrispondenze tra perturbazioni e differenza predetta
identicamente nulla nel cieco.

**proposal.** Riutilizzare questa lettura con righe farmaco/dose su supporto
comune finito, preservando il centraggio e le stesse convenzioni di
correlazione. Per T2/singolo target togliere gene bersaglio e finestra cis
con le coordinate e ampiezza congelate del banco E2. Per farmaci con più
target usare l'unione delle finestre note; senza target/TSS dichiarare
separatamente il readout senza esclusione cis, non chiamarlo identico E2.
La permutazione scambia identità dei farmaci, mantenendo insieme le dosi
e stratificando per dose comparabile: dosi e piastre non sono repliche
indipendenti. Media prima per farmaco, poi per coppia; bootstrap a blocchi
di farmaco e linea per evitare falsa precisione da coppie sovrapposte.

**proposal — regola da congelare.** Promuovere T1 solo se il vantaggio medio
sul cieco ha limite inferiore CI95 sopra zero, la correlazione E2 supera il
quantile 97,5% di almeno 200 permutazioni a blocchi e lo scambio dei basali
peggiora la previsione. Riportare copertura, ampiezze, MSE delle differenze,
e risultati per dose. Per l'ipotesi «più contesti», sottoinsiemi annidati
di 5, 10, 25 e tutte le linee di training disponibili sul medesimo test,
anche a budget cellulare comparabile. Nessuna metrica qui è uno score VCC.

## T2: ponte verso CRISPRi

**proposal.** Per ogni candidato con singolo target, calcolare il coseno
tra `raw` farmacologico e knockdown di quel target, sul supporto genico
comune finito, escludendo target e cis. Analisi principale sugli inibitori;
agonisti, attivatori e MOA incerti separati senza cambiare il segno a
posteriori. Escludere vettori a norma zero, riportando quanti e la copertura.
Preferire stessa linea, condizione e tempo quando realmente disponibili;
confronti fra linee o studi diversi sono uno strato distinto. Verificare
che gli universi scelti abbiano lo stimatore corretto e unità ln compatibili.

**proposal.** Confrontare il coseno col target corretto con almeno 1.000
target casuali misurati nello stesso universo, abbinati per norma della
risposta, copertura e numerosità. Usare lo stesso supporto per ogni confronto.
Tenere insieme farmaci dello stesso target e tutte le dosi nel bootstrap;
riportare rango del target vero, differenza dal nullo e CI95 per target,
oltre a un controllo con risposta generica media rimossa. Nessuna selezione
della dose migliore sui dati di test. Un segnale aggregato con CI95 del
vantaggio sopra zero sostiene il ponte; un fallimento non prova che ogni
farmaco sia inutile per apprendere il contesto.

**interpretation.** Concordanza sostiene una componente condivisa della
risposta. Non prova equivalenza farmacologia/CRISPRi né causalità esclusiva
del target: off-target, dose, tempo di esposizione, inibizione proteica
contro repressione trascrizionale e diversa profondità di perturbazione
possono cambiare segno e ampiezza. Chimica 3' degli screen contro chimica
Tahoe e batch possono alterare il supporto e le frazioni: stessa unità e
asse non eliminano questi confondenti. Senza metadati temporali/chimici
verificati l'attribuzione resta aperta.

## Leakage e avvio del lavoro

**measured.** Nei nomi/ID locali è presente HCT116 (`CVCL_0291`). K562 e
HEK293T non compaiono; non sono annotate linee iPSC o T cells. Questa è
un'osservazione del catalogo, non una verifica della composizione cellulare
delle shard. HCT116 deve essere esclusa interamente quando è test esterno,
anche dai bracci Tahoe e dall'encoder. Confrontare ID e alias curati per
tutti i disegni K562, HCT116, HEK293T, iPSC e T cells prima del training.
Non inferire mai identità per i contesti di gara A, B, C.

**proposal.** Per un successivo test J, nascondere anche i target di test
in tutti gli screen, i farmaci con quei target, derivati ed embedding di
risposta; gestire esplicitamente farmaci multi-target e alias. Tenere
repliche e dosi nella stessa partizione. Non usare T2 sul test esterno
per scegliere il modello da valutare su quello stesso test.

**measured.** Entrambi i `--selftest` sono passati offline; la selezione
CSV è stata eseguita. Non sono state lette shard reali né eseguite chiamate
di rete. Il trasporto Range, il pairing reale e le risposte restano da
verificare. Il checker documentale richiede registro e indice esterni
alla cartella consentita: Claude1 deve aggiungerli durante l'integrazione.
La suite generale ha concluso 203 test: 201 passati, un fallimento per
il registro mancante e un errore nell'import preesistente
`cell_eval2.config` (`test_sc_pipeline.BenchComponentTests`). Non sono state
modificate dipendenze o file esterni alla nuova cartella.

**proposal — comandi per Claude1**, dal checkout integrato, con directory
nuove. Prima: verificare commit HF completo e provenienza coerente dei
metadati locali (gli hash sono conservati; non provano da soli la revisione).
Controllare la discrepanza 50/102, annotazioni farmacologiche e copertura
del pilot prima di allargare l'estrazione. Impostare `$revision` al commit
completo verificato; il codice rifiuta `main`.

```powershell
.\scripts\py.cmd reports/tahoe_bracci_2026-09-28/extract_arms.py --selftest
.\scripts\py.cmd reports/tahoe_bracci_2026-09-28/arms_effects.py --selftest
.\scripts\py.cmd reports/tahoe_bracci_2026-09-28/choose_drugs.py --out C:/Users/ferra/vcc2026-data/processed/tahoe_drugs_r1
.\scripts\py.cmd reports/tahoe_bracci_2026-09-28/extract_arms.py --drugs C:/Users/ferra/vcc2026-data/processed/tahoe_drugs_r1/drugs.csv --revision $revision --step 5 --out C:/Users/ferra/vcc2026-data/processed/tahoe_arms_r1
.\scripts\py.cmd reports/tahoe_bracci_2026-09-28/arms_effects.py --arms C:/Users/ferra/vcc2026-data/processed/tahoe_arms_r1 --out C:/Users/ferra/vcc2026-data/processed/tahoe_effects_r1
```

**proposal.** Aggiungere `--max-shards` per un pilot e scegliere un altro
`--out` per l'estrazione successiva. Il pilot può fallire per DMSO mancante:
non colmare con controlli di altre piastre. T1/T2 sono un disegno da
registrare e implementare, non banchi già eseguiti.
