# Matrice QC, prima versione (R-LAB, prima consegna)

30 settembre 2026 sera, Claude (sessione `a1ec75f0`). **Non è la politica di QC** (P3,
`QC_REPORT.md`): dice quali controlli del §5 del piano si possono fare su ogni sorgente con ciò che
c'è, e riporta le prime misure per cellula sulle sorgenti già su disco. Nessuna cellula è stata
scartata.

## 1. Misure per cellula (misurato, `qc_sample.py`, file in `qc_r1/`)

| Sorgente | Saggio | Cellule misurate | Geni dell'asse nativo | Conteggi per cellula q01 / q50 / q99 | Geni rilevati q50 | Frazione MT q50 / q99 |
|---|---|---:|---:|---|---:|---|
| Controlli di gara, contesto A | 10x Flex | 18.400 (tutte) | 18.533 (12 MT) | 4.470 / 20.109 / 47.490 | 6.147 | 0,27 % / 1,42 % |
| Controlli di gara, contesto B | 10x Flex | 18.400 (tutte) | 18.533 (12 MT) | **1.007** / 19.946 / 38.812 | 5.756 | 0,26 % / 0,94 % |
| Controlli di gara, contesto C | 10x Flex | 18.400 (tutte) | 18.533 (12 MT) | 4.685 / 20.034 / 46.623 | 6.006 | 0,49 % / 1,85 % |
| HepG2 (Nadig) | 10x 3′ | 145.473 (tutte) | 9.624 (13 MT) | 4.312 / 15.487 / 62.631 | 4.029 | 9,4 % / 16,4 % |
| HIPSCI genome-wide fitness | 10x 3′ | 3.000 (le prime colonne del file) | 36.518 | 8.764 / 23.546 / 41.962 | 5.941 | 1,8 % / 3,7 % |
| Jurkat GSE249595, canale 16 | vedi nota | 67.041 barcode con ≥ 500 UMI | 20.606 | 644 / 3.045 / 11.892 | 600 | **16,1 % / 54,3 %** |

**Che cosa se ne ricava (interpretazione):**
- **Una soglia mitocondriale unica sbaglierebbe.** Sul saggio Flex i geni MT sono 12 e la frazione
  mediana è sotto lo 0,5 %; in 3′ HepG2 sta al 9,4 %, HIPSCI all'1,8 %. Nel canale Jurkat è al 16 %,
  con code oltre il 50 %. Là la selezione dei geni del saggio andrà verificata prima di leggere quella
  frazione come qualità della cellula.
- **Il contesto B ha una coda di cellule povere**: l'1 % sta sotto 1.007 conteggi, contro circa
  4.500 di A e C. È un fatto dei controlli, da tenere nell'encoder dello stato, non da tagliare in
  silenzio.
- **HepG2 pubblica il totale prima del filtro dei geni** (`UMI_count`). Il 99 % degli UMI cade sui
  suoi 9.624 geni (q01 97,9 %), quindi la massa fuori asse si misura: è il campo `depth_native`
  del contratto.
- **Il canale Jurkat è una matrice non filtrata**: 6,79 milioni di barcode, di cui 1,85 milioni con
  almeno un UMI e 1,71 milioni con meno di 100 UMI (4,2 milioni di UMI in tutto). È il materiale che
  serve per stimare l'RNA ambientale, che per le altre sorgenti locali manca. Con l'hashing, un canale
  ha decine di migliaia di cellule: doppietti e cellule con più guide sono attesi per disegno.

## 2. Che cosa si può controllare, per sorgente

`sì` = con ciò che c'è; `dopo` = dopo il recupero delle cellule; `no` = mancano gli input
necessari, e il motivo; `?` = da verificare sul file.

| Sorgente | Integrità e scala | Profondità e geni | MT | Doppietti e ambiente | Assegnazione delle guide | Efficacia del knockdown | Controlli | Asse e composizione |
|---|---|---|---|---|---|---|---|---|
| Controlli di gara | sì | sì | sì (12 geni) | no: niente gocce vuote né guide | non si applica | non si applica | sono i controlli | sì |
| HepG2 | sì | sì, con il totale pubblicato | sì | no: niente gocce vuote | sì (`guide_id`) | sì, il bersaglio sta nell'asse per molti bersagli | sì (NTC) | sì |
| HIPSCI (tre schermi) | sì | sì | sì | no: niente gocce vuote | sì (conteggi delle guide e metadati per cellula, in locale) | sì | NTC scarsi (36 nel pool fitness) e non assegnate da tenere separate | sì |
| Jurkat GSE249595 | sì | sì | ? (selezione dei geni del saggio) | **sì**: matrice non filtrata e hashing | sì (matrici delle guide per canale) | ? | ? | ? |
| K562 GWPS (Drive) | dopo | dopo | dopo | ? | dopo | dopo | dopo | dopo |
| Mixscale (Zenodo, RDS) | dopo | dopo | dopo | ? | dopo | dopo | dopo | dopo |
| Southard (Zenodo) | dopo | dopo | dopo | dopo, dalle uscite di cellranger | dopo | CRISPRa: effetto sul bersaglio atteso in su | dopo | dopo |
| A549 (GEO) | dopo | dopo | dopo | ? (matrice grezza da 10 GB) | dopo (`sgRNA.csv.gz`) | KO: il bersaglio non scende per forza nell'RNA | dopo | dopo |
| KOLF2.1J, Orion, CD4, VIPerturb | dopo | dopo | dopo | ? (file già filtrati dagli autori) | dopo | dopo | dopo | dopo |
| Tahoe | sì (uno shard) | sì (uno shard) | ? | no | non si applica: farmaci | non si applica | DMSO | ? |
| DLD-1, DepMap, H1 2025 (metadati) | no: non sono cellule | no | no | no | no | no | no | parziale |

La colonna «Asse e composizione» chiede la maschera dei geni misurati dal saggio, la dimensione
della libreria dichiarata e l'analisi del supporto comune e di quello completo (§5 del piano). Si fa
per ogni shard al momento della scrittura (`contracts.py`, campi `measured` e `depth_native`).
