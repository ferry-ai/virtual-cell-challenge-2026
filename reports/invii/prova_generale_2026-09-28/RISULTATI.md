# La prova generale del 22 ottobre: protocollo e regole (azione 3 di R-REV, F8 di R-V2)

28 settembre 2026. Scrive Claude (app desktop, sessione `f2abd9a6`); orari letti da `date`. Schede:
[R-REV](../../../docs/piani/revisione-critica.md), azione 3; [R-V2](../../../docs/piani/modello-v2.md), F8;
[revisione](../../analisi/revisione_criticita_2026-09-28/REVISIONE.md), §2.4 e §3.4. Il piano viene da un sottoagente
di questa sessione che ha letto il codice senza eseguire nulla; rivisto qui.

**Protocollo fissato alle 20:00 del 28/09, prima di girare.**

Etichette: **misurato**, **interpretazione**, **ipotesi**, **proposta**; **[C]** vuol dire verificato nel codice.
Nessun numero qui è un punteggio VCC, e nessun file di questa prova si carica sul server.

## La domanda

Dal pacchetto del 22/10 (tre contesti con i soli controlli, 300 bersagli nuovi) la ricetta del t22 arriva a un `.vcc`
che lo stadio 48 convalida e verifica? Dove dipende ancora da A/B/C o dal loro pannello? Quanto tempo, disco e memoria
chiede ogni passo?

## Il materiale

- **Contesti finti.** Copie di `raw/controls/context_{A,B,C}.h5ad` in `raw/controls_prova_2026-09-28/` nella radice
  dati, rinominate D, E, F con una permutazione estratta dal seme (scritta in `manifest.json`). Nella copia si riscrive
  solo l'etichetta `obs/context`. Copia vera, mai un collegamento. Gli originali: sha256 prima e dopo, identici.
- **300 bersagli finti.** Seme 20261022, strati estratti in quest'ordine:
  - 30 del pannello di oggi (P3);
  - fuori dal pannello e sull'asse: 120 coperti da tutte e quattro le sorgenti del t22, 50 da tre, 40 da due, 30 da
    una (P1);
  - 30 da nessuna (P0).

  Il pannello finto è volutamente più povero di quello vero (236 su 300 coperti da quattro sorgenti), per provare i
  ripieghi dello stadio 100. Elenco in `bersagli.csv`.
- **Sorgenti.** Le cache del pannello si ricavano dagli universi, non dagli stadi 97/102/98: K562 del 26/09, CD4 e
  Orion `_me1`. È la regola del t25: la correzione entra nelle cache costruite da qui in avanti.
- **Ricetta.** `ricetta_t22_DEF.json`: il t22 con le chiavi D, E, F e nient'altro di diverso.

## Scritto prima di girare

**γ = 1 e la cache [C].** Con γ = 1 lo stadio 100 toglie a ogni sorgente, gene per gene, la media dello `shrunk` su
tutti i bersagli della sua tabella nella cache (`multisource.AxisTable.common`). Con una cache del pannello sono i
bersagli del pannello che quella sorgente misura, quindi con un pannello nuovo il vettore tolto cambia. Misurato per il
solo K562: media sul pannello (272 bersagli) contro media sull'universo (9.866), coseno 0,63.
- Per la prova si usa la cache del pannello nuovo (G-a): è ciò che il §7 di LAVORO farebbe con gli stadi 97/102/98.
- La media congelata di r9 (G-b) e la media sull'universo (G-c) si misurano soltanto, e non entrano negli effetti.

**Ampiezza.** Si genera a 1,576, la ricetta del t22 invariata. La regola candidata, calcolabile dai soli controlli, è
**R-B**: una sola ampiezza per D/E/F tale che la media sui tre contesti della mediana dei geni rilevabili eguagli
quella di A/B/C a 1,576.
- I geni rilevabili si contano come in `match_detectable`: soglia 4/√(400 μ), geni ≥ 5 CPM, testa cis fuori dalla
  scala.
- Si calcola sugli effetti del t22 del pannello di oggi.

Si riportano anche R-C (con gli effetti nuovi), R-D (per contesto) e R-E (con la profondità dei controlli). Quale
adottare lo decide il banco dell'azione 4, non questa prova.

## Previsioni registrate

1. Lo stadio 48 con vcc-cli 0.2.0 rifiuta D/E/F («Unknown context label(s)»): il difetto D1 qui sotto.
2. Lo stadio 45 scrive `pilot: True` per una corsa D/E/F.
3. **Parità:**
   - le cache assemblate per il pannello di oggi coincidono con r5 (dagli universi del 26/09) e con r9 (dagli
     universi `_me1`): 0 differenze in raw, SE, shrunk e cellule per K562 e Orion, al massimo 2e-8 per `cd4_mix`;
   - gli effetti dello stadio 100 su quelle cache coincidono con quelli del t22 e del t25 entro 1e-6, con la stessa
     maschera `observed`.
4. **Copertura:** 270 bersagli su 300 con effetti in almeno una sorgente (P1 e P3), 0 su 30 in P0. In P0 il gene
   bersaglio stesso ha effetto 0.
5. R-B sulle copie di A/B/C restituisce 1,576 ± 0,001.
6. **Controllo negativo:** lo stadio 100 con i bersagli finti sulla cache r9 finisce con codice 0 e circa 30 bersagli
   coperti.

## Che cosa si misura

- **Per ogni stadio** (`tempi.jsonl`):
  - orario UTC di inizio e fine;
  - codice d'uscita;
  - picco di memoria del processo;
  - disco libero prima e dopo;
  - in più, il picco di disco dello stadio 48.
- **Poi:**
  - la copertura per strato e le righe tutte zero;
  - la diagnostica di γ (G-a, G-b, G-c);
  - i valori di R-B, R-C, R-D e R-E;
  - ogni punto in cui la pipeline dipende ancora da A/B/C.

## Difetti attesi dalla lettura del codice

Ciascuno si corregge con il suo test quando la prova ci arriva.

| # | Difetto [C] | Correzione minima | Test |
|---|---|---|---|
| D1 | Lo stadio 48 non ha `--contexts`, e vcc-cli 0.2.0 fissa A/B/C (`vcc/prep.py:54`; `src/vcc2026/packaging.py:457-459`) | `--contexts` nello stadio 48, passato come `required_contexts`; senza, come oggi | un h5ad minuscolo D/E/F fallisce senza e passa con; A/B/C invariato; confronto prima/dopo su un pilota |
| D2 | Stadi 98 e 100 leggono la prima colonna del file del pannello per posizione | un aiuto che legge `target_gene` per nome, senza doppioni | file nudo, con `n_cells`, con `context` e doppioni: stessi 300 bersagli |
| D3 | Chiavi della ricetta e contesti del pacchetto non si controllano fra loro | lo stadio 100 rifiuta una ricetta con chiavi diverse da `--contexts` | la ricetta D/E/F ha le stesse specifiche del t22 |
| D4 | Una cache costruita per un altro pannello dà una previsione quasi nulla senza errore | il manifest della cache registra lo sha256 dei bersagli; lo stadio 100 rifiuta una discrepanza e zero bersagli coperti | cache e bersagli sintetici; il controllo negativo lo mostra |
| D5 | Una corsa D/E/F vera è marcata `pilot` (`45:283-284`) | accettare `contexts_test` | `is_pilot` falso per D/E/F a 300 × 400 |
| D6 | LAVORO §7 scrive `--contexts D,E,F` per lo stadio 76, che vuole valori separati da spazi | correggere il testo | — |
| D7 | Un bersaglio che nessuna sorgente copre non riceve il silenziamento del proprio gene | proposta: un blocco facoltativo `"self"` nella ricetta; non entra nel t22 | un bersaglio sintetico scoperto riceve il prior sul proprio gene |
| D8 | Nessun codice vivo scrive i CPM di D/E/F, e il conteggio dei rilevabili vuole un riferimento sullo stesso pannello | un'opzione che scrive i CPM sull'asse, e `"amplitude_rule"` nella forma R-B | CPM di A/B/C uguali a `interim/basal_cpm_by_context.csv`; R-B su A/B/C dà 1,576 |
| D9 | La media tolta da γ dipende da ciò che la cache contiene, e nulla lo dice | chiave `"common"` nella ricetta | «panel» riproduce l'uscita di oggi |
| D10 | Nessuno stadio vivo costruisce una cache del pannello dagli universi | uno stadio nuovo che la assembla | universi sintetici nei due formati di indice |
| D11 | Provenienza incompleta: lo stadio 98 non scrive un manifest, il 100 non registra il file dei bersagli | aggiungere i campi | le chiavi del manifest ci sono |
| D12 | Le riserve di disco degli stadi 45 e 48 chiedono circa 17 GB liberi, non i 13 del §7 | correggere LAVORO §7 | — |
| D13 | Le uscite degli stadi 85 e 99 vanno sotto `reports/` per default: rischio di identità | una riga di procedura: uscite di D/E/F nella radice dati | — |

## Forma e risorse

- **400 cellule per bersaglio** se all'inizio ci sono almeno 17 GB liberi. Altrimenti 40, con
  `pert_counts_n40.csv` per lo stadio 48. Le durate a forma piena degli stadi 45 e 48 restano quelle misurate sul t22
  (1.309 s e 1.009 s).
- **Misurato alle 19:53:** C: ha 2,7 GB liberi; il file di paging è cresciuto a 20,3 GB. Alle 19:54 sono andati nel
  Cestino 25,3 GB di file rigenerabili (t18, t19, t20: [autorizzazioni](../trial_2026-09-22/autorizzazioni.md)). Lo
  spazio torna quando il proprietario svuota il Cestino.
- Si parte dopo la lettura della regola di r1, che tiene occupata la CPU (LAVORO §2: un lavoro pesante alla volta).

## Regola di chiusura

- La prova **riesce** se un `.vcc` di D/E/F sui bersagli finti passa convalida, impacchettamento e verifica dello
  stadio 48.
- Ogni arresto è un difetto. Si corregge con il suo test, e lo stadio che decide l'invio con un confronto prima/dopo
  su un pilota; poi si riprende dal passo fermo.
- Le previsioni 1–6 si leggono come scritte: una che non si avvera si riporta, non si corregge dopo.
- Nessun invio, nessun download. Il `.h5ad` e il `.vcc` della prova vanno nel Cestino dopo le misure, con sha256 e
  dimensioni nel report. Le uscite degli stadi 85 e 99 restano nella radice dati.

## Limiti

D, E ed F sono copie di A, B e C: la prova non dice nulla sul punteggio né su contesti davvero nuovi. Il pannello
finto non è quello degli organizzatori: la copertura vera si misura il 22/10.

## Codice, deviazioni dichiarate e primi passi (28/09 sera – 29/09 mattina)

Codice di un sottoagente della sessione `f2abd9a6`: `estrazione.py`, `bundle_finto.py`, `assembla_cache.py`,
`cpm_contesti.py`, `diagnostica.py`, `confronta_effetti.py`, `misura.py`, `comune.py`, `ricetta_t22_DEF.json`,
`comandi.ps1`, `test_prova.py` (25 prove sintetiche). Il difetto D1 è corretto nello stadio 48 (`--contexts`), con
cinque prove in `tests/test_packaging_parity.py`. Senza l'opzione il `.vcc` è identico bit per bit a quello della
versione precedente, su un pilota sintetico A/B/C. Il confronto prima/dopo su un pilota di dati veri è in
`comandi.ps1`, prima del passo 9(b).

**Misurato:**
- **Passo 1, l'estrazione** (28/09, 18:09 UTC): pool come nel piano; permutazione D = B, E = A, F = C. Gli universi
  del 26/09 e `_me1` elencano gli stessi bersagli.
- **Passo 5, parità della cache del pannello di oggi** ricostruita dagli universi del 26/09 contro r5 (21:34–21:36
  UTC, 265 MiB, uscita di 136 MB). Previsione 3, parte cache:
  - K562, HCT116 e HEK293T: 0 differenze in raw, SE, shrunk e cellule;
  - `cd4_mix`: al massimo 1,49e-8, entro 2e-8.

  Passa. Gli sha256 degli npz di Orion e `cd4_mix` differiscono comunque, perché la stringa `meta` è diversa (N2).

**Deviazioni dal protocollo, dichiarate prima dei passi 2–10:**
1. **CPM dei contesti (passo 4).** `read_basal_profile` somma i conteggi prima di dividere, e non riproduce
   `interim/basal_cpm_by_context.csv`, che è la media dei CPM delle singole cellule (scarto relativo massimo 0,83 su A).
   `cpm_contesti.py` scrive la definizione del file. La regola di parità a 1e-9 non cambia.
2. **Regole d'ampiezza R-B…R-E.** Il conteggio dei geni rilevabili va a gradini, quindi un intervallo di ampiezze
   raggiunge il bersaglio. Si riportano i due estremi. Il valore della regola è il punto dell'intervallo più vicino a
   1,576, oppure l'estremo inferiore (`s_cross`) se nessun punto lo raggiunge esattamente.
3. **Previsione 5, letta in anticipo e vera per costruzione.** Con D/E/F copie permutate di A/B/C la media su tre
   contesti non dipende dall'ordine. R-B dà 1,576 (estremi 1,57585–1,57672), come doveva. Vale come prova del codice,
   non come misura.
4. **Scomposizione di P3:** la parte di γ è l'ampiezza per (miscela G-a − miscela G-b); il resto è il prior cis
   ristimato più ogni differenza nelle righe delle sorgenti.
5. Il controllo delle impronte dello stadio 99 (passo 3) resta un confronto a mano, scritto in `comandi.ps1`.

**Difetti nuovi trovati scrivendo il codice:**
- **N1:** `read_basal_profile` e il CSV dei CPM che lo stadio 100 passa a `match_detectable` usano due definizioni
  diverse di CPM, e nessun codice vivo scrive la seconda. Conta per la correzione D8.
- **N2:** le stringhe `meta` delle cache ricostruite differiscono da quelle di r5/r9. Le ricette con `zshrink` o con
  la stima gerarchica vorrebbero anche le parti di `cd4_mix` nella cache. t22 e t25 non ne sono toccati.

## Esito (misurato, 29/09, 09:35–10:19 UTC; forma ridotta)

Girata dalla sessione Claude `f2abd9a6` con `comandi.ps1`, un passo alla volta. **Forma ridotta, 40 cellule per
bersaglio:** all'inizio C: aveva 5,97 GB liberi, sotto i 17 della forma piena, perché il Cestino non era ancora stato
svuotato. Tempi e memoria per passo in [`tempi.jsonl`](tempi.jsonl); manifest e report di impacchettamento copiati qui
(`pg22_*`, `pg22val_*`, `pg22pack_*`).

**La prova riesce.** Il `.vcc` di D/E/F sui 300 bersagli finti passa la convalida, l'impacchettamento e la verifica
dello stadio 48 con `--contexts D,E,F`:
- validatore ufficiale del contenitore superato;
- contenuto identico bit per bit all'input;
- 300 bersagli e 12.000 cellule per contesto;
- sha256 `b678b25f…`, 420.976.640 byte.

L'h5ad e il `.vcc` sono andati nel Cestino ([sha256 e dimensioni](artefatti_nel_cestino.json)).

| Passo | Durata | Picco di memoria |
|---|---|---|
| 2, pacchetto finto | 72 s | 283 MiB |
| 3, stadi 85 e 99 | 43 s + 37 s | 373 / 186 MiB |
| 4, CPM di D/E/F e di A/B/C | 116 s + 116 s | 341 MiB |
| 5, cache dagli universi (parità r9; pannello finto) | 192 s + 208 s | 260 MiB |
| 6, stadio 100 (quattro corse) | 36–65 s ciascuna | 563 MiB |
| 7, diagnostica | 252 s | 306 MiB |
| 8, stadio 45, 40 cellule | 254 s | 429 MiB |
| 9, stadio 48 senza e con `--contexts` | 40 s + 229 s | 506 MiB |

A forma piena gli stadi 45 e 48 valgono i tempi misurati sul t22 (1.309 s e 1.009 s). La stima dello stadio 45 per la
forma piena di questa corsa è 36 minuti (`projected_generation_seconds_at_full_shape`).

### Le previsioni registrate, lette come scritte

1. **Si avvera.** Lo stadio 48 senza l'opzione rifiuta: «Unknown context label(s) in 'context': D, E, F»
   (`pg22val_packaging.json`).
2. **Si avvera, ma non isolata.** `is_pilot` vale true nella diagnostica dello stadio 45. In questa corsa è vero anche
   per le 40 cellule; che bastino i contesti D/E/F lo dice il codice (`45:283-284`).
3. **Si avvera:**
   - cache ricostruite dagli universi uguali a r5 (26/09) e a r9 (`_me1`): 0 differenze per K562 e Orion, 1,49e-8 per
     `cd4_mix`;
   - effetti dello stadio 100 uguali a quelli del t22 e del t25 entro 7,5e-9 e 3,7e-9, con la stessa maschera
     (`parita_effetti_t22.json`, `parita_effetti_t25.json`).
4. **Si avvera:** 270 bersagli coperti su 300, 0 su 30 in P0, gene bersaglio a zero in tutti i P0 (`diagnostica.json`).
   Le righe tutte a zero sono 25: i 5 P0 restanti hanno almeno un vicino cis.
5. **Si avvera per costruzione** (dichiarato sopra): R-B dà 1,576.
6. **Si avvera:** il controllo negativo sulla cache r9 finisce con codice 0 e 30 bersagli coperti. Il difetto D4
   esiste: una cache del pannello sbagliato dà una previsione quasi vuota senza errore.

### Altre misure

- **Impronte (passo 3):** lo stadio 99 sui contesti finti riproduce quelle del 22/09 letti come B, A, C. 319 valori su
  319 sono identici; cambia solo la data.
- **CPM (passo 4):** i CPM di D/E/F sono uguali alle colonne permutate di A/B/C entro 1e-13.
- **γ = 1 con un pannello nuovo** (`diagnostica.json`), coseno fra il vettore tolto con il pannello finto (G-a) e
  quello con il pannello di oggi (G-b):
  - K562 0,59;
  - HCT116 0,88;
  - HEK293T 0,91;
  - CD4 0,97.

  **Interpretazione:** il riferimento tolto da γ = 1 cambia molto per K562 al cambio di pannello. Con un pannello nuovo
  il t22 non è più «lo stesso t22»; resta da decidere se fissarlo (G-b o G-c), difetto D9.
- **Ampiezza per contesto** (R-D, descrittiva): D 1,551, E 1,742, F 1,446.
- **Pilota prima/dopo per lo stadio 48:** 4 bersagli × 400 cellule × A/B/C con gli effetti del t22, stadio 48 della
  versione precedente la correzione (`e4edcd9~1`) contro quello corretto, entrambi senza `--contexts`. Stesso sha256
  del `.vcc` (`ee786ded…`).

### Difetti

- **Corretto:** D1 (stadio 48, `--contexts`, con test).
- **Visti in questa corsa, da correggere prima del 22/10:**
  - D4, la cache sbagliata che passa in silenzio;
  - D9, il riferimento di γ.
- **Dalla lettura del codice, non incontrati perché la prova usa file puliti:** D2, D3, D5, D6, D7, D8, D10–D13, N1 e N2.

**Per la chiusura dell'azione 3** (ogni difetto corretto con il suo test) mancano le correzioni di D4 e D9 e delle
altre voci. Un vincolo pratico per il 22/10: la forma piena chiede circa 17 GB liberi. Oggi ce ne sono 3,9, più 25 GB
nel Cestino che solo il proprietario può svuotare.
