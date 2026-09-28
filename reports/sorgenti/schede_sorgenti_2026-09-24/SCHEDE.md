# Schede delle sorgenti candidate, 24 settembre 2026

Schede di 17 sorgenti di perturbazione a singola cellula, più una tabella di accessioni viste
una volta sola, nel formato di [GENERALIZZAZIONE.md](../../docs/GENERALIZZAZIONE.md) §2 (D-044).
Le ha redatte **claude2**, un agente dell'hub multi-agente (`C:\Users\ferra\agent-hub`, run
`20260924-222329-cards-sources`), leggendo i 14 report della ricerca della sera: il testo
dell'agente è riportato più sotto senza modifiche. Sono **elenchi di candidati, non sorgenti
adottate**: nessuna è entrata in una ricetta.

Come leggerle: **[v]** = fatto letto su una fonte primaria da un agente e ricontrollato da un
agente di un'altra famiglia; **[v1]** = letto da un solo agente; **[dv]** = da verificare. I
report citati con le sigle (R1, G4, V8, …) stanno nella cartella `runs/` dell'hub, fuori da
questa repo.

## Correzioni verificate dopo la stesura

Di Claude, sui file o sulla repo:
- **DLD-1, orientamento della matrice:** geni sulle righe (2.827), perturbazioni sulle colonne
  (6.451, di cui 496 `NTC_*`). Misurato sul file: `reports/dld1_ceiling_2026-09-24/`.
- **Orion, licenza:** CC-BY-NC-SA-4.0 è registrata nella repo (`scripts/102_extract_orion_panel.py`,
  docstring; `docs/PROGETTO.md` §4 punto 9), non verificata alla fonte. La scheda la dava ignota.

Seconda verifica di grok sulle sei schede [v1] (`SECONDA_VERIFICA.md`, run
`20260924-222755-cards-second-check`):
- **THP-1, GSE221321:** confermata. Yao et al., Nat Biotechnol 2024 (PMID 37872410); knockout e
  CRISPRi (dCas9-KRAB), 598 geni della risposta a LPS, 10x; `RAW.tar` 5,8 GB con h5ad/rds elaborati.
- **Neuroni da iPSC, GSE289235:** **corretta**. Su GEO c'è un CROP-seq di **45 geni** più 5
  non-targeting, 9.252 neuroni, 10x GEM-X 3′ v4; i 1.343 geni sono uno screen di imaging
  (CaMPARI2). Boggess et al., Nat Commun 2026.
- **Demo 10x GEM-X Flex K562:** **corretta**. 1.233.385 cellule, circa 6.903 sgRNA; la scomposizione
  "4.045 assegnate" era sbagliata. Licenza della pagina CC BY 4.0. Nota tecnica CG000814.
- **CD4 elementi, E-MTAB-13324:** confermata, 250.195 cellule, 4 gRNA per bersaglio e 35
  non-targeting; dati dell'articolo sotto CC0.
- **Perturb-Multi, GSE275483:** confermata; i 50 controlli sono "negativi", non per forza
  non-targeting.
- **Glia radiale, GSE284197:** confermata. CRISPRi di 44 fattori di trascrizione, circa 600
  cellule per gene; letture grezze umane su dbGaP (phs002624), dati elaborati pubblici su GEO.

## Fonti di profili basali

Per i descrittori di contesto e per le ipotesi sulle linee di A/B/C: file pubblici DepMap in
`DEPMAP.md` (run `20260924-222758-depmap-files`). Verificata la versione 24Q4 su Figshare+
(CC BY 4.0: espressione 507 MB, numero di copie 1,39 GB, `Model.csv` 646 KB); la 26Q1 del 1°
aprile 2026 esiste ma i suoi file non erano leggibili in automatico.

---

## Testo dell'agente (claude2)

Ho scritto le schede di 17 sorgenti e ho messo in una tabella le altre accessioni ancora da verificare. Non ho modificato nessun file e non ho usato il web: le schede vengono solo dai 14 report e dai documenti del repository indicati.

**Come ho lavorato.** Ho letto per intero i 14 `result.md`, `docs/GENERALIZZAZIONE.md` (§2, §3, §5), `docs/checkpoints/0035-dld1-mixscale-audit.md` e `reports/dld1_audit_2026-09-24/RISULTATI.md`. I report sono indicati con queste sigle:

| Sigla | Report |
|---|---|
| R1 | `20260924-195148-data-r1/claude2` |
| F1 | `20260924-200824-followup-claude2` |
| G4 | `20260924-201813-data-r4-a/grok` |
| F2 | `20260924-202151-followup-claude2` |
| FG | `20260924-202506-followup-grok` |
| V6 | `20260924-202505-data-r6-verify-jurkat` |
| P7 | `20260924-202903-data-r7-panel-grok` |
| M7 | `20260924-202940-data-r7-geo-mining` |
| M8 | `20260924-203626-followup-grok` |
| M9 | `20260924-204116-followup-grok` |
| V8 | `20260924-203623-data-r8-verify-dld1` |
| V9 | `20260924-204117-data-r9-verify-organoids` |
| IA | `20260924-212855-ingest-a-dld1-methods` |
| IB | `20260924-212857-ingest-b-mixscale-files` |

**Legenda.** **[v]** = verificato: il report citato lo ha letto su una fonte primaria, e l'URL è nel report. **[v1]** = verificato da un solo agente, senza seconda verifica. **[dv]** = da verificare. Ruoli secondo D-044: Add (addestramento), CC (confronto fra contesti), TE (test esterno), DB (descrittori basali), BS (baseline dello stesso bersaglio). Tutte le etichette sono **inferred**: le ho ricavate io dai report.

---

### 1. DLD-1 — GSE337988 (Yeung … Xie, bioRxiv 10.64898/2026.07.10.737863)
- **Bersagli:** CRISPRi con Zim3-dCas9 inducibile [v V8]. Libreria di 5.943 promotori su 4.954 geni scelti a caso, non l'intero genoma; c'è anche una libreria pilota [v V8]. Etichette con suffissi P1, P2, P1P2, ENST, W/D [v RISULTATI §1]. Nel pannello: 67/300 [v CP-0035]. L'unità della perturbazione è probabilmente il promotore [dv IA].
- **Risposte:** gli autori fanno la DE su circa 3.000 geni altamente variabili, "3022 transcripts" [v IA]. Nella matrice Low1: 2.827 geni, di cui 2.587 sull'asse ufficiale [v CP-0035]. Stime limma-voom [v IA]. Base del log [dv]. Orientamento righe/colonne [dv].
- **Contesti:** una linea sola, 10x 3′ GEM-X v4 con hashing CMO [v V8]. Low/Med/High indicano la MOI: medie di 1,2, 3,7 e 6,7 guide per cellula [v V8]. Low1 e Low2 sono probabilmente due metà divise per lane [dv IA].
- **Qualità:** 1.869.846 cellule dopo il QC, mediana 132,2 cellule per gene [v IA]. Controlli: cellule con almeno una guida NT [v IA]. Numero di guide NT [dv]. Knockdown verificato con CD81 [v IA].
- **Uso:** Add e CC come contesto colorettale; BS limitata a 61 bersagli (in comune con K562).
- **Accesso:** GEO pubblico; preprint CC-BY 4.0; nessuna licenza propria sui dati [v V8]. SRA privata fino al 2026-12-21 [v V8]. `assays.h5` da 1,1 a 4,3 GB, `se.rds` da 0,64 a 2,9 GB, `RAW.tar` 25 GB [v V8]. Contenuto di `.h5` e `.rds` [dv].
- **Prima dell'uso:** unità, SE, aggregazione dei promotori, indipendenza di Low1 e Low2.

### 2. Mixscale — GSE281048 e Zenodo (Jiang, Nat Cell Biol 2025, doi 10.1038/s41556-025-01622-z)
- **Bersagli:** CRISPRi con dCas9-KRAB-MeCP2. Cinque librerie, una per via di segnalazione, da 44 a 61 geni con 3 sgRNA ciascuno e 14 NT [v FG, PMC12083445]. Nell'archivio DE: 271 file e 218 bersagli; 9 nel pannello [v CP-0035].
- **Risposte:** chimica whole-transcriptome, non un pannello mirato [v IB]. DE pesata Mixscale: log2FC, beta, p-value [v RISULTATI §2]. I beta non sono log2FC [v RISULTATI §4]. Numero di geni negli RDS [dv].
- **Contesti:** A549, MCF7, HT29, HAP1, BxPC3, K562 × 5 stimoli (IFNβ, IFNγ, INS, TGFβ, TNFα), tutti a 24 h, cioè 30 contesti [v FG]. Nessuna cellula non stimolata nello screen [v FG]. Chimica Parse Evercode WT Mega [v F2, FG]. Due repliche [v IB].
- **Qualità:** circa 2,6 milioni di cellule e 1.626 test [v FG]. Cellule per perturbazione non riportate [dv]. Le stime DE potrebbero condividere selezione o parametri fra linee [dv CP-0035].
- **Uso:** CC (sei linee), Add su bersagli nuovi, TE per linea esclusa. Per DB servono profili basali, che nel pacchetto DE non ci sono [v GENERALIZZAZIONE §5].
- **Accesso:** Zenodo 10.5281/zenodo.14518762, CC-BY-4.0 [v FG, IB]. Zip DE da 324.112.587 byte già scaricato, MD5 verificato [v RISULTATI]. Seurat: 2,64–5,60 GB su Zenodo (`.rds`), 2,4–5,2 GB su GEO (`.rds.gz`) [v FG]. RAM di picco sotto i 12 GB [dv].
- **Prima dell'uso:** fold per identità del bersaglio (181 bersagli compaiono in un solo stimolo); non contare gli stimoli come linee.

### 3. Jurkat — GSE247601, sottoserie GSE249595 (Song et al., Nat Cell Biol 2025, PMC11906366)
- **Bersagli:** CRISPRi con dCas9-KRAB su 18.595 geni (3.220 con 8 sgRNA, 15.375 con 4) [v G4, V6]. Numero di guide NT [dv V6].
- **Risposte:** pannello mirato TAP-seq di **374 geni** [v P7, dall'articolo, SRA SRX22812235 e deck Myllia]. Numero di righe di `transcriptome_features` [dv P7].
- **Contesti:** Jurkat E6, maschio, T-ALL [v V6]. Nelle stesse corse: 10% non trattate e 90% stimolate 24 h con anti-TCR/CD28 [v V6]. 10x Chromium X 3′ [v V6]. Chiave di corrispondenza fra hash e condizione [dv V6].
- **Qualità:** più di 586.000 cellule, MOI alta (mediana 13 guide per cellula), circa 400 cellule per gene [v G4, V6]. Assegnazione binomiale con correzione BH [v V6].
- **Uso:** CC e TE sul solo supporto misurato; Add molto limitato dalla MOI.
- **Accesso:** GEO pubblico, nessuna licenza sul record; articolo CC BY-NC-ND 4.0 [v V6]. Matrici transcriptome da 2,28 GB, calcolate dal modello di fetch [v V6, da ricontare]. Escludere GSM7897840–43.
- **Prima dell'uso:** maschera fuori dai 374 geni; un modello per cellule con più guide.

### 4. VIPerturb-seq (bioRxiv 10.64898/2026.02.12.705613)
- **Bersagli:** CRISPRi con dCas9-KRAB-MeCP2, circa 57.050 sgRNA su geni codificanti [v R1].
- **Risposte:** pannello di sonde (nome e versione) [dv F1]; uguale a v1.0.1 [dv].
- **Contesti:** K562 per lo screen genome-wide; pilota in K562, HEK293 e HAP1 [v R1]. 10x Flex v2 (Apex); pilota in v1 e v2 [v F1]. CellRanger 9.0 [v F1].
- **Qualità:** mediana 14 cellule per guida, 42 per gene [v R1].
- **Uso:** controllo della chimica Flex; BS su K562; CC tecnica fra chimiche.
- **Accesso:** Zenodo 10.5281/zenodo.18460279, CC-BY-4.0, 17,3 GB in `.rds`; `genome_wide_filtered.rds` 3,6 GB [v R1].
- **Prima dell'uso:** asse dei geni contro le 18.533 feature ufficiali.

### 5. X-Atlas/Orion (bioRxiv 10.1101/2025.06.11.659105)
- **Bersagli:** CRISPRi, 41.780 sgRNA su 18.903 geni [v R1].
- **Risposte:** h5ad con solo coppie di guide dello stesso gene [v R1]. Dimensioni [dv].
- **Contesti:** HCT116 e HEK293T; chimica GEM-X 5′ [v R1].
- **Qualità:** circa 8 milioni di cellule [v R1]. Cellule per perturbazione [dv].
- **Uso:** Add e BS (è già nel repository: `reports/orion_2026-09-23/`, che non ho aperto).
- **Accesso:** Figshare+ 10.25452/figshare.plus.29190726; licenza [dv R1, la pagina ha risposto 403]. F1 dice che Orion ha la stessa licenza di Pisces, ma non cita la fonte.

### 6. X-Atlas/Pisces (bioRxiv 10.64898/2026.03.18.712807)
- **Bersagli:** CRISPRi genome-wide; dimensione della libreria [dv F1].
- **Risposte:** formato [dv].
- **Contesti:** 16 contesti: HCT116, HEK293T, HepG2, iPSC, Jurkat a riposo, Jurkat attivato, più un braccio iPSC multi-lineage con 10 tipi cellulari [v F1]. Il braccio iPSC è su Flex [v F1, G4]. Chimica di Jurkat: vedi le contraddizioni.
- **Qualità:** 25,6 milioni di cellule [v F1].
- **Uso:** CC (sei contesti e più tipi derivati) e Add, quando i dati saranno rilasciati.
- **Accesso:** Hugging Face "Coming Soon", 24,3 kB [v F1]. CC-BY-NC-SA-4.0 [v F1]. Compatibilità con le regole di gara [dv R1].

### 7. H1 hESC — GSE295214 (Pan … Zhuang, bioRxiv 10.64898/2026.05.16.725005)
- **Bersagli:** CRISPRi, 6.638 sgRNA su **2.978 geni selezionati**, non l'intero genoma [v V8].
- **Risposte:** matrici Cell Ranger per campione [v V8]. Numero di feature [dv].
- **Contesti:** H1, 85 campioni [v V8]. 10x inferito; 3′ o 5′ [dv].
- **Qualità:** circa 1,3 milioni di cellule, "tens to hundreds" per perturbazione [v V8]. Numero di NT [dv].
- **Uso:** CC con un contesto pluripotente; Add.
- **Accesso:** solo `RAW.tar` da 7,8 GB, con file h5 da 20 a 160 MB [v V8]. Preprint CC-BY 4.0 [v V8].

### 8. THP-1 — GSE221321
- **Bersagli:** knockout e CRISPRi, 598 geni della risposta a LPS [v1 M9].
- **Risposte:** [dv].
- **Contesti:** THP-1; stimolo LPS da verificare [dv].
- **Qualità:** [dv].
- **Uso:** CC mieloide; tenere separati KO e CRISPRi.
- **Accesso:** solo `RAW.tar` 5,8 GB [v1 M9]. Articolo e licenza [dv].

### 9. Neuroni da iPSC — GSE289235
- **Bersagli:** CRISPRi CROP-seq, 1.343 geni [v1 M9].
- **Risposte:** H5AD indicato da esummary; FTP non controllato [dv].
- **Contesti:** Qualità: [dv].
- **Uso:** CC con un contesto lontano; Add.
- **Accesso:** dimensioni, articolo e licenza [dv].

### 10. Organoidi gastrici — GSE280506 (Lo … Kuo, Nat Commun 2025, PMC12354852)
- **Bersagli:** braccio single-cell: 69 CRISPRi (dCas9-KRAB) e 22 CRISPRa (dCas9-VPR) [v V9]. I 1.952 geni e il knockout appartengono agli screen bulk [v V9].
- **Risposte:** una matrice Cell Ranger [v V9]. Se contenga entrambi i bracci [dv].
- **Contesti:** organoidi primari TP53/APC doppio KO; DMSO o cisplatino; 10x 3′ v2 [v V9].
- **Qualità:** 20.414 cellule CRISPRi (circa 142 per sgRNA) e 9.026 CRISPRa (circa 198) [v V9]. Numero di NT [dv].
- **Uso:** CC (epitelio primario); TE su pochi bersagli.
- **Accesso:** `.h5` 226 MB, `mtx` 601 MB [v V9]. Articolo CC BY-NC-ND 4.0; GEO senza licenza [v V9].
- **Prima dell'uso:** separare i due trattamenti e i due effettori.

### 11. A549 — GSE337804 (Myllia)
- **Bersagli:** knockout CRISPRn a MOI bassa, 218 geni × 3 sgRNA, più 20 NT e 20 guide in regioni prive di geni [v F2, dal PDF su FTP].
- **Risposte:** whole-transcriptome inferito; 10x 5′ HT v2 con depletion Jumpcode [v F2].
- **Contesti:** A549 su GEO; HCT116 descritto ma non depositato [v F2].
- **Qualità:** circa 36.300 singoletti attesi per canale, cioè un obiettivo e non un conteggio misurato [v F2]. Circa 100 cellule per guida [dv, inferito].
- **Uso:** CC (KO contro CRISPRi) e TE.
- **Accesso:** articolo e licenza [dv].

### 12. Demo 10x GEM-X Flex K562
- **Bersagli:** circa 6.903 sgRNA, di cui 4.045 assegnati (567 codificanti, 280 lncRNA, 177 NT) [v1 G4].
- **Contesti:** K562 con KRAB-dCas9, Flex 16-plex, Cell Ranger 9.0.0, circa 1,2 milioni di cellule [v1 G4].
- **Uso:** controllo tecnico della chimica Flex.
- **Accesso:** pagina /cn/ [v1 G4]. File, dimensioni e licenza [dv].

### 13. CD4 elementi — E-MTAB-13324 (Alda-Catalinas, Genome Biol 2024)
- **Bersagli:** CRISPRi con ZIM3-dCas9 su 45 elementi non codificanti e 35 TSS [v1 G4, da estratti di ricerca].
- **Contesti:** CD4 primarie, 10x 3′, 250.195 cellule [v1 G4].
- **Uso:** CC (cellule T primarie); pochi bersagli genici.
- **Accesso:** lista dei file e licenza dei dati [dv]; codice MIT.

### 14. Squiers et al. 2026 (bioRxiv 10.64898/2026.07.22.739901)
- **Bersagli:** CRISPRi (dCas9-KRAB) su fattori di trascrizione [v F2].
- **Contesti:** cheratinociti Ker-CT in organoidi epidermici, 10x 3′ HT v3.1, 236.112 cellule [v F2].
- **Uso:** CC (contesto squamoso), se si ottiene l'accesso.
- **Accesso:** solo su richiesta agli autori [v F2].

### 15. Nadig — GSE264667 (Nat Genet 2025)
- **Bersagli:** CRISPRi su 2.393 geni essenziali [dv R1, solo snippet di ricerca].
- **Contesti:** Jurkat e HepG2; chimica 3′ [dv].
- **Uso:** BS e CC; già noto al repository (CP-0016, citato in R1).
- **Accesso:** mirror di 1,294 GB su scPerturb (secondo R1, dal repository). Licenza [dv].

### 16. Perturb-Multi — GSE275483 (Saunders, Cell 2025)
- **Bersagli:** knockout con Cas9, 202 geni × 2 sgRNA più 50 NT [v1 G4].
- **Contesti:** epatociti di **topo**, Flex [v1 G4].
- **Uso:** controllo tecnico; si usa per l'uomo solo con la conversione degli ortologhi.
- **Accesso:** `RAW.tar` 231 MB [v1 G4].

### 17. hiPSC CRISPRi in 34 linee (Cell Genomics 2025)
- **Bersagli:** 7.226 geni [v R1].
- **Contesti:** 26 donatori [v R1].
- **Accesso:** accessione Figshare, chimica e licenza dei dati [dv]. Forse è lo stesso studio dell'atlante Nat Biotechnol 2026 [dv].

### Altre accessioni viste una sola volta
Tutte **[v1]** su esummary e FTP; articolo, licenza e chimica sono da verificare.

| Accessione | Contesto e disegno |
|---|---|
| GSE327644 | macrofagi primari, KO |
| GSE283574 | NCI-H358, Cas12a |
| GSE294098 | MOLM-13 |
| GSE311503 | astrociti, CRISPRa |
| GSE248941 | teratomi |
| GSE266618 | CAR T |
| GSE241882 | cellule T, perdita di cromosomi |
| GSE221578 | AML/PDX |
| GSE289721, GSE311359, GSE335887 | microglia, CRISPRi |
| GSE284197 | glia radiale, CRISPRi, h5ad da 4,1 GB |
| GSE273677 | EndoC-βH1 |
| GSE306853 | CAF, 4 geni, probabilmente KO [v V9] |
| GSE309511 | WI-38, CRISPRa di elementi |
| GSE293514 | mioblasti |
| GSE279287 | 786-O e Caki-1 |
| GSE281464 | fibroblasti cardiaci, KO di enhancer |
| GSE244732 | miometrio |
| GSE238219 | HepaRG, CRISPRi |
| GSE270828 | cellule staminali neurali, 180 HAR |
| GSE215253 | HSPC, base editing |
| GSE271444 | cardiomiociti, CRISPRa |

GSE171737 e GSE271788 sono bulk o non single-cell, secondo G4.

---

## Contraddizioni fra i report
1. **GSE247601, lettura:** G4 la chiama trascrittoma intero; V6 e P7 misurano un pannello di 374 geni. Si chiude a favore di P7.
2. **GSE247601, dimensioni:** G4 dice 2,42 GB; V6 dice 2,28 GB. Anche il numero di V6 viene da un modello e va ricontato.
3. **GSE247601, autori:** G4 li presenta come "Song, Loregger, Bürckstümmer, Li"; V6 mostra che sono il 1°, 10°, 19° e 24° autore.
4. **GSE295214:** M7 scrive "genome-scale" con modalità non indicata; V8 misura CRISPRi su 2.978 geni. Numero di campioni: 85 contro i 64 riportati dallo strumento.
5. **GSE280506:** M8 attribuisce KO e 1.952 geni ai dati single-cell; V9 misura 69 CRISPRi e 22 CRISPRa.
6. **Chimica di Pisces Jurkat:** F1 riporta "optimized FiCS" con kit non indicato; G4, dalla tabella del PDF, dice GEM-X 5′.
7. **Mixscale, file:** GEO ha `.rds.gz`, Zenodo ha `.rds`. Nome del file TGFβ: `TGFB` nell'API, `TGFB1` nel readme (IB).
8. **GSE337988:** M7 scrive "~5000 genes" e cita 3 file; V8 misura 4.954 geni su 5.943 promotori e 7 file grandi. Campioni High: 7 contati contro 8 nel sommario (IA).
9. **DLD-1, geni di risposta:** il preprint parla di circa 3.000 HVG (3.022); la matrice Low1 ne ha 2.827. È una lacuna da spiegare più che una contraddizione.

## Cosa manca ancora a tutte le schede
- **Numero di controlli NT:** manca per tutte tranne Mixscale e GSE337804. Cellule per perturbazione: mancano per Mixscale, Orion, GSE337804, Nadig e i dataset GEO visti una sola volta.
- **Asse dei geni misurati e unità:** nessuna sorgente ha ancora l'intersezione misurata con le 18.533 feature ufficiali, tranne DLD-1.
- **Licenza dei dati:** manca per Orion, Nadig, demo 10x, E-MTAB-13324, GSE337804, THP-1, neuroni e hiPSC. La licenza dell'articolo non è la licenza dei dati.
- **Checksum:** ce n'è solo uno, per lo zip DE Mixscale.
- **Profili basali per i descrittori di contesto:** non individuati in nessuna sorgente.

## Non fatto e domande per Claude1
- Non ho aperto `reports/orion_2026-09-23/` né CP-0016: non erano fra i documenti indicati. Le schede Orion e Nadig restano quindi più povere di quanto il repository permetterebbe.
- THP-1, neuroni, demo 10x, CD4 elementi e Perturb-Multi non hanno una seconda verifica.
- **Domanda:** la licenza CC-BY-NC-SA si applica anche a Orion? F1 lo afferma senza fonte.
