# Come Arc ha prodotto i dati della gara 2026: il post del 1° ottobre

**Fonte primaria:** Arc Institute, *Generating high-quality Perturb-seq data for the 2026 Virtual
Cell Challenge*, datato 1 ottobre 2026,
<https://arcinstitute.org/news/behind-the-data-virtual-cell-challenge-2026>. Il proprietario l'ha
segnalato il 2/10 inoltrando in chat un'email degli organizzatori («Generating the data for the
competition»). Il testo è stato letto per intero nel browser il 2/10, verso l'01:00 ora locale
(`date`: 01:03). Il testo non è copiato qui per non riprodurre un'opera protetta: quella che segue
è una parafrasi, con i numeri del post.

**Perimetro:** che cosa dichiarano gli organizzatori sui dati, il confronto con ciò che abbiamo
già misurato e che cosa ne segue per noi. Ogni riga dice il tipo di affermazione. Nessun job,
nessun download, nessun invio.

## 1. Che cosa dichiara il post

Tipo: **dichiarato dagli organizzatori**, non verificato da noi salvo dove indicato al §2.

| Punto | Dichiarazione |
|---|---|
| Linee | Sei linee cellulari, scelte per coprire tessuto d'origine, lignaggio e stato di malattia; diverse dalle H1 della gara 2025. **Non sono nominate**, e il post non dice quali tre siano di validazione e quali tre finali. Una figura illustra tre tipi di linea comuni nel Perturb-seq: staminali, immortalizzate da tessuto sano (spesso con hTERT), tumorali |
| Uniformità fra linee | Ogni linea è stata validata per l'attività CRISPRi con una soglia severa prima dello screen. Stesse sequenze di sgRNA in ogni linea, MOI in un intervallo stretto, raccolta allo stesso tempo dopo l'introduzione della perturbazione. Stesso protocollo, stesse piattaforme di profilazione e sequenziamento, stessa pipeline di elaborazione; controlli di qualità a ogni passo |
| Scala | Più di 10.000 perturbazioni per linea, più 100 sgRNA non-targeting. Oltre un miliardo di cellule maneggiate, oltre 30 milioni profilate sulle sei linee. Mediana di 500 cellule per perturbazione e per linea; circa 50.000 cellule di controllo per esperimento |
| Selezione per la gara | Perturbazioni e NTC della gara sono scelti dall'insieme completo: tenute le perturbazioni con **riduzione mediana dell'espressione del bersaglio di almeno l'80%**, poi **sottocampionate a 400 cellule** per perturbazione. La figura 5 parla di copertura, profondità e silenziamento coerenti nelle sei linee |
| Saggio | 10x Flex a sonde; sonde su misura catturano le sgRNA. Mediana di 20.000 UMI per cellula, oltre 800 miliardi di letture per linea su Ultima UG100. Elaborazione con `cyto` (Teyssier e Dobin 2026), la pipeline di Arc per il Flex |
| Tempi | Circa sei mesi dall'ingegnerizzazione delle linee all'analisi |
| Rilascio | Nessuna data di rilascio del dataset completo. Le sei linee sono descritte come «la punta dell'iceberg» di una produzione che continua |

**Il post non dice:** i nomi delle linee; la divisione fra validazione e set finale; l'effettore
CRISPRi; le guide per gene; i giorni fra infezione e raccolta; se la soglia dell'80% valga linea
per linea o sulle sei linee insieme.

## 2. Confronto con quello che avevamo già misurato

| Dichiarazione | Nostra misura | Esito | Fonte |
|---|---|---|---|
| 400 cellule per perturbazione | Forma attesa 300 × 400 × 3 | coerente | [SOTTOMISSIONE](../../../docs/SOTTOMISSIONE.md), §1 |
| 100 NTC nell'esperimento | 46 guide NTC per contesto, 400 cellule ciascuna (18.400), **stessi 46 identificativi in A, B e C**, numerati fra 3 e 99 | coerente con un sottoinsieme comune dei 100 (interpretazione) | [ntc_guide_structure.csv](../external_compat/ntc_guide_structure.csv), riletto il 2/10 |
| Mediana di 20.000 UMI per cellula | Dimensione media di libreria per guida NTC: A 19.862–22.023 (mediana 21.140), B 19.206–20.722 (20.052), C 20.170–22.076 (21.147) | coerente; la nostra è una media per guida, non la mediana per cellula | stesso file |
| 10x Flex a sonde | Asse ufficiale = pannello di sonde Flex v1 | coerente | [context_fingerprints](../context_fingerprints_2026-09-22/) |

Il riassunto per contesto viene da [riassunto_ntc.py](riassunto_ntc.py), poche righe sul CSV
citato: conta guide e cellule, dà minimo, mediana e massimo di `mean_library_size` e l'intervallo
degli identificativi.

## 3. Che cosa ne segue per noi

**3.1 Profondità del silenziamento.** *Interpretazione.* Un calo dell'80% vale ln 5 ≈ 1,61 in
logaritmo naturale. Nelle nostre sorgenti la profondità mediana del silenziamento va da 0,62
(HEK293T) a 1,81 (K562) ([profondità del silenziamento](../../sorgenti/profondita_silenziamento_2026-09-27/RISULTATI.md)).
I bersagli della gara sono quindi silenziati almeno quanto la mediana del K562. Le mediane di
HCT116 (1,00), HEK293T (0,62) e KOLF2.1J (0,83) stanno sotto la soglia della gara.

Due cautele:
- le nostre mediane valgono su tutti i bersagli di un universo, quella della gara sui soli
  bersagli selezionati;
- lo stesso report misura che la profondità spiega poco della risposta a valle (pendenze da 0,09
  a 0,48). Non sostiene una normalizzazione delle sorgenti per profondità.

*Proposte, non eseguite:*
- verificare sui file degli invii t22/t28 che il gene bersaglio stesso scenda di almeno l'80% in
  ogni contesto rispetto ai controlli; il calcolo è locale e non consuma quota;
- se una rete riceve la profondità come ingresso, come propone il report sulla profondità, per
  D/E/F il valore da imputare è almeno 1,61, non la mediana della sorgente.

**3.2 Protocollo identico nelle sei linee.** *Interpretazione.* Fra A/B/C e D/E/F le differenze
tecniche dovrebbero essere minime: cambiano la biologia della linea e la sua risposta alle stesse
guide. Le calibrazioni fatte sui controlli di A/B/C (profondità, dispersione) sono un punto di
partenza ragionevole per D/E/F. I controlli di D/E/F arriveranno comunque il 22/10, e la
calibrazione si rifà su di essi ([PROCEDURE §7](../../../docs/PROCEDURE.md#7-il-set-finale-22-ottobre)).
Con le stesse sgRNA ovunque, le differenze di efficacia fra linee non dipendono dal disegno delle
guide.

**3.3 Tipi di linea.** *Ipotesi.* Il post mette lo stato di malattia fra gli assi di diversità e
illustra tre tipi di linea. È probabile che almeno una delle sei sia immortalizzata da tessuto
sano, non tumorale. In quale gruppo cada non si scrive qui: dipende dalle identità di A/B/C, che
restano fuori dalla repo pubblica. Cautela: la figura descrive i tipi «comunemente usati», non la
composizione dichiarata delle sei linee.

*Proposta:* il banco a sei membri di [R-LEAD](../../../docs/piani/strategia-scientifica.md)
includa almeno una sorgente immortalizzata non tumorale. Nel corpus c'è già RPE1 (hTERT-RPE1,
Replogle 2022), negli universi del 26/09 ([sorgenti](../../sorgenti/README.md)).

**3.4 Dataset completo.** *Fatto.* Non è pubblico e il post non dà date. Non cambia i piani sui
dati prima del 5 novembre.

## 4. Sorgenti citate dal post: catalogo

Nessuna è stata scaricata; ogni download richiede il via del proprietario. Il catalogo è
fatto come quelli in `reports/sorgenti/ricerca_sorgenti_*`.

| Sorgente | Che cos'è | Dati | Ruolo possibile | Stato della verifica |
|---|---|---|---|---|
| Swinderman et al. 2026, ProPer-seq, bioRxiv [10.64898/2026.02.04.703058](https://doi.org/10.64898/2026.02.04.703058) | Il metodo Flex a sonde su misura di Arc e del gruppo Gilbert. K562 con CRISPRa, confronto fra 3', 5' e Flex sulle stesse cellule; 3.550 combinazioni sgRNA × effettore dCas9 (fra cui dCas9-KRAB); 260 combinazioni CAR × ORF in linfociti T primari. Dice di aver generato con questo metodo i dati di training della gara 2025 (H1): 844.736 cellule, mediana di 540 UMI di sgRNA per cellula, il 93% con silenziamento oltre l'80% | Grezzi su SRA (SUB15796302, non ancora pubblici); processati su un Dropbox per i revisori; GEO alla pubblicazione. Codice: `github.com/jswinderman/custom_flex_probe_design`, `github.com/aidanwinters/pyturbseq` | Ponte di piattaforma Flex/3'/5' nello stesso K562, come in [ponte_flex](../../sorgenti/ponte_flex_2026-09-28/); poco per CRISPRi | Letti l'abstract e le sezioni dei metodi e della disponibilità dei dati; preprint CC-BY-NC-ND 4.0 |
| Teyssier e Dobin 2026, `cyto`, bioRxiv [10.64898/2026.01.21.700936](https://doi.org/10.64898/2026.01.21.700936) | La pipeline di Arc per il 10x Flex, usata per i dati della gara | software | Capire come nascono i conteggi della verità di gara | non letto |
| Allen Institute, *10x Flex v2 Enables High Throughput IL-6 Signaling Inhibitor Analysis in T cells*, [10.57785/vpde-ss91](https://doi.org/10.57785/vpde-ss91) | Dati causali di segnalazione IL-6 in linfociti T, in Flex v2 | da verificare | Linfociti T in Flex; perturbazioni non genetiche | non letto |
| Oesinghaus et al. 2025, dizionario delle citochine nel sangue periferico, bioRxiv [10.64898/2025.12.12.693897](https://doi.org/10.64898/2025.12.12.693897) | Perturbazioni con citochine in cellule immunitarie, Parse e UG100 | da verificare | Non genetico, non Flex | non letto |
| Zhang et al. 2025, Tahoe-100M | Perturbazioni chimiche su larga scala | già noto al progetto | — | — |

Il post cita anche Rood et al. 2024 (Cell) e Replogle et al. 2022 (eLife), che non sono dataset
nuovi.
