# Procedure — il percorso vivo

Scritto il 2026-09-23, con la pulizia di [D-040](DECISIONI.md#d-040--il-codice-vivo-è-solo-quello-che-produce-o-valuta-una-sottomissione),
come `docs/LAVORO.md`; rinominato il 30/09 ([ARCHIVIO](ARCHIVIO.md#nomi-cambiati)).
**Perimetro:** gli strumenti di esecuzione del progetto, cioè che cosa gira e in che ordine, con
quali comandi, e dove finiscono i risultati. **Si legge per sezione**, quella del compito: §1–2
generare, impacchettare, inviare e leggere un punteggio; §3 job su Colab e Kaggle; §4 gli stadi
vivi; §5 aggiungere e togliere codice; §6 dove stanno le cose; §7 il set finale. Si aggiorna
quando cambia il percorso vivo. I lavori da scegliere e le assegnazioni stanno in
[PIANI.md](PIANI.md) e nelle sue schede.

I numeri e le incertezze stanno in [PROGETTO.md](PROGETTO.md), il perché delle scelte in
[DECISIONI.md](DECISIONI.md). Il contratto del formato è in [SOTTOMISSIONE.md](SOTTOMISSIONE.md)
§1–2; per i comandi vale questa pagina.

Questa pagina elenca la pipeline di produzione. Il codice di ricerca resta nelle cartelle
dei [report](../reports/README.md#il-codice-di-ricerca-che-sta-qui), con copie congelate per
esperimento; il codice ritirato si recupera tramite [ARCHIVIO](ARCHIVIO.md).

## 1. Il percorso di un invio

Il percorso si ricostruisce dai manifest del riferimento scelto: ricetta, cache, effetti,
generatore, scala e seed sono tutti parte del candidato. R-LEAD distingue replica t22,
stimatore corretto t25 e variante di emissione t28; il numero più recente non è il default.

```
sorgenti: bulk K562 · 97 CD4 · 102 Orion ──▶ 98  cache degli effetti per sorgente
ricetta configs/recipes/tNN.json ──────────▶ 100 effetti per contesto (effects_A/B/C.npz)
                                          ──▶ 45  cellule: generatore di trial-01 (trial-ext-profile)
                                              76  in alternativa ControlModel (§3)
                                          ──▶ 48  convalida a flusso + .vcc + verifica bit per bit
previsione e testi scritti PRIMA ─────────▶ vcc submit ──▶ vcc status ──▶ checkpoint
```

Prima di generare scegliere una destinazione nuova e registrare i parametri nel protocollo.
Questi sono i punti d'ingresso per controllare gli argomenti correnti:

```powershell
.\scripts\py.cmd scripts\100_build_context_effects.py --help
.\scripts\py.cmd scripts\45_generate_prediction.py --help
.\scripts\py.cmd scripts\48_package_prediction.py --help
```

Preparare poi un comando esplicito con `--recipe`, `--cache` e un `--out` nuovo per 100;
`--run-id` nuovo, `--trial trial-ext-profile`, effetti per contesto e opzioni congelate
per 45; file realmente prodotto e altro `--run-id` nuovo per 48. Per un export neurale
documentare il percorso che sostituisce 100. Il pacchetto da inviare è quello dichiarato
dal manifest di 48, non un percorso copiato da un esempio vecchio. Invio e lettura: §2.

Gli esempi t11 precedenti sono nello [storico](storico/rinnovo_2026-10-01/docs/PROCEDURE.md);
contengono destinazioni occupate e non vanno eseguiti come un nuovo trial.

I manifest di ogni stadio stanno accanto all'output (`manifest.json`); quelli degli invii si
copiano in `reports/invii/trial_<data>/`, con i nomi elencati in `reports/CLAUDE.md` («What a
submission leaves here»).

Lo stadio 45 conserva Poisson come comportamento predefinito. Con `--gene-dispersion`,
`--gene-dispersion-scale` moltiplica la dispersione stimata sui controlli (1 mantiene la
stima, 0 torna a Poisson). L'alternativa sperimentale `--depth-bins` apprende dai controlli
la composizione condizionata sulla profondità, poi calibra i profili dei gruppi sul profilo
pooled richiesto; non si combina con le opzioni di dispersione. Le diagnostiche registrano
la scelta dei quantili, la convergenza e gli eventuali limiti applicati ai conteggi.
Implementazione e prove: `reports/analisi/lead_scientist_2026-09-29/`; l'esistenza di queste
opzioni non ne dimostra un vantaggio sul punteggio.

Il t28, massimo osservato, è la ricetta del t25 generata con `--effects-scale 1.5` e
`--gene-dispersion` alla scala 1, su Colab. Le opzioni sono registrate nella sua previsione
(`reports/invii/prediction_t28_2026-09-29/prediction.json`) e nel manifest dello stadio 45
(`reports/invii/trial_2026-09-29/t28_manifest_45_generate_prediction.json`); il job è
`reports/analisi/lead_scientist_2026-09-29/candidate_generation_remote/recovery_r2/079_lead_t28_generate_r2.sh`.
Un'opzione dello stadio 45 che fa parte di un candidato si scrive nella previsione, prima di
generare, come la ricetta.

## 2. Le regole dell'invio

Ognuna è costata qualcosa. Le date sono quelle in cui è stata pagata.

1. **Prima di generare**, si registrano la previsione e la regola di lettura in
   `reports/invii/prediction_tNN_<data>/prediction.json`:
   - una banda numerica;
   - che cosa si concluderà in ciascun caso.

   Anche i testi della sottomissione si scrivono prima, in
   `reports/invii/trial_<data>/submission_texts.md`. La soglia non si sposta dopo aver visto il
   numero ([CP-0030](checkpoints/0030-t10-attribuzione-cd4.md)).
2. **Un fattore alla volta per attribuire un effetto.** Per scegliere un candidato sono
   ammesse modifiche congiunte dopo un banco fattoriale preregistrato e una conferma
   separata con soglie congelate ([D-047](DECISIONI.md#d-047--le-interazioni-richiedono-confronti-congiunti)).
   L'eventuale invio misura allora il pacchetto, senza attribuire il risultato a un solo fattore.
3. **L'invio consuma quota:** 2 al giorno, uno solo in volo per squadra. Serve
   l'autorizzazione del proprietario, data in chat. Quelle già ricevute sono trascritte in
   `reports/invii/trial_2026-09-22/autorizzazioni.md`: leggile, ma un agente nuovo le conferma
   in chat prima di usarle.
4. **Un lavoro pesante alla volta.** Il 23 settembre tre lavori insieme hanno riempito il
   disco durante l'impacchettamento. Un candidato arriva a circa 13 GB di picco, e le riserve
   degli stadi 45 e 48 chiedono circa 17 GB liberi per partire a forma piena (§7). Controlla
   con `df -h /c` prima di partire.
5. **Il portatile non deve andare in sospensione durante l'upload.** Il 23 settembre il
   sonno ha interrotto il secondo tentativo del t11 (`reports/invii/trial_2026-09-23/`).
   - **Un upload interrotto lascia l'entry sul server** in stato `uploading`. Occupa lo slot
     della squadra, anche se `vcc whoami` può dire `can_submit: true`.
   - La CLI tiene l'upload in `~/.config/vcc/state.json`, alla voce `pending_uploads`.
     `vcc submit --resume <entry>` lo riprende sullo stesso file; controlla prima lo sha256
     del `.vcc` contro il report dello stadio 48.
   - `vcc cancel <entry>` abbandona l'entry, e non conta sul limite giornaliero: conta solo
     un invio valutato (`vcc cancel --help`).
   - **L'upload gira come processo Windows separato** (`Start-Process`), non come comando in
     background della sessione dell'agente: il 29/09 il sistema ha fermato per memoria scarsa un
     upload lanciato così, mentre la sessione era ferma al limite d'uso. Il processo ucciso lascia
     anche un lucchetto in `~/.config/vcc/locks/`: prima di riprendere si controlla che il suo pid
     non esista più ([CP-0045](checkpoints/0045-t26-soglia-espressione.md)).
6. **L'output di `vcc` si salva così com'è**, in `reports/invii/trial_<data>/`
   (`submit_<entry>.json`, `status_<entry>.json`). Un tentativo fallito si registra come
   tale, in un file suo. **Lo stato va chiesto appena il punteggio c'è, prima dell'invio
   successivo:** il 25 settembre `vcc status` rispondeva `not_found` per t15 e t16 e serviva
   solo l'ultimo invio, e l'output di `submit --wait` porta gli scalati ma non i grezzi
   ([CP-0037](checkpoints/0037-t16-ampiezza-quadrupla.md)).
7. **Dopo il punteggio**, questa è la lista completa:
   - `comparison.json` accanto alla previsione, con i sei scalati pubblicati e la regola applicata;
   - una riga nella tabella dei punteggi di `reports/invii/README.md`, la loro sede unica;
   - un checkpoint (`python scripts/30_new_checkpoint.py`);
   - il §0 di [PROGETTO](PROGETTO.md) se cambiano il massimo osservato, il riferimento o la
     direzione, e la sezione 2 di [AMBITI](AMBITI.md).

   Leggere i sei scalati pubblicati dallo status completo e verificarne la media.
   Le ancore aggregate in `reports/gara/anchors_2026-09-17/` sono pesi storici utili
   per indici locali, **non una conversione esatta** dei grezzi aggregati: i contesti
   hanno normalizzazioni separate. Non ricostruire membri ufficiali mancanti come misure.
   Prova e portata: [audit credibilità](../reports/analisi/lead_scientist_2026-09-29/SCORE_CREDIBILITA.md)
   e [CP-0050](checkpoints/0050-credibilita-score-e-riserva.md). Un esempio di lettura offline e
   testata, specifica del t28, è `reports/analisi/lead_scientist_2026-09-29/candidate_generation_remote/recovery_r2/read_t28_score.py`:
   per un altro invio se ne fa una copia in una cartella nuova.

## 3. Job su Colab e Kaggle

### Scelta del runtime — priorità operativa

**Configurazione confermata dal proprietario in chat il 2 ottobre 2026: Colab CPU
stabile e Kaggle GPU.** Questa è la configurazione del progetto, non una promessa
generale dei provider. Prima di ogni calcolo pesante applicare questa scelta:

| Lavoro | Destinazione preferita |
|---|---|
| Sviluppo, fixture, test piccoli | Portatile |
| Banchi C/J, preprocessing, predizione e valutazioni pesanti su CPU | Colab CPU |
| Training neurale con modello e tensori effettivamente su CUDA | Kaggle GPU |

### Parallelismo cloud obbligatorio (D-057)

**Mandato del proprietario del 4 ottobre 2026:** sfruttare in parallelo le sessioni
disponibili degli account Kaggle configurati e Colab per i job indipendenti già
autorizzati. Colab resta la destinazione CPU preferita; Kaggle CPU la affianca per
ingestione, preprocessing e banchi, senza accendere GPU che il job non usa.

1. Prima di assegnare i job, rilevare per ogni account/runtime accessibilità, sessioni
   attive e in coda, slot consentiti, quota residua disponibile, CPU, RAM libera,
   disco e disponibilità degli input. Registrare data e fonte della misura nel
   manifest o registro della campagna; un dato non leggibile resta «non verificato».
   I valori 32 GB Kaggle e 12 GB Colab non sono capacità garantite per account.
2. Dividere il lavoro pronto per sorgente, shard, fold o seme quando le dipendenze
   lo consentono. Assegnare parti distinte ai runtime disponibili: non lasciare
   lavoro indipendente in serie mentre una risorsa idonea è inutilizzata senza
   motivazione registrata. Preparare codice e input mancanti fa parte del lavoro.
   Ogni processo deve rientrare nella RAM del proprio runtime; le memorie delle
   sessioni non costituiscono un unico spazio condiviso.
3. Usare un'assegnazione univoca per job, launcher con lock, output separati e
   manifest con hash. Prima di un rilancio verificare che lo stesso lavoro non
   sia già attivo su un altro account; non interrompere job di altre sessioni.
4. Dopo il lancio verificare stato remoto e avanzamento/heartbeat per ciascun job;
   ricevuta di push o stato in coda non provano parallelismo effettivo. Registrare
   runtime, job e orari osservati; alla chiusura verificare output e ricomposizione
   senza parti mancanti o duplicate. Conservare checkpoint prima della fine.
5. Se il parallelismo non è possibile, nominare la dipendenza, il limite di
   risorse/accesso, la contesa I/O o l'altro impedimento misurato e rivalutare
   l'assegnazione quando cambia. Rispettare quote e condizioni dei servizi:
   non usare account aggiuntivi per aggirare restrizioni. Restano valide le
   autorizzazioni di lancio e download; nessun acquisto è implicito.

Il partizionamento conserva tutte le linee e i contesti idonei di D-053 e gli split
congelati: riconciliare le parti attese con quelle effettivamente usate, mantenendo
le esclusioni di validazione. Questa è una regola operativa per ogni agente, non
la dichiarazione che esista già uno scheduler automatico fra gli account.

### Preparazione e verifica del runtime

Un'esecuzione pesante sul portatile richiede una motivazione registrata nel manifest
del job: risorse misurate, disponibilità del cloud, input e ostacolo concreto. Preparare
un pacchetto remoto mancante è un'attività da svolgere, non un motivo automatico per
preferire il locale. Verificare CPU/thread BLAS, RAM disponibile, disco e job attivi
sul runtime effettivo. I circa 10 GB liberi ricordati dal proprietario per Colab sono
da rimisurare, non una garanzia. Più RAM può ridurre la pressione sulla memoria;
il guadagno di velocità richiede un confronto misurato, inclusi trasferimento e avvio.

Per i banchi di ricerca, trasferire uno snapshot dei file necessari in `reports/` e
delle dipendenze importate, oltre agli input e al protocollo congelati. Il mirror
standard `sync_to_drive.ps1` **non include `reports/`**. Preparare i percorsi per Linux
e verificare gli stessi hash nel runtime destinatario. Per letture ripetute usare,
quando il disco lo consente, una copia verificata sul disco locale del runtime;
Drive conserva input persistenti, checkpoint e risultati. Salvare avanzamento e
artefatti senza attendere soltanto la fine del job. Separare i tempi di lettura,
preprocessing, fit/training, predizione e scoring. La scelta del runtime non cambia
dati, split, regole scientifiche o autorizzazioni in chat e non implica acquisti.

Il portatile ha 7,8 GiB di RAM. Lo stadio 76 (`ControlModel`) gira anche qui: il 23 settembre
ha generato il t14 in 35 minuti, con 1–3 GiB di RAM
(`reports/generatore_e_banchi/dispersion_2026-09-23/T14_IN_LOCALE.md`). I banchi 73 e 75 restano su Colab. Il notebook `notebooks/colab_sc_training.ipynb` fa da dispatcher: esegue i `.sh`
depositati in `G:\Il mio Drive\vcc2026\runs\queue\`.

**Prima di mettere in coda un nuovo job** si segue [ERRORI](ERRORI.md), da «Prima del prossimo
job» a «Registro immutabile e chiusura»: manifest di tutti gli input con hash, preflight in locale
e poi sul runtime destinatario prima del calcolo, guasti come incidenti in sola aggiunta. Gli
script rimasti in `notebooks/colab_jobs/` sono del 17/09 e non eseguono il preflight: i launcher che
lo eseguono sono nella revisione lead, per esempio in `reports/analisi/lead_scientist_2026-09-29/neural/`.
Gli script dei singoli job del 17–18/09 sono archiviati dal 30/09 ([ARCHIVIO](ARCHIVIO.md)).

- **Portare il codice su Drive:** `powershell -File notebooks\colab_jobs\sync_to_drive.ps1`.
  Fa un mirror (`robocopy /MIR`) di `src`, `scripts`, `configs` e `notebooks` in `code/`:
  quello che non c'è in locale sparisce anche da Drive. Ogni job ne copia una versione
  privata alla partenza, e `code/SYNC_STAMP.txt` dice da quale commit.
- **Mettere in coda:** `bash notebooks/colab_jobs/queue_trial.sh <NNN_nome> <TRIAL> "<GEN_ARGS>" [<file da attendere>]`
  scrive `runs/queue/<NNN_nome>.sh` con il corpo di `generate_trial.sh`, cioè una generazione con
  lo stadio 76 e l'impacchettamento con il 48, e rifiuta di sovrascrivere. Un altro job si scrive
  a mano sullo stesso schema, caricando `common.sh`. Per catene di job si attende
  il `.done` del precedente, che si scrive con qualunque codice d'uscita.
- **Avviare:** solo il proprietario, eseguendo le celle 1 e 2 del notebook (autorizzano
  Drive). Il segno che è partito è un `NNN_*.sh.started` entro un minuto.
- **Sapere se è vivo:**
  - le righe `alive; running=[...]` di `runs/jobs/dispatcher.log`, ogni 10 minuti;
  - i file di output che compaiono su Drive.

  Il log del singolo job non si sincronizza finché il job non lo chiude: un log fermo non
  è un job fermo.
- **Runtime perso** (ore di silenzio nel dispatcher): un job con `.started` non riparte mai
  da solo. Si rimette in coda con un numero nuovo e un output nuovo, mai sopra il vecchio.
  La nota sulle disconnessioni notturne del tier gratuito descrive l'esperienza
  precedente; non prova che l'attuale Colab CPU confermato stabile dal proprietario
  sia perso. Verificare heartbeat e runtime effettivo prima di concludere.
- **Memoria:** due banchi HepG2 insieme, o un banco HepG2 con uno K562, possono esaurire i
  12 GB del runtime (`rc=137`). Per due job `ControlModel` insieme il job 045 annota lo
  stesso rischio, e per questo aspetta il `.done` del 044.
- **Kaggle:** notebook e dataset privati dell'account del proprietario, via API. La procedura
  seguita il 29/09 è in `reports/analisi/lead_scientist_2026-09-29/CALCOLO.md` e
  `reports/analisi/lead_scientist_2026-09-29/KAGGLE_REMOTO.md`, report datati di una sessione
  Codex: i loro script si copiano in una cartella nuova, non si modificano. Lo stesso preflight
  vale anche qui.

## 4. Gli stadi vivi

Gli stadi vivi sono quelli della tabella; ogni altro numero è in un tag d'archivio. Il
prossimo numero libero è **107**.
`tests/test_live_tree.py` fallisce se questa tabella e la cartella `scripts/` non coincidono:
uno stadio nuovo entra qui nello stesso commit. Le regole di uno stadio sono in
`scripts/CLAUDE.md`, la mappa dei moduli in `src/vcc2026/CLAUDE.md`.

| Stadio | Che cosa fa | Dove gira |
|---|---|---|
| `scripts/97_extract_cd4_rows.py` | Righe pseudobulk CD4 dei bersagli del pannello, per intervalli di byte da S3 | locale |
| `scripts/102_extract_orion_panel.py` | Pseudobulk Orion (HCT116, HEK293T) per lotto GEM; `--finalize` produce l'h5ad | locale |
| `scripts/98_multisource_effects.py` | Effetti per sorgente sull'asse ufficiale e proxy di trasferimento fra sorgenti | locale |
| `scripts/106_assemble_panel_cache.py` | Cache del pannello nel formato dello stadio 98, ricavata dagli universi (i due formati d'indice), con lo sha256 dei bersagli nel manifest | locale |
| `scripts/101_transfer_diagnostics.py` | Tre diagnostiche del trasferimento fra sorgenti dello stadio 98 | locale |
| `scripts/103_direction_transfer.py` | Accordo di segno fra sorgenti sui geni che si chiamerebbero, una sorgente tenuta fuori alla volta | locale |
| `scripts/100_build_context_effects.py` | Effetti per contesto da una ricetta di `configs/recipes/` | locale |
| `scripts/105_ctj_bench.py` | Valutazione C/T/J con split congelati, bootstrap appaiato e scambio del contesto basale | locale |
| `scripts/104_learned_reweighting.py` | Ripesa gli effetti di uno stadio 100 con un canale di magnitudine appreso da sorgenti pubbliche; sperimentale, non adottato (r5 del 26/09) | locale |
| `scripts/45_generate_prediction.py` | Cellule con il generatore di trial-01 (`--trial trial-ext-profile --effects ...`) | locale |
| `scripts/76_generate_sc_prediction.py` | Cellule con `ControlModel` (e termini cis e di trasferimento) | locale o Colab |
| `scripts/48_package_prediction.py` | Convalida a flusso, `.vcc`, verifica del contenitore e del payload | locale o Colab |
| `scripts/83_prediction_calls.py` | Chiamate DE per bersaglio su una previsione, contro controlli veri | locale o Colab |
| `scripts/72_generator_null.py` | Chiamate spurie di un generatore a effetto nullo | locale o Colab |
| `scripts/73_bench_k562_panel.py`, `scripts/75_bench_hepg2_transfer.py` | Banchi a sei metriche su cellule perturbate vere (K562, HepG2) | Colab |
| `scripts/79_fast_de_parity.py` | Parità del DE veloce con il percorso scanpy dello scorer (D-037) | locale |
| `scripts/82_solve_anchors.py`, `scripts/84_predict_official.py` | Diagnostica storica di ancore aggregate e previsione approssimata; non score ufficiale né criterio di promozione | locale |
| `scripts/85_identify_contexts.py`, `scripts/99_context_fingerprints.py` | Che cellule sono i contesti: marcatori, saggio, impronte genetiche | locale |
| `scripts/71_extract_k562_sc.py`, `scripts/74_fetch_gene_coordinates.py`, `scripts/77_cis_effect_report.py` | Input vivi: K562 a singola cellula, coordinate geniche, coppie cis | Colab / locale |
| `scripts/30_new_checkpoint.py`, `scripts/31_check_docs.py` | Checkpoint nuovo; controllo strutturale della documentazione | locale |

Gli stadi 82/84 conservano un metodo storico approssimato: CP-0050 smentisce la conversione
esatta dei grezzi aggregati, anche entro la famiglia originaria. Leggere [R-022](REGISTRO.md#r-022--ancore-aggregate-e-indipendenza-della-conferma).
Per il risultato ufficiale usare i sei scalati pubblicati; per nuovi banchi vale R-LEAD P2.

## 5. Aggiungere e togliere codice

- **Uno stadio nuovo** segue le regole di `scripts/CLAUDE.md` ed entra nella tabella del §4, e i
  moduli che importa nella mappa di `src/vcc2026/CLAUDE.md`, nello stesso commit.
- **Un esperimento chiuso** dal suo checkpoint lascia nel percorso vivo solo gli stadi che
  servono ancora. Gli altri si archiviano lo stesso giorno (D-040):
  1. un tag annotato `archivio/<motivo>-<data>` sul commit che ha ancora i file;
  2. una sezione datata in [ARCHIVIO.md](ARCHIVIO.md), con percorso, righe e prima riga del
     docstring;
  3. `git rm`;
  4. il controllo documentale e i test.
- **Prima di chiudere una sessione:** i due controlli di [CLAUDE.md](../CLAUDE.md), «Before you
  finish».

## 6. Dove stanno le cose

| Che cosa | Dove |
|---|---|
| Controlli ufficiali A/B/C, asse genico, pannello | `C:/Users/ferra/vcc2026-data/raw/controls/` |
| Cache delle sorgenti (stadio 98) | `C:/Users/ferra/vcc2026-data/processed/multisource_<data>_<run>/` |
| Effetti per contesto (stadio 100) | `C:/Users/ferra/vcc2026-data/processed/effects_tNN_<data>/` |
| La ricetta usata da un invio | nel `manifest.json` dello stadio 100, per intero. `recipe_sha256_lf` vale su ogni checkout (esecuzioni dopo il 24 settembre). `recipe_sha256` è l'hash dei byte: LF per t08–t12, CRLF per t15–t17 (D-043) |
| Previsioni e pacchetti | `C:/Users/ferra/vcc2026-data/artifacts/<run>/` |
| Codice, coda e log di Colab | `G:\Il mio Drive\vcc2026\` (`code/`, `runs/queue/`, `runs/jobs/`); non è la cartella `runs/` della base di lancio degli agenti ([AGENTI](AGENTI.md)) |
| Report, uno per esperimento | `reports/<categoria>/<tema>_<data>/` (D-046), ciascuno con una riga nel README della categoria e in [REGISTRO.md](REGISTRO.md); la mappa è [reports/README.md](../reports/README.md) |

## 7. Il set finale (22 ottobre)

Il 22 ottobre arrivano tre contesti nuovi, D, E ed F, con i soli controlli, e 300 bersagli
nuovi. Le sottomissioni chiudono il 5 novembre, e la classifica finale dipende solo da questo
set. Il percorso è quello del §1, rieseguito su bersagli e contesti nuovi.

Questo è il percorso della **baseline di trasferimento dello stesso bersaglio**.
La ricerca per il finale segue anche D-044 e
[GENERALIZZAZIONE.md](GENERALIZZAZIONE.md): non richiede overlap dei bersagli
dei dataset con il pannello attuale. Un bersaglio nuovo per la gara può essere
già misurato nelle sorgenti pubbliche oppure essere nuovo anche per il training;
le due condizioni si valutano e si riportano separatamente. I filtri `--targets-csv`
degli stadi di produzione non sono criteri generali di acquisizione dei dati.

**Già pronto (verificato il 24 settembre):**
- lo stadio 45 accetta `--controls-dir` e `--contexts`. Due piloti su A, con e senza
  l'opzione, danno matrici identiche;
- lo stadio 99 accetta `--contexts`. Rieseguito su A/B/C riproduce identico
  `reports/gara/context_fingerprints_2026-09-22/fingerprints.json`, date a parte;
- gli stadi 76, 83 e 85 accettano `--controls-dir` e `--contexts`;
- gli stadi 97, 98, 100, 102 e 106 accettano `--targets-csv`; 45, 98, 100 e 106 leggono il pannello
  per nome di colonna (`vcc2026.panel`, dal 29/09), 97 e 102 ancora per posizione;
- lo stadio 48 accetta `--genes`, `--perts` e, dal 29/09, `--contexts` (difetto D1 della prova generale);
- lo stadio 100 accetta `--contexts`, verifica che la cache sia del pannello letto e registra nel manifest
  bersagli, cache e risorse (difetti D3, D4, D11); lo stadio 45 non marca più come pilota una corsa D/E/F
  a forma piena (D5).

**Il giorno del rilascio, in ordine** (provato il 29/09 sulla prova generale,
[CP-0044](checkpoints/0044-prova-generale-22-ottobre.md); i comandi esatti sono in
`reports/invii/prova_generale_2026-09-28/comandi.ps1`):
1. Il bundle nuovo va in una cartella sua, per esempio `raw/controls_final/`: i controlli di
   A/B/C non si toccano.
2. Identità dei contesti: stadi 85 e 99 con `--controls-dir`, `--contexts D E F` e un `--out`
   **nella radice dati**, mai sotto `reports/`: le impronte possono rivelare le linee.
3. CPM dei controlli di D/E/F sull'asse, per le ricette che li leggono (soglia d'espressione,
   `match_detectable`): `reports/invii/prova_generale_2026-09-28/cpm_contesti.py`, che scrive la
   stessa definizione di `interim/basal_cpm_by_context.csv` (media dei CPM per cellula).
4. Cache delle sorgenti per il pannello nuovo **dagli universi**, con lo stadio 106
   (`--preset me1 --targets-csv <bundle>/pert_counts.csv`): circa 100–200 s e meno di 300 MiB
   per il pannello di oggi. Scrive `manifest.json` con lo sha256 dei bersagli. Gli stadi 97,
   102 e 98 servono solo per sorgenti che non hanno un universo.
5. Stadio 100 con la ricetta scelta, riscritta con le chiavi D, E, F e nient'altro di diverso,
   con `--targets-csv` del bundle e `--contexts D,E,F`. Rifiuta una cache costruita per un altro
   pannello e una ricetta con contesti diversi. Il riferimento tolto da γ = 1 cambia con il
   pannello (per K562, coseno 0,59 fra pannello finto e pannello di oggi): la chiave
   `"common"` della ricetta lo può fissare, e la scelta va scritta prima.
6. Cellule con lo stadio 45 (`--controls-dir`, `--contexts D,E,F`) o 76 (`--contexts D E F`,
   separati da spazi); pacchetto con lo stadio 48 (`--genes`, `--perts` del bundle,
   `--contexts D,E,F`), invio.

**Da controllare quel giorno, perché oggi non si può sapere:**
- **I contesti obbligatori.** Lo stadio 48 li prende dalla CLI `vcc` installata
  (`prep.REQUIRED_CONTEXTS`, oggi A/B/C) se non gli si passa `--contexts`. Se gli organizzatori
  rilasciano una CLI nuova, va installata prima di impacchettare.
- **Il formato del bundle:** nomi dei file e colonne di `pert_counts.csv`.
- **L'asse genico.** Gli stadi controllano che l'ordine dei geni coincida con
  `gene_names.csv`, e si fermano se non coincide.
- **Il disco.** Ogni candidato arriva a circa 13 GB di picco (generazione più
  impacchettamento, misurati su t11, t14 e t15), ma le riserve degli stadi 45 e 48 chiedono
  circa 17 GB liberi per partire a forma piena.
