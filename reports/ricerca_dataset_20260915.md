# Dossier Ricerca Dataset VCC2026
**Data:** 2026-09-15
**Run Orchestratore:** `20260914T222203Z-campagna-dati-v1-037cbd`
**Motore:** Orchestratore deep-kimi (Modalità `scientific_research`)

## 1. Registro delle ricerche e degli esiti
La campagna si è svolta su 3 fasi (indipendente, confronto, mirata). 
* **DeepSeek (solver_a):** Ha effettuato 15 query mirate sfruttando la modalità `ricerca_intelligente`, identificando 10 fonti uniche.
* **Kimi (solver_b):** Ha elaborato un piano di 10 query mirate (Google Scholar, PubMed, GEO) ma non le ha potute eseguire a causa della mancanza di uno strumento di web browsing abilitato sul suo profilo. Ha agito in veste di revisore e critico sulle evidenze trovate da DeepSeek.
* **Esito finale:** Arresto per disaccordo irrisolto (`unresolved_disagreement`). Due contraddizioni sono rimaste aperte (legate all'inaccessibilità dei file senza credenziali e alla mancata verifica indipendente delle fonti da parte di Kimi).

## 2. Tabella dei candidati e livelli di verifica

| Candidato | Contesto cellulare | Tipo | Matrice RNA | Livello di verifica (Dichiarato da DeepSeek) |
|---|---|---|---|---|
| **Zhu/Marson GWCD4i** (CZ Platform / Zenodo 18876252) | CD4+ T cells primarie (22M cellule) | CRISPRi Perturb-seq | Sì | Sezione/Full-text consultato. Da verificare scaricabilità file h5ad senza credenziali AWS. |
| **iPSC Perturbation Cell Atlas** (Katalog 2024) | iPSC umane | CRISPRi Perturb-seq | Sì | Trovato nei risultati. Da verificare record GEO e presenza NTC. |
| **Papalexi et al. 2021** (GSE153056) | THP-1 (Monociti) | CRISPR (multimodale) | Sì | Sezione consultata. Contesto non T-cell né epiteliale. |

## 3. Sovrapposizioni misurate
**Nessuna sovrapposizione misurata.** 
*Motivo della lacuna:* Entrambi i worker hanno segnalato, tramite esplicita richiesta all'operatore, di non avere accesso all'elenco dei 300 geni bersaglio del pannello VCC2026. Di conseguenza, il calcolo della sovrapposizione per il candidato CD4 (GWCD4i) o iPSC non è stato matematicamente possibile durante il run.

## 4. Duplicati e candidati scartati
* **Shifrut et al. 2018 (Cell):** Scartato. Sebbene eseguito in T cells primarie, il readout è arricchimento/deplezione via FACS, non vi è matrice RNA single-cell.
* **MCF10A CROP-seq (GSE108699):** Scartato. Perturbazione di tipo Knockout (KO), non CRISPRi, con un solo NTC.
* **GSE190604:** In sospeso/Scartato. Mescola CRISPRa e CRISPRi, non verificata l'indipendenza delle matrici per la parte CRISPRi.

## 5. Candidati prioritari
1. **Primary Human CD4+ T Cell Perturb-seq (Zhu et al. 2025/2026)**
2. **A Perturbation Cell Atlas of Human Induced Pluripotent Stem Cells (Nourreddine 2024)**

## 6. Vantaggio concreto rispetto ai dati disponibili
* **CD4+ GWCD4i:** Copre massicciamente il contesto "linfoide T", lo stesso del **Contesto A** della gara VCC2026. È su scala immensa (22M cellule) e copre l'intero genoma, garantendo teoricamente l'inclusione dei bersagli VCC2026. È la controparte linfoide del K562 di Replogle (già in nostro possesso).
* **iPSC Atlas:** Fornisce un vastissimo set di baseline su un contesto distale. Ottimo per misurare il trasferimento (transfer ceiling) e la specificità di linea.

## 7. Raccomandazione di acquisizione
**Raccomandazione: ACQUISIRE IN PILOT il candidato CD4+ GWCD4i.**
* *Prerequisiti per l'acquisizione:* Eseguire uno script per verificare che il bucket S3 di CZ Virtual Cells Platform permetta il download degli `h5ad` senza credenziali gestite. 
* *Incertezze residue:* Scaricare la lista completa dei bersagli del Perturb-seq e interpolarla con i 300 target VCC2026 per determinare le esatte `cells per target` prima di inglobare i dati nel training. Verificare se gli NTC sono mappati correttamente nell'oggetto AnnData.
