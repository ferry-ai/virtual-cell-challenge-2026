# Banca canonica: registro delle fonti, release congelata e fit con ricevuta di consumo

7 ottobre 2026, Claude Code (sessione `6cf149d8`), incarico del proprietario in chat sul binario
[R-LEAD](../../../docs/piani/strategia-scientifica.md). **È l'ingresso unico** del percorso
archivio verificato → banca → fonti derivate → release congelata → fit → ricevuta del consumo.
Sostituisce come guida operativa [RIUSO r3](../percorso_riusabile_2026-10-05/RIUSO_r3.md), che resta
come prova della release t36.

**Che cosa non è.** Non è un punteggio, non è una validazione a linee escluse (produzione, bersagli
nascosti vuoti) e **non chiude D-053**: 28 unità di banca su 45 arrivano a un trainer, le altre 17
sono nominate qui sotto con il motivo. Nessun invio VCC è stato fatto o preparato.

## 1. Stato in una pagina (misurato)

| Livello | Riferimento | Che cosa dice |
|---|---|---|
| Registro canonico | [REGISTRO_FONTI_r1.md](REGISTRO_FONTI_r1.md), [JSON](registro_fonti_r1.json) | 45 unità di banca, 31 studi, 100 record del catalogo r4: identità, provenienza e una sola destinazione ciascuno |
| Regola di ammissione | [PROTOCOLLO.md](PROTOCOLLO.md) | scritta alle 01:35 prima di ogni lancio; non spostata |
| Derivazioni dalla banca | [ammissione_r1.json](ammissione_r1.json), cartelle `derivazioni/<fonte>/` | 12 job nuovi conclusi e verificati, più HIPSCI mirato già derivato: 13 tabelle |
| Release congelata | [fit/release_r1.json](fit/release_r1.json), sha256 `0650d1d6…771c8c` | 17 fonti al voto: le 13 del t36 più 4 nuove |
| Fit reale | [fit/r1/completion/](fit/r1/completion/consumo.json) | transfer t25 invariato; 17 fonti attese = verificate = lette dallo stage 100 |
| Secondo avvio | [fit/riuso_r2.json](fit/riuso_r2.json) | stessa release, nessuna derivazione rilanciata, effetti byte-identici |

**Numeri, tenuti distinti** (dal registro; nessuno è dedotto dal conteggio di job o file):

| Grandezza | Valore | Nota |
|---|---:|---|
| GB grezzi unici conservati | 395,75 | 41.765.207 righe cellulari; include Jurkat GSE249595, che non ha banca |
| GB derivati: banca (statistiche per riga) | 38,12 | `count_sum`, maschere, medie, varianze, righe |
| GB derivati: campioni cellulari 32/64/128 | 189,20 | persistenti; **nessun trainer li consuma** in questo percorso |
| GB derivati: tabelle di effetti | 0,24 | le 26 tabelle del registro |
| Cellule nella banca | 39.973.948 | i 38.176 controlli H1 sono in due unità e qui contati due volte |
| Gruppi di linea | 15 | un gruppo non è una linea: `iPSC` riunisce KOLF2.1J, i cloni HIPSCI e le iPSC di Tian |
| Contesti distinti | 54 | (studio, contesto, condizione); i cloni HIPSCI contano come donatori |
| Donatori o cloni distinti | 51 | 4 donatori CD4, 2 Shifrut, cloni HIPSCI contati una volta |
| Fonti ammesse al voto | 17 | 13 hanno bersagli del pannello; HepG2, Jurkat, RPE1 e K562 essential ne hanno 0 |
| Fonti effettivamente lette dal fit | 17 | hash di ogni tabella nel manifest dello stage 100 |
| Unità di banca dietro le fonti lette | 28 su 45 | più la tabella storica K562 BULK, che non viene dalla banca |
| Cellule nelle righe di banca lette | 2.367.170 | controlli più bersagli del pannello; K562 BULK escluso dal conto |

**Fonti nuove al voto** (regola del verso del knockdown, mediana del log-rapporto sul proprio gene):
HIPSCI mirato (5 bersagli, 19 cloni, mediana fra i cloni −1,47), Xu 2023 HEK293 (5, −1,43),
Tian 2021 neuroni CRISPRi (6, −0,48), Tian 2019 neuroni giorno 7 (1 bersaglio, RFK, **−0,0014**).

> **Caso limite da decidere.** Tian 2019 neuroni passa la regola alla lettera, ma −0,0014 non è
> evidenza di knockdown; Tian 2019 iPSC, stesso bersaglio, è a +0,049 ed è fuori. La regola senza
> soglia di ampiezza è troppo debole per fonti con un solo bersaglio: non l'ho spostata dopo la
> lettura. L'effetto pratico è un voto in più, quasi nullo, sul solo RFK. Togliere quella fonte è
> una release r2 (§2, passo 6), decisione del proprietario.

**Che cosa cambia nel modello.** Niente: media a peso 1, effetti shrunk, gamma 1, ampiezza 1,576,
testa cis. Il fit ricostruisce la ricetta del t36 dagli stessi mount e ne ritrova l'hash registrato
(`3109a6d9…`), poi la confronta con la release: gli effetti differiscono **solo sui 17 bersagli** che
ricevono un voto nuovo, e su nessun altro. Bersagli coperti 300 su 300 in entrambi.

**Due verifiche d'identità chieste dall'incarico.**
- *K562:* la banca a singola cellula (blocchi a+b sommati, 1.989.578 cellule) e la tabella storica
  BULK danno gli stessi 272 bersagli con coseno mediano 0,994 (decimo percentile 0,984). Sono lo
  stesso esperimento: vota una volta sola, con la tabella storica. Lettura descrittiva.
- *A549:* gli «otto pool» del 27 settembre non sono donatori: sono il codice di una colonna di lotto
  modulo 8 ([prova](a549_identita_r1.json)). Stesse cellule per bersaglio nelle due derivazioni;
  coseno mediano 0,94 fra stima per lotto e stima unica. `donor_or_clone` non riportato è corretto.

## 2. Come si esegue (un solo ingresso)

Tutto passa da `percorso.py`, con `.\scripts\py.cmd`. Ogni uscita si scrive una volta: per rifare un
passo si sceglie un nome nuovo. Servono i tre token Kaggle già configurati.

```powershell
$p = "reports/modelli/banca_canonica_2026-10-07/percorso.py"
.\scripts\py.cmd $p piano <piano_rN.json>              # 1. piano dai metadati, senza leggere conteggi
.\scripts\py.cmd $p preflight <preflight_rN.json>      # 2. slot liberi sui tre account (vale 15 minuti)
.\scripts\py.cmd $p prepara <fonte>                    # 3. pacchetto del job; VCC_REV=r2 per una revisione
.\scripts\py.cmd $p lancia <fonte> <preflight_rN.json> #    un solo push, con registro e controllo doppioni
.\scripts\py.cmd $p raccogli <fonte>                   #    ricevute piccole e codice salvato verificati
.\scripts\py.cmd $p ammissione <ammissione_rN.json> <cartella tabelle nella radice dati>   # 4. regola
.\scripts\py.cmd $p fit dataset <cartella di stage>    # 5. tabelle di effetti in una cartella di stage
.\scripts\py.cmd $p fit dataset-create <cartella di stage> fit/dataset_create_rN.json   # dataset privato
.\scripts\py.cmd $p fit dataset-status fit/dataset_status_rN.json                       # conferma
.\scripts\py.cmd $p fit release fit/release_rN.json    # 6. release congelata
.\scripts\py.cmd $p fit package fit/release_rN.json rN # 7. pacchetto del fit; poi: fit lancia rN <preflight>
.\scripts\py.cmd $p fit raccogli rN                    #    consumo.json verificato
.\scripts\py.cmd $p registro <out.json> <out.md> rN    # 8. registro rigenerato con il consumo
```

**Per un nuovo training sulla stessa banca** bastano i passi 7–8: nessuna ingestione, nessuna
derivazione ([prova](fit/riuso_r2.json); il fit dura circa tre minuti). **Per aggiungere una fonte**
si scrive la sua voce in [derivazioni.json](derivazioni.json) e si rifanno i passi 1–8 solo per lei, con
`VCC_BANCA_REV=r2` per ammissione, dataset e release. **Per un altro insieme di bersagli** si cambia il
pannello nel pacchetto: la banca `count_sum` contiene tutti i bersagli nativi, le tabelle di effetti
di oggi solo quelli del pannello.

Guardie nel runtime, non nei documenti: ogni file di banca è cercato **per contenuto** (dimensione e
sha256 della ricevuta), mai per nome o titolo; ricetta dello stimatore, asse dei geni e pannello
sono verificati prima di ogni stima; il fit si ferma se una fonte attesa manca, è diversa o non
risulta fra le tabelle lette dallo stage 100. Nessun ripiego su pilot, cache storiche o `latest`.
Otto prove su banche sintetiche: `consumer/test_runtime.py`.

Le 67 tabelle `rows.csv` (57 MB) e le tabelle di effetti stanno nella radice dati,
`processed/banca_canonica_2026-10-07/`; qui restano i manifest con percorsi, dimensioni e hash
([rows_r1/](rows_r1/POSIZIONE.json)).

## 3. Che cosa resta fuori, e che cosa lo sbloccherebbe

| Fonti | Unità | Stato | Che cosa serve |
|---|---:|---|---|
| A549, Frangieh, Sunshine, Dixit (3 unità), Shifrut | 7 | KO derivato e conservato, non votato | decidere se un braccio KO entra nel transfer (scelta di modello, GENERALIZZAZIONE §2.1) o serve un trainer che lo consumi |
| Norman 2019, Tian 2021 CRISPRa | 2 | attivazione derivata, non votata | un modello che usi l'attivazione; mai nel voto di knockdown |
| K562 GWPS a/b a singola cellula | 2 | derivata; l'esperimento vota già con la tabella BULK | niente: sostituire la tabella BULK sarebbe una scelta dichiarata, non un difetto |
| Tian 2019 iPSC | 1 | derivata, non ammessa (verso +0,049) | regola di QC per le gocce non filtrate e le etichette a più guide |
| HIPSCI genome-wide, fitness e non | 2 | in banca, non derivabili con lo stimatore originale | 36 e 12 cellule di controllo in tutto: serve un riferimento dichiarato diverso dai controlli abbinati |
| Papalexi 2021 arrayed | 1 | in banca | l'unico bersaglio del pannello ha 4 cellule, sotto il minimo di 10 |
| Datlinger 2017 e 2021 | 2 | in banca | le etichette sono nomi di guida: serve una mappa guida → gene dichiarata. Controllo fatto dopo il commit: anche togliendo prefisso di libreria e numero di guida (32 e 20 nomi di gene), **nessuno è nel pannello**; la mappa serve alla banca generale, non a questo transfer |
| 44 record del catalogo r4 senza banca | — | motivo del catalogo riportato nel registro, **non riverificato qui** | topo, enhancer, farmaci (testa separata), ORF, proteine, Southard (ingestione mai chiusa), Adamson, DLD-1, Mixscale |

Altre lacune note: Orion HCT116 e HEK293T sono in banca ma **assenti dal catalogo r4**; per le unità
CD4, KOLF pan e Orion il registro non riporta i GB grezzi per unità (solo il totale); le cellule del
catalogo e quelle della banca differiscono per CD4 (per esempio 3.074.496 contro 1.750.820 in D1
Rest) e di poco per Tian 2019: la differenza non è spiegata in questa cartella. I duplicati
biologici fra studi (stesse linee in laboratori diversi) sono tenuti come fonti distinte; il
doppio conteggio evitato è quello dello stesso esperimento (13 alias, K562 BULK e GWPS, H1 train e
val, condizioni CD4).

## 4. Incidenti e correzioni di questa sessione

- Due job (`tian2019_ipsc` r1, `norman2019` r1) si sono fermati sulla guardia d'identità prima di
  ogni stima: le loro banche stanno in copie montabili con nomi di file diversi. Corretto cercando
  i file per contenuto; rilanciati come r3 e r2. Il pacchetto `tian2019_ipsc` r2 è preparato e
  **mai lanciato**.
- `kaggle datasets create` fallisce con un percorso a barre dritte su Windows e la sua barra di
  avanzamento non si decodifica in cp1252: lo stato si rilegge con `fit dataset-status`.
- Un primo `riuso_r1.json` confrontava l'hash del pacchetto, che contiene il nome del job: dice
  `all_true: false` per quel solo motivo. Vale [riuso_r2.json](fit/riuso_r2.json).

Proposte di pulizia, **nessuna eseguita**: [DA_ELIMINARE.md](DA_ELIMINARE.md).
