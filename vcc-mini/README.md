# vcc-mini — banco locale fra linee cellulari (Alfredo)

Un dataset piccolo per addestrare in locale, o su Colab, un modello che prevede l'effetto di un
knockdown CRISPRi in una linea cellulare mai vista, dati i suoi controlli e gli effetti misurati in
altre linee. È un banco di pseudobulk: **non produce punteggi VCC** e dei sei membri copre in proxy
solo MSE e PDS.

Stato al 28 settembre 2026: codice scritto e provato solo su dati sintetici. Nessun dato reale
costruito e nessun confronto sui dati reali eseguito.

## Dati (`sources.json`, 2,69 GB, CRISPRi Perturb-seq, CC BY 4.0)

| chiave | linea | file | MB | fonte |
|---|---|---|---|---|
| K562_ess | K562 | K562_essential_raw_bulk_01.h5ad | 80 | Replogle 2022, Figshare+ 20029387 |
| K562_gw | K562 | K562_gwps_raw_bulk_01.h5ad | 375 | stesso deposito |
| RPE1 | RPE1 | rpe1_raw_bulk_01.h5ad | 95 | stesso deposito |
| HepG2 | HepG2 | NadigOConner2024_hepg2.h5ad | 851 | Nadig 2025, mirror scPerturb, Zenodo 13350497 |
| Jurkat | Jurkat | NadigOConner2024_jurkat.h5ad | 1.294 | stesso mirror |

Le quattro linee condividono la libreria di geni essenziali. K562 genome-wide aggiunge bersagli non
scelti per essenzialità. Sono le stesse quattro linee analizzate da Molina e Zhang (2026), citati in
`reports/modello_contesto_2026-09-27/RISULTATI.md`: lì nessun modello recupera l'interazione
bersaglio × linea dai soli controlli.

## Passi

```
python fetch.py                          # scarica in raw/ e verifica l'md5
python build_mini.py --inspect           # colonne ed etichette, prima di costruire
python build_mini.py                     # scrive mini/
python train.py --held HepG2 --fold 0 --seed 0 --out runs/hepg2_f0_s0
python aggregate.py runs/hepg2_f0_s* --out runs/aggregate.json
python -m unittest discover -s tests     # fuga d'informazione e parametri per gene
```

`make_synthetic.py` scrive dati finti nello stesso formato, per provare la pipeline. `VCC_MINI_DATA`
sposta `raw/` e `mini/` in un'altra cartella.

## Su Colab in una cella

`python make_runcell.py` scrive `runcell.py`: una cella sola che porta con sé il codice e fa tutto
in sequenza, dai dati già su Drive:
1. i test;
2. la costruzione di `mini/`;
3. l'addestramento scelto da `RUN`.

| `RUN` | Che cosa fa |
|---|---|
| `build` | si ferma dopo test e dataset |
| `smoke` | aggiunge una prova breve, solo per vedere che gira |
| `full` | 4 linee tenute fuori × 2 semi, poi `aggregate.py` |

Si apre un notebook vuoto, si incolla la cella e si preme Shift+Invio. Le uscite vanno in cartelle
nuove su Drive (`mini_<data>`, `runs_<data>`).

## Google Drive e Colab

- `make_catalog.py` congela in `catalog.json` URL, byte e checksum di tutti i file che si possono
  caricare su Drive, presi dalle API dei depositi. I tier sono `mini`, `sc_replogle`, `sc_k562_gw`,
  `cd4`, `orion_hct116` e `orion_hek293t`: 341 file, 258,7 GB in tutto.
- `drive_fetch.py` scarica i file sulla VM di Colab, li verifica, li copia su Drive e scrive un
  `.verified.json` accanto a ciascuno.
- `gen_notebook.py` genera `colab_drive_loader.ipynb` con il codice incorporato. Va rilanciato dopo
  ogni modifica ai file incorporati.

Su Drive la struttura è `vcc-data/{raw/<tier>/, code/, logs/, mini_<data>/}`.

## Modello e valutazione

- **TransferNet** (`model.py`): media convessa, per gene, degli effetti dello stesso bersaglio nelle
  altre linee, con attenzione e un gain costruiti da quantità trasferibili; più un termine a programmi
  per i bersagli senza sorgenti. Nessun parametro indicizzato per gene o per linea.
- **Regimi sulla linea tenuta fuori:**
  - **CT**: bersaglio mai visto in training, i suoi effetti nelle altre linee in ingresso;
  - **J**: bersaglio mai visto, nessuna sorgente;
  - **C**: bersaglio visto in altre linee;
  - **CT_max2**: come CT, con al massimo tante sorgenti quante ne ha viste il training.
- **Riferimenti:** `zero`, `train_mean`, `oracle_mean`, `transfer_simple`, `transfer_gamma1` e, per
  K562, `replicate`. Nessuno dei due trasferimenti è la ricetta del t22: niente restrizione, niente
  pesi di affidabilità, niente cis.
- **Incertezza:** bootstrap appaiato sui bersagli; `aggregate.py` media i semi e applica la regola
  di lettura, che è una bozza non ancora approvata.

## Correzioni della revisione del 27 settembre

| Punto | Correzione |
|---|---|
| P1 | Bootstrap appaiato sui bersagli e più semi (`train.py`, `aggregate.py`); il sottoinsieme C è lo stesso per ogni seme |
| P2 | `transfer_eq` diventa `transfer_simple`; aggiunto `transfer_gamma1`; si sceglie il migliore dei due sulla validazione |
| P3 | Le sorgenti sono gruppi di linee: i due esperimenti K562 entrano come una sola sorgente; tolta la feature «numero di sorgenti»; regime CT_max2 come controllo |
| P4 | `basal_common.npy`: controlli normalizzati sui soli geni comuni, usati come feature |
| P5 | Nessun parametro per gene: le caratteristiche dei programmi e dei geni vengono dai loro descrittori; il vettore per gene resta solo come ablazione (`--gene-res`) |
| test | `tests/test_leakage.py`: coppie e sorgenti senza linee o bersagli tenuti fuori; descrittori invariati se i dati di test diventano rumore, con un controllo negativo; nessun parametro dipendente dal numero di geni |

## Limiti noti

- Si usa il log della media, non la media dei log dello scorer.
- L'asse genico è l'intersezione dei cinque esperimenti, non le 18.533 sonde Flex della gara; il
  numero di geni lo dirà `build_mini.py`.
- Le quattro linee sono lette in 3', la gara in Flex.
- Con quattro linee il contesto entra solo attraverso l'espressione di controllo gene per gene.
- I nomi delle colonne in `SPEC` di `build_mini.py` sono ipotesi finché non li conferma `--inspect`.
