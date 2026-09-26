# Cache "universo" di Orion (HCT116 e HEK293T): tutti i bersagli, non solo i 300

26 settembre 2026, sera. Filone F1 della scheda [R-V2](../../docs/piani/modello-v2.md), parte Orion; la
parte K562 è in [RISULTATI.md](RISULTATI.md). Script `orion_universe.py`, in questa cartella.

I download sono quelli autorizzati dal proprietario alle 15:25 del 26 settembre (scheda R-V2, «Piano
del 26 settembre sera»): X-Atlas/Orion da Hugging Face (`Xaira-Therapeutics/X-Atlas-Orion`), HCT116
109 file (46,6 GB) e HEK293T 223 file (79,7 GB), licenza CC-BY-NC-SA-4.0, un file alla volta, ogni
file cancellato appena usato.

## Stato quando è stato scritto questo file

- **Pilota: fatto** (4 file HCT116, sezione sotto). Parità esatta con lo stadio 102 e con lo stadio 98.
- **Esecuzione completa: in corso**, lanciata alle 18:43 locali come processo staccato dalla sessione
  (catena: stream HCT116 → finalize HCT116 → stream HEK293T → finalize HEK293T, un passo dopo
  l'altro, mai due download insieme). Alle 19:21 HCT116 era a 23 file su 109, 18.219 bersagli
  registrati, nessun pool ricostruito.
- **Memoria dello stream HCT116 in corso: cresce**, vedi «Memoria» sotto. Da HEK293T in poi lo
  stream gira in segmenti di 10 file, ognuno in un processo nuovo.
- I numeri finali di ogni linea (bersagli, cellule, byte e sha256 dei blocchi, parità con la cache
  r5 del pannello) li scrive il finalize in `manifest.json`, nella cartella dei blocchi e in
  `orion_hct116/` e `orion_hek293t/` qui accanto. Finché quelle cartelle non esistono, la linea
  non è finalizzata.

## Che cosa fa lo script (implementato)

1. **Elenco dei file**: quello dello stadio 102 (`list_files`), congelato in `files.json` insieme
   allo sha256 che Hugging Face pubblica per ogni file (oid LFS). Il pool di un file è il suo indice
   nell'elenco ordinato modulo 8, come nel `--finalize` dello stadio 102. Controllato: per entrambe
   le linee gli 8 pool coincidono con quelli di `reports/orion_2026-09-23/manifest_<linea>.json`.
   Il finalize lo ricontrolla e lo scrive nel manifest (`pools_match_stage102_manifest`).
2. **Un file alla volta**: download a intervalli paralleli (la funzione `download` dello stadio
   102), controllo di dimensione e sha256, lettura a blocchi di 512 cellule, filtro
   `pass_guide_filter == 1`. I conteggi di ogni cellula vanno sommati nel suo pool, sulla riga del
   suo bersaglio. Poi il file viene cancellato.
3. **Accumulatori su disco**: per ogni pool un file float32 con una riga per bersaglio (nell'ordine
   in cui i bersagli compaiono) e una colonna per ciascuno dei 18.533 geni dell'asse ufficiale. I
   token di Orion vanno sull'asse per nome, come negli stadi 102 e 98: 18.106 geni dell'asse hanno
   un token. Si scrive attraverso un buffer di 256 MiB, senza accumulatori densi in RAM. Per ogni
   (pool, bersaglio) si tengono anche cellule, UMI e conteggi su tutti i 38.606 token (la dimensione
   di libreria che usa lo stadio 98); i controlli non-targeting si sommano per pool in float64.
4. **Resistenza ai crash**: `journal.json` elenca i file applicati a ogni pool. Un pool viene
   segnato "sporco" prima che un file lo tocchi e pulito solo dopo la scrittura su disco (fsync).
   Un pool trovato sporco alla ripartenza viene azzerato e ricostruito dai suoi file, quindi nessun
   file è contato due volte. Un lock impedisce a due processi di lavorare sulla stessa linea.
5. **Finalize**: la stima è quella dello stadio 98, con le sue funzioni. `effects_from_pseudobulk`
   dà il ln fold change di ogni pool contro i controlli dello stesso pool, con SE quasi-Poisson
   (phi 0,2), pseudoconteggio 0,5, solo pool con almeno 10 cellule del bersaglio, media pesata sulle
   cellule e `z_shrink`. `AxisTable.from_source` porta tutto sull'asse, con NaN dove la frazione
   del gene nei controlli è sotto 1e-6. Una colonna in più tiene i conteggi fuori dall'asse, così
   la dimensione di libreria resta quella dello stadio 98.
   I blocchi npz hanno 600 bersagli e le chiavi dei blocchi K562 (`targets`, `shrunk`, `raw`, `se`,
   `n_cells`, `meta`). `index.csv` elenca **ogni bersaglio con almeno una cellula che passa il
   filtro**. Chi non ha nessun pool con 10 cellule resta senza effetti e ha il blocco vuoto
   nell'indice.
6. **Catena** (`--chain`): per ogni linea lo stream e poi il finalize, ogni passo in un processo
   nuovo che esegue lo script com'è in quel momento. Lo stream va in segmenti di 10 file (codice
   d'uscita 3: altri file da fare), ciascuno in un processo nuovo; anche `--line X` senza altre
   opzioni fa così. Se lo stream fallisce, riparte dal journal dopo dieci minuti, fino a tre
   fallimenti per linea.

## Pilota (misurato; `orion_pilot/`)

Quattro file HCT116 (`Batch1`, `Batch10`, `Batch100`, `Batch101`; 1,81 GB), in una cartella di lavoro
separata da quella dell'esecuzione completa.

- **Somme uguali a quelle dello stadio 102.** Per ciascuno dei primi tre file, `process_file` dello
  stadio 102 è stato rieseguito sullo stesso file scaricato, per i 168, 206 e 207 bersagli del
  pannello presenti. Cellule, UMI, conteggi sull'asse, dimensioni di libreria e controlli risultano
  identici, differenza massima 0 in ogni campo. Stesso esito contro i `part_*.npz` scritti dallo
  stadio 102 il 22-23 settembre: per questi tre file il contenuto remoto non è cambiato da allora
  (`orion_pilot/journal.json`).
- **Stima identica.** Il `--finalize` di questo script sui 4 file è stato confrontato con la catena
  vera: `--finalize` dello stadio 102 sui suoi part degli stessi 4 file, poi lo stimatore dello
  stadio 98. Sui 281 bersagli del pannello presenti, raw, se e shrunk sono identici bit per bit
  (differenza massima 0, nessuna maschera diversa) e n_cells coincide
  (`orion_pilot/finalize_min1_manifest.json`). Nel pilota la soglia era di 1 cellula per pool da
  entrambe le parti, perché con 4 file su 109 quasi nessun bersaglio arriva a 10. L'esecuzione
  completa usa 10, come lo stadio 98.
- **Righe**: nel pilota tutte le 112.709 righe lette passano il filtro, e già in 4 file compaiono
  17.150 bersagli con almeno una cellula.
- **Memoria.** Con le impostazioni iniziali il picco era di 1,7 GB di working set e 2,5 GB privati:
  pyarrow 25 legge in anticipo interi column chunk, e mimalloc trattiene la memoria liberata. Con
  quelle finali (niente lettura anticipata, allocatore di sistema, blocchi da 512 cellule, buffer
  da 256 MiB) si scende a 0,68-0,82 GB di working set e 1,28-1,29 GB privati. Il picco di 1,85 GB
  privati del terzo file viene dal controllo con `process_file`, che gira solo nel pilota
  (`orion_pilot/memory_*.csv`).
- **Tempi** per un file da circa 450 MiB: download 33-45 s, accumulo 46-57 s (nel quarto file:
  decodifica 7 s, disco 13 s, il resto calcolo). Il finalize del pilota (17.150 bersagli, 29 blocchi, 2,4 GB) ha richiesto 803 s a
  priorità bassa, mentre giravano altri due lavori pesanti; picco 0,70 GB di working set.

## Esecuzione completa

I numeri finali (bersagli per linea, cellule, controlli per pool, byte, parità con la cache r5)
stanno nei manifest del finalize, quando ci sono. Nei primi 23 file di HCT116 (misurato,
`orion_pilot/memoria_stream_hct116.txt`, istantanea del journal delle 19:21) ogni file da circa
450 MiB ha richiesto 25-40 s di download e 40-115 s di accumulo. L'accumulo rallenta quando la
macchina è carica.

## Memoria (misurato)

- **Lo stream HCT116 lanciato alle 18:43 gira tutto in un solo processo** (PID 5924), con il
  codice di quell'ora, e la sua memoria privata cresce. A fine file vale 0,68 GB dopo il primo,
  1,14 GB in media nei file 8-14, 1,41 GB nei file 15-21 e 1,71 GB al file 23: circa 40 MB in più
  per file, con oscillazioni ampie. Il picco privato è 2,19 GB. Il working set resta basso (picco
  0,85 GB; a fine file di solito 30-120 MB), quindi quella memoria è impegnata ma quasi tutta fuori
  dalla RAM.
- **Da dove viene:** misurato in isolamento su un file di 6 MB, 15 ripetizioni
  (`orion_pilot/memoria_*.log`). Il buffer dei pool non trattiene nulla (0 MB per chiamata), il
  download dello stadio 102 nemmeno (torna a circa 300 MB dopo ogni chiamata). La lettura del
  parquet con pyarrow lascia invece circa 2,6 MB per chiamata con l'allocatore di sistema; con
  mimalloc la crescita è più rumorosa e più alta.
  Interpretazione, non verificata: memoria trattenuta dentro pyarrow o dall'heap del processo, non
  dai dati accumulati.
- **Rimedio (implementato):** un processo non applica più di 10 file e poi esce, e il successivo
  riparte dal journal. La catena in corso lancia ogni passo come processo nuovo con lo script
  attuale, quindi il finalize di HCT116 e tutto HEK293T useranno i segmenti. Il processo HCT116 già
  partito non si può cambiare: se si arriva in fondo alla linea con la crescita di oggi, avrà
  qualche GB impegnato. Poco dopo le 19:15 la macchina aveva 23,5 GB impegnati su un limite di
  26,9 GB, con file di paging gestito dal sistema. La sessione che ha scritto questo file non ha il
  permesso di fermare quei processi. Chi vuole fermarli prima lo fa sui processi il cui comando
  contiene `orion_universe.py`, poi rilancia la catena (sezione sotto). Un file lasciato a metà fa
  solo ricostruire il suo pool.

## Dove stanno le cose

- Blocchi: `C:/Users/ferra/vcc2026-data/processed/universe_orion_hct116_2026-09-26/` e
  `.../universe_orion_hek293t_2026-09-26/` (`orion_<linea>_NN.npz`, `index.csv`, `manifest.json`).
- Copie di indice e manifest: `orion_hct116/` e `orion_hek293t/`, in questa cartella.
- Accumulatori, cioè il pseudobulk per pool, riusabile con un'altra stima senza riscaricare nulla:
  `C:/Users/ferra/vcc2026-data/interim/orion_universe_<linea>/` (`pool0.f32` … `pool7.f32` float32,
  righe nell'ordine di `targets.json`, 18.533 colonne; `pool<k>_counts.npz`; `journal.json`;
  `files.json`). Occupano circa 11 GB per linea.
- Log della catena: `C:/Users/ferra/vcc2026-data/interim/orion_universe_chain_2026-09-26.log`.
- Cartella del pilota: `C:/Users/ferra/vcc2026-data/interim/orion_universe_pilot_hct116/` (6,4 GB,
  rigenerabile; se serve spazio si può spostare nel Cestino). Le due cartelle delle prove di
  memoria (`orion_universe_leaktest`, con il file `HEK293T_Batch72` da 6 MB, e `orion_universe_segtest`)
  sono state spostate nel Cestino verso le 19:22 del 26 settembre.

Un bersaglio si legge così:

```python
import numpy as np, pandas as pd
root = "C:/Users/ferra/vcc2026-data/processed/universe_orion_hct116_2026-09-26/"
idx = pd.read_csv(root + "index.csv", keep_default_na=False).set_index("target")
t = "TP53"
if t in idx.index and idx.at[t, "chunk"]:          # chunk vuoto: nessun pool con 10 cellule
    z = np.load(root + idx.at[t, "chunk"])
    i = list(z["targets"]).index(t)
    raw, se, shrunk = z["raw"][i], z["se"][i], z["shrunk"][i]   # asse ufficiale, NaN dove non misurato
```

## Come controllare o riprendere

- Stato: `scripts\py.cmd reports\universo_2026-09-26\orion_universe.py --line HCT116 HEK293T --status`
  (file applicati, pool sporchi, PID del processo che ha il lock, picchi di memoria).
- Se il processo si è fermato (spegnimento, sospensione lunga, rete assente oltre i tentativi),
  basta rilanciare la catena: riparte dal journal, un pool rimasto a metà viene ricostruito, e una
  linea già finalizzata viene saltata (la catena rilanciata va in segmenti di 10 file). Comando:
  `scripts\py.cmd -u reports\universo_2026-09-26\orion_universe.py --line HCT116 HEK293T --chain`.
  Il 26 settembre è stato lanciato staccato dalla sessione con `Win32_Process.Create`, con
  l'uscita accodata al log della catena.
- Un finalize non sovrascrive mai. Se uno fallisce a metà, se ne rilancia un altro con `--out` e
  `--report` nuovi.

## Limiti

- La stima è quella dello stadio 98, quindi ne eredita i limiti. I "donatori" sono pool di lotti
  GEM, non repliche biologiche. Un bersaglio senza un pool con almeno 10 cellule non ha effetti;
  nessuna stima con soglie diverse è stata calcolata, ma gli accumulatori permettono di farla.
- I bersagli hanno i nomi del campo `gene_target` di Orion. Il legame con l'asse ufficiale è solo per
  nome esatto, come nello stadio 98: gli alias non sono riconciliati.
- La parità è verificata sul pilota e, a finalize fatto, sui bersagli del pannello contro la cache
  r5. Per gli altri bersagli vale perché il codice è lo stesso, non per un confronto indipendente.
- La licenza è CC-BY-NC-SA-4.0. Per l'uso di Orion in un invio vale quanto dice lo stadio 102
  (decisione del proprietario, D-004).
- L'esecuzione dipende dal portatile: se va in sospensione, i download si fermano finché non si
  risveglia.
