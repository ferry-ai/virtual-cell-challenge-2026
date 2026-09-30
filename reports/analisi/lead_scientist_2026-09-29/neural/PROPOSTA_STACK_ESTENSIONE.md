# Stack: conferma distinta e copertura del pannello corrente

29 settembre 2026. **Misurato dai metadati; proposta prospettica, nessuna
inferenza/scoring dell'estensione eseguita.** Evidenza riproducibile:
`expansion_metadata_r1.json`, prodotto da `audit_stack_expansion.py` senza leggere
conteggi o esiti perturbati HepG2. Il pilot congelato di 12 target resta invariato.

## Che cosa contiene davvero x002

`data/processed/k562_gwps_sc/x002/` contiene 8 shard H5AD CSR per 146.510 cellule,
complessivamente **1.065.798.677 byte**. Il report di estrazione del 17 settembre
collega il subset all'originale K562 da 65.830.941.948 byte e registra MD5 completo
`887e3e6a8c8df6eadf7a3030a53c9546`. Questo è il checksum storico, non una nuova
verifica integrale del file attuale. `source_row` conserva gli indici originali;
`barcode`, `gene`, `gene_transcript`, `sgID_AB` conservano l'identità della cellula.

I record di `groups.csv` sono gruppi `gene_transcript`; la disponibilità va sommata
per `gene`, non valutata per guida. Le colonne di risposta sono **8.248**, con
8.246 simboli unici (duplicati TBCE e HSPA14). **7.681** è l'intersezione con
l'asse ufficiale di 18.533 geni. Si mantiene la prima colonna per simbolo, come nel
pilot; i geni non misurati restano separati dagli zeri osservati.

| Copertura dei 300 target correnti | Target |
|---|---:|
| Almeno una cellula K562 | 272 |
| Almeno 40 cellule | 266 |
| Almeno 64 cellule | **254** |
| Almeno 128 cellule | 201 |
| Fallback t25 con soglia minima 64 | **46** |

I conteggi del pannello in x002 coincidono con quelli originali riportati nei
metadati: le cellule di questi target erano state tutte conservate. **Non è una
prova di uguaglianza di tutte le matrici.** Il numero 224 del banco 73 nasce dal
filtro aggiuntivo «il target deve anche comparire fra i geni misurati», con minimo
40 cellule. Stack usa la risposta cellulare come prompt e non richiede che il gene
perturbato stesso sia misurato: quel filtro non va trasferito automaticamente.
Sono disponibili 20.000 NTC x002 su 75.328 originali; ne bastano 512 per il prompt.

## Conferma indipendente proposta, selezione già fissata

Pool: i 130 target `eligible` HepG2 del manifest generatore r3 che non appartengono
né ai 48 development né ai 96 confirmation del banco generatore. Tenere soltanto
quelli con almeno 64 cellule K562 originali. Ordinare per
`SHA256("StackConfirm:20260929:<target>")` e prendere i primi 12. La lista, fissata
prima di qualsiasi score Stack, è:

`PCBP1, CDC20, RNF31, KIF11, C7orf26, RPS24, GINS2, YRDC, DESI1, MRPL38, RSL1D1, MYBBP1A`.

Nessuna sostituzione dopo gli score. x002 copre solo tre target di quella riserva
con almeno 64 cellule — SCAF1, PPP1R8, PHF10 — quindi non può fornire da solo una
conferma a 12. Per la lista fissata servono **1.421 nuove righe originali K562**,
46.881.632 byte di conteggi densi utili; il traffico Drive effettivo può essere
maggiore per amplificazione delle letture. Riutilizzare esattamente i 512 NTC
K562 e i 2.000 NTC HepG2 già estratti nel bundle del job064. L'inferenza resta
cieca ai perturbati HepG2; lo scorer li legge in un processo successivo.

Proposta di lettura da approvare e congelare prima dell'avvio: stessi parametri
Stack/correzione/supporto del pilot; una stima dell'effetto Stack con seed fissato,
tre seed del generatore finale appaiati fra i bracci. Promozione solo con delta
medio della proiezione ≥0,005, delta positivo per ciascun seed, limite inferiore
del bootstrap appaiato sui target al 95% >0 e PDS medio non inferiore. Il bootstrap
su 12 bersagli resta fragile e non equivale a una convalida su nuove famiglie.
Non si dichiara HepG2 assente dal pretraining.

## Preparazione anticipata della produzione, senza inferenza

Bloccare ora tutti i **254 target ≥64**; per ognuno scegliere min(128,n) cellule
senza rimpiazzo tramite seed derivato da target e seed globale, aggregando tutte
le guide e usando `source_row` per rendere la scelta indipendente dagli shard.
Con 512 NTC sono **31.285 cellule sorgenti**, 1.032.154.720 byte se dense. Si possono
leggere gli shard CSR da 1,066 GB, evitando il file da 65 GB. La nuova preparazione
conserva i profili di tutti i geni misurati e una mappa esplicita verso l'asse
ufficiale, senza trasformare l'assenza di misura in una risposta nulla.

Controlli A/B/C: i tre file ufficiali già presenti `raw/controls/context_*.h5ad`
(224.973.316, 210.966.111 e 226.056.691 byte). Conservare il basale completo e le
library size dei controlli; estrarre con seed fisso i controlli che alimentano il
modello. Non inserire perturbati dei contesti destinatari.

Fallback congelato: `processed/effects_t25_2026-09-27/effects_A.npz`,
`effects_B.npz`, `effects_C.npz`, più `manifest.json`. Ogni NPZ ha effetti in log
naturale e mask `observed`; la mask non si ricava da `lfc != 0`. Per i 46 target
non ammessi, mantenere integralmente l'effetto t25. Per i 254 ammessi, applicare
Stack soltanto sul supporto misurato condiviso e mantenere il resto della
baseline, inclusa la sua massa totale sul supporto, come nel pilot.

Il confronto HepG2 del pilot usa un transfer congelato; la produzione usa t25
multisorgente e controlli A/B/C. È un'estensione del regime, non la prova che un
eventuale guadagno del pilot si conservi sopra t25. La preparazione degli input
non autorizza inferenza, adozione o invio. Il numero di passaggi GPU e il tempo
reale vanno ricavati dal pilot completato, non da una promessa preventiva.
Con le cardinalità osservate dei prompt ci sono 35 dimensioni diverse: cache dei
controlli appaiati per dimensione implica 3 × (254 + 35) = **867 chiamate** a
`get_incontext_generation`, ciascuna con cinque passi, per A/B/C. Il dato misura
il lavoro richiesto, non la durata o la possibilità di completarlo nella sessione.
