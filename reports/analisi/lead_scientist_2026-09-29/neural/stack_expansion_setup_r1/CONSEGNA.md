# Stack: due preparatori separati, pronti per review

29 settembre 2026. **Implementati e provati su fixture sintetiche; nessuna
estrazione reale, inferenza, training, scoring o upload avviati.** Il pilot del
job071 resta immutato. L'archivio contiene soltanto codice e metadati piccoli;
non contiene matrici cellulari né pesi. Il root assegna i numeri di coda.

Il file `target_registration.json` conserva la scelta prospettica già descritta
in `../PROPOSTA_STACK_ESTENSIONE.md`. Il piano delle singole cellule sarà scritto
dal comando `plan` prima di leggere i conteggi selezionati. I preparatori rifiutano
un cambiamento del pannello, dei conteggi sorgente o del codice dopo il piano.

Destinazione comune di `code_snapshot.tar.gz`:
`/content/drive/MyDrive/vcc2026/runs/lead_stack_expansion_setup_2026-09-29_r1/`.
Gli SHA dei file sono in `artifact_hashes.json`; l'allowlist del contenuto è
`setup_manifest.json`. Le due shell non sono state accodate.

## Produzione: solo input per 254 target

`colab_stack_production_prepare_r1.sh` legge gli otto shard CSR di x002, aggrega
per gene tutte le guide, sceglie senza rimpiazzo al massimo 128 cellule per i
254 target con almeno 64 cellule e 512 NTC sorgenti. La scelta dipende dagli ID
originali `source_row`, non dall'ordine degli shard. Ogni matrice scritta conserva
l'ordine crescente degli ID documentati; i conteggi devono essere integrali,
finiti e non negativi. I duplicati del simbolo mantengono la prima colonna.

Output nuovo: `runs/lead_stack_production_prompts_2026-09-29_r1/`. Include i tre
controlli A/B/C integrali con hash identico, un sottoinsieme deterministico di
512 controlli per contesto destinato al modello, i fallback t25 con maschera
`observed` esplicita, la mappa dei geni misurati e il manifest degli ID. I 46
target non coperti sono registrati per il fallback t25; questa preparazione non
produce ancora predizioni.

**Risorse stimate, non misurate:** 31.285 cellule sorgenti; limite superiore
conservativo della matrice CSR circa 2,1 GB prima della rimozione dei duplicati,
più blocchi temporanei. La shell richiede almeno 4 GiB RAM disponibili. Il piano
calcola il numero di elementi non nulli selezionati e una stima più stretta.
Gli input sorgente pesano 1.065.798.677 byte; tre controlli più tre NPZ t25
richiedono circa 715 MB di copie in output, oltre ai prompt compressi. Il file
originale da 65 GB non viene aperto per questo preparatore.

**Lineage misurata parzialmente:** i due controlli in
`../subset_spotcheck_r2.json` hanno gene, barcode e tutti gli 8.248 conteggi
identici all'originale. Non è una prova integrale di tutti gli shard. Il manifest
conserva il riferimento al report storico di estrazione e gli hash dei nuovi
output; non dichiara di avere ricalcolato l'MD5 del file originale.

## Conferma: solo input per 12 target distinti

`colab_stack_confirmation_prepare_r1.sh` usa i 12 target congelati della riserva
HepG2, esclusi da development, confirmation del generatore e pilot Stack:
PCBP1, CDC20, RNF31, KIF11, C7orf26, RPS24, GINS2, YRDC, DESI1, MRPL38, RSL1D1,
MYBBP1A. Richiede che la selezione basata sui metadati riproduca esattamente la
lista; non sostituisce target mancanti.

Output nuovo: `runs/lead_stack_confirmation_prompts_2026-09-29_r1/`. Legge solo
1.421 nuove righe sorgenti dal file originale, senza copiarlo, e riusa byte per
byte `source_00.h5ad` e `destination_controls.h5ad` del bundle064: stessi 512 NTC
K562 e 2.000 NTC HepG2. Le nuove righe dense utili sono 46.881.632 byte; l'I/O
Drive effettivo può essere maggiore. Guardia RAM di 2 GiB. Il transfer è estratto
dal `prepared_effects.npz` r3, mantenendo la maschera dei geni osservati.

Il bundle mantiene il formato del pilot. La successiva inferenza a tre seed del
generatore e la regola di promozione sono una proposta da congelare separatamente
prima dell'avvio; questi preparatori non implementano quella valutazione.

## Verifica

Sette test sintetici passati: quattro per shard/assi/maschere/fallback, tre per
selezione distinta, conteggi estratti e riuso esatto dei controlli. La fixture
include shard con ordine degli ID volutamente non monotono, geni duplicati,
effetti nulli sia osservati sia non misurati, target insufficienti e file alterati.
Nessun esito perturbato HepG2 è stato letto per selezionare i target.
