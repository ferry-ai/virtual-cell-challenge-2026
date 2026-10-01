# R-LAB — piano del giorno: dati cellulari, qualità e rete biologica

- **Stato:** aperto; corpus e training r1–r3 eseguiti, t29 valutato con esito negativo.
  Il quarto training ha un protocollo tecnico, non un risultato registrato.
- **Aggiornato:** 1 ottobre 2026, dopo lo scoring t29 e il riordino serale, Europe/Rome.
- **Mandato:** richiesta del proprietario in chat: rendere evidente un nuovo piano per Claude, usare più dati possibile per generalizzare, preferire singole cellule al pseudobulk e progettare un'ingestione su risorse Colab/Kaggle con controlli su disomogeneità ed estremi.
- **Assegnazione:** redazione completata da Codex, chat `01a0f312-3075-7741-bb98-e15ab7c4c4b8`; destinatario operativo Claude, presa in carico da registrare con sessione, file e output secondo [PIANI §3](../PIANI.md#3-lavorare-in-una-cartella-condivisa). Nessun incarico altrui viene liberato o sostituito.
- **Riferimento operativo più recente:** Claude `07ebf08b`, ultimo esito alle 20:25 qui sotto;
  il proprietario conferma in chat al riordino serale che gli agenti sono fermi.
- **Prossimo passo vigente:** banco locale a sei membri richiesto dal ramo c del t29
  ([CP-0055](../../../../checkpoints/0055-t29-rete-cellulare-punteggio.md)), coordinato con le correzioni
  e i confronti di [R-LEAD](strategia-scientifica.md). Misurare la parte specifica del bersaglio
  e verificare l'esportazione delle reti disponibili prima di proporre un altro invio.
  Il quarto training resta una verifica tecnica: non include il banco a sei membri e non
  soddisfa da solo la condizione. La sua priorità va conciliata con A/B di R-LEAD alla ripresa.

## Registro degli avanzamenti del 30/09–1/10

Le note e i «prossimi passi» seguenti conservano la sequenza delle consegne; per riprendere
vale l'intestazione aggiornata sopra, insieme ai protocolli congelati di ogni esperimento.

- **Presa in carico (30/09, 19:08 CEST, Claude Code, sessione `a1ec75f0`),** su richiesta del
  proprietario in chat («Esegui questo piano»): P0 e P1, poi la prima consegna del §10. File di
  lavoro nuovi: `reports/sorgenti/corpus_cellulare_2026-09-30/` (D) e
  `reports/modelli/risposta_biologica_2026-09-30/` (M); dati derivati sotto
  `VCC2026_DATA_ROOT/processed/corpus_cellulare_2026-09-30/`. Misurato alla presa in carico: 1,7 GB
  liberi su C: e 0,75 GB di RAM libera su 7,8, quindi nessuna ingestione pesante in locale.
  Download e job in cloud partono solo dall'elenco approvato dal proprietario (§6).
- **Avanzamento (30/09 sera, Claude `a1ec75f0`):** P0 e P1 fatti; prima consegna del §10 in
  [corpus_cellulare](../../../../../reports/sorgenti/corpus_cellulare_2026-09-30/README.md):
  - inventario misurato delle 26 sorgenti: 7 hanno cellule in locale, 1 su Drive, 11 solo in
    remoto, con i byte;
  - contratto degli shard e pilota HepG2 di 1.000 cellule in parità;
  - prime misure QC per cellula;
  - [piano dei job](../../../../../reports/sorgenti/corpus_cellulare_2026-09-30/PIANO_JOB.md) J01–J12 e R01.

  Ruoli e riserva proposti in [risposta_biologica](../../../../../reports/modelli/risposta_biologica_2026-09-30/PROTOCOLLO.md):
  fra i dati sul disco nessun grande schermo CRISPRi cellulare è intatto, e la riserva primaria
  proposta è H1 della gara 2025. **Aspetta il proprietario:** destinazione degli shard, via a J01–J03
  e ai download, regola sugli account, riserva.
- **Ripresa (30/09, 19:56, Claude Code, sessione `ec2e5b07`):** la sessione `a1ec75f0` ha esaurito
  i token a metà di P2. Il proprietario ha passato la chat e riconfermato in chat le autorizzazioni:
  vedi [AUTORIZZAZIONI](../../../../../reports/sorgenti/corpus_cellulare_2026-09-30/AUTORIZZAZIONI.md).
  Ha scelto anche il ruolo di H1 2025: il test fa da riserva, train e validation vanno nel training
  ([registro r2](../../../../../reports/modelli/risposta_biologica_2026-09-30/holdout_registry_r2.json)).
- **Avanzamento (30/09, 20:50, Claude `ec2e5b07`):** P2 è implementato e provato in locale, non
  ancora eseguito su Colab; stato in [README §7](../../../../../reports/sorgenti/corpus_cellulare_2026-09-30/README.md#7-p2-i-job-j01j03-e-il-download-di-h1-3009-sera-sessione-ec2e5b07).
  - Adattatori, runner, download verificato e builder dei job.
  - Prova locale su ritagli dei file veri: tre schemi, parità esatte, ripresa con `--reuse`.
  - In coda sul Drive, con preflight locale passato: 086 J01 HepG2, 087 J03 Jurkat, 088 J02 HIPSCI,
    089 H1 2025 (parte dopo J02).
- **Svolta (30/09, 21:40–21:56):** su richiesta esplicita del proprietario (README del corpus §8) il
  lavoro è una **rete addestrata direttamente sulle singole cellule** con tutti i dataset utilizzabili;
  la rete sugli effetti pseudobulk non si estende. Colab fa la CPU (ingestione, due dispatcher: `runs/queue`
  e `runs/queue2`), Kaggle la GPU: solo `davidmaisterx` ha GPU (2× T4) e internet, misurato con un
  probe; `davideferrante11` e `davideferante` no, senza verifica del telefono.
- **Passaggio di consegne (30/09, 22:55, Claude `ec2e5b07`).** Stato misurato e dove leggerlo:
  - **Colab, coda 1:** J02 HIPSCI in corso (088); J06 K562 genome-wide da Drive in corso (096, pubblica
    su `davideferrante11`: dopo il suo `complete.json` serve un job di sola pubblicazione verso
    `davidmaisterx`, con `colab_job.py --publish-only ... --owner davidmaisterx --secrets rlab_secrets_davidmaisterx`).
    J01 HepG2 e J03 Jurkat GSE249595 finiti; pubblicati su `davideferrante11`.
  - **Colab, coda 2** (avviata 22:48): 098–099 ripubblicano J01 e J03 su `davidmaisterx`; 100 H1
    train+validation dal bucket Arc, 101 Jurkat di Nadig, 102 K562 essenziali e RPE1 di Replogle, tutti letti
    a intervalli di byte e pubblicati su `davidmaisterx`. Ricevute in `runs/rlab_setup_2026-09-30_r3/receipts/`.
  - **Codice** (committato): adattatori `h5rows` e `mtx10x`/`hipsci`, `rlab_job.py`, `publish_kaggle.py`,
    `colab_job.py` nel corpus; `cellnet.py`, `train_cellnet.py`, `target_descriptors.py` in
    [risposta_biologica](../../../../../reports/modelli/risposta_biologica_2026-09-30). La rete: supervisione sui
    conteggi grezzi (NB, maschere), miscela "risponde/sfugge" per cellula, contesto dai controlli, bersaglio
    da descrittori biologici (GO, STRING, HGNC, GENCODE, DepMap; 18.533 × 284, in
    `VCC2026_DATA_ROOT/processed/risposta_biologica_2026-09-30/descriptors_r1/`) con l'identità come braccio
    di confronto; split C/T/J, controllo di non-contaminazione, QC e copertura distinta. Provata solo in
    miniatura su CPU: **nessun training vero ancora eseguito**.
  - **Inventario remoto:** `inspect_remote.py` ha misurato 72 dei 77 h5ad elencati in `urls_r4.json`
    (scPerturb, H1, Southard, A549, KOLF, CD4) in `p1_r4/remote/`; manca la sintesi in catalogo.
- **Revisione di Codex (30/09, 23:00), accolta:** prima del training esteso servono controlli e maschere per
  studio e libreria, copertura completa, stimatore unico nella valutazione, QC di ammissione e classi C/T/J
  effettive, verificati su casi piccoli. Fatto: `cell_data.py` con `test_cell_data.py`, 13 casi a verità nota
  che passano. **Da fare:** portare `cell_data.py` dentro `train_cellnet.py` (oggi usa ancora serbatoi per
  contesto e campionamento con reinserimento), poi il training.
- **Passaggio di consegne aggiornato (30/09, 23:20, Claude `ec2e5b07`, a fine quota; sostituisce lo stato del
  blocco delle 22:55, che resta come storia).** Letto sulle code e su Kaggle alle 23:13:
  - **Colab coda 1** (`runs/queue`, dispatcher 1): in corso J02 HIPSCI (088, pubblica su `davideferrante11` a
    fine job) e J06 K562 genome-wide (096, idem). Quando esiste `…/j02_hipsci_r1/complete.json` o
    `…/j06_k562_gwps_r1/complete.json`, serve un job di sola pubblicazione verso `davidmaisterx` (l'unico account con
    GPU): `colab_job.py --job p05_… --number <libero> --queue queue --publish-only data/processed/corpus_cellulare_2026-09-30/<job>
    --publish ALL=<slug> --owner davidmaisterx --secrets rlab_secrets_davidmaisterx --snapshot <setup_r5> --commit <sha> --setup rlab_setup_2026-09-30_r5`
    (HIPSCI per schermo: `--publish hipsci_gw_fitness=rlab-hipsci-gwfit` ecc.).
  - **Colab coda 2** (`runs/queue2`, dispatcher 2): 103 Jurkat di Nadig in corso; 105 H1 train+validation (blocchi da
    5.000 cellule, dopo che il 100 ha esaurito la memoria); 106 K562 essenziali e RPE1 (lettore corretto per i redirect
    firmati di Figshare, **non ancora provato su Colab**: se fallisce di nuovo con 403, scaricare i due file sul runtime
    con `fetch.py` e leggerli in locale). Tutti pubblicano su `davidmaisterx`.
  - **Falliti e sostituiti:** 090 (archivio H1: controllo dello spazio sbagliato), 100 (H1: memoria), 101/102 (chiave
    `sha256` mancante), 104 (403 Figshare). Nessun dato perso; le ricevute stanno in `runs/rlab_setup_2026-09-30_r*/receipts/`.
  - **Kaggle `davidmaisterx`:** pronti `rlab-hepg2-nadig`, `rlab-jurkat-gse249595` (senza chiamate delle guide: non
    supervisionabile) e `rlab-cellnet-code` (versione con `cell_data.py`, commit 281e899). GPU: 2× T4, misurata;
    quota settimanale residua non misurata.
  - **Rete:** `cell_data.py` (regole dei dati) con 13 casi controllati che passano; `train_cellnet.py` le usa (pre-passata
    con QC di ammissione per studio che non toglie i fenotipi, duplicati, classi C/T/J effettive, epoche senza
    reinserimento con pesi per studio, controlli per libreria, stimatore unico, controllo di non-contaminazione);
    provata in miniatura: copertura 1.340/1.340, non-contaminazione passata. **Nessun training vero eseguito.**
- **Ripresa (30/09, 23:24 CEST, Claude Code, sessione `07ebf08b`),** su richiesta del proprietario in chat, dopo la
  fine della quota di `ec2e5b07`; autorizzazioni riconfermate in chat
  ([AUTORIZZAZIONI](../../../../../reports/sorgenti/corpus_cellulare_2026-09-30/AUTORIZZAZIONI.md)). Sottoattività: code e
  pubblicazioni, primo training tecnico su Kaggle, catalogo dalle misure remote, adattatore CSC e ondate successive.
  Stessi file di lavoro (D) e (M); ogni esecuzione nuova scrive in cartelle e numeri di coda nuovi. L'ispettore
  `inspect_remote.py` lanciato da `ec2e5b07` alle 21:42 era ancora vivo alle 23:24 (ultimo file CD4): i suoi
  output si committano com'erano, a suo nome.
- **Avanzamento (1/10, 01:00 CEST, Claude `07ebf08b`).** Misurato o implementato, con dove leggerlo:
  - *le quattro regole qui sotto*: scritte in `cell_data.py` con 30 casi controllati e 15 casi da capo a fondo
    (`test_cell_data.py`, `test_prepass.py`), rivedute su due note di Codex (identità per provenienza; nessuna soglia
    relativa ai controlli rifiuta da sola una forte perdita di RNA); il loro esito su dati reali è il pre-passo del
    primo training (sotto);
  - *training in due stadi*: `train_cellnet.py prepass` su CPU, `train` su GPU con processi di caricamento, checkpoint
    periodici, ripresa esatta nella sequenza dei dati (catena degli hash dei lotti), throughput e memoria misurati,
    fine pianificata con riserve per valutazione ed esportazione; `kaggle_train.py` per i kernel. Su Kaggle il ciclo
    r2 (CPU, pochi shard reali) ha ripreso con sequenza identica e parametri entro 7,2e-7 su 74,5;
  - *incidenti*: E-20260930-001 (cache del lettore HTTP, verificato in remoto dal job 108), -002 (firme S3 di
    Figshare da 10 secondi, job 114 in verifica), -003 (categorie AnnData vecchie lette come codici: gli shard di
    Replogle di J06 e J07 non hanno controlli; rilettura con i job 114 e 115, il dataset `rlab-k562-gwps` del 30/09
    non entra in nessun training);
  - *dati su `davidmaisterx`*: HepG2, Jurkat di Nadig, H1 train e validation (job 108), HIPSCI in tre dataset (job 111);
    catalogo del corpus in [catalogo_r1](../../../../../reports/sorgenti/corpus_cellulare_2026-09-30/catalogo_r1/CATALOGO.md);
  - *primo training reale*: protocollo e regola di lettura scritti prima del lancio in
    [cellnet_tecnico_2026-10-01](../../../../../reports/modelli/cellnet_tecnico_2026-10-01/PROTOCOLLO.md); autorizzazioni del
    proprietario dell'1/10, 00:29, in AUTORIZZAZIONI (tutto, compreso uno scoring).
- **Stato alle 02:25 del 1/10 (Claude `07ebf08b`), dove leggerlo:**
  - *primo training reale* in corso su Kaggle GPU dalle 02:05 (`rlab-cellnet-r1`: ciclo di ripresa su CUDA, poi bracci
    `desc` e `ident` per 100 minuti), sul pre-passo r3: 2.609.698 cellule, 1.066.336 di training ammesse, HepG2 tenuto
    fuori; lanci e protocollo in [cellnet_tecnico_2026-10-01](../../../../../reports/modelli/cellnet_tecnico_2026-10-01/README.md);
  - *pre-passo del secondo training* (`rlab-prepass-r4`, CPU) in corso dalle 01:58 sul corpus completo supervisionabile:
    il primo più K562 genome-wide, K562 essenziali e RPE1, riletti dai job 114 e 115 dopo E-20260930-003;
  - *seconda ondata d'ingestione* in coda su Colab (job 116-120: KOLF piccoli e forte, Southard RPE1 e Hs27 CRISPRa, A549
    KO, Tian e Norman), con l'adattatore CSC nuovo; catalogo aggiornato in
    [catalogo_r2](../../../../../reports/sorgenti/corpus_cellulare_2026-09-30/catalogo_r2/CATALOGO.md);
  - *scoring*: autorizzato (uno) ma non preparato stanotte. L'upload di un `.vcc` da circa 4 GB chiede una copia locale,
    e il disco ne ha 1,2; caricarlo da Colab o Kaggle chiederebbe di copiarvi la chiave `vcc`, non autorizzato in modo
    specifico. `export_effects.py` scrive gli effetti della rete nel formato dello stadio 100, provato in locale.
- **Prossimo passo (1/10 notte):** leggere `rlab-cellnet-r1` secondo il §4 del protocollo e salvarne gli esiti in
  `esito/`; poi lanciare il secondo training GPU sul pre-passo r4 entro la quota restante (circa 4 ore dopo il primo);
  pubblicare la seconda ondata quando i job finiscono.
- **Stato alle 03:45 del 1/10 (Claude `07ebf08b`; sostituisce il prossimo passo qui sopra, che resta come storia):**
  - *primo training letto* con la sua regola
    ([ESITO](../../../../../reports/modelli/cellnet_tecnico_2026-10-01/ESITO.md)):
    - passano la ripresa su CUDA, gli hash dei 183 shard e la copertura e la valutazione del braccio `desc`;
    - il braccio `ident` è stato ucciso per memoria, e la GPU ha aspettato i dati per l'87% del tempo;
    - incidente `E-20261001-001`. Quota GPU usata: circa 62 minuti;
  - *caricatore misurato e corretto*
    ([caricatore](../../../../../reports/modelli/cellnet_esteso_2026-10-01/caricatore/README.md), kernel CPU senza quota GPU):
    - la decompressione gzip costa 6-10 s per shard, e il vecchio passaggio per COO quasi la raddoppiava;
    - correzioni: `read_csr` diretto (stessa matrice), bracci in un solo processo sugli stessi lotti, valutazione con
      processi di caricamento. Commit `12e0040`, dataset `rlab-cellnet-code` aggiornato;
  - *Colab*: la coda 1 ha perso il runtime (nessun battito dopo le 02:29). Il suo lavoro è passato alla coda 2 come
    job 124-126, e il 123 è ritirato. Il proprietario, quando vuole, riavvia il notebook del dispatcher 1. Sulla coda 2
    girano 121 (K562 essenziali e RPE1) e 122 (K562 genome-wide), riletti con `gene_name` dopo `E-20260930-004`;
  - *seconda ondata*: A549 (`rlab-a549`) e Tian e Norman (`rlab-tian-norman`) sono finiti e pubblicati. KOLF piccoli
    (124, riusa gli shard di cromatina del 116), Southard (125) e KOLF forte (126) sono in coda;
  - *scoring*: ancora rimandato, per le ragioni delle 02:25 (disco e chiave `vcc`).
- **Prossimo passo:**
  1. quando 121 e 122 pubblicano, il pre-passo `rlab-prepass-r5` (CPU), poi il secondo training `rlab-cellnet-r2`
     secondo il [protocollo](../../../../../reports/modelli/cellnet_esteso_2026-10-01/PROTOCOLLO.md) e gli
     [scostamenti](../../../../../reports/modelli/cellnet_esteso_2026-10-01/SCOSTAMENTI.md) scritti prima;
  2. leggerlo con la regola del protocollo §4;
  3. un protocollo per un terzo training con la seconda ondata.
- **Stato alle 06:10 del 1/10 (Claude `07ebf08b`; sostituisce il prossimo passo qui sopra):**
  - *secondo training* `rlab-cellnet-r2` su Kaggle GPU dalle 05:57 (ciclo di ripresa, poi 150 minuti; fine verso le
    08:40), sul pre-passo r5: 5.157.575 cellule, 3.354.670 di training ammesse. Prima del lancio:
    - una prova del codice corretto su Kaggle CPU con shard reali (in
      [caricatore](../../../../../reports/modelli/cellnet_esteso_2026-10-01/caricatore/README.md));
    - la lettura riga per riga degli shard in valutazione (scostamento 7).
  - *incidente E-20260930-004* verificato in remoto: le tre chiavi di Replogle hanno controlli nel pre-passo r5;
  - *terzo training*: [protocollo](../../../../../reports/modelli/cellnet_completo_2026-10-01/PROTOCOLLO.md) scritto alle 03:59,
    prima del lancio del secondo. Il pre-passo `rlab-prepass-r6` gira su Kaggle CPU dalle 06:00, con la seconda ondata:
    A549, Tian e Norman, KOLF piccoli e forte. Southard resta fuori: il job 125 legge 850.225 + 447.301 cellule da
    Zenodo a circa uno shard ogni 9 minuti, e finirà a fine mattina;
  - *terza ondata* in coda su Colab (job 127-129): Frangieh, Sunshine, Papalexi arrayed, Shifrut, Datlinger, Dixit, Xu.
    Etichette provate in remoto prima della coda (`smoke_labels.py`, `smoke_w3/`);
  - *CD4* (Marson 2025): 33,6 milioni di cellule in 12 file da circa 140 GB. Per intero non si ingerisce: serve un
    disegno di campionamento (per donatore e stimolo, controlli interi e un tetto per guida), **da decidere col
    proprietario**.
- **Prossimo passo:**
  1. leggere `rlab-cellnet-r2` con la regola del suo protocollo;
  2. lanciare il terzo training sul pre-passo r6, con il budget del protocollo (quota restante meno 20 minuti, almeno
     60);
  3. pubblicare la terza ondata, poi Southard.
- **Stato alle 15:30 del 1/10 (Claude `07ebf08b`; sostituisce il prossimo passo qui sopra).** La sessione è rimasta
  ferma dalle 07:45 alle 12:46 circa, quasi certamente per la sospensione del portatile.
  - *Secondo training*: A passa per intero
    ([ESITO](../../../../../reports/modelli/cellnet_esteso_2026-10-01/ESITO.md)). `desc` ha guadagni positivi su C, T e J e
    batte `identity` su J. Su C non batte il trasferimento (coseno 0,266 contro 0,390). Ogni braccio riceve 1.583
    cellule/s, la GPU aspetta ancora i dati per il 58% del tempo.
  - *Terzo training*: lanciato alle 12:49 sul pre-passo r7. r6 è scartato, perché Tian 2019 di scPerturb non è
    filtrato ([SCOSTAMENTI](../../../../../reports/modelli/cellnet_completo_2026-10-01/SCOSTAMENTI.md)). A passa per intero
    ([ESITO](../../../../../reports/modelli/cellnet_completo_2026-10-01/ESITO.md)). `desc` migliora su HepG2 (C 0,303, quota
    J 0,72). Il braccio `ident` è collassato, con `pi` a zero dopo il passo 6.200: è un difetto della miscela da
    correggere prima di un nuovo training.
  - *Quota GPU*: circa 320 minuti usati dei 360 dichiarati.
  - *Invio t29*, autorizzato dal proprietario (00:29, poi «invia appena puoi» alle 15:05 circa):
    - è la rete r2 `desc` con il generatore del t22, registrata alle 12:06 UTC prima dell'esportazione
      ([previsione](../../../../../reports/invii/prediction_t29_2026-10-01/prediction.json), banda −0,02…+0,10);
    - esportazione, stadio 45 e stadio 48 sono passati in locale ([trial_2026-10-01](../../../../../reports/invii/trial_2026-10-01));
    - l'upload è partito alle 13:28 UTC come processo separato, e il portatile resta sveglio fino alle 18:09 UTC.
  - *Disco*: con l'ok del proprietario sono andati nel Cestino generazione e pacchetto di t23 e t25 e il pacchetto
    del t26, tutti con i manifest in `reports/invii`. Il proprietario ha svuotato il Cestino. La somma KOLF
    (`interim/kolf_sums/sums.npz`) è compressa in NTFS da 6,4 a 2,3 GB, senza perdita.
  - *Terza ondata* finita e pubblicata (`rlab-scp-ko`, `rlab-scp-tcells`, `rlab-scp-k562-hek`: 617.524 cellule,
    parità ok). Southard (job 125) è ancora in lettura da Zenodo.
- **Prossimo passo:**
  1. a punteggio arrivato, la lista di PROCEDURE §2 punto 7: `comparison.json`, la riga in `reports/invii/README.md`,
     un checkpoint, eventualmente PROGETTO §0;
  2. correggere il collasso di `pi` (un pavimento o una penalità) e provarlo su CPU;
  3. un training con la terza ondata e Southard quando la quota GPU si rinnova;
  4. **decisioni del proprietario:** il campione di CD4 (33,6 milioni di cellule, circa 1,7 TB).
- **Aggiunte delle 16:50 (Claude `07ebf08b`):**
  - *Correzione di `pi`* in codice e test (commit `39f451d`): `--pi-floor`, con 0 che lascia il modello di prima. Il
    dataset `rlab-cellnet-code` è aggiornato. Il quarto training ha il suo
    [protocollo](../../../../../reports/modelli/cellnet_terza_ondata_2026-10-01/PROTOCOLLO.md), scritto alle 16:02: terza
    ondata, `--pi-floor 0.05`. Parte quando si rinnova la quota GPU.
  - *Catalogo* [r4](../../../../../reports/sorgenti/corpus_cellulare_2026-09-30/catalogo_r4/CATALOGO.md).
  - *Incidente E-20261001-001* verificato in remoto (r003). La GPU aspetta ancora i dati per più di metà del tempo:
    la prossima leva sono shard senza gzip o una lettura con più core.
  - *Upload del t29*: entry `K6Q36uGCaEwQ1wRLmBLp`. Il Wi-Fi di casa va fra 0,2 e 1 MB/s; alle 16:45 metà era
    inviata. Lettore del punteggio pronto, scritto prima: `reports/invii/trial_2026-10-01/read_t29_score.py`.
  - *Proposta per CD4, da decidere col proprietario.* I 12 file sono 4 donatori per 3 condizioni (Rest, 8 h e 48 h di
    stimolo), da 2,5 a 3,1 milioni di cellule ciascuno: circa 76 mila NTC e 1,75 milioni con una sola guida per file.
    - **Proposta di partenza:** un donatore e le tre condizioni, con tutti gli NTC e al più 10 cellule per guida
      (circa 23 mila guide). Sono circa 0,9 milioni di cellule e 10 GB di shard, letti da S3 in poche ore.
    - **Versione intera:** tutti i donatori con al più 25 cellule per guida, circa 7,8 milioni di cellule e 80 GB.
      Va prima verificato il limite di spazio dei dataset privati di Kaggle.
    - `var` ha gli ID Ensembl nell'indice e i simboli in `gene_name` (lezione di E-20260930-004).
- **Stato alle 20:25 del 1/10 (Claude `07ebf08b`).**
  - **t29 valutato: −0,029625**, rango 893, sotto la banda registrata: ramo c della regola
    ([CP-0055](../../../../checkpoints/0055-t29-rete-cellulare-punteggio.md),
    [confronto](../../../../../reports/invii/prediction_t29_2026-10-01/comparison.json)).
  - Il PDS grezzo vale 0,50 contro 0,79 del t22: la rete prevede soprattutto una risposta comune e distingue poco i
    bersagli. La fedeltà della direzione è pari alla ricetta.
  - Il t28 resta il massimo osservato e la ricetta del t22 il riferimento.
  - La sessione è rimasta ferma anche dalle 17:28 alle 20:21 circa: il punteggio è stato letto solo alle 20:21.
- **Prossimo passo (R-LAB):**
  1. nessun nuovo invio della rete finché un banco locale a sei membri sui contesti pubblici non la mostra almeno al
     livello del trasferimento (regola del t29);
  2. misurare in locale la parte specifica del bersaglio, cioè il PDS dei contesti tenuti fuori, sul secondo e sul
     terzo training;
  3. provare la rete come correzione della ricetta invece che al suo posto;
  4. il quarto training ([protocollo](../../../../../reports/modelli/cellnet_terza_ondata_2026-10-01/PROTOCOLLO.md)) quando si
     rinnova la quota GPU;
  5. decisioni del proprietario: il campione di CD4.
- **Aperti prima del training esteso (proprietario in chat, 30/09, prima delle 23:39):** quattro punti della
  revisione di Codex che i 13 casi di `test_cell_data.py` non coprono. Restano aperti finché ognuno non ha una regola
  scritta in `cell_data.py`, casi controllati che la provano e il suo esito nel pre-passo di un training vero:
  1. **duplicati e collisioni:** la stessa cellula in due shard o ripubblicata da un altro archivio conta una volta;
     due cellule diverse con la stessa chiave restano due; più feature native sullo stesso gene non si sommano in
     silenzio; etichette diverse che finiscono sullo stesso simbolo sono riportate;
  2. **perturbazioni combinate:** un'etichetta con più geni bersaglio non diventa il suo primo gene; ha una classe
     esplicita, e un bersaglio nascosto dentro una combinata non entra nel training;
  3. **conservazione dei fenotipi nel QC:** un knockdown che abbassa i conteggi o alza la frazione mitocondriale non
     viene tolto in modo selettivo; il rifiuto per perturbazione confrontato con quello dei controlli guida la regola;
  4. **maschere dei controlli:** ogni cellula e ogni controllo usano la maschera dei geni del proprio shard, mai
     l'unione della chiave; lo stimatore confronta perturbate e controlli sui geni misurati da entrambi.
- **Prossimo passo:** (0) ricontrollare le code (`runs/jobs/dispatcher*.log`) e i dataset (`kaggle datasets list --mine` con
  `KAGGLE_CONFIG_DIR=~/.kaggle`); (1) quando su `davidmaisterx` ci sono almeno HepG2, Jurkat di Nadig, K562 essenziali,
  RPE1 e H1, un kernel Kaggle GPU con `train_cellnet.py` (dataset di codice con `cellnet.py`,
  `train_cellnet.py`, `gene_names.csv`, descrittori), contesto tenuto fuori HepG2, bracci `descriptors` e
  `identity`: è la **verifica tecnica**, non un risultato; (2) catalogo completo dalle misure remote,
  con per ogni dataset stato, modalità, cellule, adattatore e motivo di esclusione; (3) adattatore CSC per
  i file scPerturb ordinati per gene; (4) KOLF, CD4, Orion, Southard, A549 e Mixscale/VIPerturb (serve R)
  a ondate; HIPSCI pubblicato per schermo quando J02 finisce.
- **Dipendenze:** [GENERALIZZAZIONE](../../../../GENERALIZZAZIONE.md), [R-COMP](modello-competitivo.md), [ERRORI](../../../../ERRORI.md), [PROCEDURE §3](../PROCEDURE.md#3-job-su-colab-e-kaggle). R-DATI e R-SWITCH contribuiscono ai blocchi qui definiti.
- **Ambito:** nuova priorità operativa dentro R-COMP. La ricetta iPSC resta un confronto; non è il prerequisito della rete. Nessuna scadenza artificiale o arresto a fine giornata: l'ordine sotto indica dipendenze, non durata promessa.

## 1. Indicazione al prossimo Claude

**Costruire un corpus di singole cellule conservando la massima diversità utilizzabile di studi, contesti, target, stati e modalità.** Il nucleo HIPSCI/CD4/Orion serve a verificare i contrasti appaiati, non delimita il corpus finale. Nessuna soglia di overlap con i 300 bersagli per ammettere una sorgente. Un dataset assente dal training deve avere un motivo e un passo di integrazione espliciti.

Non ridurre irreversibilmente le cellule a medie per rendere più semplice la rete. Streaming, lettura a blocchi e shard sparsi **non sono pseudobulk**: preservano identità e conteggi di ogni cellula. Mini-batch e aggregazioni temporanee nella loss sono consentiti; un pseudobulk resta una vista ausiliaria per controlli, confronti e baseline, non il sostituto unico del corpus.

Usare anche sorgenti che offrono soltanto pseudobulk, bulk o DE: hanno una loss e una maschera proprie, non cellule sintetiche spacciate per osservazioni. Acquisire le cellule originarie dove esistono e l'accesso è verificato; se non esistono pubblicamente, documentarlo. Conservare raw, viste derivate e provenienza fuori dalla repo, senza sovrascrivere i dati precedenti.

**Più dati è un obiettivo di copertura, non la promessa che ogni riga aiuti.** Non eliminare sorgenti perché una prima miscela peggiora: verificare prima unità, dominio, qualità, bilanciamento e compito ausiliario. Distinguere archivio acquisito, corpus ammissibile per fold e dati realmente visitati dall'ottimizzatore. Gli outcome riservati non entrano nel training per soddisfare la copertura.

## 2. Da quali evidenze partire

Questa scheda è una **proposta operativa**. Le misure restano nei report:

- [Copertura del training](../../../../../reports/analisi/lead_scientist_2026-09-29/TRAINING_COPERTURA.md): sorgenti acquisite e usate sono diverse; r2 ha etichette aggregate e non include i 19 universi HIPSCI per linea.
- [Audit biologico](../../../../../reports/analisi/lead_scientist_2026-09-29/neural/AUDIT_BIOLOGICO.md): prior del bersaglio poveri, supporto STRING diseguale, efficacia non riducibile a un divisore universale.
- [Audit dati](../../../../../reports/analisi/lead_scientist_2026-09-29/AUDIT_DATI.md) e [indice sorgenti](../../reports/sorgenti/README.md): CD4 e VIPerturb sono Flex; denominatori e supporti genici differiscono; stimatori vecchi hanno artefatti noti. La normalizzazione basale sull'asse comune non è ancora una soluzione misurata.
- [Audit generatore](../../../../../reports/analisi/lead_scientist_2026-09-29/AUDIT_GENERATORE.md): bulk e media per cellula differiscono quando profondità e stato sono correlati.
- [Replica neurale](../../../../../reports/analisi/lead_scientist_2026-09-29/RISULTATI_NEURALE_SEED1.md), [covariazione](../../../../../reports/modelli/covariazione_2026-09-28/RISULTATI.md) e [programmi](../../../../../reports/trasferimento/programmi_2026-09-26/RISULTATI.md): limiti delle formulazioni provate, non prova che tutta la biologia o tutte le reti siano inutili.
- [Proposte biologiche precedenti](../../../../../reports/analisi/biologia_architetture_2026-09-25/PROPOSTE.md): programmi, relazioni e quota/intensità erano già ipotesi. Qui si specificano dati cellulari, contratti, confronti e percorso realizzativo.

**Risposta sulla qualità attuale:** esistono correzioni locali importanti, ma non c'è evidenza di una certificazione uniforme di QC e armonizzazione dell'intero corpus. Questa scheda non dichiara i dati già puliti né tutti contaminati; P1–P3 devono misurare lo stato per sorgente.

## 3. Tutti i dati hanno un posto nel piano

Inventario iniziale da riconciliare con file e manifest, non lista di download già autorizzati. Una presenza remota storica va ricontrollata; i conteggi originali non si ricavano dalle somme.

| Sorgente | Punto di partenza attestato | Percorso cellulare e ruolo richiesto |
|---|---|---|
| Replogle K562 GWPS, essential, RPE1 | Universi r2, controlli e archivi/estrazioni documentati | Recuperare ubicazione e integrità dei raw; conservare tutte le perturbazioni, guide e repliche. Supervisione CRISPRi e confronto fra contesti |
| VIPerturb K562 | Somme e universo, controlli e confronti fra metà | Verificare recuperabilità del raw cellulare; ponte tecnico K562 Flex/3', senza attribuire ogni differenza alla chimica |
| CD4 Rest/Stim8hr/Stim48hr | Grande H5AD pseudobulk locale, pannello e metadati | Il file pseudobulk non conta come raw cellulare: verificare accesso alle cellule complete. Conservare donatore, guida, condizione e tempo; usare intanto gli aggregati con il loro contratto |
| Orion HCT116/HEK293T | Universi ottenuti in streaming e cellule del pannello | Ingestione cellulare dell'universo completo se accessibile; due linee dello stesso studio, con controlli e lotti distinti |
| KOLF2.1J | Somme di milioni di cellule, universo completo; originale remoto documentato | Leggere a blocchi mantenendo righe cellulari; non ricominciare da un archivio già materializzato senza verificarlo. PC10 non è la correzione di default |
| HIPSCI genome-wide fitness/non-fitness | Raw e derivati `_ua1`; controlli NTC scarsi in alcuni disegni | Tenere separati NTC e unassigned, versioni e librerie; sensibilità alla contaminazione dei controlli. Non contare raw e LFC come studi indipendenti |
| HIPSCI mirato, 19 linee | RNA locale, guide/LFC e 19 universi materializzati | Priorità d'integrazione, non unico dataset: singole cellule, linea/donatore/clone, guide, controlli, qualità del knockdown; linee deboli stratificate, non scartate in silenzio |
| A549 KO e Southard Hs27 CRISPRa | Somme, universi e controlli | Recuperare raw e usare modalità esplicite con teste/loss separate; nessuna equivalenza automatica KO = CRISPRi forte |
| Jurkat GSE249595 | RNA, guide e hashing locali | Adattatore multi-guida/alta MOI; conservare combinazioni intenzionali, distinguere doppietti da multiplex previsto. Testare l'assegnazione prima della supervisione |
| Mixscale | DE locali su più linee/stimoli | Verificare e acquisire conteggi, controlli, guide e repliche se accessibili. Nel frattempo loss DE mascherata; disegno non interamente incrociato, nessuna imputazione di coppie assenti |
| DLD-1 | Low1/Low2 LFC e SE parziali, pannello di risposte mirato | Verificare promotori/target/unità e raw eventualmente disponibili; loss su geni misurati, non esclusione per scarso overlap |
| HepG2 Nadig | Cellule locali e benchmark storici | Registro degli outcome già letti; ruolo train/development/test deciso prima, non riutilizzare la stessa verità come conferma intatta |
| Tahoe DMSO e farmaci | Corpus DMSO locale; estrazioni e bracci farmacologici documentati anche su remoto | Non fermarsi al singolo parquet in `external`. Recuperare shard cellulari selezionati e ampliare la copertura; mantenere piastra/dose/tempo/linea, controlli appaiati, testa farmacologica distinta |
| DepMap 24Q4 | Espressione, CNV e corpus basale locali | Bulk e covariate come supervisione ausiliaria; CNV non disponibile al test non diventa input obbligatorio. `CRISPRGeneEffect` va verificato/acquisito, non dichiarato già locale |
| Controlli gara e annotazioni | Controlli cellulari; GO/GOA/HGNC/STRING/GENCODE locali | Encoder di stato e funzione; nessun outcome di gara. Verificare mapping e copertura delle annotazioni prima del training |
| H1 VCC2025, microglia, Jost, PerturbFate, altri cataloghi | Candidati con disponibilità diseguale; i CSV H1 locali non sono una matrice RNA | Riconciliare ogni accessione citata. Acquisizione motivata da nuova diversità o identificabilità di dose/risposta; file, accesso e licenza da verificare prima. Non limitarsi ai target del pannello |
| scBaseCount e altri atlanti basali | Accesso/ingestione non dimostrati nel corpus corrente | Espansione possibile dell'encoder, con provenienza e campionamento per studio; non etichette perturbative sostitutive |

Per Tahoe partire anche da [corpus basale](../../../../../reports/sorgenti/corpus_basale_2026-09-28/SORGENTI.md), [estrazione DMSO](../../../../../reports/sorgenti/tahoe_dmso_2026-09-28/RISULTATI.md) e [bracci](../../../../../reports/modelli/tahoe_bracci_2026-09-28/RISULTATI.md): sono complementari all'inventario `external`.

## 4. Contratto del corpus: cellula prima, viste dopo

**Proposta di formato:** shard AnnData H5AD sparsi indipendenti, indice tabellare leggero; lettura lazy senza concatenare l'intero corpus in RAM. Ogni shard mantiene asse nativo completo e mapping all'asse canonico. Cambiare formato solo dopo una misura di I/O, senza perdere semantica.

1. **Raw immutabile:** conteggi originali con tipo numerico corretto, asse/feature originali, release/checksum. Conteggi corretti ambientali o trasformazioni stanno in layer/versioni separati; non diventano il raw.
2. **Identità:** chiave stabile studio × campione/libreria × barcode originale; checksum e appartenenza dei duplicati. Stessi barcode in librerie diverse non sono la stessa cellula. Il raw ripubblicato in due archivi conta una sola volta.
3. **Metadati:** target e insieme di guide, confidenza assegnazione, modalità, donor/clone, batch/plate, chimica, stimolo/tempo/dose, controllo, covariate disponibili al test. I mancanti hanno valore e maschera espliciti; non inventare donor o repliche.
4. **Feature:** Ensembl/versione, simbolo e alias, tipo feature/probe, mapping ambiguo. Le collisioni promotore→gene richiedono una regola documentata, non somma silenziosa. Zero osservato e gene non misurato restano distinti.
5. **Profondità:** totale prima del filtro dei geni, totale sull'asse nativo e sull'asse ufficiale quando ricostruibili, massa fuori asse. Se il file pubblicato non permette il totale originale, dichiararlo: non ricostruirlo arbitrariamente.
6. **Viste:** counts per decoder, normalizzazioni e ranghi per encoder, attività/programmi, aggregati per parità. Denominatore, pseudocount e base del log sono obbligatori; niente doppia normalizzazione di input già logaritmici.
7. **Ammissione:** ruolo e split, versione QC, ragioni dei flag/esclusioni, disponibilità delle etichette. Le celle respinte rimangono nel raw; la quarantena non cancella il dataset.
8. **Parità:** somme dei conteggi prima/dopo sharding, numero di cellule/guide/target, mapping e checksum; ricostruzione del pseudobulk su campioni confrontabile con il riferimento, con ogni differenza di stimatore spiegata.

Le pseudorepliche ottenute partizionando cellule non aumentano il numero di donatori o studi. Un campionamento per mini-batch non giustifica dichiarare usato l'intero archivio: il fit produce copertura delle cellule e gruppi effettivamente visitati.

## 5. QC: correggere artefatti senza cancellare biologia

Congelare criteri e trasformazioni su training/controlli, per assay e libreria. Sui test applicare regole fissate; qualsiasi adattamento sui soli controlli del nuovo contesto è una modalità transduttiva da dichiarare. Nessuna selezione secondo il miglioramento dello score o la forza della risposta del test.

| Rischio | Controllo e azione | Salvaguardia biologica |
|---|---|---|
| File/scala errati | Integrità, shape, CSR, valori non finiti/negativi nei raw counts, unità e base log, campione confrontato con fonte | File non interi possono essere conteggi corretti: classificarli, non arrotondarli come raw |
| Cellule vuote/degradate, profondità estrema | Distribuzioni di UMI, geni rilevati, complessità, frazioni mitocondriali dove misurabili; soglie robuste per gruppo e campioni QC | Niente soglia universale 3'/Flex/pannelli mirati; geni mitocondriali non saggiati non valgono 0% biologico |
| Doppietti, ambient RNA, guide spurie | Flag e probabilità usando input richiesti dai metodi; verifica hashing/guide e multiplet previsti | Senza empty droplets/raw necessari non dichiarare decontaminazione validata; alta MOI intenzionale non equivale a doppietto |
| Outlier e alte ampiezze | Revisione degli estremi per guida/replica/stato; loss robusta e pesi d'incertezza; trasformazioni apprese solo nel train | Non winsorizzare irreversibilmente raw o LFC; stress, ciclo, aneuploidia, morte e risposte rare possono essere vere |
| Knockdown debole o assegnazione incerta | Concordanza fra guide/repliche e controlli; etichette di qualità, modello di efficacia e sensitivity analysis | Non selezionare solo i knockdown forti: cambierebbe la popolazione obiettivo. Efficacia del test resta sconosciuta |
| Controlli contaminati | NTC, unassigned, DMSO, veicolo, pool separati; controlli della stessa piastra/tempo; falsi positivi NTC-vs-NTC | Non assorbire una perturbazione non assegnata nel controllo senza etichetta e analisi di sensibilità |
| Gene space e composizione | Maschera dell'assay, library size dichiarata, analisi del supporto comune e di quello completo | Nessuna intersezione globale che scarti permanentemente geni; nessuna imputazione a zero dei non misurati |
| Batch/studio | Confronti entro studio e controlli appaiati, ponti della stessa linea tra saggi; decoder tecnico e covariate | Non forzare tutti gli studi a sovrapporsi: batch e biologia possono essere confusi e non identificabili |
| Normalizzazioni che distorcono | Confronto raw/trasformato: riproducibilità guide, nulli, segni e ampiezze, stati rari, bulk e media per cellula | Integrazione latente candidata per l'encoder; conteggi corretti d'integrazione non diventano truth del decoder |

**Cosa deve contenere `QC_REPORT.md`:** tabella per sorgente dei passaggi e conteggi prima/dopo; distribuzioni degli estremi; perdite per target/contesto/stato/guida; non-applicabilità dei test; parità degli assi; controlli negativi e riproducibilità; anomalie aperte e decisione per gruppo. Ogni esclusione ha una ragione tecnica verificabile. Testare se i filtri eliminano selettivamente un fenotipo perturbativo.

**Batch alignment:** confrontare prima nessuna correzione, normalizzazione esplicita, aggiustamento tecnico moderato e decoder con covariate. Una maggiore mescolanza nell'embedding non decide: misurare insieme rimozione del segnale tecnico dove identificabile e conservazione dei contrasti biologici. Un classificatore di studio è una diagnostica, non l'obiettivo da annullare a ogni costo. Non applicare PC10/Harmony/scVI indiscriminatamente; validare fitting per fold, inversione/unità e conservazione di perturbazioni rare. Non regredire automaticamente ciclo/stress.

## 6. Ingestione da laboratorio guidata da Claude

Claude prepara e revisiona un **piano di job indipendenti**, per studio/libreria/shard, con un solo registro autorevole. Nessuna scrittura concorrente sullo stesso H5AD o manifest finale. La disponibilità di diversi account non è assunta come moltiplicatore automatico di quota. Rimane possibile l'utilizzo di altri account colab e kaggle (i token kaggle sono disponibili in cartella .kaggle e .kaggle-codex indistinamente, anche se non sei codex puoi usare il token)

**Vincoli del servizio verificati il 30/09:** le [FAQ Colab](https://research.google.com/colaboratory/faq.html) vietano l'uso di account multipli per aggirare restrizioni di accesso/risorse e, sui runtime gratuiti senza saldo positivo, i worker di calcolo distribuito. Non basare il progetto su quella modalità. Per risorse compatibili con il piano d'uso si possono predisporre notebook autonomi o calcolo dedicato; per Kaggle verificare [termini](https://www.kaggle.com/terms), account, regole della competizione e disponibilità effettiva prima dei lanci. Non assumere autorizzata una politica multi-account non verificata.

Il messaggio del proprietario dispone la **preparazione di questo piano** e prospetta risorse Colab/Kaggle; non è la ricevuta di un download/job già lanciato. L'esecutore riusa le autorizzazioni della propria sessione quando coprono i job. Per quelle mancanti prepara prima elenco concreto di file/byte/accesso, storage e job da approvare, secondo CLAUDE; nessuna domanda ulteriore è necessaria per scrivere il piano.

Flusso proposto, da implementare sopra il preflight esistente in [ERRORI](../../../../ERRORI.md):

1. **Inventario risorse:** disponibilità RAM/CPU/GPU, storage persistente, rete, titolare e accessi; alias pubblicabili, credenziali e identità sensibili fuori repo. Misurare spazio libero e I/O: non assumere che il portatile ospiti tutto.
2. **Pianificazione deterministica:** `job_id`, release sorgente, shard/range/cell-ID attesi, hash snapshot/config/schema, dipendenze, output nuovo e risorse. Il coordinatore assegna ogni shard una sola volta; Drive non è un lock distribuito.
3. **Prima unità per schema:** estrazione cellulare rappresentativa, roundtrip e parità raw, QC e metadata. Il pilot valida l'adattatore, non restringe in modo permanente il training.
4. **Ingestione CPU/I/O:** lettura sequenziale o range verificati, conversione sparsa, QC, checkpoint di shard. GPU solo per fasi che la usano. Non densificare l'intero h5ad né scaricare l'originale enorme se la lettura a range conserva le cellule richieste.
5. **Integrità remota:** release/ETag stabili durante i range; checksum sorgente dove disponibile, hash dei blocchi e di ogni output. Se non è stato ricalcolato il checksum completo dell'originale, registrare quel limite: non attestarlo implicitamente.
6. **Pubblicazione:** scrivere tentativi in percorsi nuovi, validare schema/hash/conteggi, poi ricevuta di completamento e inserimento nell'indice. Un `.done` o rc0 da solo non significa dati validi. Su object store usare manifest verificati, non presumere rename atomico.
7. **Ripresa e merge:** dopo un'interruzione riusare soltanto shard completi verificati; nuovo attempt per gli altri. Merge deterministico con rifiuto di duplicati e buchi, senza copiare tutte le matrici in RAM. Registro del job riconciliato da un solo coordinatore.
8. **Consegna locale:** riportare manifest, indici e report piccoli; dataset pesanti in storage persistente sotto layout documentato. Nessuna dipendenza esclusiva dal filesystem temporaneo di Colab/Kaggle.

La regia dei job è distinta dal training distribuito sincrono. Non servono gradienti fra notebook instabili per ingestire in parallelo. Non riattivare l'orchestratore ritirato della repo; nessun servizio o monitor viene creato da questa scheda.

## 7. Rete e ipotesi da implementare

**Filone A — suscettibilità funzionale.** Predire come funzione del target e attività/stati dei controlli cambiano la risposta. GO/HGNC/STRING locali sono il punto di partenza; reguloni TF, complessi e pathway curati sono integrazioni da verificare. Il nucleo appaiato testa l'ipotesi, l'intero corpus ammissibile fornisce supervisione.

**Filone B — intensità e popolazione.** Modellare stato, efficacia incerta, quota di rispondenti, dispersione e profondità. Una risposta media uguale non implica la stessa distribuzione. Con soli aggregati non identificare quota/intensità; usare cellule e guide indipendenti. Nessuna corrispondenza uno-a-uno inventata tra una cellula NTC e una perturbata.

| Blocco | Contratto proposto | Ablazione richiesta |
|---|---|---|
| `TargetEncoder` | Funzione/relazioni/coordinate; mancanza delle annotazioni esplicita; generalizzazione senza embedding libero obbligatorio del target | Sette vecchi prior; GO/relazioni permutati conservando grado/supporto; MLP sugli stessi input |
| `StateEncoder` | Insiemi di controlli, attività e composizione degli stati, profondità e maschere | Media basale; cieco; contesto scambiato; programmi senza informazione funzionale |
| `ResponseInteraction` | Target × attività; iniziare con bilineare/ridge e confronto neurale. Loss sui contrasti appaiati e sul corpus completo | Nessuna interazione; stesso modello con più dati; stessi dati con più capacità |
| `SourceMemory` | Effetti sorgente ammessi e affidabilità; ramo opzionale, accessi esclusi in T/J | Memoria spenta; transfer con stessi input e maschere, senza vantaggi illeciti |
| `EfficacyHead` | Predire/marginalizzare efficacia da informazioni disponibili in inferenza; modalità e incertezza esplicite | Efficacia latente vs modello senza efficacia; niente oracle knockdown del test |
| `ResponseDecoder` | Programmi + residuo genico completo + cis separato; può indurre programmi poco attivi al basale | Nessun residuo; nessun cis; programmi random. Non ripetere la sola proiezione che ha perso |
| `ObservationHead` | Conteggi e distribuzioni condizionate da stato/assay/library size; readout coerenti bulk e DE | Stessa media con emissione uniforme, dispersione o miscela; generatore tenuto fisso quando si isola il predittore |

Loss: conteggi con modello di osservazione adeguato, contrasti appaiati, discriminazione dei target, risposta media e distribuzionale. Aggregati e LFC degli autori hanno operatori/loss mascherati propri; SE solo quando disponibili o stimati da repliche, non inventati. CRISPRi, KO, CRISPRa e farmaci conservano modalità/tempo/dose. Stessa evidenza in due derivati non viene pesata due volte.

Campionamento gerarchico studio → donatore/contesto → target/guida → cellule, con copertura monitorata. Milioni di cellule di una linea non devono cancellare quelle di uno stato raro. Distinguere bilanciamento da cambio dell'estimando, e registrare pesi. Curriculum ammissibile, purché l'esclusione temporanea abbia una fase di ingresso e la corsa con tutti i dati utili sia davvero eseguita.

**Interpretabilità accessibile:** attività TF/pathway e cNMF come input/diagnostiche; Mixscape come supervisione ausiliaria sulle cellule di training; SWIM/SWIMmeR come descrittori da confrontare con hub appaiati e reti permutate, non matrice causale. SCENIC opzionale dopo la prova dei reguloni curati. Non dichiarare RNA velocity o SCENIC+ applicabili senza layer/dati necessari. Pacchetti e risorse non risultano tutti già installati/acquisiti: registrarli nel manifest.

## 8. File, dipendenze e prove di completamento

Percorsi seguenti **proposti, non già creati**. Codice di ricerca in nuovi report come richiede la repo; dati pesanti fuori dalla repo. Prima di creare le cartelle controllare nomi e assegnazioni, leggere la guida e registrare indice/registro. Non modificare i file storici importati da altri banchi: copiarli in una nuova versione.

Radici previste nella repo: `reports/sorgenti/corpus_cellulare_<data>/` (D), `reports/modelli/risposta_biologica_<data>/` (M), con data effettiva di creazione nel formato 2026-09-30. Sono template di percorsi futuri. Se un nome è già occupato scegliere un nome nuovo; D/M sono abbreviazioni di questa tabella. Artefatti pesanti sotto `VCC2026_DATA_ROOT` o storage remoto persistente equivalente, versionati per run.

| Passo | File/moduli da creare o collegare | Prova richiesta |
|---|---|---|
| **P0 — ambiente e storia** | D:`environment_manifest.json`, `validate_runtime.py`; M:`holdout_registry.json`, `PROTOCOLLO.md` | Import dello scorer reale, roundtrip sparse/mask, storia degli outcome verificata, ruoli train/development/riserva. Correggere ambiente senza cambiare metriche |
| **P1 — inventario esaustivo** | D:`inventory.py`, `sources.yaml`, `availability.csv`, `contracts.py` | Ogni sorgente del §3 e ogni accessione dei cataloghi ha stato locale/remoto/candidato, formato, ruolo, ostacolo e prossimo passo; nessun «usato» senza input manifest del fit |
| **P2 — ingestione cellulare** | D:`adapters/`, `shard_writer.py`, `validate_shards.py`, `plan_jobs.py`, `reconcile_jobs.py`, `jobs/` | Primo shard per schema in parità; ripresa dopo interruzione; merge senza duplicati/buchi; poi espansione all'universo, con ricevute locali/remoto |
| **P3 — qualità e armonizzazione** | D:`qc.py`, `qc_policy.yaml`, `normalization.py`, `QC_REPORT.md`, `tests/` | Tabella prima/dopo e cause, controlli NTC, supporto genico e denominatori, conservazione fenotipi, confronti di correzione. Sorgenti bloccate non impediscono quelle pronte |
| **P4 — viste biologiche e split** | M:`splits.py`, `gene_features.py`, `activity_features.py`, `state_programs.py`, `feature_manifest.json`; `test_leakage.py` nella sottocartella test di M | C/T/J per famiglie/studi/donatori; centri/PC/programmi/norme fit nel training; riserva non consumata; raw disponibili al loader |
| **P5 — modelli e curve dati** | M:`cell_dataset.py`, `sampler.py`, `linear_baselines.py`, `model.py`, `losses.py`, `train.py` | Baseline appaiate, rete funzionale e modello cellulare; log delle cellule/target/studi visitati; curve con dataset annidati e ripetute selezioni delle sorgenti |
| **P6 — distribuzioni e validazione** | M:`efficacy.py`, `observation.py`, `evaluate_six.py`, `export_effects.py`, `tests/` | Sei grezzi e aggregazione locale dichiarata, più seed, guide/repliche escluse, controllo del sampler, missing-mask e parità export/lettore |
| **P7 — candidato e produzione** | Solo dopo conferma: moduli necessari in `src/vcc2026/`, relativa guida, ricetta in `configs/recipes/`, test e collegamento a stadi 100/45 | Refit e inferenza con medesimi contratti, asse ufficiale completo, fallback dichiarato, preflight; eventuale invio segue la procedura esistente |

Riutilizzare, dopo controllo del contratto: `src/vcc2026/sc_stream.py` e lettori remoti; `AxisTable`/`effects_from_pseudobulk` in `src/vcc2026/multisource.py` per viste di controllo; `Pool`/`Phase` della rete precedente per le guardie C/T/J; `src/vcc2026/bench.py` per i sei membri. L'export deve scrivere `targets`, `genes`, `lfc` in ln e `observed` attesi da `scripts/45_generate_prediction.py`, non una maschera rinominata `measured`.

## 9. Come decidere senza premiare la sola pulizia o il solo volume

- **Più dati:** stesso test congelato, sottoinsiemi annidati e selezioni replicate. Riportare confronto a esposizione/computazione comparabile e corsa con tutti i dati utili fino al criterio di arresto scelto nella validation. Nessun tetto permanente al corpus per comodità del pilot.
- **Singole cellule:** confronto con versione aggregata dagli stessi dati ammessi, medesimi split e sampler di valutazione. Separare il guadagno delle cellule da quello di avere più sorgenti o parametri.
- **Qualità:** correzione assente/moderata/completa candidata; nulli tecnici e fenotipi mantenuti. Miglior clustering o minore varianza non certificano migliore predizione.
- **Biologia:** cieco/scambio di contesto, prior permutati, MLP/bilineare sugli stessi input, memoria sorgenti spenta. Un guadagno senza vantaggio sullo scambio può essere utile, ma non dimostra lettura dello stato corretto.
- **Generalizzazione:** famiglie intere, donatori/cloni raggruppati e test T/J su target mai osservati in alcuna fonte/derivato, incluse combinazioni. Target e complessi condivisi inducono dipendenze: incertezza per gruppi e variabilità dei seed, non milioni di cellule indipendenti.
- **Sei metriche:** PDS, MSE, NMAE, fidelity, reach, Jaccard sullo stesso pannello/supporto; nessun proxy a due membri come veto universale alle reti. Soglia di utilità e regressioni ammesse si congelano prima del test nel nuovo protocollo, seguendo R-COMP; ancore locali non sono una conversione esatta in punti VCC.

Una prima ipotesi negativa chiude quella formulazione, non autorizza a cambiare soglia sullo stesso test. Tornare a sviluppo e registrare una nuova ipotesi; non consumare di nuovo la riserva per scegliere varianti.

## 10. Consegna e chiusura

Claude aggiorna qui presa in carico e avanzamento P0–P7, con link agli output. Ogni risultato nuovo va prima in un report immutabile con manifest; questa scheda non diventa il log dei job.

Il piano si chiude con: inventario completo riconciliato; corpus cellulare versionato e QC verificabile; decisione motivata per tutte le fonti non entrate; training con copertura consumata dimostrata; confronto di generalizzazione e sei metriche riproducibile; candidato promosso oppure esito negativo circoscritto con nuova ipotesi. Un corpus tecnicamente completo è un risultato d'infrastruttura, non ancora un modello migliore.

**Primo messaggio di consegna di Claude:** indicare quali sorgenti sono pronte a livello cellulare, quali richiedono recupero, quali esistono soltanto aggregate, quali sono riserva; mostrare i primi manifest/job e la matrice QC. Poi eseguire le fasi indipendenti autorizzate. Non ripartire scegliendo soltanto i quattro dataset della ricetta corrente.
