# Imparare dagli errori e impedirne la ripetizione

Questa è la guida operativa per trasformare un guasto in una prova di regressione
e in un controllo obbligatorio del prossimo lavoro pertinente. La pipeline resta
descritta in [PROCEDURE.md](PROCEDURE.md); stato e risultati scientifici restano in
[PROGETTO.md](PROGETTO.md) e nei report. Non serve un altro `pipeline.md` parallelo.

La guida ha tre parti, e ciascuna ha i suoi lettori: **si legge solo la parte del proprio
compito**.
- **Job e guasti operativi**, da «Prima del prossimo job» a «Registro immutabile e chiusura»:
  il preflight e il registro degli incidenti. Per chi prepara o segue un job su Colab o Kaggle.
- **[Errori di metodo già commessi](#errori-di-metodo-già-commessi)**: ragionamenti che hanno
  prodotto conclusioni sbagliate, con la regola che li evita. Per chiunque stia per scrivere una
  conclusione, un report o un checkpoint: è una tabella.
- **[Lezioni operative](#lezioni-operative-da-non-ripetere)**: trappole di Colab, Drive, disco,
  file e cartella condivisa, comprese quelle che stavano solo nella memoria privata di un agente.
  Per chi esegue codice o lavori lunghi. Le trappole della base di lancio degli agenti stanno in
  [AGENTI](AGENTI.md), §4.

Un esperimento concluso correttamente che smentisce un'ipotesi **non è un errore
infrastrutturale**. Per esempio, Stack A termina lo scoring ma perde il confronto:
si conserva il [risultato negativo](../reports/analisi/lead_scientist_2026-09-29/neural/RISULTATI_STACK_A.md)
e si applica il protocollo, senza cercare un guasto da correggere per promuoverlo.

## Prima del prossimo job

1. Leggere gli incidenti pertinenti nel [registro degli errori](../reports/analisi/lead_scientist_2026-09-29/learning/README.md).
   Riportare nel manifest del job i loro EID e le guardie applicate.
2. Dichiarare **tutti** gli input consumati: dati, metadata, predizioni, marker,
   bundle, snapshot del codice, configurazioni/ancore esterne allo snapshot.
   Per ogni file servono percorso locale e del runtime, dimensione e SHA256.
   Un marker `finished.json` non sostituisce gli H5AD, e un dataset esistente
   non prova che contenga i target necessari.
3. Preparare il manifest e validarlo localmente nel Python dichiarato. Verificare
   autorizzazioni già presenti in sessione: non richiederle di nuovo se coprono
   l'azione. Il preflight non concede né revoca autorizzazioni, e non consuma quota.
4. Il launcher deve verificare sul **runtime destinatario** lo stesso manifest
   e gli hash completi prima del calcolo e prima di creare l'output del job.
   Con Drive, attendere tutti i file fino al limite dichiarato; un hash corretto
   sul disco locale non dimostra che Colab abbia sincronizzato quel file.
5. Conservare ricevute locali e remote, nuovi output e hash del manifest,
   validatore e launcher. Usare lo stesso Python del job. Non installare pacchetti
   nel runtime base per aggirare una verifica fallita: correggere e registrare
   l'ambiente scelto.

Questi passaggi si applicano ai nuovi job preparati dopo l'introduzione della
guida. Non interrompono quelli già in esecuzione e non autorizzano nuovi lanci.
Non ricreano il vecchio orchestratore o i cicli ritirati il 23 settembre.

## Controllo eseguibile comune

Il codice riusabile è
[`learning/preflight.py`](../reports/analisi/lead_scientist_2026-09-29/learning/preflight.py),
con [test](../reports/analisi/lead_scientist_2026-09-29/learning/test_preflight.py).
Non è uno stadio produttivo: controlla un contratto esplicito senza avviare
training, inferenza, scoring, submission o installazioni.

Il manifest JSON versione 1 ha questi campi:

| Campo | Contenuto obbligatorio |
|---|---|
| `schema_version`, `job_id` | `1`, identificatore del nuovo job |
| `incident_ids` | EID pertinenti, oppure lista vuota motivata nella revisione |
| `inputs` | Lista con `id`, `paths.local`, `paths.runtime`, `bytes`, `sha256`; tutti i file effettivamente usati |
| `outputs` | Lista con `id`, i due percorsi assoluti e `must_be_absent: true` |
| `target_checks` | Per ogni NPZ di effetti: `input_id`, `npz_key: "targets"`, lista `required` dei target richiesti |
| `environment` | `python.paths.local/runtime`, `packages`, `imports`, `probes`; liste vuote esplicite dove non applicabile |

In `packages`, il valore stringa richiede la versione esatta; `null` controlla
presenza e registra la versione, senza inventare un pin. `imports` prova il
percorso Python reale, per esempio `stack.model_loading`, non soltanto `pip check`.
Il manifest è codice operativo revisionato: non si eseguono import da documenti
o risultati non attendibili.

`probes: ["h5ad_nullable_roundtrip"]` verifica scrittura e rilettura di conteggi,
assi e label nullable in un file temporaneo. `allow_write_nullable_strings: true`
applica l'opzione **soltanto nel processo del preflight**. Non configura i processi
Python successivi: il produttore deve applicarla nel proprio wrapper, come
[`stack_pack_runtime.py`](../reports/analisi/lead_scientist_2026-09-29/neural/stack_pack_runtime.py).
La ricevuta esplicita questo limite. Per uno scorer che non scrive H5AD il probe
rimane una verifica di capacità, non una modifica scientifica.

Esempio di comandi; `job.json` deve contenere input reali, nessun segnaposto:

```powershell
.\scripts\py.cmd reports/analisi/lead_scientist_2026-09-29/learning/preflight.py validate --manifest job.json --site local --receipt receipts/job_local_r1.json
```

Nel launcher remoto, con `$PY` impostato al Python revisionato del job:

```bash
"$PY" preflight.py validate --manifest job.json --site runtime --receipt receipts/job_runtime_r1.json --attempts 45 --interval-seconds 20
```

Solo codice d'uscita zero permette il passo successivo. Il launcher verifica
prima anche gli hash del validatore e del manifest trasferiti. `--receipt` deve
stare fuori dagli output del job: la sua creazione non deve farli sembrare già
esistenti. Una ricevuta locale non vale come ricevuta remota.

Il controllo legge il solo array NPZ dei nomi target con `allow_pickle=False`,
non le matrici di effetti. Rifiuta target mancanti, duplicati, metadata object e
output preesistenti. Verifica presenza/dimensione di tutti gli input prima dei
loro hash completi. Può controllare soltanto i file **dichiarati**: la revisione
del launcher deve verificarne la completezza, inclusi gli snapshot. Non fornisce
un lock contro modifiche successive; usare input congelati e ricontrollare la
provenienza nei lettori scientifici.

## Quando qualcosa fallisce

Conservare tentativo, log e output parziali; classificare prima il problema:
input, ambiente, serializzazione, perdita del runtime, difetto del codice o
risultato scientifico. Aprire un incidente per un guasto operativo reale; una
nuova ipotesi scientifica ha un protocollo e una valutazione separati.

Ogni record include **sintomo → causa verificata o ancora ipotetica → correzione
→ test che riproduce il guasto → stato della verifica → guardia del prossimo job**.
Citare file e SHA256, distinguere il momento del guasto da quello della scrittura
del record. Non attribuire al provider una causa di disconnessione non dimostrata.

## Registro immutabile e chiusura

Le registrazioni sono in
[`learning/incidents/`](../reports/analisi/lead_scientist_2026-09-29/learning/incidents/).
Un EID è `E-AAAAMMGG-NNN`; ogni revisione è un nuovo JSON `E-…r001.json`,
`r002.json`, ecc. La revisione cita lo SHA256 della precedente. Non si sovrascrive
il record iniziale per far scomparire un guasto o anticipare un successo.

Il registro sta in una cartella di report datata, che per la regola di `reports/CLAUDE.md` non si
modifica. È l'unica eccezione dichiarata (D-049): in `learning/incidents/` si aggiungono file nuovi,
e nessun file che c'è già si cambia. Spostarlo in una sede senza data romperebbe i launcher che lo
leggono per percorso.

| Stato | Che cosa dimostra |
|---|---|
| `observed` | Il guasto è documentato; causa/fix possono essere ancora incerti |
| `implemented` | La correzione esiste; non prova una verifica riuscita |
| `verified_locally` | Test pertinente superato localmente; runtime remoto ancora da verificare |
| `verified_remotely` | Criterio esplicito superato nel runtime interessato, con evidenza e hash |

`verified_remotely` richiede un criterio circoscritto: un H5AD recuperato non prova
che il pacchetto VCC sia finito; un import corretto non prova che il modello sia
accurato. Un `.done` scritto anche per codice d'uscita nonzero non prova successo.
Se la correzione fallisce ancora, aggiungere una revisione e registrare la causa
nuova; non abbassare retroattivamente il criterio di chiusura.

[`learning/ledger.py`](../reports/analisi/lead_scientist_2026-09-29/learning/ledger.py)
valida campi, identità, sequenza e catena degli hash. L'indice è derivabile:

```powershell
.\scripts\py.cmd reports/analisi/lead_scientist_2026-09-29/learning/ledger.py index --directory reports/analisi/lead_scientist_2026-09-29/learning/incidents
```

Per aggiornare: preparare un nuovo record completo con revisione successiva e
`previous_sha256`, poi `ledger.py append --directory <incidents> --record <nuovo.json>`.
Per salvare un indice usare `--out <nuovo-indice.json>`; il file è un derivato,
non la fonte degli stati. Testare la correzione, leggere l'esito remoto completo
e aggiungere la revisione di verifica prima di dichiarare l'incidente chiuso.

## Errori di metodo già commessi

Ragionamenti che hanno prodotto conclusioni sbagliate, scoperti dopo. Prima di scrivere una
conclusione, controllare che non ricada in uno di questi. Gli approcci provati e non riusciti (modelli,
correzioni, strategie sui dati), con il loro meccanismo e che cosa li riaprirebbe, stanno in
[STRADE](STRADE.md): si legge prima di progettare. Una correzione nuova si aggiunge qui
come riga, con la fonte; le righe vecchie non si riscrivono.

| Errore | Come si è visto | Regola che lo evita | Fonte |
|---|---|---|---|
| Confondere seme fisso e test fisso su un corpus che cresce | Liste nascoste r5/r7 con soli 128 target comuni | Manifest stabile degli split; classificare C/T/J dopo QC e contro le etichette realmente ammesse | [CP-0053](checkpoints/0053-audit-cellnet-e-strategia.md), [audit §2](../reports/analisi/lead_audit_2026-10-01/REVISIONE.md) |
| Dedurre il bilanciamento dai pesi dichiarati | Replay r2: normalizzare nel batch dà a K562 GW il 32,61% della loss invece del 16,67% | Verificare coefficienti effettivi insieme a campionatore, shard e denominatore | stesso audit, §2.2 |
| Chiamare baseline generica un ingresso unknown non addestrato | Gradiente zero dell'embedding unknown; la loss dei controlli esclude il ramo di risposta | Addestrare un confronto senza bersaglio; separare ablation di ingresso e confronto predittivo | stesso audit, §2.4 |
| Una deduzione riscritta come misura in un riassunto | «non nei pannelli essenziali» → «non essenziale» → «effetti piccoli per costruzione», 12/09 | Riportare i caveat della fonte; etichettare misurato, interpretazione, ipotesi | [CP-0002](checkpoints/0002-correzioni-dopo-revisione-umana.md) |
| Una premessa sui dati ripetuta senza leggere i metadati primari | «Tutte le sorgenti tranne VIPerturb sono in 3'»: il CSV degli autori con CD4 `GEMX_flex_v1` era nella repo dal 12/09 | Per saggio, chimica o stato di una sorgente citare il file di metadati primario | [audit dei dati](../reports/analisi/lead_scientist_2026-09-29/AUDIT_DATI.md), [CP-0046](checkpoints/0046-audit-lead-e-due-vie-neurali.md) |
| Attribuire a un fattore l'effetto di un intervento che ne cambia diversi | t20 − t16 cambia forma, ampiezza e cis insieme; il t26 letto come prova sul t23 | Un contrasto identifica solo ciò che cambia da solo; altrimenti si parla di pacchetto (D-047) | [audit scientifico](../reports/analisi/lead_scientist_2026-09-29/AUDIT_SCIENTIFICO.md) §2 |
| Una media piatta letta come saturazione | «Dal t16 nessuna leva»: in t23 − t22 il 94,5 % del movimento dei membri si annulla nella media | Leggere tutti e sei i membri e i loro contributi | stesso audit, §1 |
| Una sola coppia di semi usata come deviazione standard | t24 − t22 = 0,0016 chiamato «il rumore del seme» | ±0,005 è una soglia operativa, non un intervallo statistico | stesso audit, §2.2 |
| Scegliere con un proxy che vede due membri su sei | Δ = 0,36 ΔPDS − 0,27 ΔnMAE non riproduce le differenze ufficiali | Scegliere con lo scorer vero, sui sei membri | [CP-0041](checkpoints/0041-proxy-contro-ufficiale.md) |
| Un indice locale letto come guadagno atteso in gara | t28: +0,0289 sul banco HepG2, +0,0046 in gara. Interpretazione: già la forma t19 dava +0,026 al banco, mentre t20 − t16 in gara valeva +0,002, con altre modifiche insieme | Il banco dà il verso, non l'entità; la previsione ufficiale si registra a parte | [CP-0052](checkpoints/0052-t28-punteggio-ufficiale.md), [banco HepG2](../reports/generatore_e_banchi/banco_hepg2_v2_2026-09-26/RISULTATI.md) |
| Una riserva già valutata chiamata indipendente | 95 dei 96 bersagli della conferma del generatore erano già in un banco del 27/09 | Un registro globale delle riserve, controllato prima di selezionare | [CP-0050](checkpoints/0050-credibilita-score-e-riserva.md) |
| Le ancore aggregate usate come conversione esatta | Errore di +0,0007 sul t03 e +0,0008 sul t25 | Leggere i sei scalati pubblicati nello status | [CP-0050](checkpoints/0050-credibilita-score-e-riserva.md) |
| Una soglia nata per un'ipotesi usata per chiudere una linea | Il nullo «meno di 10 chiamate» chiuse il generatore con dispersione (t13); il prescreen PDS +0,01 trattato come condizione necessaria per le reti | Chiudere una linea richiede una prova sulla metrica obiettivo | [audit scientifico](../reports/analisi/lead_scientist_2026-09-29/AUDIT_SCIENTIFICO.md) §3, [prescreen](../reports/analisi/lead_scientist_2026-09-29/neural/NN_PRESCREEN_AUDIT.md) |
| Un calcolo riuscito letto come prova di utilità | «La rete è addestrata», «il job ha codice 0» | Il successo tecnico non è un risultato scientifico | [CP-0048](checkpoints/0048-rete-sorgenti-primo-seme.md) §7 |
| Scegliere i dati di un training con misure che leggono le risposte della sua valutazione | Lo studio dei campioni annidati del 4/10 leggeva linea esclusa e bersagli nascosti, e la sua regola raccomandava il tetto; «qui non si addestra» non bastava | La scelta dei dati è per fold e legge solo la classe training; un test cambia le risposte escluse e pretende che campioni e tetti restino identici, con un controllo positivo | [emendamento §10](../reports/modelli/rete_ancorata_v4_2026-10-03/CAMPIONI_ANNIDATI.md), `test_nested_fold.py` nella stessa cartella |
| Inviare un candidato che il banco non ha valutato | Il t30 somma al t25 una correzione appresa e provata contro un'altra baseline, con uno stimatore e un regime degli ingressi mai passati per il banco: +0,044 locale, −0,005 ufficiale | Il candidato inviato è esattamente un braccio del banco; ogni differenza residua si elenca prima, con la prova che non conta | [CP-0064](checkpoints/0064-t30-ibrido-selettivo-punteggio-ufficiale.md), [diagnosi](../reports/modelli/diagnosi_t30_2026-10-04/TABELLA_CATENA.md) |
| Una media che copre la perdita del membro che pesa di più | Sul fold esportato il PDS locale scendeva di 0,093 e la media saliva di 0,063; sul sito è rimasta la perdita di PDS | Guardia per membro su ogni linea, sviluppo compreso; previsione registrata per membro | stesso checkpoint, [membri del banco](../reports/modelli/diagnosi_t30_2026-10-04/esito/bench_members_r1.json) |
| Guardie del training non applicate all'inferenza | Quota comune della correzione 0,17 nel training e 0,62–0,69 all'esportazione, oltre la soglia 0,5 dell'arresto | Le stesse guardie come rifiuto dell'esportazione, sul contesto di destinazione | stesso checkpoint, [esportazione contro righe](../reports/modelli/diagnosi_t30_2026-10-04/esito/export_vs_rows_r1.json) |
| «Un fattore solo» con un flusso casuale condiviso | Le cellule dei bersagli non corretti del t30 non sono quelle del t25: 1 blocco su 210 identico | Flusso per blocco, oppure dichiarare che il delta contiene un cambio di realizzazione; più semi | stesso checkpoint, [catena](../reports/modelli/diagnosi_t30_2026-10-04/esito/chain_t30_r2.json) |
| Una scala locale con denominatore piccolo letta nella media | JAC locale di K562 a −4,7 (replicato − baseline = 0,047): il 77 % del suo guadagno | Riportare grezzi e denominatori; fissare prima come entra un membro instabile | stesso checkpoint |
| Decidere su differenze più piccole del rumore del banco | Guadagni di CP-0062 letti a un seme e 32 cellule per bersaglio: +0,074 su K562 diventa +0,023 ± 0,045 su 5 semi e +0,005 ± 0,015 a 400 cellule; due bracci quasi identici differivano di 0,06 | Tarare il rumore prima di fissare una soglia; guadagno appaiato su più semi, con la numerosità dell'invio; una differenza conta se risolta | [CP-0065](checkpoints/0065-d056-confronti-e-rumore-del-banco.md), [esito](../reports/modelli/diagnosi_t30_2026-10-04/ESITO_CONFRONTI.md) |
| Scegliere la rete da esportare con una regola che non guarda il suo esito | Il fold «con più cellule di training» (HepG2) era l'unico con PDS in perdita netta sulla sua linea esclusa | La rete da esportare passa una guardia sul PDS, su più semi | stesso checkpoint |
| Registrare l'esito di un fallimento senza il suo meccanismo | Tre reti di fila senza capacità di distinguere i bersagli (t29, pilot r3, v4), ogni volta registrate come «non ha passato la regola»; la terza è partita senza una guardia che lo cogliesse nei primi minuti | Ogni esito letto diventa una voce di [STRADE](STRADE.md) con meccanismo etichettato e segnale precoce; un protocollo nuovo cita i precedenti e dichiara il proprio arresto (D-055) | [STRADE](STRADE.md), voci S-001, S-002, S-006 |
| Una misura di guardia definita su un supporto che può svuotarsi | Nel fold a K562 esclusa la discriminazione era calcolata sui geni validi per tutti i 272 bersagli: ne restava uno, e il braccio vero valeva quanto quello a bersagli permutati (0,492 contro 0,498) | Ogni misura di guardia porta il proprio controllo positivo, fold per fold, e si legge solo dove passa; il supporto usato si riporta accanto al numero | [contratto v2](../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/PROTOCOLLO_v2.md) §1 |
| Leggere come proprietà di una fonte ciò che produce lo stimatore | Il voto «quasi nullo» di Tian 2019 su RFK attribuito al knockdown debole: con la centratura sul pannello una tabella con un bersaglio vota zero qualunque cosa contenga, e una con n bersagli perde 1/n dell'effetto di ciascuno | Prima di interpretare il contributo di una fonte, provare lo stimatore sui suoi casi degeneri (un bersaglio, pochi bersagli) con un controllo numerico | [audit](../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/AUDIT_DATI_E_LEAKAGE.md) §2 |
| Contare le tabelle lette come fonti che contribuiscono | «16 fonti lette» nel fit T1: 12 hanno almeno un voto, 7 sono i lignaggi; dei 16 voti nuovi solo 6 vengono da un lignaggio che su quel bersaglio non votava già | Accanto al numero di fonti riportare tabelle senza voti, voti per lignaggio e voti ripetuti della stessa linea | stesso audit, §2 e §3 |
| Scrivere come attuale lo stato di un altro incarico da una lettura vecchia | L'8/10 la raccomandazione, R-LEAD e la nota di consegna hanno detto fino alle 23:08 che T2 non aveva effetti di produzione e attendeva il consenso; erano stati consegnati alle 22:10, e la cartella era stata letta l'ultima volta alle 21:27 | Prima di scrivere lo stato di un altro incarico in un documento condiviso o in una raccomandazione, rielencare la sua cartella per data e leggere l'ultima consegna; accanto allo stato va l'ora della lettura, non quella della scrittura | [raccomandazione](../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/RACCOMANDAZIONE.md), §8; [R-LEAD](piani/strategia-scientifica.md) |

## Lezioni operative da non ripetere

Trappole già incontrate, fuori dal registro degli incidenti dei job. Diverse erano scritte solo
nella memoria privata di un agente: qui valgono per tutti.

- **Colab.** Il log di un job si sincronizza solo alla fine; un dispatcher muto per ore vuol dire
  runtime perso: i job con `.started` non ripartono e `/content/work` si perde
  ([PROCEDURE §3](PROCEDURE.md#3-job-su-colab-e-kaggle)). Salvare su Drive ogni
  artefatto prima del passo successivo (E-20260929-003).
- **Drive virtuale (G:).** La lettura di un file grande può fallire con un errore di I/O prima
  dell'upload (E-20260929-007): copiarlo in locale e verificarne lo SHA completo prima del CLI.
- **Orari.** Si leggono con `date` o dal commit, mai a memoria: il 27/09 un «00:45» scritto a
  memoria era 00:25.
- **Processi lunghi** (generazione, packaging, upload): si lanciano come processo Windows separato;
  i comandi in background di una sessione vengono chiusi quando manca memoria.
- **`vcc status`** può restituire solo l'ultimo invio ([CP-0037](checkpoints/0037-t16-ampiezza-quadrupla.md)):
  salvare subito lo status completo di ogni invio.
- **Disco.** Un candidato occupa circa 13 GB di picco: misurare lo spazio libero prima di generare
  (il 30/09 alle 02:30 restavano 3,8 GB su C:). I file rigenerabili vanno nel Cestino, mai
  cancellati in modo definitivo.
- **Cartella condivisa fra agenti.** `git commit -- <file>` prende il file intero dal working
  tree, anche le righe di altri (e7c933b, corretto da db32204); Codex mette segnaposto con
  `git add -N`. Prima di committare: `git status`, `git diff --cached --stat`, poi solo i propri
  file, per nome. Chi chiude una sessione committa il proprio lavoro (D-048): il 30/09 alle 02:07
  circa 1.160 file di due sessioni chiuse erano ancora fuori dai commit. Come si committa un file
  che anche altri stanno modificando: [AGENTI §3](AGENTI.md#3-coordinamento-fra-sessioni-nella-stessa-cartella).
- **Heredoc in Git Bash.** Un heredoc passato a `py` o `python` dimezza le barre rovesciate: il 24/09
  un `\r\n` scritto così è diventato un vero a capo, e il 30/09 un `\n` in una sostituzione è
  diventato un a capo, facendola fallire. I file si modificano con gli strumenti dell'editor o con
  uno script salvato in un file.
- **Copie di lavoro dentro l'albero.** Una copia della repo del 24/09 (`.runtime-deps/`, 858 file)
  faceva comparire testi superati nelle ricerche; è stata spostata fuori il 30/09
  (`reports/analisi/riordino_repo_2026-09-30/`). Nella cartella della repo non vanno copie, venv
  o dati.
- **Lanciatori che spendono quota.** La scadenza di un Monitor non ferma il processo che lo alimenta:
  il 3/10 quattro cicli bash sopravvissuti hanno spinto due volte lo stesso training GPU (due
  sessioni Kaggle, circa 3 ore di quota) e bloccato gli altri sul limite di 2 sessioni
  (E-20261003-001). Un lanciatore è un processo unico con lock che termina da solo; dopo ogni
  spinta si legge la quota GPU usata e riservata. Una versione nuova non annulla quella in corsa.
- **Banchi sul portatile «perché la sessione prima ha fatto così».** Il 4/10 la corsia B di H1 (venti minuti di
  scorer, con meno di 1 GB di RAM libera) è girata in locale e quella di HepG2 era partita, con una motivazione di
  comodità nel verbale: Colab occupato, pacchetto remoto assente, corsie r3 già girate in locale. Il proprietario lo ha
  fermato: la regola di `CLAUDE.md` dice che il pacchetto mancante è lavoro da fare. Rimedio in mezz'ora: ogni input
  era già su Kaggle, mancavano lo snapshot del codice e lo scorer
  (`reports/modelli/rete_ancorata_v4_2026-10-03/kaggle_lanes.py`). Un'esecuzione locale precedente non è un
  precedente; prima di lanciare un banco si controlla dove stanno già gli input.
- **Scratchpad di sessione.** Sono temporanei e possono sparire: i risultati vanno in `reports/`
  prima di chiudere la sessione. Il 26/09 risultati verificati sono rimasti solo in uno scratchpad;
  il 30/09 erano ancora lì, in attesa della decisione del proprietario.
- **Identità dei contesti.** Nessun nome di linea accanto ad A, B o C nella repo, che è pubblica
  (decisione del proprietario del 24/09): quel materiale sta nella cartella dati.
- **Scorer installato.** `cell_eval2` nel venv contiene note degli organizzatori sui pannelli di
  validazione: cercarle prima di dedurre ([PROGETTO §3](PROGETTO.md#3-che-cosa-sappiamo-e-guida-le-scelte)).
  La suite della repo si esegue con `.\scripts\py.cmd`: con un altro interprete tre test cadono per
  `No module named cell_eval2.config` (il 4/10: 287 + 3 con l'interprete di Codex, 290 OK con il venv;
  [report](../reports/gara/scorer_0_18_2026-10-04/README.md)).
- **Shard negli output dei kernel d'ingestione.** Stanno in `<job>/shards/<unità>/<shard>.h5ad`, con un `manifest.json`
  per unità, non in `<job>/shards/`. Il 4/10 un kernel degli shard campionati cercava `shards/*.h5ad` e si è fermato
  dopo 10 s con «no shard found» (`vcc-sampled-hct116-l64-r1`); il pattern giusto è `shards/*/*.h5ad`, come legge
  `build_fast_units.py`. Un costruttore che non trova input deve fermarsi così, mai produrre un manifest vuoto.
- **Banca in una copia montabile.** Un kernel finito in ERROR non si monta: la sua banca vive allora in un dataset copia, a volte con nomi di file diversi (`bank__norman2019__count_sum.npz`). Cercare i file per dimensione e sha256 della ricevuta, non per nome o percorso (7/10, `reports/modelli/banca_canonica_2026-10-07/consumer/runtime.py`).
- **`kaggle datasets create` su Windows.** Con un percorso a barre dritte fallisce sul file di ripresa; la barra di avanzamento non si decodifica in cp1252 e l'esito non si legge dall'uscita: confermare con `datasets status` e `datasets files`.
- **Kernel di un account, dati di un altro.** Un kernel monta i dataset condivisi con il suo account, non gli output dei
  kernel privati di un altro account. Gli shard delle sorgenti nuove sono output di `davideferrante11`: ciò che li legge
  gira su `davideferrante11` (`reports/sorgenti/prepasso_ampliato_2026-10-04/STATO.md`). I dataset piccoli di codice si
  copiano byte per byte, quelli grandi si condividono in lettura
  (`reports/modelli/ibrido_selettivo_2026-10-04/replicate_datasets.py`, `share_to.py`).
