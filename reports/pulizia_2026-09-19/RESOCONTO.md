# Resoconto della pulizia del codice — 19 settembre 2026

**Dove:** branch `refactor/pulizia`, worktree `../vcc2026-refactor`. Nessun push, nessun
merge su `main`, nessuna modifica alla cartella principale. Il branch contiene il merge
di `main` a `ec980b4` (il lavoro della notte del 19), così la pulizia agisce sull'albero
corrente, script 95 compreso.

**Il codice tolto non è perduto:** sta nel tag annotato
`archivio/pre-pulizia-2026-09-19`, che punta a `ec980b4`. L'elenco completo, con righe,
funzione e comando di recupero per ogni percorso, è in
[`docs/ARCHIVIO_CODICE.md`](../../docs/ARCHIVIO_CODICE.md). Il tag **non è stato
inviato** a nessun remoto.

**Niente è stato cancellato in `reports/`, `docs/`, `configs/`, `notebooks/`**, e nessun
checkpoint è stato modificato. I checkpoint continuano a citare per nome il codice
archiviato: è per questo che `scripts/31_check_docs.py` ora accetta come validi i
percorsi elencati nell'archivio.

---

## 1. Righe prima e dopo

File `.py` tracciati, contati con `git ls-files … | xargs wc -l` a `7391e69` (l'albero
come stava su `main`) e a `HEAD`.

| Cartella | File prima | File dopo | Righe prima | Righe dopo | Δ |
|---|---:|---:|---:|---:|---:|
| `src/` | 72 | 18 | 24.014 | 4.902 | **−19.112** |
| `scripts/` | 80 | 29 | 18.245 | 5.497 | **−12.748** |
| `tests/` | 18 | 4 | 8.956 | 1.405 | **−7.551** |
| **totale** | **170** | **51** | **51.215** | **11.804** | **−39.411 (−77,0%)** |

Restano inoltre, fuori dal conteggio `.py`, tre wrapper in `scripts/`: `py.cmd`,
`vcc.cmd` ed `env.ps1` (§6).

La somma dei sedici commit qui sotto fa esattamente −39.411: il conto torna riga per
riga, non per differenza.

---

## 2. Commit per commit

I primi quattro sono di stamattina, con il mandato vecchio («nessun comportamento
cambiato, niente cancellazioni»); gli altri sono la semplificazione aggressiva.

| Commit | Che cosa | Righe `.py` |
|---|---|---:|
| `6040bec` | Un solo lettore di righe h5ad: `read_rows` esisteva quattro volte (stadi 42, 75, 92, 95), ora è `sc_stream.read_rows` e `inference.read_csr_rows` | **−33** |
| `af36846` | Una sola porta sui bulk Replogle: le stesse otto righe aprivano il file in sette stadi più `common_from_bulk`; ora `predictor_sc.read_bulk` e `bulk_symbols` | **+2** |
| `ba8ed5d` | `load_effects`, venti righe identiche negli stadi 73 e 75, spostata in `vcc2026.bench` | **−22** |
| `b7e83ed` | Quattro definizioni che nessuno raggiungeva (`prediction_on_axis`, `is_research_brief`, `campaign_id`, `sc_stream.write_json`) | **−24** |
| `b4f53b1` | `configs/**/*.yaml text eol=lf`, perché il `rule_md5` registrato nei verdetti sia riproducibile (§4a) | 0 |
| `4b20fd6` | Il controllo documentale impara l'archivio: `docs/ARCHIVIO_CODICE.md`, la lettura in `31_check_docs.py`, il test del caso | **+63** |
| `8656177` | `_Adam` copiata in `conditioned.py`, unico chiamante rimasto | **+29** |
| `db35b52` | Archiviato l'orchestratore (27 file) | **−11.867** |
| `d4a11f9` | Archiviato l'oracolo pairwise (28 file, fixture comprese) | **−1.698** |
| `dd2e001` | Archiviata la catena di cicli (`scripts/32`, `ciclo.cmd`, il suo test) | **−2.631** |
| `093c2d7` | Archiviata l'ingestione remota (18 file) | **−4.137** |
| `47053c5` | Archiviata la pipeline trial-01 pseudobulk (9 file) | **−2.916** |
| `aa307b1` | Archiviato il benchmark modulare pseudobulk (37 file) | **−13.219** |
| `d32ef2f` | Archiviate le sonde e gli audit delle sorgenti (22 file) | **−2.775** |
| `5297e14` | Tre funzioni rimaste senza chiamanti: `align_to_axis`+`AlignedMatrix`, `predicted_profile`, `reset_caches` | **−183** |
| `d6f913b` | Registro annotato (27 righe) e `PULIZIA_2026-09-18.md` spostato in questa cartella | 0 (solo documenti) |

Prima di **ogni** commit: `python scripts/31_check_docs.py` e
`.\scripts\py.cmd -m unittest discover -s tests`, entrambi verdi. Il numero di test
scende man mano che i test del codice archiviato se ne vanno con lui: 582 → 401 → 358 →
316 → 281 → 239 → 78.

---

## 3. L'insieme tenuto, e come è stato calcolato

Non a occhio: con la chiusura transitiva degli import a partire dai punti di ingresso
dichiarati nel mandato (stadi 30, 31, 46, 48 e dal 71 al 95), risolvendo anche gli
import relativi e quelli dentro le funzioni. Lo script di analisi sta nella cartella
temporanea della sessione; il suo risultato è riproducibile con un `grep` mirato su
ciascun modulo.

**29 script** — 30, 31, 46, 48, 71…95 — più i wrapper `py.cmd` e `vcc.cmd`, che i job
Colab usano (`notebooks/colab_jobs/*.sh` chiama 48, 71, 72, 73, 75, 76).

**18 moduli di `src/vcc2026/`**: `__init__`, `bench`, `bench_score`, `conditioned`,
`config`, `de_tools`, `evaluation`, `generator`, `genes`, `inference`, `manifest`,
`packaging`, `predictor_sc`, `resources`, `sampling`, `sc_effects`, `sc_stream`,
`submission`.

**4 file di test**, che coprono il codice tenuto: `test_packaging_parity` (46 test),
`test_doc_workflow` (16), `test_sc_pipeline` (11), `test_conditioned` (5) = **78 test**.

Un solo arco teneva in vita tutto il resto: `conditioned.py` importava `_Adam` da
`benchmark/models.py`, dentro `fit()`. Quell'unico import trascinava `benchmark/`
intero, più `vcc2026/models.py` e `signatures.py`. La classe è stata copiata in
`conditioned.py` **senza una modifica** — 19 righe non vuote, `difflib` non trova
differenze — e verificata anche numericamente: 500 passi a lr 3e-3, l2 1e-4 su tre
tensori da seme fisso, vecchio e nuovo ottimizzatore affiancati, parametri identici
**byte per byte**, massimo |Δ| 0,0, stato `t`/`m`/`v` uguale alla fine.

Dopo la copia, la chiusura transitiva si ferma su 18 moduli invece di 24: è così che il
benchmark modulare ha potuto essere archiviato.

---

## 4. Le quattro riproduzioni di riferimento

Tutte e quattro eseguite **prima** delle rimozioni e **dopo**, scrivendo in una cartella
temporanea, mai sopra un report.

### a) Stadio 94 sui banchi in `G:\Il mio Drive\vcc2026\runs\conditioned_2026-09-18`

Confronto con `reports/conditioned_2026-09-18/verdict/verdict.json`:
**identico campo per campo**, `finished_utc` a parte. Verdetto `DISCARD`, le stesse
condizioni, le stesse ampiezze scelte, gli stessi bootstrap.

Una cosa è stata trovata e corretta strada facendo. Al primo tentativo l'unico campo
diverso era `rule_md5`: `80a33f34…` invece di `c1bc011f…`. Il contenuto della regola era
identico — a cambiare erano i **fine riga**. `core.autocrlf` scrive CRLF al checkout
mentre l'indice tiene LF, e nella cartella principale quei file stanno per caso in LF.
Il commit `b4f53b1` fissa `configs/**/*.yaml text eol=lf`; da lì i tre file di regola
che i verdetti nominano tornano al loro md5 registrato:

```
conditioned_rule.yaml      c1bc011f445fb706b7fa38b086e0bd87
common_component_rule.yaml 6b5bad61a4276a80727edc936c41ef11
specificity_rule.yaml      dd472a1e9905e930c7d8a1689bf449ce
```

Non è un dettaglio di forma: `rule_md5` è la prova che un verdetto ha applicato *quella*
regola, e finora non era riproducibile su un checkout diverso.

### b) Stadio 84 per il t07

Confronto con `reports/prediction_t07_2026-09-19/prediction.json`, `written_utc` escluso
come chiede il mandato: **identico entro 1e-12** in ogni campo, compresi i sei membri,
il punto di calibrazione e la media attesa +0,0101.

### c) Stadio 95 sullo split T

Confronto con `reports/conditioned_2026-09-18/effect_space/centered_T_k562_test.json`:
**identico entro 1e-12**, `finished_utc` escluso — i cinque bracci, le correlazioni
centrate, i loro intervalli bootstrap e le quote di corrispondenza.

### d) Stadio 75 in piccolo, in locale

`--n-targets 4 --control-cells 300 --cis-pairs … --seed 2026`, stesse opzioni prima e
dopo, undici bracci.

`bench.json`: tutte le metriche aggregate coincidono entro 1e-12. Confrontando invece
**bit a bit**, 6 valori su 78 differiscono, tutti `de_wilcoxon_lfc_nmae`, con scarto
relativo massimo **4,3·10⁻¹⁶**. Nei file per bersaglio: 331 valori, 7 diversi, scarto
relativo massimo **8,9·10⁻¹⁶**, e in 8 file su 10 cambia l'**ordine delle righe**.

Prima di attribuire quegli scarti alla pulizia ho eseguito lo stadio una **terza volta,
sullo stesso identico codice**. Risultato del controllo:

| Confronto | Metriche aggregate diverse (su 78) | Scarto rel. max | Valori per bersaglio diversi (su 331) | Scarto rel. max | File riordinati |
|---|---:|---:|---:|---:|---:|
| vecchio contro nuovo | 6 | 4,3·10⁻¹⁶ | 7 | 8,9·10⁻¹⁶ | 8 |
| **stesso codice, due esecuzioni** | 3 | 3,0·10⁻¹⁶ | 7 | 8,7·10⁻¹⁶ | 10 |

**Lo stadio 75 non è riproducibile bit a bit con sé stesso**, e la differenza fra prima e
dopo è della stessa natura e dello stesso ordine di grandezza della differenza fra due
esecuzioni identiche. Un esempio: il `de_wilcoxon_lfc_nmae` del braccio `baseline` vale
0,741060606988922 in un run e 0,7410606069889222 nell'altro, **a codice invariato**, e i
due valori si scambiano fra le esecuzioni. Sul criterio chiesto (1e-12) la prova passa
ampiamente; sotto quel livello il rumore è dello stadio, non della pulizia. Vale la pena
saperlo: chi confrontasse due banchi all'ultima cifra confronterebbe il rumore.

---

## 5. Che cosa garantisce la tracciabilità

- Il tag `archivio/pre-pulizia-2026-09-19` (annotato, non inviato) su `ec980b4`.
- `docs/ARCHIVIO_CODICE.md`: 144 file e 39.408 righe in sette gruppi, più le tre funzioni
  tolte da file tenuti; per ognuno righe, una frase su che cosa serviva — condensata dal
  docstring del file stesso, non inventata — e il comando `git show`.
- `scripts/31_check_docs.py` legge quell'elenco e accetta un percorso archiviato, e
  **solo** quello: un percorso che sparisce senza comparire lì resta un errore. Il caso è
  coperto da `tests/test_doc_workflow.py::test_an_archived_path_counts_as_existing`, che
  verifica le tre cose — il percorso elencato passa, la cartella che lo contiene passa,
  il percorso non elencato viene ancora segnalato.
- 27 righe del registro dicono ora «Codice archiviato nel tag …». **Nessuna ha cambiato
  stato**: un documento `attuale` resta `attuale`, perché quello che racconta è vero
  quanto prima; si è spostato il codice, non la conclusione.

---

## 6. Ciò che non ho tolto, e perché

- **`configs/`, `notebooks/`, `.agents/`, `.claude/`**: il mandato limita l'archiviazione
  a `src/`, `scripts/` e `tests/`. Restano quindi `configs/ciclo_giornaliero/` (8 file) e
  `configs/orchestrator/` (20) pur essendo la configurazione di codice archiviato, e
  `notebooks/remote_ingest_hepg2.ipynb`, che chiama moduli archiviati. Il notebook oggi
  non funzionerebbe senza recuperarli dal tag: è la conseguenza più concreta
  dell'archiviazione, ed è segnalata qui perché la si veda prima di riaprirlo.
- **`scripts/env.ps1`** (12 righe): nessun file tenuto lo usa, quindi per la regola
  andrebbe archiviato, ma `README.md` lo documenta come modo di attivare l'ambiente in
  PowerShell. L'ho tenuto per non rompere una procedura scritta, e lo segnalo: se vuoi,
  se ne va in una riga.
- **La copertura dei test scende da 582 a 78.** Non è un effetto collaterale: i 504 test
  spariti erano i test del codice archiviato, e archiviare il codice senza i suoi test
  lascerebbe una suite che non compila. Quello che resta copre ciò che resta: parità di
  impacchettamento (46), flusso documentale (16), pipeline a singola cellula (11), rete
  condizionata (5).
- **Le riproduzioni coprono quattro stadi, non tutta la pipeline.** 71, 72, 73, 76 e 92
  girano su dati di scala Colab che qui non ci sono: per loro la garanzia è indiretta —
  l'analisi degli import dice che nessuno di essi tocca codice archiviato, e i test
  tenuti passano — ma **non** è una riesecuzione. Se vuoi una prova diretta, il modo è
  rimettere in coda un job con lo stesso input e confrontare il `bench.json`.
- **Nessun altro candidato è rimasto.** Dopo l'ultimo commit, la scansione degli import
  inutilizzati non trova più niente, e quella delle definizioni pubbliche senza uso
  neppure: nel codice tenuto non c'è più codice morto che io sappia riconoscere.

---

## 7. Come rifare le verifiche

```bash
git -C ../vcc2026-refactor log --oneline 7391e69..HEAD
git -C ../vcc2026-refactor show archivio/pre-pulizia-2026-09-19:src/orchestrator/engine.py | head

python scripts/31_check_docs.py                    # dice anche quanti percorsi archiviati accetta
.\scripts\py.cmd -m unittest discover -s tests     # 78 test

for d in src scripts tests; do git ls-files "$d/*.py" "$d/**/*.py" | sort -u | xargs wc -l | tail -1; done
```

Le quattro riproduzioni sono i comandi degli stadi 94, 84, 95 e 75 con gli argomenti
registrati nei rispettivi report (`inputs`, `benches`, `args`), scritti in una cartella
temporanea e confrontati con un raffronto JSON ricorsivo a tolleranza 1e-12 che ignora
solo i campi di data. Gli script usa e getta stanno nella cartella temporanea della
sessione e non sono versionati; i comandi si ricostruiscono dai campi `args` dei report.
