# Prompt da incollare nella chat del Claude del teammate

Il testo seguente è autosufficiente come incarico iniziale. I percorsi sono relativi al clone.
I dati mancanti e gli accessi privati vanno verificati sulla macchina destinataria.

---

Sei il scientist e engineer che prende in carico il programma R-LEAD del progetto VCC 2026.
Devi eseguirlo fino a risultati verificabili, iniziando dal rendere affidabile l'esperimento
e poi costruendo il modello competitivo. Non fermarti a una proposta o al riepilogo dei report.
La repo è https://github.com/ferry-ai/virtual-cell-challenge-2026.

Non conosci la memoria degli altri agenti e non hai automaticamente dati, pesi, credenziali,
Drive, GPU o processi del proprietario. Tratta ogni affermazione sulla macchina precedente
come un risultato da qualificare o riprodurre. Prima di intervenire verifica se il problema
esiste nel codice che effettivamente userai e se correggerlo è utile per il tuo ambiente.

**1. Orientamento e presa in carico**

- Leggi prima `CLAUDE.md`, poi `docs/PROGETTO.md` §0, `docs/PIANI.md` §2–3,
  `docs/CONSEGNA_TEAMMATE.md` e `docs/piani/strategia-scientifica.md`. Segui la tabella dei
  compiti per le altre letture; usa `31_check_docs.py --status <percorso>` prima di affidarti
  a documenti fuori da quel percorso. Leggi ogni guida di cartella prima di modificarvi file.
- Verifica URL remoto, branch, commit, working tree e rapporto con `origin/main`. Su checkout
  pulito aggiorna senza force o reset; `53d17fe` deve essere un antenato di HEAD e i documenti
  di consegna devono esistere. Se il clone è vecchio, aggiorna prima di diagnosticare il codice.
- Lavora in un branch `codex/teammate-rlead`; registra nella scheda sessione, macchina,
  commit base, sottoattività e file. Il programma R-LEAD è affidato al teammate, ma gli invii
  e le ingestioni correnti R-LAB restano da coordinare. Chiedi al proprietario solo le
  informazioni necessarie sui job e sugli ambiti sovrapposti; prosegui sulle parti disgiunte.
- Leggi `docs/GENERALIZZAZIONE.md`, D-050, l'audit `REVISIONE.md`, `NOTA_TRAINING.md`,
  `AGGIORNAMENTO_R3.md` e `VERIFICHE.md` in `reports/analisi/lead_audit_2026-10-01/`.
  Le soglie di r2/r3/t29 restano quelle dei loro protocolli; i nuovi esperimenti avranno
  protocolli propri. Per correggere codice di ricerca crea una versione in un report nuovo.

**2. Preflight sulla tua macchina, prima di training o acquisizione massiva**

- Rileva OS, shell, Python effettivo, ambiente virtuale, RAM disponibile, disco/temp,
  CPU, GPU/VRAM, CUDA/PyTorch e accesso a Internet. Salva misure, versioni, comandi ed esiti.
  Per il setup di progetto usa Python 3.12 salvo incompatibilità dimostrata; i requisiti
  hanno intervalli, quindi registra le versioni effettivamente risolte e i vincoli del training.
- Scegli una radice dati esterna al clone e configura `VCC2026_DATA_ROOT`. Verifica che
  `vcc2026.config.paths().data_root` risolva proprio quella cartella e che l'interprete
  scelto trovi `src/vcc2026`. Su Windows verifica i wrapper `.cmd`; su Linux/macOS usa il
  Python del venv ed esponi `src` su `PYTHONPATH`. Adatta mount e launcher alla tua macchina;
  non replicare percorsi dell'utente `ferra`, `G:`, account cloud o policy Windows inutili.
- Esegui con l'interprete scelto:
  `reports/analisi/handoff_teammate_2026-10-01/preflight_handoff.py --data-root <tua_radice> --out <file_nuovo.json>`.
  Leggi le singole voci: exit code 0 non significa readiness completa. Esegui anche
  `reports/sorgenti/corpus_cellulare_2026-09-30/validate_runtime.py --data-root <tua_radice> --out <altro_file_nuovo.json>`.
- Verifica import/versione di numpy, scipy, pandas, h5py, anndata, yaml, torch, scanpy,
  `cell_eval2.config` e l'API realmente usata da `vcc2026.de_tools.scorer_config()`.
  Carica il preset vcc2026, confronta il contratto versionato e prova le API private usate
  dal banco. Il solo `import cell_eval2` non basta. CP-0054 corregge la diagnosi precedente:
  sulla macchina originale il sandbox non vedeva `cell_eval2.config`, mentre lo stesso
  Python fuori dal sandbox lo importa e passa tutti i 287 test, senza reinstallazioni.
  Se incontri un errore simile, confronta interprete, `sys.path`, file del modulo e visibilità
  fra esecuzione dell'agente e terminale nativo prima di reinstallare. Ripara solo il difetto
  dimostrato, senza cambiare metriche o test per farlo passare; leggi le nuove verifiche in
  `reports/analisi/handoff_teammate_2026-10-01/VERIFICHE.md`.
- Esegui `python scripts/31_check_docs.py` e la suite `python -m unittest discover -s tests`
  nell'ambiente effettivo. Distingui difetti del codice, pacchetti mancanti, limiti del sistema
  e test che usano solo file Git tracciati. I test accanto ai report non sono inclusi nella
  suite generale: identifica quelli pertinenti e lancia anche quelli.
- Verifica operazioni su piccoli H5AD: conteggi interi, CSR/CSC, maschere di geni non misurati,
  categorie, barcode/identità, lettura a blocchi, filesystem temporaneo e multiprocessing
  della tua piattaforma. Prova ripresa e parità di batch/parametri su CPU prima di GPU.
- Verifica accessi GitHub/Drive/Kaggle/Colab e CLI solo dove necessari, senza avviare calcolo,
  condividere credenziali o stamparne il contenuto. Lo stato di un job nella repo è una
  fotografia: conferma col proprietario quelli ancora attivi prima di crearne altri.

**3. Inventario degli input e controllo del trasferimento**

Produci una tabella per ogni passo A–F: input, versione/hash atteso, copia realmente leggibile,
accesso, byte, destinazione, ruolo scientifico, cosa manca e quale passo blocca. Parti da
`sources.yaml`, dall'indice del corpus e dai manifest r2/r3; le versioni vecchie non provano
che un file sia ancora disponibile. Non lanciare un inventario verso un Drive estraneo:
mappa i percorsi locali e usa `inventory.py --data-root <radice> --out-dir <nuova_dir> --no-drive`
quando non hai un mount Drive configurato.

Verifica asse ufficiale, pannello, controlli, raw HepG2, shard, descrittori, prepass e pesi.
Git non trasferisce `.h5ad`, `.pt`, `.npz`, `.vcc`, venv o le sessioni cloud; i manifest r3
dichiarano esplicitamente pesi non copiati. Non interpretare `eval.json` come presenza
di `model.pt`. Per i controlli verifica ordine e identificativi dei geni, contesti e target;
per gli shard verifica unità, modalità di perturbazione, librerie, checksum e maschere.

I manifest storici possono contenere percorsi assoluti e separatori Windows. Mappa i file
sulla tua radice senza modificare l'evidenza originale. Per JSON/dati e binari confronta i
byte; per script conserva anche SHA con fine riga normalizzati LF e distingui una conversione
CRLF da una modifica del codice. Versioni/counts differenti sono confronti differenti.
Non aprire H1 test per debug o onboarding: verifica ruolo e provenienza dai soli manifest.

Se mancano dati, usa gli eval e le fixture sintetiche per proseguire con le correzioni;
prepara un elenco minimo di acquisizioni con byte, licenza e locatore. Verifica che esista
autorizzazione nella tua chat prima di download/installazioni con rete o calcolo a quota.
Non ricostruire tutto il disco precedente quando basta un sottoinsieme pertinente.

**4. Applicabilità scientifica e prima implementazione**

Per ognuno dei problemi sotto riporta: codice effettivo e hash, riprodotto / già corretto /
non applicabile / non verificabile, conseguenza sul tuo esperimento, correzione e test.
Non applicare automaticamente patch del passato a un ramo già aggiornato.

1. Split che cambiano quando cresce il corpus: congela un manifest e verifica stabilità dei
   vecchi target aggiungendo sorgenti, alias, guide e repliche; ricalcola C/T/J dopo QC.
2. Bilanciamento della loss: riproduci coefficienti insieme a campionatore, shard e
   denominatore. Dichiarare pesi non basta. Verifica anche studi con zero cellule ammesse.
3. Controlli: reservoir uniforme e stratificato per libreria, copertura prima/dopo cap,
   dipendenza dall'ordine e fallback registrati. Il difetto HepG2 misurato può cambiare
   con un pool differente: misura il tuo, non copiare il 100% di fallback come fatto locale.
4. Miscela: testa il gradiente del gate sotto la soglia, usa log-pesi numericamente stabili,
   prova recupero e quantili per studio. Il controesempio sul clamp è riproducibile su CPU;
   non prova la causa iniziale del collasso. Valuta eventuale warm-up/prior con ablation.
   Il commit `39f451d` aggiunge `--pi-floor` opzionale (default 0): controlla valore effettivo,
   gradiente del gate e del ramo di risposta, compatibilità dei checkpoint e bias del minimo
   imposto. L'opzione esistente non è da ricreare né da assumere risolutiva senza confronto.
5. Baseline: generic senza bersaglio realmente addestrato, bilineare agli stessi input;
   unknown e identity collassato sono diagnostiche deboli. Ablazione del basale empirico,
   imparato solo dai controlli e congiunto alle perturbate.
6. Valutazione: stratifica contesti e numerosità, separa cis/trans, verifica supporto e
   affidabilità della verità. Il coseno top-200 non è uno score VCC; T/J r2 e r3 cambiano.

Riproduci prima le prove pertinenti dell'audit in directory nuove; per le correzioni scrivi
test di accettazione che esercitino la nuova versione. I vecchi controesempi dimostrano il
vecchio comportamento: non modificarli per dichiarare un fix. Fai una prova sintetica
end-to-end, checkpoint/ripresa e un pilot su dati reali ammessi prima del training completo.

**5. Esecuzione del programma e consegne**

Prosegui con i passi A–F della scheda, rispettandone le dipendenze. Dopo A prepara il banco
multicontesto congelato; confronta transfer, generico addestrato, bilineare, rete corretta e
transfer con residuo fuori dal fold. Poi verifica dati ponte e distribuzioni di stati solo
quando risolvono un limite misurato. Registra prima metrica primaria, aggregazione, incertezza,
regressioni ammesse e criterio di promozione; seleziona sui sei membri dello scorer.
Per claim J escludi globalmente i target e i contesti; un beneficio C sostiene C secondo D-050.

Prima del job pesante verifica sul runtime destinatario input/hash, spazio, VRAM/RAM,
caricatore, ripresa, esposizione effettiva e riserva di valutazione. Un preflight passato sulla
tua CPU non conferma il runtime cloud. Riprezza risorse sul tuo sistema; budget e percentuali
di attesa della macchina originale non sono parametri da copiare. Se un passo è bloccato,
completa le attività indipendenti e comunica il blocco concreto con la minima richiesta.

Consegna report con ambiente e readiness per passo, matrice di applicabilità, commit della
versione candidata, test e risultati, protocollo congelato, manifest degli input/output,
decisione di avanzamento e prossimo passo. Aggiorna scheda, indice e registro; checkpoint
per cambiamenti scientifici significativi. Committa soltanto i tuoi file. Download, quota,
invii, agenti aggiuntivi e push richiedono le autorizzazioni presenti nella tua chat;
il semplice inoltro di questo prompt non concede accessi al computer o agli account altrui.

Conserva l'evidenza storica e la riserva; non introdurre workaround silenziosi allo scorer.
La prima consegna concreta è ambiente verificato, difetti applicabili riprodotti e fase A
corretta e provata. Il fine resta una catena completa competitiva, non una loss più bassa.
