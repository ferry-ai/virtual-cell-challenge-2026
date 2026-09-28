# storico — linee chiuse dell'11–19 settembre, sonde, infrastruttura ritirata

Tutto ciò che sta qui ha il codice nel tag `archivio/pre-pulizia-2026-09-23` o `-24`
([ARCHIVIO.md](../../docs/ARCHIVIO.md)) e nessuna scelta di oggi ne dipende direttamente. Molte
misure restano vere per ciò che misuravano: sono **fotografie datate**, non guide. Il riassunto
delle misure di quei giorni è in [docs/storico/PROGETTO_sezioni_3_4_2026-09-28.md](../../docs/storico/PROGETTO_sezioni_3_4_2026-09-28.md).
Indice generale: [../README.md](../README.md).

## Esperimenti in pseudobulk e primi modelli (12–19 settembre)

| Data | Cartella | Nocciolo | Vale? |
|---|---|---|---|
| 18–19/09 | [conditioned_2026-09-18/](conditioned_2026-09-18/) | Primo predittore neurale condizionato su bersaglio e contesto: scartato dalla sua regola; il lineare con gli stessi input lo pareggia (CP-0026); il t07 perde in classifica | sì, esito negativo |
| 18/09 | [common_component_2026-09-18/](common_component_2026-09-18/) | Componente comune RPE1: scartata dalla sua regola (CP-0025) | sì, esito negativo |
| 18/09 | [source_lineage_2026-09-18/](source_lineage_2026-09-18/) | RPE1 trasferisce su HepG2 meglio di K562, anche a parità di chiamate, ma soprattutto per la parte comune; RPE1 non copre nessun bersaglio ufficiale (CP-0023, CP-0024) | sì |
| 17/09 | [source_coverage_2026-09-17/](source_coverage_2026-09-17/) | Quanto del banco HepG2 coprono RPE1 e K562; il pannello condiviso di 1.059 bersagli | sì |
| 17/09 | [coexpression_2026-09-17/](coexpression_2026-09-17/) | La co-espressione nei controlli HepG2 non predice l'effetto del knockdown (0,0015 di correlazione parziale mediana) | sì, esito negativo |
| 16/09 | [expression_gate_2026-09-16/](expression_gate_2026-09-16/) | Gate di espressione sul contesto di destinazione: non promosso dalla sua regola (CP-0017, D-033) | sì, esito negativo |
| 15/09 | [go_slim_2026-09-15/](go_slim_2026-09-15/) | Il GO slim non aggiunge nulla: il controllo permutato va come quello vero (CP-0014, D-028) | sì, esito negativo |
| 15/09 | [svd_2026-09-15/](svd_2026-09-15/) | SVD randomizzata: non sostituisce l'esatta senza cambiare le predizioni (CP-0015) | sì |
| 15/09 | [rank_2026-09-15/](rank_2026-09-15/) | Il rango oltre 16 non trasferisce (CP-0015, D-030) | sì |
| 15/09 | [gpu_2026-09-15/](gpu_2026-09-15/) | Prontezza GPU: la GPU accelera il solo DE dello scorer | storico |
| 15/09 | [runtime_2026-09-15/](runtime_2026-09-15/) | 7,81 GiB di RAM, disco sotto il pavimento per TGFB | storico |
| 15/09 | [eval_protocol_2026-09-15/](eval_protocol_2026-09-15/) | 12 split del protocollo congelato di allora, tutti di sviluppo (D-032) | storico |
| 14/09 | [benchmark_3ctx_2026-09-14/](benchmark_3ctx_2026-09-14/) | Benchmark a tre contesti (K562, RPE1, HepG2): la differenza modular_frozen − ShrunkTransfer è positiva nei tre fold (CP-0013) | sì, in spazio proxy |
| 14/09 | [benchmark_2026-09-14/](benchmark_2026-09-14/) | Primo confronto modulare su K562/RPE1: inconcludente (CP-0011) | sì |
| 14/09 | [hepg2_2026-09-14/](hepg2_2026-09-14/) | Acquisizione di HepG2 (md5 verificato) e confronto generatore × predittore: il generatore decide Jaccard e fedeltà, il predittore il PDS (CP-0013) | sì |
| 14/09 | [encoder_inputs_2026-09-14/](encoder_inputs_2026-09-14/) | Sonda dei descrittori dei bersagli: HGNC, GO, STRING scaricati con sha256 | sì |
| 12/09 | [pipeline/](pipeline/) | Prima pipeline verticale: a piena ampiezza il trasferimento è peggio del nulla; l'ampiezza calibrata guadagna l'1–8 % in MSE; correlazione fuori lignaggio 0,095 (CP-0003) | in parte: un file superato (R-010); l'ampiezza per gli invii è superata da D-042 |
| ≤12/09 | [transfer_ceiling/](transfer_ceiling/) | Numeri corretti e riusati; il nome della cartella suggerisce un «tetto» mai dimostrato (R-007) | in parte |

## Sonde, acquisizione dei dati e prime ricerche (11–17 settembre)

| Data | Cartella | Nocciolo | Vale? |
|---|---|---|---|
| 17/09 | [drive_evidence_2026-09-17/](drive_evidence_2026-09-17/) | md5 e percorsi delle copie su Drive dei grezzi pesanti | storico |
| 15/09 | [remote_2026-09-15/](remote_2026-09-15/) | Parità HepG2 e ripresa dei download; le istruzioni usano «65,8 GiB» invece di 61,31 (R-013) | in parte |
| 15/09 | [remote_catalog_2026-09-15/](remote_catalog_2026-09-15/) | Piano del catalogo remoto, nessun download | storico |
| 15/09 | [source_cards_2026-09-15/](source_cards_2026-09-15/) | Schede di Replogle SC, H1, CD4, Srivatsan, McFaline, Tahoe, scBaseCount | in parte (unità del profilo, R-013) |
| 15/09 | [jiang_2026-09-15/](jiang_2026-09-15/) | Jiang/TGFB: record Zenodo e file piccoli; copertura del pannello mancante | storico |
| 15/09 | [nadig_reconcile_2026-09-15/](nadig_reconcile_2026-09-15/) | HepG2: GEO e mirror scPerturb coincidono; Jurkat 1,29 GB, 0/300 bersagli del pannello | sì |
| 15/09 | [primeflow_2026-09-15/](primeflow_2026-09-15/) | Fattibilità da preprint; codice e pesi mancanti; rinviato | storico |
| 15/09 | [ricerca_dataset_20260915.md](ricerca_dataset_20260915.md) | Dossier di una campagna dell'orchestratore: livelli di consultazione dichiarati, non misure nostre | storico |
| 11–12/09 | [candidate_verification/](candidate_verification/) | Sonde remote con byte e sha256: coperture per sorgente e per bersaglio (`panel_coverage.csv`), annotazioni, pilota CD4 a 64 cellule | in parte: due file sono corpi di risposte 404 (R-005) |
| 12/09 | [grok_verification/](grok_verification/) | Sonde sulle piste fornite da Grok (R-008) | in parte |
| 12/09 | [candidate_pdf_extracted.txt](candidate_pdf_extracted.txt) | Testo di un PDF esterno di candidati: diverse sue tesi sono state smentite (R-006) | storico, fonte non affidabile |
| 11/09 | [data_audit/](data_audit/) | Audit dei controlli ufficiali (18.400 × 18.533 per contesto, UMI mediani ~20.000) e metadati HIPSCI con md5 | sì |

## Infrastruttura degli agenti ritirata (13–19 settembre, D-040)

| Data | Cartella | Nocciolo | Vale? |
|---|---|---|---|
| 16–19/09 | [ciclo_giornaliero/](ciclo_giornaliero/) | Registrazioni della catena di cicli (piano, revisione, collaudo, controllo di Grok): che cosa hanno consegnato gli agenti, non risultati scientifici | storico |
| 16/09 | [catena_2026-09-16/](catena_2026-09-16/) | Le sole prove della catena sui servizi veri | storico |
| 13–15/09 | [orchestrator/](orchestrator/) | Esecuzioni dell'orchestratore multi-modello: le prove del 13–14 sono a secco, con contenuti inventati (DOI `10.0000/finta-`) | storico |
| 13/09 | [oracle/](oracle/) | Prima esecuzione dell'oracolo pairwise su fixture sintetici | storico |
