# Ricerca di dati del 25 settembre, notte: audit di tre candidati e nuove sorgenti

25 settembre 2026, 00:20–00:45 (ora italiana). Sei esecuzioni in sola lettura di agenti
dell'hub (`C:\Users\ferra\agent-hub\runs\20260925-0020*`, fuori dalla repo): claude2 per
Mixscale, Flex e nuove sorgenti; grok per la microglia e per una seconda ricerca di nuove
sorgenti, indipendente; antigravity per le leve della fedeltà (rapporto non usato qui: contiene
due errori sul metodo, vedi §6). Le sottoattività 1–3 della scheda
[R-DATI](../../docs/piani/dati-affidabilita.md) avanzano; nessun dato è stato scaricato.

**Come leggere le etichette.** *Verificato da Claude* = riletto da Claude attraverso un'API
pubblica (Zenodo, Figshare, FTP del GEO) il 25 settembre. *Verificato dall'agente* = l'agente
cita la pagina da cui l'ha letto; non riletto da Claude. *Dedotto* e *da verificare* come
nel resto della repo.

## 1. Mixscale: come sono calcolati i log2FC dell'archivio (sottoattività 1)

- **Misurato sul file locale:** le colonne sono `log2FC_<linea>`, `beta_cell_type<linea>` e
  `p_cell_type<linea>`; una riga (`ZFPM2-AS1`) ha `NA` nel log2FC di tre linee e valori finiti
  in tutti i sei beta (`reports/dld1_audit_2026-09-24/source_inventory_r2/mixscale_inventory.json`,
  righe 1961 e 1968 secondo l'agente).
- **Dedotto dal codice del pacchetto** (`Run_wmvRegDE` in `satijalab/Mixscale`,
  `R/scoring_de.R`, letto dall'agente attraverso uno strumento che riassume la pagina: **le
  citazioni vanno rilette sul testo grezzo**):
  - il `log2FC` di una linea confronta le sole cellule perturbate di quella linea con i suoi
    non-targeting, senza pesi, su conteggi grezzi più pseudoconteggio;
  - `beta` e `p` vengono da una sola regressione su tutte le linee insieme, con dispersione
    stimata in comune;
  - le righe sono l'unione dei filtri per linea, e il log2FC di una linea è `NA` dove il gene
    non passa il filtro di quella linea.
- **Conseguenza, dedotta:** i confronti di CP-0035 e di `reports/pattern_mixscale_2026-09-24/`
  usano i soli `log2FC` sui geni finiti in tutte e sei le linee, quindi l'intersezione dei
  filtri: ogni valore viene dalle cellule della propria linea, e la dipendenza residua fra
  linee passa solo dalla scelta delle righe. **Qualunque uso di `beta` o `p` non è
  indipendente fra linee.** Resta da verificare che l'archivio sia stato prodotto proprio
  con questa funzione: gli autori non lo scrivono.
- **File (verificato dall'agente, Zenodo 14518762, v2.1, CC-BY-4.0):** cinque oggetti Seurat,
  uno per stimolo, 2,6–5,6 GB; l'archivio DE da 324,1 MB; tre file di firme; un oggetto di RNA
  bulk. Le colonne dei metadati per cellula non sono documentate; che esistano cellule non
  stimolate non è scritto da nessuna parte (**da verificare**).
- **Memoria, stima dell'agente:** nessun oggetto entra in 8 GB; 12 GB di Colab sono al limite.

## 2. Microglia GSE335887 (sottoattività 2) — verificato dall'agente sul GEO e su PMC

- File: `iMG_processed_cite_crop.h5mu` 520 MB, `iTF_processed_cite_crop.h5mu` 778 MB,
  `iTF_processed_merged_crop.h5ad` 2,7 GB, matrici Cell Ranger filtrate e grezze
  (105–195 MB). Libreria di 31 geni × 2 sgRNA più 5 non-targeting; una sola linea iPSC nei
  campioni depositati.
- La distinzione "binaria" (ZNF532) contro "graduale" (PRDM1) usa un punteggio Mixscale
  costruito **sullo stesso trascrittoma** delle firme di stato: nessuna stima dell'intensità
  su geni disgiunti. L'efficienza di knockdown per guida non è data in numeri nel testo.
- **Che prova permetterebbero** (proposta): dentro la linea, intensità stimata su geni
  esclusi dalla risposta, poi gradino contro spostamento graduale contro quota di rispondenti,
  sulle due repliche biologiche del braccio iTF, se le etichette delle guide sono negli
  oggetti (**da verificare** aprendo gli h5mu). Nessuna replica fra donatori.

## 3. Ponte fra saggi: dati K562 letti con Flex (sottoattività 3)

- **VIPerturb-seq, verificato da Claude** (API di Zenodo, record 18460279, pubblicato il
  2026-02-02, CC-BY-4.0): `genome_wide_filtered.rds` 3,61 GB, `genome_wide_binA/B/C.RDS`
  3,56 / 3,78 / 2,89 GB, `vimentin_screen.rds` 1,88 GB, `multimodal_cell_line_mixing_pilot.rds`
  1,58 GB, `genome_wide_manifest.txt`.
- **Verificato dall'agente** sul preprint (bioRxiv 10.64898/2026.02.12.705613): CRISPRi con
  KRAB-dCas9-MeCP2; tre guide per gene codificante; lo schermo genome-wide è letto con Flex v2;
  6.724 perturbazioni superano il controllo di qualità; mediana di 42 cellule per gene
  bersaglio; mediana di 15.100 UMI e 5.300 geni per cellula; knockdown rilevato nell'88% delle
  perturbazioni. Nessun numero pubblicato di concordanza fra Flex e 3' sulle stesse
  perturbazioni: andrebbe calcolato da noi contro K562 genome-wide di Replogle.
- **Demo 10x GEM-X Flex K562:** pagina irraggiungibile (HTTP 429). Resta com'è nella scheda 12
  di `reports/schede_sorgenti_2026-09-24/SCHEDE.md`.

## 4. Nuove sorgenti: due ricerche indipendenti

Nessuna delle due trova dati a singola cellula nuovi in linee T, squamose o cervicali oltre a
quelli già schedati il 24 settembre.

| Sorgente | Che cos'è | Stato della verifica |
|---|---|---|
| **KOLF2.1J, atlante CRISPRi del genoma espresso** (Nourreddine, Doctor et al., Nat Biotechnol 2026; Figshare+ 10.25452/figshare.plus.27261219) | CRISPRi, 11.739 geni perturbati, >2,5 milioni di cellule, una linea iPSC; `KOLF_Pan_Genome_QC_Filtered.h5ad` 189,39 GB, `KOLF_Strong_Perturbations.h5ad` 46,72 GB, due sottoinsiemi da 1,3–7,0 GB; CC BY 4.0 | **Verificato da Claude** (API di Figshare): titolo, licenza, numero di geni e di cellule nella descrizione, file e dimensioni. Trovato solo da grok |
| **GSE345058** (Liu, Hillsley et al., bioRxiv 10.64898/2026.06.01.728087) | Knockout Cas9 di 1.000 geni in A549, CROP-seq, 606.075 cellule, mediana 564 cellule per knockout | **Verificato da Claude** (FTP del GEO): h5ad 23 GB, conteggi grezzi `.mtx.gz` 10 GB, annotazioni 38 MB, sgRNA. Chimica e MOI **da verificare**. Trovato solo da claude2 |
| **CRISPRa di 1.836 fattori di trascrizione in fibroblasti Hs27 e RPE-1** (Southard et al., Nat Genet 2025) | 10x 3' v3.1, circa 0,8 + 1,76 milioni di cellule; h5ad per cellula su Zenodo, 8–30 GB; CC BY 4.0 | Trovato da entrambi; dimensioni e licenza verificate da grok (API di Zenodo), non rilette da Claude. **Attivazione, non knockdown** |
| Organoidi/linee gastriche dcPerturb-seq (PRJNA1219803) | Knockout di 226 geni in sette linee gastriche | Solo letture grezze su SRA; nessuna matrice pubblica trovata |

### Catalogo completo di quanto trovato stanotte

Su richiesta del proprietario nessun dataset si perde, anche se lontano dai contesti della
gara: per D-044 può servire a generalizzare o a studiare pattern. I rapporti integrali degli
agenti sono copiati in [agenti/](agenti/), perché le cartelle dell'hub si possono ripulire.
Dove non indicato, i fatti sono **verificati dall'agente** sulla pagina citata nel suo
rapporto e **non riletti da Claude**.

| Dataset | Che cosa contiene | Ruolo possibile (proposta) | Rapporto |
|---|---|---|---|
| KOLF2.1J, Figshare+ 27261219 | CRISPRi su 11.739 geni espressi, iPSC, >2,5 M cellule, CC BY 4.0 (verificato da Claude) | Contesto CRISPRi a copertura quasi genomica; bersagli nuovi del set finale; regimi T/J | grok |
| GSE345058 | Knockout di 1.000 geni in A549, 606 mila cellule, conteggi per cellula (verificato da Claude) | Confronto fra modalità KO e CRISPRi sugli stessi geni; pattern di risposta in epitelio polmonare | claude2 |
| Southard et al. 2025, Zenodo 15200179, 15213597, 15213619, 15211972 | CRISPRa di 1.836 fattori di trascrizione in fibroblasti Hs27 e RPE-1, h5ad per cellula, CC BY 4.0 | Programmi regolati da TF in due contesti con gli stessi bersagli (H1–H3); segno di attivazione, non convertibile d'ufficio in knockdown | entrambi |
| VIPerturb-seq, Zenodo 18460279 | CRISPRi genome-wide in K562 letto con Flex v2, CC-BY-4.0 (verificato da Claude) | Sorgente nel saggio della gara; ponte Flex–3' (H8) | claude2 |
| Microglia GSE335887 | CROP-seq e CITE-seq di 31 regolatori in microglia da iPSC | Forme di risposta: soglia, gradualità, quota di rispondenti (H4–H5) | grok |
| PerturbFate, GSE291147 | CRISPRi di oltre 140 geni della resistenza al vemurafenib in melanoma, RNA nuovo/vecchio e ATAC | Tempo e cromatina insieme alla risposta (H9–H10); linea e chimica da verificare | claude2 |
| dcPerturb-seq gastrico, PRJNA1219803 | Knockout di 226 geni in sette linee gastriche | Stessi bersagli in molte linee epiteliali; solo letture grezze, nessuna matrice trovata | grok |
| Perturb-multiome HSPC, GSE274113 | 19 fattori di trascrizione in cellule staminali ematopoietiche primarie, RNA + ATAC | Prior di cromatina (H10); troppo pochi bersagli per trasferire | grok |
| GSE343369 | Knockout di 225 geni in iPSC e corpi embrioidi | Pattern in differenziamento; lontano dalla gara | entrambi |
| GSE344535 | RPE-1, Flex 16-plex, perturbazioni di micro-ORF virali | Riferimento tecnico Flex; bersagli non geni umani | grok |
| GSE327057 | Perturb-seq di 1.130 ligasi E3 in cellule dendritiche primarie di topo, LPS | Pattern in cellule primarie stimolate; specie diversa | grok |
| GSE320250 | CRISPRi di 520 geni in cellule staminali ematopoietiche di topo | Specie diversa; matrice usabile da verificare | grok |
| Perturb-seq cerebrale in vivo (bioRxiv 10.64898/2026.03.16.711480) | Knockout di 1.947 geni nel cervello di topo, letto con Flex, 7,7 M nuclei | Riferimento Flex in tessuto; nessuna accessione trovata | claude2 |
| bioRxiv 2026.08.24.746802 | Perturb-seq Cas9 in 16 linee tumorali, 100 geni | Molti contesti con gli stessi bersagli; accessione non trovata | grok |
| GSE203240 | Schermo genome-wide in HCT116 (letalità da dosaggio sintetico) | Da capire se è a singola cellula | claude2 |

Scartati dagli agenti come non genetici o già noti: GSE327727 (farmaci su PBMC), schermi
mieloidi GSE327124/GSE327133 (ordinati, non a singola cellula), l'annuncio Tahoe/Arc/Biohub
(farmaci). Le ricerche che non hanno trovato nulla sono elencate nei due rapporti.

## 5. Ruoli proposti (proposte, non adozioni)

1. **VIPerturb-seq** come sorgente letta nel saggio della gara e come ponte con K562 in 3'
   (ipotesi H8 di `reports/ipotesi_trasferimento_2026-09-24/IPOTESI.md`). Costo: circa
   3,6 GB di `.rds` da convertire fuori da R; prima leggere `genome_wide_manifest.txt` e
   l'elenco delle feature per sapere asse delle sonde e bersagli.
2. **KOLF2.1J, perturbazioni forti (46,7 GB)** come ulteriore contesto CRISPRi a copertura
   quasi genomica, utile anche per i 300 bersagli nuovi del set finale. Costo alto: da
   valutare un'estrazione mirata per bersaglio invece del download intero, come per CD4
   (stadio 97). Il lignaggio pluripotente non è un criterio di esclusione (D-044).
3. **GSE345058** solo come confronto fra modalità (knockout contro CRISPRi), non come
   sorgente dello stesso intervento.

Se una sorgente aggiunta alla media migliori il punteggio lo dirà per prima il t17 (HEK293T
come quarta sorgente), in lettura il 25 settembre.

## 6. Limiti

- Parte dei fatti viene da pagine lette dagli agenti attraverso un riassuntore; le citazioni di
  codice Mixscale vanno rilette sul testo grezzo prima di costruirci sopra.
- Il rapporto di antigravity sulle leve della fedeltà non è usato: afferma che le chiamate
  spurie abbassano la fedeltà sotto la precisione dei segni e che il coseno di PDS è
  invariante alla traslazione, e nessuna delle due cose segue dalla definizione dello scorer.
