# Passaggio di consegne a claude2: regia dell'ingestione completa

Scritto il 3/10/2026 verso le 16:25 CEST dalla sessione Claude Code «R-LEAD implementazione vcc2026» (`22d21f`), che
ha consumato l'80% della finestra di 5 ore. Il proprietario apre claude2 dall'app desktop, con l'altro account, nella
cartella `C:\Users\ferra\OneDrive\Desktop\vcc2026`. **Priorità esclusiva: l'ingestione completa** (mandato del
proprietario del 3/10: tutti i dataset per intero, in fretta, anche in parallelo su più code Colab).

## Da leggere prima di agire

1. `CLAUDE.md` alla radice: regole, autorizzazioni e la checkout condivisa.
2. `docs/PROCEDURE.md` §3 e `docs/ERRORI.md`, da «Prima del prossimo job» a «Registro immutabile»: preflight e job
   Colab.
3. `docs/AGENTI.md` §3. **Commit sempre con percorsi espliciti** (`git commit -- <percorsi>`): l'indice è condiviso
   con altre sessioni.
4. [README dell'ingestione](README.md): sorgenti, vincoli e file. La scheda
   [R-LAB](../../../docs/piani/piano-giorno-2026-09-30.md) ha lo stato riprendibile.
5. [GEO_METADATI.md](GEO_METADATI.md): DLD-1, microglia, PerturbFate.

## Stato alle 16:25

**Colab**, account del proprietario. I dispatcher li avvia lui dal browser; il battito sta in
`G:/Il mio Drive/vcc2026/runs/jobs/dispatcher*.log`, ogni 10 minuti, in ore UTC. I log dei singoli job arrivano su
Drive solo alla fine.

| Coda | Notebook | Job in corso o in attesa |
|---|---|---|
| `queue` | `notebooks/colab_sc_training.ipynb` | 134 verifica dell'archivio A (ripresa r2); 138 Orion HCT116 shard, parte 1/2 |
| `queue2` | `reports/sorgenti/corpus_cellulare_2026-09-30/colab_dispatcher_queue2.ipynb` | 132 Southard r3; 137 Orion HCT116 shard, parte 0/2 |
| `queue3` | `colab_dispatcher_queue3.ipynb` (questa cartella, e su Drive in `vcc2026/notebooks/`) | 139 e 140, Orion HEK293T, parti 0 e 1 di 4 |
| `queue4` | `colab_dispatcher_queue4.ipynb` (idem) | 141 e 142, Orion HEK293T, parti 2 e 3 di 4 |

Le code 3 e 4 partono quando il proprietario apre i due notebook. Un job con `.started` e senza battito per ore è
perso: si rimette in coda con **numero e output nuovi**, mai sopra il vecchio.

**Output su Drive** (`G:/Il mio Drive/vcc2026/`):
- Orion: `data/processed/ingestione_completa_2026-10-03/<job>/`; la parità dei metadati è passata su entrambe le
  linee (3.409.169 e 4.534.299 cellule);
- Southard: `data/processed/corpus_cellulare_2026-09-30/j09_southard_r3/`;
- verifiche: `runs/archivio_verify_2026-10-03_r2/out_*_r2/` (la B è finita alle 16:06, con codice 0).

**Agenti e compagni:**
- **Codex** è il supervisore. Lavora in `adattatori_codex/`: `h5csc` compatto a intervalli di cellule (KOLF) e
  `h5rows` con filtro di idoneità (CD4). La consegna è in corso; i file sono suoi, non toccarli.
- **Grok** non riesce a fare ricerche GEO senza shell: non riassegnargliele.
- Il run claude2 dell'hub `20261003-155531-vcc-rds-conversion` si è fermato per un limite di spesa e non ha scritto
  niente.

## Prossimi passi, in ordine

1. **Orion**, quando le parti finiscono:
   - leggi `complete.json` e le ricevute di ogni parte: le cellule devono essere uguali al campione;
   - misura la dimensione degli shard;
   - pubblica su Kaggle con `publish_kaggle.py` (`reports/sorgenti/corpus_cellulare_2026-09-30/`) sull'account dei
     dati `davidmaisterx`. La quota privata è di 200 GB, di cui circa 108 usati il 2/10: se non basta, pubblica il
     campione del training e lascia tutto il resto su Drive;
   - fai rileggere gli shard da un altro runtime (`verify_resume.py` o `verify_drive.py`).
2. **KOLF pan-genome e CD4**, appena Codex consegna gli adattatori:
   - rivedi i suoi test e integra in una copia tua;
   - costruisci i job sullo schema di `orion/build_orion_job.py`: KOLF diviso per intervalli di cellule su due code,
     CD4 un job per file (12 file su S3, 1,74 TB). Le code sono 1–4.
3. **DLD-1** (GSE337988, `RAW.tar` da 26,5 GB):
   - un adattatore per le matrici 10x h5 per canale, con la chiamata della guida da `crispr.umi_correct.h5`;
   - la MOI bassa per prima, perché è a guida singola;
   - job: scaricare il tar sul runtime, estrarre canale per canale, convertire.
4. **Mixscale, VIPerturb e PerturbFate** (RDS): il brief è [agenti/brief_claude2_rds.md](agenti/brief_claude2_rds.md).
   Tu hai la shell, quindi puoi scriverlo e provarlo. R su Colab: `apt-get install -y r-base r-cran-matrix`.
5. **Microglia** (GSE335887): piccola, matrici 10x h5 più le guide del CROP-seq.
6. Dopo ogni passo aggiorna lo stato riprendibile nella scheda R-LAB e committa con i percorsi.

## Non è priorità, ma non toccare

La rete ancorata di R-LEAD: i training Kaggle `davideferrante11/rcell-anchored-train-h1-r1` e `-hepg2-r1` sono in
corso dalle 16:09, con un budget di circa 3 ore. RPE1 va spinto quando una delle due sessioni GPU si libera: il
comando è nella scheda R-LEAD (`docs/piani/strategia-scientifica.md`). Dopo la spinta si rilegge la quota con
`kaggle quota` e il token `~/.kaggle-davideferrante11`. Il protocollo è congelato con un emendamento
(`reports/modelli/rete_ancorata_2026-10-03/PROTOCOLLO.md` §9). Se l'ingestione ti lascia tempo, spingi RPE1 una volta
sola e annotalo in `lancio_train_r1.json` o in un file nuovo.

## Autorizzazioni, già date dal proprietario in chat

- download e acquisizione di tutti i dataset per intero;
- Colab e Kaggle, anche su più code;
- agenti dell'hub quando servono.

Non autorizzati senza chiedere: push su GitHub, invii alla gara, dataset pubblici, cancellazioni. Niente segreti nella
repo; il test di H1 2025 resta chiuso.

## Trappole già incontrate

- `scripts/py.cmd` passa da cmd.exe, che spezza un argomento con `|`: in quel caso usa
  `C:/Users/ferra/vcc2026-data/.venv/Scripts/python.exe` direttamente.
- Un heredoc di Git Bash passato a `py` dimezza i backslash: per stringhe con backslash usa l'editor.
- `G:` mostra il disco del portatile, non la quota di Drive.
- Il `.started` non è atomico su Drive: due dispatcher non leggono mai la stessa coda.
- In modalità `read` dell'hub Grok si ferma al piano. I run claude2 dell'hub condividono i limiti dell'account Claude
  che li lancia.
- Dopo ogni spinta di un kernel GPU si rilegge la quota; non si lanciano cicli che spingono da soli (incidente
  E-20261003-001).
