# Come si lavora — il percorso vivo

Scritto il 2026-09-23, con la pulizia di [D-040](DECISIONI.md#d-040--il-codice-vivo-è-solo-quello-che-produce-o-valuta-una-sottomissione).
Questo è l'unico documento operativo. Dice:
- che cosa gira e in che ordine;
- con quali comandi;
- dove finiscono i risultati.

I numeri e le incertezze stanno in [PROGETTO.md](PROGETTO.md), il perché delle scelte in
[DECISIONI.md](DECISIONI.md). Il contratto del formato è in [SOTTOMISSIONE.md](SOTTOMISSIONE.md)
§1–2; per i comandi vale questa pagina.

Tutto il codice che non compare qui è archiviato ([ARCHIVIO.md](ARCHIVIO.md)). Se ti serve,
riprendilo dal tag: non riscriverlo.

## 1. Il percorso di un invio

È il percorso del t08, del t10 e del t11. Cambiano solo la ricetta e la cache delle sorgenti.

```
sorgenti: bulk K562 · 97 CD4 · 102 Orion ──▶ 98  cache degli effetti per sorgente
ricetta configs/recipes/tNN.json ──────────▶ 100 effetti per contesto (effects_A/B/C.npz)
                                          ──▶ 45  cellule: generatore di trial-01 (trial-ext-profile)
                                              76  in alternativa ControlModel (§3)
                                          ──▶ 48  convalida a flusso + .vcc + verifica bit per bit
previsione e testi scritti PRIMA ─────────▶ vcc submit ──▶ vcc status ──▶ checkpoint
```

I comandi, con i percorsi usati per il t11:

```powershell
$D = "C:\Users\ferra\vcc2026-data"
# effetti per contesto, dalla ricetta e dalla cache dello stadio 98
.\scripts\py.cmd scripts\100_build_context_effects.py --recipe configs\recipes\t11.json `
    --cache $D\processed\multisource_2026-09-23_r4 --out $D\processed\effects_t11_2026-09-23
# cellule: generatore di trial-01, seme predefinito di trial-01
.\scripts\py.cmd scripts\45_generate_prediction.py --run-id t11gen --trial trial-ext-profile `
    --effects A=$D\processed\effects_t11_2026-09-23\effects_A.npz `
    --effects B=$D\processed\effects_t11_2026-09-23\effects_B.npz `
    --effects C=$D\processed\effects_t11_2026-09-23\effects_C.npz
# pacchetto: 24 controlli ufficiali, contenitore, payload identico all'input
.\scripts\py.cmd scripts\48_package_prediction.py --run-id t11pack --prediction $D\artifacts\t11gen\prediction.h5ad
# invio (consuma quota: vedi §2)
.\scripts\vcc.cmd submit $D\artifacts\t11pack_r2\prediction.vcc -m "<nome>" -d "<descrizione>"
.\scripts\vcc.cmd --json status <entry_id>
```

I manifest di ogni stadio stanno accanto all'output (`manifest.json`); quelli degli invii si
copiano in `reports/trial_<data>/`, come `t11_manifest_45.json` e `t11_manifest_48.json`.

## 2. Le regole dell'invio

Ognuna è costata qualcosa. Le date sono quelle in cui è stata pagata.

1. **Prima di generare**, si registrano la previsione e la regola di lettura in
   `reports/prediction_tNN_<data>/prediction.json`:
   - una banda numerica;
   - che cosa si concluderà in ciascun caso.

   Anche i testi della sottomissione si scrivono prima, in
   `reports/trial_<data>/submission_texts.md`. La soglia non si sposta dopo aver visto il
   numero ([CP-0030](checkpoints/0030-t10-attribuzione-cd4.md)).
2. **Un fattore alla volta** rispetto al migliore. È ciò che ha reso leggibili t08, t10 e
   t11.
3. **L'invio consuma quota:** 2 al giorno, uno solo in volo per squadra. Serve
   l'autorizzazione del proprietario, data in chat. Quelle già ricevute sono trascritte in
   `reports/trial_2026-09-22/autorizzazioni.md`: leggile, ma un agente nuovo le conferma
   in chat prima di usarle.
4. **Un lavoro pesante alla volta.** Il 23 settembre tre lavori insieme hanno riempito il
   disco durante l'impacchettamento: generare e impacchettare chiede circa 12 GB liberi.
   Controlla con `df -h /c` prima di partire.
5. **Il portatile non deve andare in sospensione durante l'upload.** Il 23 settembre il
   sonno ha interrotto il secondo tentativo del t11 (`reports/trial_2026-09-23/`).
   - **Un upload interrotto lascia l'entry sul server** in stato `uploading`. Occupa lo slot
     della squadra, anche se `vcc whoami` può dire `can_submit: true`.
   - La CLI tiene l'upload in `~/.config/vcc/state.json`, alla voce `pending_uploads`.
     `vcc submit --resume <entry>` lo riprende sullo stesso file; controlla prima lo sha256
     del `.vcc` contro il report dello stadio 48.
   - `vcc cancel <entry>` abbandona l'entry, e non conta sul limite giornaliero: conta solo
     un invio valutato (`vcc cancel --help`).
6. **L'output di `vcc` si salva così com'è**, in `reports/trial_<data>/`
   (`submit_<entry>.json`, `status_<entry>.json`). Un tentativo fallito si registra come
   tale, in un file suo.
7. **Dopo il punteggio:**
   - `comparison.json` accanto alla previsione;
   - un checkpoint (`python scripts/30_new_checkpoint.py`);
   - la mappa aggiornata.

   I grezzi si convertono negli scalati con le ancore in `reports/anchors_2026-09-17/`.

## 3. Colab: generatore `ControlModel` e banchi

Il portatile ha 7,8 GiB di RAM. Lo stadio 76 (`ControlModel`) gira anche qui: il 23 settembre
ha generato il t14 in 35 minuti, con 1–3 GiB di RAM
(`reports/dispersion_2026-09-23/T14_IN_LOCALE.md`). I banchi 73 e 75 restano su Colab. Il notebook `notebooks/colab_sc_training.ipynb` fa da dispatcher: esegue i `.sh`
depositati in `G:\Il mio Drive\vcc2026\runs\queue\`.

- **Portare il codice su Drive:** `powershell -File notebooks\colab_jobs\sync_to_drive.ps1`.
  Fa un mirror (`robocopy /MIR`) di `src`, `scripts`, `configs` e `notebooks` in `code/`:
  quello che non c'è in locale sparisce anche da Drive. Ogni job ne copia una versione
  privata alla partenza, e `code/SYNC_STAMP.txt` dice da quale commit.
- **Mettere in coda:** `bash notebooks/colab_jobs/queue_trial.sh <NNN_nome> <TRIAL> "<GEN_ARGS>" [<file da attendere>]`
  scrive `runs/queue/<NNN_nome>.sh` e rifiuta di sovrascrivere. Per catene di job si attende
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
  Di notte, senza nessuno al browser, il tier gratuito scollega la sessione.
- **Memoria:** due banchi HepG2 insieme, o un banco HepG2 con uno K562, possono esaurire i
  12 GB del runtime (`rc=137`). Per due job `ControlModel` insieme il job 045 annota lo
  stesso rischio, e per questo aspetta il `.done` del 044.

## 4. Gli stadi vivi

Ventitré script. Ogni altro numero è nel tag d'archivio. Il prossimo numero libero è **104**.

| Stadio | Che cosa fa | Dove gira |
|---|---|---|
| `scripts/97_extract_cd4_rows.py` | Righe pseudobulk CD4 dei bersagli del pannello, per intervalli di byte da S3 | locale |
| `scripts/102_extract_orion_panel.py` | Pseudobulk Orion (HCT116, HEK293T) per lotto GEM; `--finalize` produce l'h5ad | locale |
| `scripts/98_multisource_effects.py` | Effetti per sorgente sull'asse ufficiale e proxy di trasferimento fra sorgenti | locale |
| `scripts/101_transfer_diagnostics.py` | Tre diagnostiche del trasferimento fra sorgenti dello stadio 98 | locale |
| `scripts/103_direction_transfer.py` | Accordo di segno fra sorgenti sui geni che si chiamerebbero, una sorgente tenuta fuori alla volta | locale |
| `scripts/100_build_context_effects.py` | Effetti per contesto da una ricetta di `configs/recipes/` | locale |
| `scripts/45_generate_prediction.py` | Cellule con il generatore di trial-01 (`--trial trial-ext-profile --effects ...`) | locale |
| `scripts/76_generate_sc_prediction.py` | Cellule con `ControlModel` (e termini cis e di trasferimento) | locale o Colab |
| `scripts/48_package_prediction.py` | Convalida a flusso, `.vcc`, verifica del contenitore e del payload | locale o Colab |
| `scripts/83_prediction_calls.py` | Chiamate DE per bersaglio su una previsione, contro controlli veri | locale o Colab |
| `scripts/72_generator_null.py` | Chiamate spurie di un generatore a effetto nullo | locale o Colab |
| `scripts/73_bench_k562_panel.py`, `scripts/75_bench_hepg2_transfer.py` | Banchi a sei metriche su cellule perturbate vere (K562, HepG2) | Colab |
| `scripts/79_fast_de_parity.py` | Parità del DE veloce con il percorso scanpy dello scorer (D-037) | locale |
| `scripts/82_solve_anchors.py`, `scripts/84_predict_official.py` | Ancore dagli status ufficiali; punteggio atteso di un braccio di banco | locale |
| `scripts/85_identify_contexts.py`, `scripts/99_context_fingerprints.py` | Che cellule sono i contesti: marcatori, saggio, impronte genetiche | locale |
| `scripts/71_extract_k562_sc.py`, `scripts/74_fetch_gene_coordinates.py`, `scripts/77_cis_effect_report.py` | Input vivi: K562 a singola cellula, coordinate geniche, coppie cis | Colab / locale |
| `scripts/30_new_checkpoint.py`, `scripts/31_check_docs.py` | Checkpoint nuovo; controllo strutturale della documentazione | locale |

Lo stadio 84 vale per la famiglia di modelli su cui è stato tarato, non per una famiglia
nuova ([CP-0027](checkpoints/0027-t07-punteggio-ufficiale.md)).

## 5. Aggiungere e togliere codice

- **Uno stadio nuovo:**
  - continua la numerazione e fa una cosa sola;
  - ha un docstring con l'esempio d'uso;
  - scrive in un `--out` nuovo e non sovrascrive mai un output;
  - porta un test se sbagliare in silenzio è possibile.
- **Un esperimento chiuso** dal suo checkpoint lascia nel percorso vivo solo gli stadi che
  servono ancora. Gli altri si archiviano lo stesso giorno (D-040):
  1. un tag annotato `archivio/<motivo>-<data>` sul commit che ha ancora i file;
  2. una sezione datata in [ARCHIVIO.md](ARCHIVIO.md), con percorso, righe e prima riga del
     docstring;
  3. `git rm`;
  4. il controllo documentale e i test.
- **Prima di chiudere una sessione:**
  - `python scripts/31_check_docs.py`;
  - `.\scripts\py.cmd -m unittest discover -s tests` (157 test, circa 5 minuti).

## 6. Dove stanno le cose

| Che cosa | Dove |
|---|---|
| Controlli ufficiali A/B/C, asse genico, pannello | `C:/Users/ferra/vcc2026-data/raw/controls/` |
| Cache delle sorgenti (stadio 98) | `C:/Users/ferra/vcc2026-data/processed/multisource_<data>_<run>/` |
| Effetti per contesto (stadio 100) | `C:/Users/ferra/vcc2026-data/processed/effects_tNN_<data>/` |
| La ricetta usata da un invio | nel `manifest.json` dello stadio 100, per intero. `recipe_sha256_lf` vale su ogni checkout (esecuzioni dopo il 24 settembre). `recipe_sha256` è l'hash dei byte: LF per t08–t12, CRLF per t15–t17 (D-043) |
| Previsioni e pacchetti | `C:/Users/ferra/vcc2026-data/artifacts/<run>/` |
| Codice, coda e log di Colab | `G:\Il mio Drive\vcc2026\` (`code/`, `runs/queue/`, `runs/jobs/`) |
| Report, uno per esperimento | `reports/<tema>_<data>/`, ciascuno con una riga in [REGISTRO.md](REGISTRO.md) |

## 7. Il set finale (22 ottobre)

Il 22 ottobre arrivano tre contesti nuovi, D, E ed F, con i soli controlli, e 300 bersagli
nuovi. Le sottomissioni chiudono il 5 novembre, e la classifica finale dipende solo da questo
set. Il percorso è quello del §1, rieseguito su bersagli e contesti nuovi.

**Già pronto (verificato il 24 settembre):**
- lo stadio 45 accetta `--controls-dir` e `--contexts`. Due piloti su A, con e senza
  l'opzione, danno matrici identiche;
- lo stadio 99 accetta `--contexts`. Rieseguito su A/B/C riproduce identico
  `reports/context_fingerprints_2026-09-22/fingerprints.json`, date a parte;
- gli stadi 76, 83 e 85 accettano `--controls-dir` e `--contexts`;
- gli stadi 97, 98, 100 e 102 accettano `--targets-csv`;
- lo stadio 48 accetta `--genes` e `--perts`.

**Il giorno del rilascio, in ordine:**
1. Il bundle nuovo va in una cartella sua, per esempio `raw/controls_final/`: i controlli di
   A/B/C non si toccano.
2. Identità dei contesti: stadi 85 e 99 con `--controls-dir` e `--contexts D E F`.
3. Sorgenti per i bersagli nuovi, con il `pert_counts.csv` del bundle come `--targets-csv`:
   - K562 si legge dal bulk locale, che ha tutto il genoma;
   - lo stadio 97 per CD4 ha letto 1,33 GiB in 880 s per 300 bersagli (CP-0028);
   - lo stadio 102 per Orion legge per intero tutti i file, 109 per HCT116 e 223 per
     HEK293T, qualunque sia il pannello: alcune ore per linea, da far girare di notte.
4. Stadio 98 con le sorgenti nuove, poi stadio 100 con la ricetta scelta.
5. Cellule con lo stadio 45 o 76 (`--controls-dir`, `--contexts D,E,F`), pacchetto con lo
   stadio 48 (`--genes`, `--perts` del bundle), invio.

**Da controllare quel giorno, perché oggi non si può sapere:**
- **I contesti obbligatori.** Lo stadio 48 li prende dalla CLI `vcc` installata
  (`prep.REQUIRED_CONTEXTS`, oggi A/B/C). Se gli organizzatori rilasciano una CLI nuova, va
  installata prima di impacchettare.
- **Il formato del bundle:** nomi dei file e colonne di `pert_counts.csv`.
- **L'asse genico.** Gli stadi controllano che l'ordine dei geni coincida con
  `gene_names.csv`, e si fermano se non coincide.
- **Il disco.** Ogni candidato arriva a circa 13 GB di picco: generazione più
  impacchettamento, misurati su t11, t14 e t15.
