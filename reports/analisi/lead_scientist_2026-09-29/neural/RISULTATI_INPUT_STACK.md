# Stack: perdita di conteggi dovuta agli assi di input

29 settembre 2026. **Misura sui soli controlli**, eseguita alle
20:20:25.808896 UTC, prima di leggere score Stack. Nessun outcome perturbato
HepG2, nessuna nuova inferenza, nessuna modifica a supporti, candidati o gate
del pilot A. Dati completi in `input_axis_components_r1/analysis.json` e
`input_axis_components_r1/per_control_cell.csv`.

L'intersezione comune elimina dal contesto HepG2 **l'8,8033% di tutti i conteggi
che il vocabolario Stack avrebbe potuto leggere**, equivalenti al 15,1404% dei
conteggi mappabili al modello. È una perdita aggiuntiva concreta che giustifica
un confronto prospettico. Non prova che abbia peggiorato le previsioni.

## Decomposizione della perdita

La quota complessiva esclusa dall'input è circa metà dei conteggi in entrambi i
contesti, ma attribuirla tutta all'intersezione sarebbe scorretto: la componente
maggiore è fuori dal vocabolario del checkpoint e non è recuperabile allargando
l'asse entro quel vocabolario.

| Misura | K562, 512 NTC | HepG2, 2.000 NTC |
|---|---:|---:|
| Geni misurati unici | 8.246 | 9.624 |
| Geni del proprio asse nel modello | 5.760 | 6.797 |
| Geni conservati dall'intersezione S | 5.179 | 5.179 |
| Geni nel modello eliminati solo dall'altro asse | 581 | 1.618 |
| Conteggi totali | 5.916.493 | 37.657.835 |
| Conteggi mappabili al modello | 3.041.519 | 21.895.925 |
| Conteggi conservati su S | 2.888.713 | 18.580.786 |
| Fuori dal vocabolario, % di tutti i conteggi | 48,5925% | 41,8556% |
| Persi solo dall'intersezione, % di tutti i conteggi | 2,5827% | 8,8033% |
| Perdita complessiva, % di tutti i conteggi | 51,1752% | 50,6589% |
| Persi solo dall'intersezione, % dei conteggi mappabili | 5,0240% | 15,1404% |
| Library mediana prima dei filtri | 11.361,5 | 15.510,5 |
| Library mediana sul proprio asse nel modello | 5.836,5 | 9.041,0 |
| Library mediana su S | 5.550,5 | 7.631,0 |

Percentuali aggregate = somma dei conteggi esclusi / somma dei conteggi iniziali;
non sono medie delle percentuali per cellula. Le due componenti della perdita
si sommano esattamente alla perdita complessiva, verificata dal codice.

La distribuzione per cellula conferma che non si tratta di poche righe estreme:

| Percentuale persa per cellula: p05 / mediana / p95 | K562 | HepG2 |
|---|---|---|
| Complessiva | 46,8861 / 51,0697 / 55,7037 | 46,7298 / 50,6712 / 55,6660 |
| Solo per l'intersezione con l'altro asse | 2,1032 / 2,5506 / 3,2935 | 6,2882 / 8,4607 / 12,7683 |

Tutte le 2.512 cellule hanno library iniziale positiva. L'audit non misura la
distribuzione dei prompt perturbati, le cellule decodificate, i cap finali o
l'efficacia degli effetti previsti.

## Quali geni perdono più massa

I venti geni esclusi con più conteggi complessivi sono riportati qui sotto.
Il simbolo † indica un gene presente nel vocabolario Stack ma escluso solo
perché assente dall'asse misurato dell'altro contesto; tutti gli altri in questa
tabella sono fuori dal vocabolario. Sono identità di colonne osservate, non
annotazioni funzionali inferite dai nomi.

| Rango | K562: gene, conteggi | HepG2: gene, conteggi |
|---:|---|---|
| 1 | MT-CO3, 161.280 | MT-CO3, 763.088 |
| 2 | MT-CO2, 127.046 | MT-CO2, 558.977 |
| 3 | MT-ATP6, 94.565 | MT-ATP6, 535.411 |
| 4 | MT-CO1, 86.562 | MT-ND4, 425.598 |
| 5 | MT-ND4, 71.493 | MT-CO1, 364.620 |
| 6 | MT-CYB, 58.052 | MT-ND1, 297.546 |
| 7 | RPLP1, 48.351 | MT-CYB, 283.386 |
| 8 | RPS2, 47.683 | RPL13, 276.215 |
| 9 | RPS18, 43.570 | ALB†, 255.531 |
| 10 | RPS12, 38.090 | RPL11, 227.032 |
| 11 | MT-ND3, 32.264 | RPS2, 221.129 |
| 12 | RPS23, 31.500 | RPS12, 218.017 |
| 13 | RPS8, 29.964 | RPS18, 211.151 |
| 14 | RPS3, 29.746 | APOA2†, 209.367 |
| 15 | RPL32, 27.971 | RPLP1, 195.967 |
| 16 | MT-ND1, 27.726 | RPS27A, 169.080 |
| 17 | RPL19, 27.660 | MT-ND3, 165.226 |
| 18 | RPS27A, 26.451 | RPS19, 149.658 |
| 19 | RPL7A, 26.294 | RPL10, 149.380 |
| 20 | RPS14, 25.910 | RPS3, 149.269 |

Limitandosi invece alla componente recuperabile con gli assi propri, i primi
cinque K562 sono GP1BB (9.229), TMSB4X (6.079), LDHB (4.955), VIM (4.861),
HBG2 (4.832). In HepG2 sono ALB (255.531), APOA2 (209.367), APOB (144.664),
SERPINA1 (106.841), APOA1 (103.747). Il JSON contiene i primi venti per ciascuna
popolazione, conteggi e frazioni esatte. La massa di conteggi non misura da sola
l'informazione utile: un gene poco espresso può comunque contribuire al modello.

## Maiuscole: il sospetto non è confermato su questi dati

L'intersezione esatta e quella dopo conversione in maiuscolo contengono entrambe
**5.179 geni**. Nessun simbolo aggiuntivo, nessun conteggio recuperato e nessuna
collisione uppercase in nessuno dei tre assi. I 15.012 geni del modello sono tutti
unici e già maiuscoli. La sensibilità al case esiste nel codice, ma non ha una
conseguenza misurabile su questo bundle; non giustifica una correzione qui.
In particolare, il formato del nome di un bersaglio perturbato non dimostra
che quel gene sia una colonna di risposta misurata e presente nel modello.

## Implicazione e confronto autorizzato

**Interpretazione**: l'input HepG2 del pilot A perde misure disponibili nel
modello, oltre a quelle inevitabilmente fuori vocabolario. La perdita può
influire sul contesto riconosciuto e sulla profondità che vede il modello.
Un eventuale fallimento di A, da solo, non discriminerebbe questa spiegazione
dall'assenza di trasferibilità di Stack. L'audit non dimostra un falso negativo.

**Proposta adottata prima degli outcome**: il candidato B usa per ciascun input
il proprio asse misurato intersecato con il vocabolario, mantenendo invariati
checkpoint, cellule, prompt, seed e parametri. La correzione dell'output resta
soltanto su S e il transfer resta esatto fuori S. Il confronto può migliorare o
peggiorare: con assi diversi il modello può interpretare gli zeri fuori misura
diversamente, e l'aumento di library può avere effetti propri.

La selezione development e l'unica conferma sono fissate in
`PROTOCOLLO_STACK_AB.md`, SHA256
`181d7a00b1f5957948e2daf9fcd1f66fae9adb35dbf78aab59a5b2c006133506`.
Nessun risultato di questo audit vale come score o come criterio sostitutivo:
due pilot completi, al massimo un candidato sulla riserva ancora cieca, nessun
tentativo dell'altro sulla stessa riserva se il prescelto fallisce.

## Riproducibilità e provenienza

Codice: `audit_stack_input_axis.py` e la sola estensione di decomposizione
`audit_stack_input_components.py`; output originale `input_axis_r1` conservato.
Tre test sintetici passati: frazione aggregata contro frazione per cellula,
conversione case/collisioni/zeri, decomposizione manuale delle due perdite.
Il codice estrae dal tar soltanto i due H5AD di controlli e `bundle.json`,
controlla gli hash del manifest e che tutte le etichette siano NTC. Non estrae
prompt perturbati o transfer. L'output include hash del codice e degli input.

- Bundle originale, 31.984.510 byte:
  `8c693c8457590edca74e626b08d7318a276c44f4b9737f5d4d4c13272814cf3e`.
- NTC K562 preparati:
  `616f18fe3f7b99a7239249150f67f991bfbbc48caf9d0b89d5e05520d19ee491`.
- NTC HepG2 preparati:
  `c989a3121caa5b96c1752c92fd811522caf60d19c994fa3e08237625adcff598`.
- Lista derivata di 15.012 stringhe, 129.830 byte:
  `22b0227d07ebf61aed37f3863049885911d5c178742ba40c9efc54bac5687468`.
- Manifest inferenza da cui proviene la lista:
  `e02f7cf5cbbbc9f6c759fb702867e5647a8d9a16596887d83e07b4bbae3cb7f9`.
- Lista originale ufficiale collegata dal manifest:
  `d8761dfda955b9897d3251798b72361ddd0171ef707119eaf65381bed2d85dcc`.

Il manifest originale collega anche checkpoint e helper ai loro hash congelati.
La lista derivata è stata letta con un unpickler ristretto; l'audit non carica i
pesi. Comando eseguito, con un nuovo `--out` obbligatorio per ogni ripetizione:

```powershell
.\scripts\py.cmd reports/analisi/lead_scientist_2026-09-29/neural/audit_stack_input_components.py --bundle C:/Users/ferra/vcc2026-data/interim/kaggle_stack_prompts_r1/bundle.tar.gz --genelist "G:/Il mio Drive/vcc2026/runs/lead_stack_infer_2026-09-29_r2/prediction/model_genes.pkl" --inference-manifest "G:/Il mio Drive/vcc2026/runs/lead_stack_infer_2026-09-29_r2/prediction/inference_manifest.json" --out reports/analisi/lead_scientist_2026-09-29/neural/input_axis_components_r1
```
