# Interazioni proteiche per i bersagli mai misurati: protocollo

1 ottobre 2026. Claude Code (Opus 5.5) per il teammate Alfredo, sessione
`42343bb9-c8d1-4b93-a9cc-2008dd008900`, branch `codex/teammate-rlead`. Protocollo scritto **prima di
scaricare grafi o calcolare qualunque misura**: nessun numero di questa cartella esiste ancora.

**Stato:** proposta registrata, da riprendere. Nessun download, job o training avviato. I download di
grafi e dati (sezione 3) e l'uso di quota richiedono il via in chat. Le soglie delle sezioni 5 e 6
sono fissate qui e non si cambiano dopo aver visto i risultati (CP-0030, D-050).

Etichette: **misurato**, **interpretazione**, **ipotesi**, **proposta**.

## 1. Domanda e ipotesi

Nel set finale D/E/F alcuni bersagli potrebbero non essere misurati in nessun dato pubblico:
è il regime J di [GENERALIZZAZIONE](../../../docs/GENERALIZZAZIONE.md). Per questi bersagli l'unica
informazione lecita è che cosa si sa del gene. La domanda è se le interazioni proteiche fisiche e i
complessi permettano di prevederne la risposta trans a partire dalla risposta misurata dei bersagli
vicini, meglio delle alternative più semplici.

- **H1 (segnale), ipotesi.** Due bersagli nello stesso complesso stabile, o legati da un'interazione
  fisica ad alta confidenza, hanno effetti trans più simili di due bersagli scelti a caso con la
  stessa forza d'effetto, la stessa essenzialità e lo stesso numero di cellule. L'eccesso decresce
  con la confidenza dell'arco.
- **H2 (uso), ipotesi.** Per un bersaglio escluso ovunque, la media dei vicini pesata per tipo di
  arco e per contesto supera, nella risposta trans centrata, risposta generica, vicini GO,
  modello lineare sui descrittori e propagazione sulla rete, e perde il vantaggio quando il grafo
  viene rimescolato conservando il grado.
- **H0.** L'eccesso di somiglianza si spiega con il grado, la multifunzionalità o la forza
  dell'effetto (Gillis e Pavlidis 2012), e scompare con il rimescolamento a grado costante o
  condizionando sulla vicinanza GO.

## 2. Che cosa sappiamo già (misurato, nel progetto)

| Prova | Esito | Fonte |
|---|---|---|
| Media dei vicini STRING come predittore, banco HepG2 di test | −0,155 contro +0,020 della ricetta t03 (punteggio previsto) | [CP-0026](../../../docs/checkpoints/0026-predittore-neurale-condizionato.md) |
| Lo stesso sul banco K562, bersagli ufficiali | +0,031, alla pari col lineare (+0,030) | CP-0026 |
| Bersagli senza misure: STRING da solo / cis da solo / 0,1 × STRING + cis | PDS proxy 0,528–0,550 / 0,555–0,579 / fino a +0,035 sul cis; un bersaglio misurato in K562 dà 0,711–0,755 | [bersagli_nuovi](../../trasferimento/bersagli_nuovi_2026-09-26/RISULTATI.md) |
| Rete relazionale costruita dalla covariazione fra geni negli altri knockdown | nessuna abilità, neanche nella stessa linea; sommata al transfer lo peggiora | [covariazione](../covariazione_2026-09-28/RISULTATI.md) |
| Grado STRING fisico dei 300 bersagli del pannello | mediano 2, contro 16 nei 2.057 della screen essenziale | [audit biologico](../../analisi/lead_scientist_2026-09-29/neural/AUDIT_BIOLOGICO.md) |
| Complessi (CORUM), reti TF con segno, GO come grafo | mai provati | bersagli_nuovi, sezione «Che cosa non si è fatto» |

**Interpretazione.** È stata provata solo la forma più grezza (media dei vicini su STRING largo) e
sul lato dei geni letti; il lato bersaglio con complessi e archi ad alta confidenza resta aperto.
Il grado basso del pannello limita il guadagno possibile e va stratificato in ogni risultato.

## 3. Dati

| Ingresso | Versione | Uso | Licenza |
|---|---|---|---|
| Effetti pseudobulk: K562 genome-wide ed essential, RPE1 (Replogle 2022, raw_bulk); HepG2, Jurkat (Nadig 2025, singola cellula, mirror scPerturb) | file e md5 in `vcc-mini/sources.json` del branch `alfredo`; costruiti con `build_mini.py` | risposte dei bersagli, quattro linee | CC BY 4.0 |
| STRING v12.0, *Homo sapiens*, archi fisici con punteggi per canale | file `protein.physical.links.detailed` e `protein.info`, hash al download | strati di confidenza | CC BY 4.0 |
| CORUM 5.0, complessi umani | file di tutti i complessi, hash al download | strato «stesso complesso» | da verificare prima del download |
| hu.MAP 3.0 | complessi, hash al download | replica indipendente dei complessi | da verificare |
| BioPlex 3.0 (HEK293T, HCT116) | archi AP-MS per linea | sensibilità a grafi specifici di una linea | da verificare |
| GOA umano e go-basic | già usati da `target_descriptors.py` | controllo «vicinanza funzionale» | CC BY 4.0 |
| Descrittori dei bersagli | `target_descriptors.py`, senza esiti di perturbazione | caratteristiche dei nodi | derivati |

Simboli mappati sull'asse ufficiale con HGNC (alias e simboli precedenti), mapping ambiguo scartato
e contato. Nessun dato della gara (controlli A/B/C, H1 test) entra in questo studio.

## 4. Stima degli effetti

- Effetto: log1p(10⁴ · media/libreria) perturbato − controllo, nello stesso studio, sui geni comuni
  alle quattro linee; stimatore unico del mini-banco (`build_mini.py`).
- **Solo trans:** si toglie il gene bersaglio; in una sensibilità, anche la finestra cis di 5 kb
  (coordinate GENCODE).
- **Centratura:** per ogni linea si sottrae la media degli effetti dei bersagli di training. È la
  variazione sistematica di Systema (Viñas Torné et al. 2025), che altrimenti gonfia ogni somiglianza.
- **Affidabilità:** HepG2 e Jurkat hanno singole cellule, quindi coseno fra metà indipendenti di cellule
  e controlli. Replogle raw_bulk non le ha, quindi strati di numero di cellule. Nessun filtro per efficacia
  osservata del knockdown (D-011).

## 5. Esperimento E1: il segnale (H1)

**Misura.** Per linea L e strato S, la statistica è

D(S, L) = media sugli archi (u, v) di S del coseno fra effetti centrati
          − media sulle coppie nulle appaiate.

- **Strati S:** stesso complesso CORUM; STRING fisico ≥ 900, 700–899, 400–699; nessun arco entro
  distanza 2.
- **Coppie nulle:** stessi decili di forza d'effetto (norma trans) di u e di v, stessa appartenenza
  alla screen essenziale e stessa fascia di cellule; 20 coppie nulle per arco, con seme fisso.

**Controlli.**
1. **Rimescolamento a grado costante** (Maslov e Sneppen 2002): 1.000 grafi con scambi di archi pari
   a 10 volte il loro numero; p empirico di D osservato contro D rimescolato.
2. **Vicinanza GO:** D ricalcolato dentro fasce di somiglianza GO (Jaccard dei termini propagati).
   La PPI deve aggiungere segnale a parità di GO.
3. **Grado:** D per fasce di grado dei due nodi; ipotesi nulla di Gillis e Pavlidis.

**Incertezza.** Bootstrap a grappoli, 2.000 ricampionamenti. I grappoli sono le componenti dei
complessi CORUM e di STRING ≥ 900 fra i bersagli misurati; con una componente gigante si usano
comunità di Leiden a risoluzione fissata qui (1,0, seme 0). Così archi dello stesso complesso non
contano come prove indipendenti.

**Regola (fissata ora).** H1 passa se, per lo strato CORUM o per STRING ≥ 900, valgono tutte e tre:
1. D > 0 con intervallo al 95% sopra zero in almeno 3 linee su 4;
2. p del rimescolamento < 0,01 nelle stesse linee;
3. D > 0 con intervallo sopra zero dentro la fascia GO più alta che contiene almeno 200 archi.

Altrimenti: **no** per H1, e E2 parte solo come misura descrittiva, senza costruire la rete.
Se meno di 2 linee hanno almeno 200 archi nello strato: **inconclusivo**.

## 6. Esperimento E2: la previsione (H2)

**Regime.** Zero-shot fra linee, come la gara. Si tiene fuori una linea L alla volta. Dei suoi
bersagli si vedono solo i controlli; gli effetti dei vicini vengono dalle altre tre linee. Il
bersaglio da prevedere è nascosto in tutte le linee, con split per hash (`cell_data.stable_splits`
della versione corretta, sale `ppi-2026-10-01`, frazione 0,2). Due varianti:

- **J-gene:** i vicini del bersaglio possono essere misurati nelle linee di training;
- **J-complesso:** si nascondono anche tutti i membri dei suoi complessi CORUM. Decide la
  dichiarazione scientifica di generalizzazione; J-gene decide l'uso in gara.

**Modelli, tutti allenati e scelti sugli stessi fold.**

| Sigla | Modello | Perché c'è |
|---|---|---|
| B0 | risposta generica della linea (braccio `generic` della fase A, o media di training) | minimo da battere |
| B1 | lineare sui descrittori (bilineare con i controlli), Ahlmann-Eltze et al. 2025 | baseline semplice forte |
| B2 | k vicini nella vicinanza GO | separa funzione e fisica |
| B3 | media dei vicini STRING pesata per punteggio | la forma già provata nel progetto |
| B4 | propagazione con riavvio sulla rete (Cowen et al. 2017) | alternativa classica senza parametri appresi |
| M | GAT-T, attenzione sul grafo dei bersagli (sezione 7) | la proposta |
| M-rew | M sul grafo rimescolato a grado costante | controllo negativo |
| M-perm | M con descrittori permutati fra nodi di pari grado | controllo negativo |

**Metriche.**
- **Primaria:** coseno sulla risposta trans centrata, per bersaglio; media per linea; aggregazione
  macro sulle linee.
- **Secondarie:**
  - rango PDS fra i bersagli valutati, con i geni bersaglio esclusi;
  - MSE;
  - segno sui 100 geni con l'effetto osservato più grande;
  - tutte stratificate per numero di vicini misurati (0, 1–2, ≥ 3) e per affidabilità.

Nessun numero si converte in punteggio VCC.

**Regola (fissata ora).** H2 passa per l'uso se, in J-gene, valgono entrambe:
1. M meno il migliore fra B0–B4 ha differenza primaria > 0 con intervallo a grappoli sopra zero in
   almeno 3 linee su 4, e il rango PDS non peggiora (intervallo non tutto sopra zero);
2. M meno M-rew > 0 con intervallo sopra zero nelle stesse linee.

Holm sulle quattro linee è riportato accanto. La stessa regola in J-complesso decide la
dichiarazione di generalizzazione. Tre semi per M, M-rew e M-perm; si riporta la media dei semi.

**Copertura, descrittiva.** Quota dei 300 bersagli del pannello attuale con almeno un vicino CORUM
o STRING ≥ 700 misurato in una fonte pubblica: limita il guadagno ottenibile in gara e si riporta
accanto a ogni risultato. Non è un risultato del modello.

## 7. GAT-T, la rete proposta

- **Grafo dei bersagli.** Nodi: i geni dell'asse. Archi: CORUM e STRING fisico ≥ 400, con tipo e
  punteggio come caratteristiche.
- **Nodi.** Descrittori senza esiti (GO, STRING spettrale, DepMap, HGNC), più l'espressione del gene
  nei controlli della linea bersaglio e in quelli della linea sorgente.
- **Messaggi.** Per il bersaglio v nella linea L, ogni coppia (vicino u, linea sorgente s) con u
  misurato in s porta il codice c(u, s): l'effetto trans centrato proiettato su K = 64 componenti,
  calcolate sui soli bersagli di training delle linee di training del fold.
- **Attenzione** (Veličković et al. 2018) su ciascuna coppia (u, s). Dipende da:
  - tipo e punteggio dell'arco;
  - somiglianza dei descrittori di u e v;
  - concordanza dell'espressione basale di u fra s e L;
  - numero di cellule di (u, s).
- **Cancello di supporto.** Mescola il risultato con la risposta generica di L. Senza vicini, o con
  supporto debole, la rete torna a B0 invece di inventare un segnale.
- **Decodifica.** Dal codice ai geni con la base del fold, più la risposta generica.
- **Addestramento a episodi.** Si nasconde un bersaglio di training e lo si prevede in una linea di
  training dai vicini misurati nelle altre: lo stesso compito del test. La loss è MSE sul codice più
  (1 − coseno) sulla risposta centrata, pesata per affidabilità.
- **Dimensione.** Decine di migliaia di parametri, nessuno indicizzato per gene. Si allena su CPU;
  la GPU non è necessaria.

## 8. Fughe d'informazione: controlli obbligatori

1. Un bersaglio nascosto non compare mai come vicino con il suo effetto, in nessuna linea: test
   automatico che sostituisce i suoi effetti con rumore e verifica predizioni identiche.
2. Base K, centratura, fasce e soglie si calcolano sui soli bersagli di training delle linee di
   training del fold.
3. I descrittori non contengono esiti di perturbazione (D-044); STRING senza il canale di
   co-espressione in una sensibilità, perché quel canale può riflettere dati di perturbazione.
4. In J-complesso, nessun membro dei complessi del bersaglio in nessuna linea.

## 9. Prima dei dati reali

- **Simulazione di potenza.** Grafi sintetici con il grado osservato e un segnale piantato di
  intensità nota. Si riporta la potenza di E1 ed E2 al numero di archi atteso, e la frequenza di
  «passa» sotto H0, che deve restare ≤ 5%.
- **Test unitari.** Il rimescolamento conserva il grado; le coppie nulle sono bilanciate sulle
  covariate; il test di fuga del punto 1 della sezione 8 passa; con metriche nulle la regola non passa.

## 10. Esiti e conseguenze

- **H1 no:** si chiude la via PPI per J nella forma a vicini, con il grado e GO come spiegazione
  registrata. Resta il cis.
- **H1 sì, H2 no:** il segnale c'è ma non si usa meglio delle baseline; si studiano gli errori per
  grado e affidabilità, senza aumentare la capacità.
- **H1 e H2 sì:** GAT-T sostituisce il blocco `association` (0,1 × STRING) dello stadio 100 solo per
  i bersagli senza misure, dopo un banco a sei membri con riserva nuova.

## Bibliografia (consultata il 1/10/2026)

- Replogle J. M. et al., *Mapping information-rich genotype-phenotype landscapes with genome-scale Perturb-seq*, Cell 2022. Bersagli dello stesso complesso (per esempio Integrator) con fenotipi trascrizionali simili.
- Roohani Y., Huang K., Leskovec J., *Predicting transcriptional outcomes of novel multigene perturbations with GEARS*, Nature Biotechnology 2023, doi:10.1038/s41587-023-01905-6. Grafo GO fra perturbazioni.
- Ahlmann-Eltze C., Huber W., Anders S., *Deep-learning-based gene perturbation effect prediction does not yet outperform simple linear baselines*, Nature Methods 22, 1657–1661 (2025). Per perturbazioni non viste vince un lineare con embedding di perturbazione presi da un'altra linea; GEARS non supera le baseline.
- Viñas Torné R. et al., *Systema: a framework for evaluating genetic perturbation response prediction beyond systematic variation*, Nature Biotechnology 2025, doi:10.1038/s41587-025-02777-8. La variazione sistematica gonfia le metriche.
- Csendes G. et al., *Benchmarking foundation cell models for post-perturbation RNA-seq prediction*, BMC Genomics 2025, doi:10.1186/s12864-025-11600-2.
- Wu Y. et al., *PerturBench*, NeurIPS 2025 (Datasets and Benchmarks). Importanza delle metriche di rango.
- *A systematic comparison of computational methods for expression forecasting* (PEREGGRN), bioRxiv doi:10.1101/2023.07.28.551039.
- Wenkel F. et al. (Valence Labs, Recursion), *TxPert: leveraging biochemical relationships for out-of-distribution transcriptomic perturbation prediction*, arXiv:2505.14919 (2025). Più grafi (STRING, GO e due mappe proprietarie); STRING il migliore da solo; il rimescolamento progressivo degli archi abbassa la Pearson Δ, metrica che Systema mostra sensibile alla variazione sistematica.
- Nadig A. et al., *Transcriptome-wide analysis of differential expression in perturbation atlases*, Nature Genetics 2025 (TRADE).
- Szklarczyk D. et al., *The STRING database in 2023*, Nucleic Acids Research 51(D1), D638–D646 (2023), versione 12.0.
- Steinkamp R. et al., *CORUM in 2024: protein complexes as drug targets*, Nucleic Acids Research 53(D1), D651–D657 (2025), CORUM 5.0, 7.193 complessi.
- Fischer S. N. et al., *hu.MAP3.0: atlas of human protein complexes by integration of >25,000 proteomic experiments*, Molecular Systems Biology 2025.
- Huttlin E. L. et al., *Dual proteome-scale networks reveal cell-specific remodeling of the human interactome*, Cell 2021 (BioPlex 3.0).
- Veličković P. et al., *Graph Attention Networks*, ICLR 2018.
- Cowen L., Ideker T., Raphael B. J., Sharan R., *Network propagation: a universal amplifier of genetic associations*, Nature Reviews Genetics 18, 551–562 (2017).
- Maslov S., Sneppen K., *Specificity and stability in topology of protein networks*, Science 296, 910–913 (2002).
- Gillis J., Pavlidis P., *"Guilt by association" is the exception rather than the rule in gene networks*, PLoS Computational Biology 8, e1002444 (2012).
