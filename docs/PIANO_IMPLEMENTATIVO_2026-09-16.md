# Workflow 1 — Implementazione: verso un candidato competitivo

**Data:** 16 settembre 2026, redatto alle 13:30 (ora italiana). Aggiornato alle 16:49 con
[CP-0018](checkpoints/0018-drive-storage-confermato.md) (I-5, I-6, §8): i grezzi pesanti
sono già su Drive e si collegano, non si scaricano.
**Responsabile:** lead scientist (agente Claude, Opus 5).
**Stato:** proposta da approvare. Nessun incarico è avviato da questa pagina: gli
agenti li avvia e li supervisiona il team.
**Parallelo:** [Workflow 2 — Comprensione](PIANO_COMPRENSIONE_2026-09-16.md), gestito
dai ricercatori.
**Orologio della gara:** la quota di due sottomissioni si azzera alle **02:00 italiane**
(mezzanotte UTC). Set finale il 22 ottobre, chiusura il 5 novembre.

Le scadenze sono volutamente strette. Un incarico che non ci sta non si allunga in
silenzio: si segnala con la prova del blocco e si passa all'alternativa scritta qui.

## 1. Dove sono i punti

Fotografia delle 13:31 in `reports/leaderboard_2026-09-16/`.

- **Misura.** Siamo 493° su circa 990 squadre con 0,0459 e **una** sottomissione. Le
  prime dieci stanno fra 0,225 e 0,292, con 17–53 sottomissioni ciascuna. La pagina
  ordina per sottomissione **più recente**, non per la migliore.
- **Interpretazione (stima delle ancore, non ufficiale).** Rispetto alla mediana delle
  prime dieci perdiamo, in punti del punteggio complessivo: **PDS 0,058, MSE 0,042,
  REACH 0,035, FID 0,032, NMAE 0,023**, JAC 0,002. Nessuno fra i primi dieci si stacca
  da zero su JAC; su FID noi siamo gli unici **sotto** zero (−0,18).
- **Misura (sorgente dello scorer installato, `cell_eval2` 0.16.0).** Il gene bersaglio
  è escluso da **tutte** le metriche: da PDS per l'intero pannello (`config.py`,
  `exclusion_scope: panel`), da MSE e dalle metriche DE riga per riga
  (`metrics/delta.py`, `_exclusion_cols`). Il knockdown del bersaglio non vale punti:
  i punti vengono dagli effetti a valle. La versione del server non è verificata.
- **Misura.** Le cellule per perturbazione sono fissate a 400
  (`docs/SOTTOMISSIONE.md` §1): non sono una leva.
- **Ipotesi da mettere alla prova oggi.**
  1. FID negativa e MSE grezza sopra la media del contesto (1,231 contro b ≈ 0,986)
     vengono in buona parte dal **generatore**: a effetto previsto zero produce il
     4–6% di geni rilevati in più dei controlli reali
     (`reports/trial_2026-09-12/q01pilot_generation_diagnostics.json`), e su HepG2 il
     predittore nullo con il generatore attuale ha MSE normalizzata grezza 1,154
     (`reports/hepg2_2026-09-14/generator_x_predictor.json`).
  2. Alla previsione manca la **risposta comune** a tutte le perturbazioni, che la
     media del contesto (il punto 0) possiede per costruzione. Trasferirla con
     un'ampiezza propria, separata da quella della parte specifica, dovrebbe muovere
     MSE e NMAE.
  3. PDS è invariante di scala ma non di rumore: la firma K562 ha effetti mediani più
     piccoli del proprio errore standard (`reports/pipeline/signature_qc.json`).
     Ripulire la parte specifica dovrebbe alzare PDS. E la sola sorgente usata,
     K562 genome-wide, copre 272 bersagli su 300
     ([CP-0004](checkpoints/0004-primo-trial-locale-e-pacchetti.md)): gli altri
     ricevono effetto zero e non discriminano.

## 2. Decisioni del proprietario che sbloccano la giornata — entro le 14:15

| ID | Decisione | Perché serve oggi |
|---|---|---|
| O1 | Autorizzare **due sottomissioni diagnostiche al giorno** da oggi, ciascuna con **un solo fattore** cambiato rispetto alla precedente, dichiarate esplorative | È l'unica misura sui contesti A/B/C e sulle sei metriche vere. D-032 prevede questa eccezione. Il rango visibile seguirà l'ultima sottomissione |
| O2 | Scrivere a help@virtualcellchallenge.org: ricampionamento dei controlli (D-017), generatore che parte da cellule di controllo reali, licenza Orion | Fino alla risposta si inviano solo generatori parametrici. Il messaggio lo invia il proprietario |
| O3 | Confermare **prima** dei run le regole di accettazione scritte in §4 | CP-0017 ha girato con `owner_confirmed: false`: da non ripetere |
| O4 | Consenso a versionare il lavoro di CP-0017, oggi non committato, e a eliminare il file spurio `, remote ingestion and scientific plans…` nella radice (è la schermata d'aiuto di `less`, 16 KB) | Gli incarichi paralleli lavorano su checkout separati: senza un commit non vedono gate, presenza e script 69–70 |
| O5 | Riaprire in parte D-031: nel breve periodo la **copertura del pannello** viene prima della diversità di contesto | Vedi I-5. I pannelli essential coprono 0/300 bersagli (misura); se il pannello finale segue lo stesso criterio (ipotesi), lo coprono solo gli schermi genome-wide |

## 3. Barriera 0 — 14:00–14:30, un solo integratore

- Test e controllo documentale, poi commit del lavoro di CP-0017 (dopo O4).
- RAM: alle 13:31 erano disponibili **0,69 GiB** su 7,81. Chiudere applicazioni fino
  ad almeno 2 GiB liberi prima di generare in locale; altrimenti la generazione va su
  Colab.
- Un checkout o worktree per incarico; ogni incarico scrive in una propria cartella
  `reports/<tema>_2026-09-16/` con run id univoco. Mappa, registro e decisioni li
  aggiorna solo l'integratore.
- Il seed di conferma 4242 resta chiuso (D-032).

## 4. Incarichi paralleli

Le regole di accettazione sono scritte qui, prima dei risultati (O3). Colonna
«Metrica»: il divario di §1 che l'incarico attacca.

| ID | Incarico | Consegna e scadenza | Dipende da | Regola di accettazione / arresto | Metrica |
|---|---|---|---|---|---|
| I-1 | **Ancore stimate come strumento.** Script numerato che stima `b` e `r` per metrica da righe di classifica e converte metriche grezze locali in scala `val` indicativa | Script con test e tabella, **15:00** | — | Riproduce entro 0,002 le righe di `reports/leaderboard_2026-09-16/rows.csv`; ogni uscita porta la scritta «indicativo, ancore val» | tutte |
| I-2 | **Generatore: calibrazione a effetto zero** sui controlli ufficiali, con due metà disgiunte (modello e riferimento). G0 attuale; G1 Gamma-Poisson con dispersione stimata sui controlli (scalare già in `src/vcc2026/sampling.py`, per gene da aggiungere); G2 = G1 con profondità e rilevazione appaiate; G3 ancorato a cellule reali **solo diagnostico** (O2). Base: `scripts/42_null_calibration.py` | Tabella: DE spuri per pseudo-perturbazione, sei metriche a nullo, varianza per strato di espressione, **16:00** | Barriera 0 | Vince il generatore più vicino al reale-contro-reale (`reports/pipeline/null_calibration_A.json`) con varianza entro ±10% di quella reale per strato. Nessun guadagno ottenuto gonfiando la dispersione | FID, MSE, REACH |
| I-3 | **Predittore sul banco a tre contesti** (solo seed 2026 e 2027): P1 trasferimento scomposto, risposta comune + parte specifica con due ampiezze calibrate sulla coppia interna; P2 parte specifica ripulita (soglia sullo z o proiezione a rango {8, 16}). Protocollo `configs/benchmark_3ctx.yaml` | Tabella MSE/nullo più una proxy di discriminazione coseno dichiarata prima del run, **17:00** | Barriera 0 | Passa a I-7 solo ciò che batte ShrunkTransfer (IC95 appaiato senza zero) in almeno 2 fold su 3 con entrambi i seed, senza peggiorare la proxy di discriminazione | MSE, NMAE, PDS |
| I-4 | **Effetto cis della CRISPRi: prima misurare.** Nei dati K562, RPE1 e HepG2, variazione dei geni con TSS vicino al bersaglio (0–1, 1–10, 10–100 kb) contro geni a distanza abbinata. Annotazione genomica piccola, con manifest e sha256, nel data root | Curva effetto-distanza con IC per contesto, **17:00** | — | Si implementa solo se l'effetto vicino è coerente nei tre contesti. I vicini che sono bersagli del pannello non contano: lo scorer li esclude | PDS, REACH |
| I-5 | **Copertura del pannello, audit senza download pesanti.** Orion completo (tutti i batch: cellule per bersaglio, byte, licenza), CD4 genome-wide (esistono pseudobulk o tabelle DE di dimensione gestibile?), K562 genome-wide a singola cellula (61,3 GiB, già in `configs/remote_catalog.yaml`; qui c'era «65,8 GiB», un errore di unità. Dal 16 settembre la copia è su Drive: l'audit apre `obs` sulla copia, senza download, CP-0018), H1 2025. Pannello in `configs/orchestrator/briefs/materiali/vcc2026-panel-2026-09-15.csv` | Tabella sorgente × bersagli con ≥30 cellule, byte, licenza, conteggi grezzi sì/no; proposta per O5, **17:00** | — | Nessuna copertura dichiarata senza un file letto. GEO, Zenodo e mirror dello stesso studio contano come una sorgente | PDS |
| I-6 | **Runtime remoto.** GPU del compagno (dichiarata non disponibile fino a oggi): `scripts/59_gpu_readiness.py` e backend DE risolto. Colab con Drive montato: ~~avvio del fetch~~ **collegamento** del K562 genome-wide a singola cellula se I-5 lo conferma. *Aggiornamento delle 16:49 (CP-0018):* la copia è già su Drive, quindi niente fetch. Servono il percorso atteso (`<VCC2026_DATA_ROOT>/raw/replogle/`), `FETCH_BLOCKS = []` e la verifica dell'md5, che rilegge l'intero file in un tempo non misurato | Preflight **15:00**; fetch avviato **16:30**, prosegue la notte. Dopo CP-0018: collegamento e md5 al posto del fetch | I-5 per il fetch | Se `de_backend_resolved` resta `scanpy`, la GPU non sta lavorando. Nessun file grande sul disco effimero senza persistenza verificata. Nessun download di un blocco già su Drive, e nessun uso della copia prima che il suo md5 coincida con il catalogo | infrastruttura |
| I-7 | **Banco HepG2 a sei metriche, seconda versione.** Predittore {nullo, ShrunkTransfer, migliore di I-3} × generatore {G0, vincitore di I-2}, un fattore alla volta, più di 25 bersagli se le cellule bastano, backend registrato. Base: `scripts/57_generator_x_predictor.py` | Tabella grezza più la conversione indicativa di I-1, **18:30** | I-1, I-2, I-3 | Stessi controlli reali e stessi bersagli in ogni braccio (D-027). Nessuna normalizzazione presentata come punteggio di gara | tutte |
| I-8 | **trial-02 = trial-01 con il solo generatore di I-2.** Genera (`scripts/45_generate_prediction.py`), impacchetta (`scripts/48_package_prediction.py`), convalida (`scripts/46_validate_package.py`), **invio n. 1** | Invio entro **17:30**, punteggio letto entro **18:30** | I-2, O1 | Si invia se la convalida passa e I-2 ha un vincitore. Lettura metrica per metrica contro trial-01. Costi misurati per trial-01: generazione 19 min (`reports/trial_2026-09-12/resources.json`), packaging 17 min, invio e lettura del punteggio 33 min | FID, MSE |
| I-9 | **trial-03 = trial-02 con il predittore promosso** da I-3 e I-7. In alternativa, trial-02 con il prior cis se I-4 lo giustifica | **Invio n. 2 entro le 23:30** | I-7 o I-4, esito di I-8 | Se nulla è promosso, la seconda quota non si usa: un invio senza domanda non misura niente | MSE, NMAE, PDS |
| I-10 | **State, fattibilità a tempo:** pesi pubblici, licenza, input richiesti, previsione su un contesto senza perturbazioni osservate, costo su GPU. PRiMeFlow resta in attesa (`reports/primeflow_2026-09-15/primeflow_feasibility.md`) | Via libera o no, **17:00** | — | Oggi nessun porting. Un via libera richiede pesi scaricabili e un compito compatibile con il protocollo congelato | PDS, MSE |

## 5. Punti di sincronizzazione

| Ora | Chi consegna | Cosa si decide |
|---|---|---|
| 15:00 | I-1, preflight di I-6 | Scala indicativa disponibile; dove gira la generazione |
| 16:00 | I-2 | Generatore di trial-02; parte I-8 |
| 17:00 | I-3, I-4, I-5, I-10 | Cosa entra in I-7 e I-9; proposta O5; eventuale via libera a State |
| 18:30 | I-7, punteggio di trial-02 | Il generatore resta o si torna indietro; contenuto di trial-03 |
| 21:00 | Review del lead | Checkpoint se un'ipotesi di §1 è confermata o smentita; proposte D-034 (generatore) e D-035 (sottomissioni diagnostiche) |
| 23:30 | I-9 | Invio n. 2; durante la notte solo fetch e job lunghi con checkpoint |

Formato di consegna al lead: quello di [REGIA_PARALLELA_2026-09-15.md](REGIA_PARALLELA_2026-09-15.md) §4.

## 6. Obiettivi di spinta

Sono traguardi per dare il ritmo, **non previsioni**: la classifica si muove e nessuna
misura ci garantisce questi numeri.

| Data | Traguardo |
|---|---|
| 16 settembre | ≥ 0,10, con FID ≥ 0 e MSE sopra 0 |
| 18 settembre | ≥ 0,15; sorgente di copertura scelta e ingestione avviata; ≥ 290/300 bersagli con una previsione non nulla |
| 22 settembre | ≥ 0,22, il livello attuale della top-10 |
| 30 settembre | ≥ 0,27; metodo congelato per la conferma sul seed 4242 |

Vincoli che valgono sempre: il pannello finale è nuovo, quindi ogni scelta deve valere
per un bersaglio qualunque; niente messo a punto sul singolo bersaglio di `val`. Ogni
sottomissione consultata per scegliere trasforma `val` in dato di sviluppo: la sola
conferma vera resta il set del 22 ottobre.

## 7. Cosa studiare oggi, per chi implementa

1. Nel pacchetto installato (`C:/Users/ferra/vcc2026-data/.venv/Lib/site-packages/cell_eval2/`):
   `metrics/delta.py` (MSE corretta per il campionamento, e quanto dipende dalla
   dispersione delle cellule previste), `de.py` (Wilcoxon, FDR per perturbazione,
   filtro a 5 CPM), `baseline.py` (la risposta media che fa da punto 0).
2. [CP-0004](checkpoints/0004-primo-trial-locale-e-pacchetti.md) §3.8 e
   [CP-0006](checkpoints/0006-prima-sottomissione-e-punteggio.md) §4: l'artefatto del
   generatore e le due ipotesi sul punteggio.
3. [CP-0013](checkpoints/0013-hepg2-terzo-contesto.md) e D-027: generatore e
   predittore muovono metriche diverse.
4. R-2 di [ROADMAP.md](ROADMAP.md): l'ampiezza scelta sulla MSE proxy non è per forza
   la migliore sulle sei metriche, e NMAE premia l'ampiezza giusta sui geni forti.

## 8. Cosa non fare oggi

- Non modellare il knockdown del bersaglio: lo scorer lo esclude ovunque.
- Non cambiare due fattori nella stessa sottomissione.
- Non aprire il seed 4242; non riaprire GO slim, rango o gate senza un'ipotesi nuova
  (D-028, D-030, D-033).
- Non scaricare RDS o atlanti sul portatile (D-005); non lasciare file grandi su un
  disco remoto effimero.
- Non riscaricare i due grezzi già su Drive, e non lanciare il notebook remoto con
  `FETCH_BLOCKS = None`: secondo il codice, letto e non provato, la selezione salterebbe
  le copie presenti e scaricherebbe il blocco successivo (CP-0018).
- Non inviare `trial-00-controls` né un generatore ancorato a cellule reali prima di O2.

## 9. Chiusura

Checkpoint solo se un'ipotesi di §1 viene confermata o smentita, o se O1 o O5 cambiano
la strategia. Poi mappa, registro e decisioni a cura dell'integratore, e le due
verifiche di `CLAUDE.md`. Il training, se parte, deve avere checkpoint persistente,
comando di ripresa e valutazione successiva già pronta.
