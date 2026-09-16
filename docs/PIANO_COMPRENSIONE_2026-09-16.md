# Workflow 2 — Comprensione: stato, esperimenti, criticità, studio

**Data:** 16 settembre 2026, redatto alle 13:30 (ora italiana). Aggiornato alle 16:49 con
[CP-0018](checkpoints/0018-drive-storage-confermato.md): i grezzi pesanti sono già su
Drive, C8 è declassata per l'ingestione (§3, §4, §8).
**Redatto da:** lead scientist (agente Claude, Opus 5). **Gestito da:** i ricercatori.
Il lead non lo supervisiona durante la giornata e lo riprende alla review delle 21:00.
**Stato:** proposta; nessun incarico è avviato da questa pagina.
**Parallelo:** [Workflow 1 — Implementazione](PIANO_IMPLEMENTATIVO_2026-09-16.md).

## 1. Obiettivo

Alle 21:00 ogni ricercatore sa spiegare, citando un file per ogni affermazione:

1. che cosa stiamo facendo e perché;
2. dove stanno i punti della gara, e perché oggi ne prendiamo pochi;
3. che cosa hanno detto gli esperimenti fatti, e che cosa **non** hanno detto;
4. quali criticità sono aperte in dati, ricerca, implementazione e infrastruttura;
5. quali meccanismi biologici e informatici decidono il punteggio.

Questo workflow non scrive codice di modello e non tocca configurazioni o report del
workflow 1. Produce comprensione verificata e righe da consegnare all'integratore.

## 2. Incarichi

| ID | Domanda | Consegna e scadenza | Alimenta |
|---|---|---|---|
| U-1 | **Stato in una pagina.** Dieci righe per area (dati, ricerca, implementazione, infrastruttura, governance), ciascuna con tipo di affermazione e percorso | Bozza **15:30**, partendo da §3 e verificandola | review 21:00 |
| U-2 | **Registro degli esperimenti.** Una riga per run: m001, m002/m004, g002, s001/s002, r001, x001, generatore × predittore HepG2, trial-01, parità remota HepG2, campagna Jiang. Colonne: domanda, regola fissata prima, esito, che cosa ha escluso, che cosa non poteva dire | **16:30** | U-7, review |
| U-3 | **Classifica.** Verificare le ancore stimate in `reports/leaderboard_2026-09-16/snapshot.md` su almeno 30 righe di pagine diverse, fondo compreso. Controllare se il modello lineare regge anche lontano dalla cima | **16:00** | I-1 del workflow 1 |
| U-4 | **Registro delle criticità.** Partire da §4: per ognuna proprietario, gravità, e la prova che la chiuderebbe | Bozza **17:00**, finale **20:30** | review 21:00 |
| U-5 | **Studio biologico** (§5): note brevi con fonti, separando ciò che è misurato qui da ciò che è letteratura | **18:30** | I-4, I-5 |
| U-6 | **Studio informatico** (§6), con lo stesso formato | **18:30** | I-2, I-7 |
| U-7 | **Controlli di comprensione:** le domande di §7 e le domande del §8 di CP-0006, CP-0013, CP-0016 e CP-0017 | **19:30** | review 21:00 |
| U-8 | **Contraddizioni e disallineamenti** da registrare, senza correggere i checkpoint (§8) | **19:30** | integratore |

Sincronizzazioni con il workflow 1: U-3 alle 16:00 verso I-1; B4 alle 17:00 verso I-5;
K1 e K2 alle 16:00 verso I-2; U-4 e U-7 alla review delle 21:00.

## 3. Stato per area — punto di partenza, da verificare

| Area | Stato | Tipo | Evidenza |
|---|---|---|---|
| Dati | Locali: K562 genome-wide in pseudobulk (272/300 bersagli del pannello), K562 e RPE1 essential, HepG2 Nadig a singola cellula (0/300) | misura | `reports/candidate_verification/coverage_summary.json`, [CP-0013](checkpoints/0013-hepg2-terzo-contesto.md) |
| Dati | Jurkat identificato (mirror 1,29 GB, 0/300), non scaricato. Jiang: solo metadati, RDS non aperti, copertura del pannello mancante | misura | [CP-0016](checkpoints/0016-piano-operativo-audit-protocollo.md), `reports/jiang_2026-09-15/` |
| Dati | CD4 rinviato (1,7 TB, 297/300 in libreria). Orion HCT116: 300/300 in libreria, ma nel solo Batch1 ne sono osservati 168, tutti sotto le 30 cellule; licenza da verificare. K562 a singola cellula: 65.830.941.948 byte, cioè 61,3 GiB (qui c'era «65,8 GiB», un errore di unità), catalogato, run Colab solo di piano. **Dal 16 settembre** una copia sta sul Google Drive del proprietario, insieme a HepG2: si collega, non si scarica | misura; copia su Drive: dichiarazione del proprietario, md5 non verificato | `reports/source_cards_2026-09-15/decisions.md`, `reports/remote_2026-09-15/COME_APRIRE.md`, [CP-0018](checkpoints/0018-drive-storage-confermato.md) |
| Dati | Controlli ufficiali: 18.400 × 18.533 per contesto; 8.409–8.923 geni sotto 5 CPM | misura | `reports/expression_gate_2026-09-16/context_presence.json` |
| Ricerca | Trasferimento calibrato: −1,0% di MSE pseudobulk sul nullo; in gara 0,046 con la sola PDS chiaramente positiva | misura | [CP-0004](checkpoints/0004-primo-trial-locale-e-pacchetti.md), [CP-0006](checkpoints/0006-prima-sottomissione-e-punteggio.md) |
| Ricerca | Esiti negativi o inconcludenti: architettura modulare, descrittore di contesto, GO slim, SVD randomizzata, rango oltre 16, gate di espressione. ShrunkTransfer resta il braccio da battere | misura | D-025, D-026, D-028, D-029, D-030, D-033 in [DECISIONI.md](DECISIONI.md) |
| Ricerca | Generatore e predittore muovono metriche diverse, talvolta in direzioni opposte | misura (25 bersagli, metriche grezze) | D-027, `reports/hepg2_2026-09-14/generator_x_predictor.json` |
| Implementazione | Percorso completo funzionante: generazione, packaging a 0,52 GiB, sottomissione accettata dal server | misura | [CP-0005](checkpoints/0005-packaging-streaming-trial01.md), [CP-0006](checkpoints/0006-prima-sottomissione-e-punteggio.md) |
| Implementazione | Modelli in NumPy, nessun ciclo di training; la GPU servirebbe oggi solo al backend DE dello scorer | misura | D-029, `reports/gpu_2026-09-15/gpu_readiness.json` |
| Implementazione | Ingestione remota: parità HepG2 e ripresa verificate; Jiang saltato per il disco. Orchestratore: DeepSeek risponde, Kimi va in timeout | misura | `reports/remote_2026-09-15/`, `reports/orchestrator/jiang-audit-20260915.md` |
| Infrastruttura | 7,81 GiB di RAM, 0,69 disponibili alle 13:31; disco libero oscillante (9,08 GiB durante il run di CP-0017, 26 GB alle 13:31). GPU del compagno da verificare oggi; quote Colab e Kaggle non misurate. Google Drive del proprietario: 5 TB, con i due grezzi pesanti già caricati | misura (ora) + dichiarazione | [CP-0017](checkpoints/0017-gate-espressione-destinazione.md), workflow 1 §3, [CP-0018](checkpoints/0018-drive-storage-confermato.md) |
| Governance | D-017 aperta; licenza Orion non verificata; regola di CP-0017 non confermata dal proprietario; lavoro di CP-0017 non ancora versionato | misura | `configs/benchmark_expression_gate.yaml`, `git status` |

## 4. Criticità — punto di partenza per U-4

| ID | Criticità | Evidenza | Che cosa la chiuderebbe |
|---|---|---|---|
| C1 | Ciclo di verifica troppo lento: una sottomissione in quattro giorni, contro 17–53 delle prime dieci | `reports/leaderboard_2026-09-16/rows.csv` | Due sottomissioni diagnostiche al giorno (O1 del workflow 1) |
| C2 | La metrica proxy non ha previsto il profilo ufficiale, e quattro metriche su sei dipendono dal generatore | CP-0006 §3.4, D-027 | Banco HepG2 a sei metriche con la scala indicativa (I-1, I-7) |
| C3 | Il banco a tre contesti non somiglia al pannello: bersagli essential condivisi, universo di 6.477 geni senza geni spenti. Il pannello non contiene geni essential | CP-0017 §3.5, `reports/candidate_verification/coverage_summary.json` | Un banco su bersagli non essential con l'asse genico intero (K562 a singola cellula o Orion) |
| C4 | Copertura del pannello: solo K562 genome-wide lo copre, 272/300 | [CP-0004](checkpoints/0004-primo-trial-locale-e-pacchetti.md) | I-5 e la decisione O5 |
| C5 | Artefatto del generatore aperto dal 12 settembre; FID sotto la media del contesto | CP-0004 §3.8, CP-0006 §3.3 | I-2 e trial-02 |
| C6 | Regole non chiarite: ricampionamento dei controlli, generatore ancorato a cellule reali, licenza Orion | D-017, [PROGETTO.md](PROGETTO.md) §4 punto 9 | Risposta degli organizzatori (O2) |
| C7 | Processo: regola di decisione non confermata prima del run, lavoro non versionato, file spurio nella radice | CP-0017 §4, `git status` | O3 e O4 |
| C8 | Macchina locale al limite: poca RAM libera, disco oscillante vicino al pavimento di 10 GiB. **Declassata per l'ingestione il 16 settembre**, su indicazione del proprietario: i due grezzi pesanti sono già su Drive, quindi non passano né da qui né da un download remoto. Resta aperta per generazione, packaging e benchmark in locale | D-005, workflow 1 §3, [CP-0018](checkpoints/0018-drive-storage-confermato.md) | Job pesanti solo su runtime remoto misurato (I-6). Per l'ingestione: il primo run che collega le copie da Drive e ne verifica l'md5 |
| C9 | Backend DE: in locale `scanpy`, sul server non noto; lo scarto fra motori non è misurato | D-014, PROGETTO §4 punto 10 | Stesso bundle valutato con `scanpy` e `gpudge` (I-6) |
| C10 | Versione dello scorer sul server non verificata: la semantica delle esclusioni letta in locale potrebbe differire | `reports/scorer_2026-09-12/vcc2026_contract.json` | Versione dichiarata dagli organizzatori o dal brief delle metriche |
| C11 | Canale di ricerca fragile: Kimi in timeout, modalità ricerca senza sostituto, campagna Jiang ferma | `reports/orchestrator/jiang-audit-20260915.md` | Diagnosi dell'orchestratore o un secondo revisore |
| C12 | Il pannello finale è nuovo, e ogni sottomissione consultata per scegliere trasforma `val` in dato di sviluppo | [PROGETTO.md](PROGETTO.md) §1, D-032 | Scelte valide per qualunque bersaglio; conferma sul seed 4242 e sul set del 22 ottobre |

## 5. Studio biologico

| ID | Tema | Domanda guida | Materiale |
|---|---|---|---|
| B1 | Meccanismo CRISPRi: dCas9-KRAB sul promotore, efficienza variabile, effetti sui geni vicini e sui promotori bidirezionali | Tolto il gene bersaglio, che lo scorer esclude ovunque, quale parte della risposta resta da prevedere? | Sorgente dello scorer (workflow 1 §1); Replogle et al. 2022, *Cell*, metodi sul knockdown (da verificare) |
| B2 | I tre contesti: A linfoide T immaturo (DNTT, RAG1), B epiteliale-mesenchimale, C epiteliale squamoso | Quali programmi sono propri di ciascun contesto, e quali risposte dovrebbero conservarsi fra linee (ribosoma, proteasoma, mediatore, splicing)? | `reports/context_identity/markers.csv` |
| B3 | Risposta comune e risposta specifica | Perché il punto 0 della scala è la media del contesto, e quanto pesa la parte comune nelle linee che abbiamo? | `baseline.py` dello scorer installato; lavori sulla variazione sistematica nei benchmark di perturbazione, per esempio *Systema* (riferimento da verificare) |
| B4 | Chi sono i 300 bersagli di `val` | Che cosa hanno scelto gli organizzatori (complessi, fattori di trascrizione, segnalazione)? Quanto sono espressi in A/B/C? Il pannello finale sarà simile? | `configs/orchestrator/briefs/materiali/vcc2026-panel-2026-09-15.csv`, `reports/expression_gate_2026-09-16/context_presence.md` |
| B5 | Geni spenti e filtro a 5 CPM | Quanti geni entrano davvero nelle metriche DE in ciascun contesto? | CP-0017 §3.6 e §4 punto 3 |

## 6. Studio informatico

| ID | Tema | Domanda guida | Materiale |
|---|---|---|---|
| K1 | Le sei metriche v2 nel codice installato: PDS coseno con esclusione del pannello, MSE corretta e normalizzata, Wilcoxon con FDR per perturbazione, FID e REACH, Jaccard | Quali metriche dipendono dalla varianza fra le cellule previste, e quindi dal generatore? | `cell_eval2` nel venv del data root: `config.py`, `metrics/delta.py`, `de.py`; [specifica ufficiale](https://github.com/ArcInstitute/cell-eval2/blob/main/docs/vcc2026_metrics/vcc2026-metrics-brief.md) |
| K2 | Il generatore | Perché, con un predittore nullo, cambiare generatore porta JAC da 0,003 a 0,120 e FID a 0? Le cellule usate come stampo coincidono con i controlli di riferimento del banco? | `scripts/57_generator_x_predictor.py`, `src/vcc2026/sampling.py`, CP-0004 §3.8 |
| K3 | Calibrazione e contrazione | Perché alzare α non aiuta PDS, e perché la contrazione che protegge MSE limita le altre metriche? | D-006, D-012, CP-0006 §4 e §8 |
| K4 | Disegno del banco | Che cosa garantiscono fold per contesto, universo per intersezione, seed di sviluppo e di conferma, controlli permutato e sorgente? | D-024, D-032, CP-0014, CP-0017 |
| K5 | Ancore e classifica | Quanto è affidabile una stima lineare da valori arrotondati e già aggregati sui contesti? | `reports/leaderboard_2026-09-16/snapshot.md` |
| K6 | Stato dell'arte, come elenco di lettura e non come evidenza | Che cosa hanno fatto i migliori della VCC 2025? Che cosa promettono State e PRiMeFlow su un contesto nuovo? Le baseline lineari reggono il confronto con i modelli profondi? | `reports/primeflow_2026-09-15/primeflow_feasibility.md`; Ahlmann-Eltze, Huber e Anders sulle baseline lineari (riferimento da verificare) |

## 7. Domande di comprensione nuove

1. La nostra PDS è 0,413 e la FID −0,182. Se cambiamo **solo** il generatore, quale
   delle due ci aspettiamo che si muova, e perché?
2. Perché lo scorer esclude il gene bersaglio da tutte le metriche, e che cosa resta da
   prevedere in una firma CRISPRi?
3. La media del contesto ha FID grezza di circa 0,51. Perché «non prevedere niente di
   specifico» sta già sopra il nostro 0,458?
4. Perché un risultato sul banco a tre contesti non basta per cambiare una
   sottomissione, e che cosa aggiunge il banco HepG2 a sei metriche?
5. Perché ogni sottomissione usata per scegliere riduce il valore di `val` come prova?

## 8. Disallineamenti già visti, da verificare per U-8

- [PROGETTO.md](PROGETTO.md) §5, «Il passo operativo», dice ancora che «nessun server
  ha accettato niente»: CP-0006 documenta l'accettazione del 13 settembre.
- La classe di perturbazione di Jiang (CRISPRi) è `cited` e non misurata
  (`reports/jiang_2026-09-15/source_card.json`): va controllata sulla sezione metodi
  prima di usare quei dati come CRISPRi.
- Ancore di MSE: CP-0006 stimava b ≈ 0,996 e r ≈ 0,022 da due righe, la fotografia di
  oggi 0,986 e 0,042 da dieci. Spiegare la differenza, senza scegliere un vincitore
  prima di U-3.
- Dimensione del K562 a singola cellula: diversi materiali scrivono «65,8 GiB», ma
  65.830.941.948 byte sono 61,31 GiB, e il «61,3 GB» del profilo è la stessa grandezza.
  Già registrato: [CP-0018](checkpoints/0018-drive-storage-confermato.md) §7 e la
  scheda R-013 del [registro](REGISTRO.md). Resta da correggere nel codice.

## 9. Formato e regole

- Consegna finale: una pagina «Stato e criticità — 16 settembre» in `docs/`, più il
  registro delle criticità e le note di studio. La riga di registro la aggiunge
  l'integratore.
- Ogni affermazione porta il suo tipo (misura, interpretazione, ipotesi, proposta,
  implementato) e un percorso. Un riassunto scritto da un agente non è evidenza.
- I checkpoint non si correggono: le contraddizioni diventano righe per il registro.
- La letteratura citata qui è un elenco di lettura: ogni riferimento va aperto e
  verificato prima di entrare in un documento del progetto.
