# Sorgenti del 27 settembre: dati multi-contesto, la struttura di KOLF2.1J e il piano d'ingestione

27 settembre 2026, pomeriggio. Nella scheda [R-V2](../../docs/piani/modello-v2.md). Catalogo e verifiche, come
chiede la regola di conservare ogni dataset trovato; nessun dato scaricato oltre ai metadati.

## Il via del proprietario (trascritto dalla chat)

- Nel pomeriggio del 27/09 (l'ora del messaggio non è registrata) il proprietario ha chiesto di far entrare in
  pipeline tutti i candidati catalogati, citando la
  tabella: HIPSCI CRISPRi, VIPerturb-seq, KOLF2.1J, knockout in A549 (GSE345058), CRISPRa di Southard, Jurkat
  (lettura mirata), X-Atlas/Pisces. È il via ai download di quelli pubblici.
- Nota di progetto dello stesso pomeriggio: «sei sempre autorizzato ad usare colab e kaggle, per runpod chiedi».
- Nello stesso pomeriggio: per ora niente invii al server e niente push.

## Ricerca di altri dati multi-contesto (misurato: due agenti, due famiglie)

La domanda: dati pubblici in cui gli stessi geni perturbati sono misurati in molti tipi cellulari (almeno cinque),
per imparare come cambia la risposta con il tipo cellulare. antigravity ha cercato solo nei risultati di ricerca
([rapporto](agenti/ricerca_antigravity.md)); grok ha verificato sulle pagine primarie
([rapporto](agenti/verifica_grok.md)). Esito di grok:

| Pista | Che cos'è davvero | Stessi geni in ≥ 5 tipi cellulari? | Dimensione, licenza |
|---|---|---|---|
| VIPerturb-seq (Zenodo 18460279) | CRISPRi letto con Flex; il braccio genome-wide è solo K562 (6.724 perturbazioni nell'oggetto filtrato); un pilota di 100 guide in K562, HEK293 e HAP1 | no | 17,3 GB in tutto (pilota 1,6 GB), CC BY 4.0 |
| Echoes of Silenced Genes (Kaggle, Myllia) | CRISPRi in una sola linea tumorale non nominata; 80 perturbazioni di training | no | 845 MB, non commerciale; l'uso richiede di accettare le regole della gara (decisione del proprietario) |
| HyperMapDB | profili **previsti** da un modello, 2.500 geni, 18 contesti; non misure | no | 16,9 GB, CC BY 4.0 |
| scPerturb, PerturBase | raccolte armonizzate di studi già noti | nessuno trovato | — |

Unica pista che corrisponde alla domanda: un set CROP-seq di Myllia con gli stessi 218 geni in THP-1, Jurkat, K562,
A549 e U2OS, **proprietario** (solo su richiesta). **Conclusione:** nessun dataset pubblico misura gli stessi geni
in cinque o più tipi cellulari.

## KOLF2.1J: la struttura del file (misurato, sonde a intervalli di byte)

`kolf_probe.py` e `kolf_probe2.py` leggono solo la struttura dell'h5ad (6 MB trasferiti ciascuna) attraverso
`vcc2026.remote_ranges`. Record Figshare+ 27261219, CC BY 4.0: `KOLF_Pan_Genome_QC_Filtered.h5ad` 189,4 GB, un
sottoinsieme «perturbazioni forti» di 46,7 GB (scelto sull'effetto, quindi selezione sull'esito: non adatto come
sorgente), due sottolibrerie di 4,6 e 7,0 GB; nessun file aggregato.

- 2.659.209 cellule × 37.567 geni; `layers/counts` sono conteggi grezzi (float32) in formato **CSC**, cioè per
  gene, **senza compressione**, a blocchi di 120.120 valori: ogni gene è un tratto contiguo del file.
- `obs`: `gene_target` (11.688 bersagli; controlli `NTC`), `channel` (90), `batch` (3), `total_counts`.

**Conseguenza (implementata in parte):** si possono sommare i conteggi per (bersaglio, gruppo di canali) leggendo
il file per blocchi di geni, in più sessioni in parallelo (Colab, Kaggle o locale), senza scaricarlo: circa 85 GB
di letture per i geni dell'asse ufficiale, poi lo stimatore corretto in locale. Il codice è affidato a codex
(base di lancio, run `20260927-142516-v2-kolf-ingest`).

## Piano d'ingestione per dataset

| Dataset | Come entra | Dove |
|---|---|---|
| KOLF2.1J | somme per blocchi di geni dall'h5ad remoto, poi stima con `min_expected` | Colab/Kaggle o locale |
| HIPSCI CRISPRi | tabelle LFC degli autori (2,7 GB) come sorgente separata; conteggi (7,9 GB) per la stima nostra | locale |
| VIPerturb-seq | `genome_wide_filtered.rds` (3,6 GB) convertito con R (4.5.3 installato), poi stima | locale |
| GSE345058 (knockout, A549) | h5ad 23 GB, per il confronto fra modalità, non come sorgente dello stesso intervento | Colab/Kaggle |
| Southard (CRISPRa) | quattro h5ad da 8–30 GB, uno alla volta; attivazione, non knockdown | Colab/Kaggle |
| Jurkat | già in locale; lettura mirata di 374 geni | locale |
| X-Atlas/Pisces | non ancora pubblicato | — |

## Che cosa pubblicano gli organizzatori (grok, pagine primarie; [rapporto](agenti/organizzatori_grok.md))

- **Dati:** sei linee di tessuti diversi, CRISPRi, 10x Flex, sequenziate su Ultima UG100; delle linee di
  valutazione si danno solo i controlli non mirati. Le perturbazioni sono state «scelte per dare un insieme forte di
  perturbazioni e risposte» (notizia di Arc del 20/08/2026). **Interpretazione, non verificata:** i bersagli del
  pannello sarebbero forti nelle linee della gara, mentre nell'atlante risultano di forza tipica nel K562 e nel CD4
  (`../atlante_2026-09-26/forza_pannello/`); è coerente con il guadagno di ogni raddoppio d'ampiezza.
- **Nuova sorgente candidata:** il dataset completo della gara 2025 (H1 hESC, training, validazione e test) è ora
  pubblico sul Virtual Cell Atlas di Arc, ed è esplicitamente ammesso. In locale ci sono solo i metadati
  (`vcc2025/`). Non è nell'elenco autorizzato il 27/09: serve il via del proprietario, con dimensione e licenza.
- **Baseline:** l'unica pubblicata è lo zero del punteggio, la risposta media del contesto assegnata a ogni
  perturbazione; nessuna baseline di trasferimento fra linee o lineare sui contesti 2026.
- **2025:** i vincitori hanno usato tutti dati del contesto di valutazione (addestramento o affinamento su H1),
  che nel 2026 non esistono; il terzo classificato trasferiva da altre linee e poi scalava linearmente.

## Profili basali per un encoder di contesto, e Flex contro 3' (grok, sera del 27/09; [rapporto](agenti/atlanti_basali_grok.md))

Ricerca in sola lettura, fonti primarie, niente scaricato. Serve alla rete del piano R-V2, che legge il contesto dai
controlli: un encoder dei profili basali si può pre-addestrare su molte più linee delle ~10 perturbate.
- **Candidati, nell'ordine proposto da grok:**
  1. DepMap 26Q1: espressione bulk delle linee, file dei geni codificanti di 305 MB, CC BY 4.0 come dichiarazione del
     programma;
  2. Tahoe-100M, solo le cellule col veicolo DMSO: circa 47 linee a cellula singola, CC0, chimica Parse fissata;
     l'intero dataset pesa 338 GB;
  3. Kinker 2020 (GSE157220): 198 linee, 10x Chromium, senza trattamento; dimensione non indicata;
  4. MIX-seq: le sole cartelle DMSO e non trattate, circa 0,37 GB di 2,26; 10x 3', CC BY 4.0;
  5. HIPSCI: i controlli non mirati, 499.998 cellule su 34 linee iPSC; già in locale. **Misurato qui:** chimica 10x
     5' v2, non Flex.
- **Flex contro 3' sulle stesse cellule:** nessuna linea cellulare pubblica profilata con entrambe. Il più vicino è De
  Simone 2025 (PBMC dello stesso donatore, 10x 3' v3.1, 5' v2 e Flex, su CELLxGENE). Il set di sonde Flex umano
  v1.0.1 ha 18.532 geni, uno in meno dell'asse di gara (18.533): coincidenza di conteggio, non un'identità verificata.
- **VIPerturb-seq è Flex (misurato 27/09, sonda Kaggle, `sonde_viperturb/`):**
  - 326.247 cellule, 19.068 geni, 6.725 bersagli, 18.880 guide, 48 campioni;
  - barcode Flex e metadati `guide`, `gene`, `sample`;
  - con i bersagli condivisi col K562 di Replogle (3') è un ponte di chimica sulle risposte, non solo sui profili
    basali, **se** la linea è il K562 come dice il catalogo del 25/09: da verificare sul file.
- **Download:** DepMap, Tahoe, Kinker, MIX-seq e De Simone non sono nell'elenco autorizzato il 27/09 (HIPSCI sì, ed è già scaricato): serve il via del proprietario.
