# Un candidato, due rappresentazioni dei dati, una sequenza di lavoro

3 ottobre 2026, Codex, sessione `01a1027a-0ae4-7c32-9001-e868a2b91698`.
Richiesta: scegliere un riferimento 2025, collegarlo alle conoscenze presenti, chiarire dati,
ibrido, training e destino dei piani. **Stato: analisi e proposta; nessun nuovo training o
invio, nessuna modifica al modello attivo.** Le misure nuove sono sui metadati e sulle
ricevute tecniche dei training già terminati. La pausa dei nuovi job resta in vigore.

| File | Contenuto |
|---|---|
| [audit.json](audit.json), [audit_inputs.py](audit_inputs.py) | Riconto riproducibile dei gruppi, KOLF e copertura dei training; hash degli input |
| [training_receipts.json](training_receipts.json), [inspect_training.py](inspect_training.py) | Ricevute tecniche lette da Kaggle; nessun peso del modello o dataset scaricato |
| [VERIFICHE.md](VERIFICHE.md) | Controlli della consegna |

## 1. Scelta: X come riferimento architetturale, transfer come fondamento

**Fonte primaria:** [resoconto Arc dei vincitori 2025](https://arcinstitute.org/news/virtual-cell-challenge-2025-wrap-up),
consultato il 3/10. X, secondo classificato di XLearning Lab, usa una rete fully connected,
controlli aggregati, descrittori proteici ESM2 e indicatori UMI per apprendere variazioni di
espressione. L'originale usa pseudobulk. Qui proponiamo un adattamento con supervisione
cellulare, coerente con il mandato corrente. Non una replica del vincitore: non abbiamo
verificato una ricetta completa con pesi, split e iperparametri originali.

**Interpretazione:** è il candidato più vicino al percorso già implementato, quindi permette
di isolare contributi nuovi senza ricostruire il progetto. Non deduciamo dal secondo posto
che la stessa ricetta vincerebbe nel 2026. Il cambiamento di contesto va misurato lasciando
intere linee fuori dal training. I controlli della nuova linea sono input, le sue risposte
perturbate sono riservate alla valutazione.

Schema concettuale del candidato:

> stato basale dai controlli + effetto trasferito da altri contesti + correzione appresa.

Nel codice v3 l'addizione avviene nei logit delle proporzioni, poi normalizzati: non si
sommano direttamente conteggi grezzi, log-fold change e UMI. Il transfer è un'aggregazione
pesata degli effetti osservati, non necessariamente una regressione lineare addestrata.
Il suo valore sta nell'informazione sperimentale che conserva; la rete deve provare di
correggerla meglio su un contesto escluso, non ricominciare da zero.

**Già implementato:** `beta(controlli) + gain * ancora + residuo`, con residuo limitato e
inizialmente nullo; descrittori GO/STRING/HGNC/GENCODE/DepMap. ESM2 non è tra i blocchi costruiti
da `target_descriptors.py`. Fonte: [protocollo v3](../../modelli/rete_ancorata_2026-10-03/PROTOCOLLO.md).

**Nuove prove proposte, una modifica per volta:**

1. Transfer da tutte le fonti aggregate ammesse dal fold, contro lo stesso transfer corretto
   dalla rete piccola. Stessi input disponibili, supporti e generatore.
2. Stessa rete e stesso campione, descrittori attuali contro attuali + ESM2 congelato.
   Copertura, mapping gene/proteina e provenienza vanno verificati prima dell'uso:
   [risorsa candidata già catalogata](../lezioni_vcc2025_2026-10-03/SORGENTI.md).
3. Conservare il confronto tra media dei controlli e insieme di cellule di controllo, già
   previsto nella v3. Una rete che legge un insieme non è automaticamente migliore.

La correzione riceve anche supporto dell'ancora, concordanza tra fonti e modalità sperimentale
quando verificati. Una fonte assente si distingue da un effetto nullo. La fiducia o il peso
della correzione si sceglie su contesti interni esclusi; non si sceglie per target guardando
la verità di valutazione. Un guadagno limitato non garantisce da solo l'assenza di regressioni.

**Punto da recuperare:** `anchors.py` ammette come fonti solo H1, HepG2, RPE1, K562, iPSC,
Jurkat, Neuron; esclude anche la tabella VIPerturb. A549 è nel training cellulare ma non in
questa lista. CD4T, HCT116 e HEK293T, utili nel riferimento di produzione, non vi entrano.
La definizione del riferimento t22/t25 nel [banco](../../modelli/risposta_contesto_2026-10-02/p1_splits.py)
nomina K562, CD4 e le due linee Orion. **Non è lo stesso identico insieme di fonti.**
Possiamo studiare un'ancora con questi aggregati già disponibili prima di avere tutte le
loro cellule. Occorre rigenerarla per fold escludendo la linea destinataria; ampliarla
significa un nuovo confronto, non cambiare il riferimento del pilot già congelato.

## 2. Quante linee: tre numeri con significati diversi

**Misurato:** unione dei gruppi nelle ricevute del pilot cellulare r3 = **8 gruppi biologici**:
A549, H1, HepG2, Jurkat, K562, RPE1, iPSC e neuroni derivati da iPSC. Ogni fold usa sette
gruppi per il training ed esclude l'ottavo per la valutazione. Il training ancorato riusa
questo corpus. Un gruppo può riunire più linee di donatori: non sono otto linee clonali.

**Catalogo proposto = 21 gruppi**, non 21 gruppi già pronti per il training. I 13 ulteriori sono
CD4T, HCT116, HEK293T, Hs27, Calu-3, THP-1, Melanoma_Frangieh2021, PrimaryT_Shifrut2018,
MCF7, HT29, HAP1, BxPC3, DLD-1. La [mappa](../../sorgenti/ingestione_completa_2026-10-03/orion/line_groups_expanded_v1.json)
è esplicitamente una proposta, con identità da verificare. Non è un censimento definitivo
di tutti i dati pubblici: altre risorse in ricognizione non vi compaiono.

**Prima espansione proposta: 8 → 11 gruppi**, aggiungendo CD4T, HCT116 e HEK293T alle cellule
quando i campioni hanno verifiche complete. I loro aggregati possono contribuire prima.
KOLF pan-genome aumenta bersagli e profondità del gruppo iPSC; VIPerturb aumenta la copertura
di K562: nessuno dei due aggiunge automaticamente un nuovo gruppo biologico.

Le 12 combinazioni CD4 di quattro donatori e tre stati non sono 12 nuovi tipi cellulari.
Si conservano come strati. Gli alias HEK293/HEK293T e i gruppi T correlati richiedono regole
conservative; per una prova severa di generalizzazione le famiglie correlate si escludono
insieme. Stimoli, tempi, assay, donatori e guide non vanno cancellati dai metadati.

## 3. Come ridurre il peso dei dati senza confondere media e popolazione

**Proposta:** mantenere tre livelli con manifest collegati, senza cancellare l'archivio completo.

| Livello | Cosa contiene | A cosa serve |
|---|---|---|
| Archivio verificato | Shard cellulari originali nel contratto del progetto, provenienza e hash | Ricostruire campioni, ampliare le prove, recuperare popolazioni rare |
| Riassunti delle cellule ammesse | Per studio/linea/donatore/stato/libreria/modalità/target: conteggio cellule, media di proporzioni, dispersione, frazione di zeri, controlli appaiati, supporto e guide | Transfer, affidabilità, confronto dei campioni, copertura dei target |
| Pacchetto di training | Campioni cellulari riproducibili di tutti i gruppi inclusi nello snapshot, controlli per libreria, maschere dei geni | Loss sulle cellule e apprendimento della correzione |

I riassunti si calcolano in streaming su CPU Colab, una volta per snapshot e split. Non si
media tutto CD4 ignorando donatore/stimolo, né si mescolano CRISPRi, attivazione e KO. Le
medie non ricostruiscono dispersione, covarianze o sottopopolazioni: il solo pseudobulk
non preserva tutta l'informazione. Manteniamo quindi una componente cellulare reale.

Per il campione, separare prima i fold e la verità riservata, poi campionare in modo
deterministico dentro gli strati con etichette disponibili. Conservare tutte le unità rare
ammesse, controlli della stessa libreria e guide/repliche distinte. I valori mancanti restano
mancanti. Il campionamento stratificato cambia le frequenze: salvarne le probabilità e
definire esplicitamente se la loss rappresenta la popolazione o un obiettivo bilanciato per
linea/studio. Non applicare due volte lo stesso riequilibrio.

I livelli 32/64/128 cellule per coppia contesto-target sono **punti per una curva di
saturazione, non una soglia sufficiente dimostrata**. Fissare un tetto anche per ogni guida,
libreria e donatore produce numeri maggiori. Con una popolazione ipotetica all'1%, un
campione casuale di 64 cellule ha circa il 53% di probabilità di non osservarla nemmeno una
volta. Nessun campione piccolo può promettere perdita nulla.

Per scegliere la taglia confrontare campioni annidati: errore delle medie/effetti contro i
riassunti completi, varianza e zeri, copertura delle guide/repliche e degli stati osservabili,
più le sei metriche sul banco cellulare a verità fissa. Le soglie vanno fissate prima dei
risultati del confronto; il campione non deve selezionare fenotipi convenienti per il punteggio.
Ampliare prima gli strati dove la perdita è misurata. Conservare tutti i target utilizzabili,
non soltanto i 300 della gara.

**Esempio misurato KOLF:** la verifica completa delle 19:44 CEST registra 2.659.209 cellule,
133 shard, **18,39 GB** nel contratto, con 2.512.462 cellule bersagliate e 146.747 controlli.
Il cap grossolano a 64 conserva 716.099 cellule bersagliate, più i controlli trattati a parte.
Non è la dimensione finale di un pacchetto stratificato; non dimostra qualità equivalente.
Fonte e hash sono in `audit.json`. Questo mostra perché i terabyte dell'archivio e i byte
letti da un training sono due quantità diverse.

Il mandato di archivio completo rimane. Alla ripresa, dare precedenza alle unità che rendono
utilizzabile una nuova linea e alle loro verifiche, poi ai duplicati di profondità. È una
priorità di esecuzione proposta, non una riduzione nascosta dell'archivio autorizzato.

## 4. Il training è già iniziato; la ripartenza richiede prima una correzione dei dati in ingresso

**Misurato via API e ricevute, 3/10 intorno alle 20:05 CEST:** H1 e HepG2 della rete ancorata
sono `COMPLETE`, uscita 0, verifica degli hash senza differenze e controllo di salute passato.
La ricerca dei kernel dell'account restituisce questi due training; il terzo RPE1 risulta
ancora non lanciato nel manifest. La quota letta verso le 19:55 era 13,06 ore GPU residue
su questo account: fotografia, non prenotazione né autorizzazione di lancio.

| Ricevuta | H1 esclusa | HepG2 esclusa |
|---|---:|---:|
| Epoche effettive | 0,714 | 1,535 |
| Cellule ammesse viste almeno una volta | 71,4% | 100% |
| Frazione di tempo in attesa dei batch registrata dal trainer | 81,4% | 83,9% |
| Quota della loss del gruppo Neuron | 0,717% | 14,208% |
| Bilanciamento entro ±0,02 da 1/7, regola già congelata | **Non passa** | Passa |

Nel training H1 la sorgente `tian2021_crispri` offre 26.218 cellule ammesse ma ne vengono
lette **zero**. Non è una bocciatura scientifica della rete: il training non soddisfa il
criterio tecnico preesistente. Non va promosso ignorando la guardia. HepG2 non è dichiarato
valido in tutto: qui non sono stati aperti punteggi, completezza della valutazione e altre
guardie. Nessun risultato ufficiale nuovo.

**Interpretazione da verificare:** lo streaming legge un buffer limitato di shard e il
riequilibrio avviene tramite pesi della loss. È bilanciato sull'epoca completa, ma può
essere molto sbilanciato se si interrompe prima. I pesi non recuperano cellule mai lette.
L'attesa dei batch include preparazione CPU e I/O: non attribuiamo l'intero 81–84% al disco
senza profilazione. La prenotazione dinamica del tempo di valutazione può interrompere
prima delle due epoche; non basta aumentare indiscriminatamente il numero di worker.

**Primo lavoro concreto alla ripresa:** preparare su Colab CPU un pacchetto cellulare
compatto con manifest completo, poi alternare le linee durante il training e controllare
la loro copertura anche nelle finestre intermedie. Conservare o correggere i pesi rispetto
alle nuove probabilità di campionamento. Una fixture deve verificare assenza di unità
dimenticate, esclusioni, controlli appaiati, distribuzione desiderata della loss e resume.
Profilare sul runtime Kaggle lettura/preparazione e compute separatamente prima del pilot.
Non è ancora implementato un nuovo loader o un pacchetto eseguibile in questa consegna.

Sequenza proposta, senza attendere tutte le 21 voci del catalogo:

1. Conservare i due training e registrare il difetto tecnico H1; non rilanciare alla cieca
   il terzo con la stessa esposizione potenzialmente incompleta.
2. Correggere il percorso dei batch e verificarlo con le otto linee attuali; non aggiungere
   contemporaneamente ESM2 e nuove fonti per poi attribuire loro ogni differenza.
3. Per il nuovo esperimento ricostruire ancore, centri e PCA senza target J nascosti, come
   richiesto dall'emendamento §9. La dipendenza indiretta rende J/T del vecchio pilot
   contaminati. C rimane interpretabile soltanto per le corse che passano le guardie tecniche.
4. Congelare il confronto transfer/ibrido e completare la fixture di generazione prevista
   dal protocollo. Training su Kaggle; costruzione aggregati, generazione e sei metriche
   su Colab CPU. Confrontare PDS, MSE, NMAE, FID, reach e Jaccard; una loss migliore non
   autorizza la promozione. La riserva H1 test resta chiusa.
5. A parità di campione valutare ESM2; separatamente passare a 11 gruppi cellulari quando
   disponibili. Le parti CD4/Orion finite non certificano una sorgente intera o tutti gli strati.

Non promettiamo un orario di conclusione senza misurare preparazione, I/O e copertura.
Non serve terminare l'archivio completo prima di questa sequenza.

## 5. Che cosa resta dei piani aperti

**Proposta di priorità all'interno di R-LEAD, non creazione di un altro programma.**

| Piano | Ruolo nella sequenza |
|---|---|
| R-LEAD P4 | Integra l'ipotesi ispirata a X nel ramo ancorato; prima validità del training, poi contributo di ancore complete ed ESM2 |
| R-LAB e R-DATI | Archivio completo e pacchetto leggero hanno manifest distinti; ripresa delle fonti che aggiungono contesti e campioni verificabili |
| R-REV | Mantiene controlli di leakage, scorer, generazione ed esecuzione a forma piena; non si chiude perché parte un training |
| R-COMP | Resta l'obiettivo comune, non un esperimento concorrente |
| R-LEAD P5 e S-INVII/P6 | Conferma dopo una prova positiva; preparazione del pacchetto finale procede anche se la rete perde |
| R-SWITCH, R-V2 | Alternative condizionate a un limite misurato; non si riattivano solo perché cambiamo nome al candidato |
| R-MODELLI | Resta chiuso secondo la decisione del proprietario; il transfer sopravvive come riferimento e componente del nuovo ramo |

Le bocciature precedenti restano prove: la miscela a posteriori di due predizioni non è lo
stesso esperimento di una rete addestrata sul residuo del transfer. Tuttavia questa differenza
non dimostra che il secondo funzioni. Non riapriamo v2 invariata e non archiviamo l'evidenza negativa.

La [consegna dell'ingestione, aggiornamento 19:55](../../sorgenti/ingestione_completa_2026-10-03/HANDOFF_CLAUDE2.md#aggiornamento-delle-1955-in-pausa-su-richiesta-del-proprietario-sessione-c7c07a)
riporta la richiesta del proprietario delle 19:51: «Aspetta, sto delineando un nuovo piano
con codex». La pausa è mantenuta. Questa analisi non spinge kernel, non riavvia code e non
riassegna il lavoro delle altre sessioni. La scheda R-LEAD contiene il collegamento alla
proposta e alla nuova evidenza tecnica; adozione e ripresa operativa restano distinguibili.
