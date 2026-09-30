# Primi job di ingestione: che cosa chiedono (R-LAB, P2)

30 settembre 2026 sera, Claude (sessione `a1ec75f0`). **Proposta da approvare**: nessun job è
partito e nessun dato è stato scaricato. I byte remoti sono **misurati** sui metadati
(`remote_sizes.json`); le dimensioni delle uscite sono **stime**: per J01–J03 vengono dal pilota HepG2 (1.000 cellule, 4,2
milioni di valori non nulli, 10,4 MB, circa 2,5 byte per valore), le altre sono ordini di grandezza. Ogni job segue il flusso del §6 del piano e il preflight di `docs/ERRORI.md`: un job,
una sorgente, uscite in percorsi nuovi, parità e ricevuta prima dell'indice.

## Il vincolo da cui partire

- **Il portatile non può ospitare il corpus.** Misurato alla presa in carico: 1,7 GB liberi su C: e
  0,75–0,9 GB di RAM libera su 7,8 GB. In locale si fanno inventario, contratti, controlli e piccoli
  piloti.
- **Serve una destinazione persistente per gli shard.** La quota di Drive non è misurata da qui:
  `G:` mostra il disco del portatile. I limiti dei dataset privati di Kaggle vanno verificati prima
  del primo job. **La scelta della destinazione è del proprietario** (domanda 1 sotto).
- **Account multipli.** La scheda annota che si possono usare altri account Colab e Kaggle. Le FAQ di
  Colab però vietano gli account multipli usati per aggirare i limiti di risorse (§6 del piano). Si
  propone un solo account per servizio finché il proprietario non conferma che l'uso previsto rispetta
  i termini.

## I job, in ordine di valore per costo

| Job | Sorgente | Letto (misurato) | Dove | Uscita (stima) | Perché prima |
|---|---|---|---|---|---|
| J01 | HepG2 Nadig | 0,85 GB, copia già su Drive | Colab, dal Drive | circa 1,5 GB di shard | schema h5ad denso: il primo adattatore, e la parità con il totale pubblicato |
| J02 | HIPSCI, tre schermi | 7,93 GB (Figshare 27989294, MIT) | Kaggle o Colab, scaricato sul runtime | circa 28 GB (1,88 M cellule; mediana circa 5.900 geni per cellula) | le sole cellule iPSC per linea, 19 linee; guide e metadati per cellula |
| J03 | Jurkat GSE249595 | circa 3,8 GB (GEO) | Colab | circa 0,1 GB per canale di 67.000 cellule (600 geni per cellula) | unico con gocce vuote e hashing: l'adattatore multi-guida e la stima dell'RNA ambientale |
| J04 | K562 GWPS | 65,8 GB, già su Drive | Colab, lettura a blocchi dal Drive | decine di GB | la sorgente più usata della ricetta, a livello di cellula |
| J05 | Mixscale | circa 20 GB di oggetti Seurat (Zenodo 14518762) | runtime con R | decine di GB | cinque stimoli, più linee: la loss DE diventa loss sulle cellule |
| J06 | VIPerturb | 3,6 GB filtrato più 10,2 GB di bin (Zenodo 18460279) | runtime con R | alcuni GB | K562 in Flex, il ponte tecnico verso la gara |
| J07 | A549 KO | 10 GB di conteggi grezzi MTX più annotazioni (GEO) | Colab o Kaggle | alcuni GB | testa KO separata |
| J08 | Southard CRISPRa | Hs27 9,7 GB e RPE-1 29,8 GB di h5ad; cellranger 21,6 e 46,8 GB, opzionali | Colab o Kaggle | decine di GB | testa CRISPRa; la parte RPE-1 non è mai stata ingerita |
| J09 | KOLF2.1J | 189,4 GB (Figshare+ 27261219, CC BY 4.0) | lettura a intervalli di byte | decine di GB | il più grande CRISPRi su iPSC |
| J10 | Orion HCT116 e HEK293T | 128,4 GB (Hugging Face) | lettura in streaming | decine di GB | due linee dello stesso studio; licenza NC-SA |
| J11 | CD4 Marson 2025 | **1.735,8 GB** in 12 file (4 donatori × 3 condizioni) | soli intervalli di byte per bersagli scelti | da decidere | donatore, guida e condizione per cellula; l'archivio intero è fuori portata |
| J12 | Tahoe-100M | 467,5 GB (Hugging Face) | shard scelti per piastra, dose e linea | da decidere | testa farmacologica; DMSO per l'encoder |
| R01 | H1 della gara 2025 | da verificare: locatore non registrato | scaricato e congelato, **non letto** | — | la riserva primaria proposta: nessuno ne ha letto gli esiti |

Restano da localizzare le cellule di K562 essential e RPE1 di Replogle, e di microglia e
PerturbFate. Per DLD-1 e DepMap non ci sono cellule da ingerire.

## Che cosa serve dal proprietario

1. **La destinazione persistente degli shard**, e il suo spazio: Drive, dataset privati Kaggle o
   altro. Senza, nessun job può pubblicare le sue uscite.
2. **Il via a J01–J03**, i tre job piccoli che validano i tre schemi (h5ad denso, CSV geni × cellule,
   MTX con hashing). Se lo schema regge, J04–J08.
3. **Il via ai download** delle sorgenti di J02–J12, con i byte della tabella, e al download
   congelato di H1 2025 come riserva (R01).
4. **Gli account**: un solo account per servizio, oppure la conferma che l'uso di più account rispetta
   i termini di Colab e Kaggle.
5. **La riserva**: approvare H1 2025 come riserva primaria (`reports/modelli/risposta_biologica_2026-09-30/holdout_registry.json`).
