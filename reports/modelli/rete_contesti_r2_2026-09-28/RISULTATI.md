# La rete con più contesti (r2): dataset e regola della tornata

28 settembre 2026, notte. Scrive il lead (Claude, sessione del proprietario); orari letti da `date`.

Rete e codice: [`../rete_contesti_2026-09-27/`](../rete_contesti_2026-09-27/DISEGNO.md). Encoder:
[`../encoder_contesto_2026-09-28/`](../encoder_contesto_2026-09-28/RISULTATI.md).

Etichette: **misurato**, **interpretazione**, **ipotesi**, **proposta**. Nessun numero qui è un punteggio VCC.

## Perché

**Misurato** nella prova a vuoto su Kaggle delle 03:30, disegno E1 con HCT116 tenuto fuori: la fase di addestramento
vede 4 contesti di 2 famiglie (K562 e le tre condizioni CD4), perché KOLF2.1J fa da famiglia di validazione. Da così
pochi contesti la rete non può imparare come il contesto cambia una risposta, con o senza encoder:
- l'embedding si traduce in un vettore di contesto con una mappa imparata da 4 punti;
- il vettore imparato di `train.py` ha lo stesso limite.

**Misurato, descrittivo** (varianti della rete su r1, Kaggle, finite alle 04:07; storie e log in
[`varianti_r1/`](varianti_r1/)). Validazione ogni 50 passi, famiglia `orion` tenuta fuori come contesto nuovo, fase 1:

| Variante | Perdita alla prima valutazione (passo 50) | La migliore (passo) | L'ultima (passo) |
|---|---|---|---|
| default, valutazione fine | 0,009379 | 0,009379 (50) | 0,009590 (1.050) |
| lenta, senza partner (lr 3e-4) | 0,009385 | 0,009381 (100) | 0,009472 (1.100) |
| solo cancelli (niente interazione, contesto globale, partner) | 0,009446 | 0,009446 (2.300) | 0,009446 (3.300) |
| sola ampiezza | 0,009446 | 0,009446 (1.700) | 0,009446 (2.700) |

Due varianti di Colab della sera del 27/09 (`nopart` e `strong`, in `G:/Il mio Drive/vcc2026/runs/rete_abl_r1/`) hanno
anch'esse il minimo entro i primi 100 passi.

**Interpretazione.**
- In ogni variante che può imparare qualcosa oltre il punto di partenza, la perdita sulla linea nuova è minima
  all'inizio e poi sale.
- Le varianti che non possono (solo cancelli, sola ampiezza) restano piatte.

La richiesta del proprietario è usare quanti più dati possibile. Il dataset r2 aggiunge i contesti CRISPRi già
ingeriti che r1 non aveva:
- K562 essenziale di Replogle;
- VIPerturb-seq (K562 letto con Flex, come i contesti di gara);
- RPE1 di Replogle;
- i due schermi genome-wide HIPSCI (linee iPSC in pool).

## Il dataset (proposta; le misure si aggiungono a costruzione finita)

Registro: [`contesti_r2.csv`](contesti_r2.csv). La tabella basale è
`processed/basal_sources_2026-09-28.csv`, cioè quella del 27/09 r2 più `viperturb`, `hipsci_fit` e `hipsci_nonfit`
dalle rispettive somme (`basal_from_sums.py`).

| Famiglia (esce intera) | Contesti | Peso in m | Perché insieme |
|---|---|---|---|
| `k562` | `k562`, `k562ess`, `viperturb` | 1/3 ciascuno | la stessa linea in tre esperimenti: tenerne fuori uno e vedere gli altri non sarebbe una linea nuova |
| `rpe1` | `rpe1` | 1 | |
| `cd4` | le tre condizioni | 1/3 ciascuna | come in r1 |
| `orion` | `orion_hct116`, `orion_hek293t` | 1 ciascuno | come in r1 |
| `ipsc` | `kolf`, `hipsci_fit`, `hipsci_nonfit` | 1/2, 1/4, 1/4 | i pool HIPSCI contengono kolf_2, la linea da cui viene KOLF2.1J |

A549 (knockout) resta nel file ma fuori per modalità, come in r1.

Prova a vuoto delle 03:57 (misurato):

| Voce | r1 | r2 |
|---|---|---|
| righe | 91.860 | 109.586 |
| geni conservati | 12.477 | 13.248 |
| byte previsti | 6,88 GB | 8,71 GB |

## Regola della tornata r2, fissata alle 04:00 del 28/09 (prima di costruire il dataset per intero e di addestrare)

### Che cosa gira

- **Seme:** solo 0.
- **Disegni:**
  - E1 con verità `k562`, `orion_hct116` e `cd4_Rest`, famiglie intere fuori;
  - E2 sulla coppia Orion.
- **Bersagli di prova:** gli stessi della prima tornata dell'encoder su r1, cioè i `test_targets.txt` delle sue
  corse `none` (`--test-targets`). Il confronto fra r1 e r2 è così appaiato.
- **Condizioni:**
  - `none`, la rete di `train.py` su r2;
  - `ours`, l'encoder con la ricetta della prima tornata, con `--require` esteso ai contesti nuovi e i due schermi
    HIPSCI associati al contesto del corpus `hipsci_pooled` (`--emb-map`).
- **Argomenti:** quelli di default, come in r1.

### Letture

**A. Più contesti** (l'ipotesi del proprietario).
- **Misura:** `none` su r2 contro `none` su r1, appaiati sugli stessi bersagli e sugli stessi geni (quelli conservati
  in entrambi i dataset e previsti da entrambe le reti). Contrasto di skill nello spazio degli effetti, con le
  formule di `compare.py` e l'intervallo bootstrap sui bersagli. Le previsioni di r1 sono conservate in float16,
  quindi anche quelle di r2 si arrotondano a float16 prima del confronto.
- **Passa** se il contrasto è positivo su almeno 2 delle 3 verità E1, con l'intervallo sopra zero su almeno una e
  nessun intervallo interamente sotto −0,002. Lettura: più contesti CRISPRi aiutano la rete sulle linee tenute
  fuori, provvisorio con un seme.
- **E2 Orion:** si riporta per r2 accanto a r1.

**B. L'encoder su r2:** la regola della prima tornata (punti 1–3) per `ours` contro `none`, su r2.

**C. Descrittivo:** la curva di validazione. La perdita sulla famiglia tenuta fuori sale ancora dalla prima
valutazione?

**Limiti dichiarati prima:**
- **un seme:** qualunque passaggio va confermato con i semi 1 e 2;
- **confondimenti in A:** r2 cambia anche l'insieme dei geni conservati e la calibrazione, non solo il numero di
  contesti, quindi A misura «il dataset r2», non i contesti da soli;
- **il K562 in E1:** con la famiglia `k562` tenuta fuori, r2 non vede nessun K562. È la stessa esclusione di r1
  estesa ai due esperimenti nuovi.

## Esito della tornata r2, seme 0 (misurato, 28/09; tabelle in `r2_shard0/` e `r2_shard1/`)

Due sessioni GPU su Kaggle, partite alle 10:06 perché la coda notturna si era fermata con il riavvio della sessione.
Nel file di sintesi della seconda sessione il percorso del dataset conteneva il nome del conto Kaggle, sostituito con
`<kaggle-user>` nella copia qui.

**Lettura B, l'encoder su r2: non passa, e peggiora molto.** Contrasto `ours` − `none` (skill):

| Verità | `ours` − `none` |
|---|---|
| HCT116 | **−0,661** [−0,691; −0,632] |
| HEK293T (disegno E2) | −0,324 |
| K562 | −0,038 [−0,049; −0,028] |
| CD4 a riposo | −0,021 [−0,023; −0,019] |

- **Il crollo su HCT116 dal log (misurato).** Nella fase 1 la migliore valutazione era al passo 750. Il
  riaddestramento su tutti i contesti visibili, con la famiglia K562 e i suoi tre embedding in più, ha portato la
  calibrazione da 0,013 a 0,042; la rete finale ha skill −0,648 su HCT116.
- **Interpretazione:** la mappa dall'embedding al contesto estrapola male per una linea lontana da quelle viste.
  Nessun limite ne contiene l'effetto: è un difetto dell'innesto, oltre che un esito negativo.

**Lettura C, la curva.** In r2, come in r1, la perdita sulla famiglia di validazione è minima alla prima valutazione
(passo 250) in ogni disegno della rete `none`, poi sale. Più contesti CRISPRi (10–12 visibili invece di 5–7) non
cambiano questo.

**E2 Orion su r2:** rete 0,0027 [−0,0008; +0,0064], non passa, come in r1.

**Lettura A, r2 contro r1 sugli stessi bersagli:** in corso con `cross_compare.py`; si aggiunge qui quando finisce.

## Lettura A, completa (misurato, 28/09 sera; tabelle in `lettura_a_shard0/` e `lettura_a_shard1/`)

Claude, sessione `f2abd9a6`. La lettura della sessione `f4f38e58` copriva solo la sessione Orion (la K562/CD4 non era
ancora scaricata), e la sua uscita non era stata salvata. Rigirata qui, `cross_compare.py` invariato, una
volta per sessione di Kaggle:

```bash
scripts/py.cmd reports/modelli/rete_contesti_r2_2026-09-28/cross_compare.py --r1 <kaggle>/out_r1_s0_v2 \
    --r2 <kaggle>/out_vcc-r2-s0-shard{0,1}_v1/keep_pred --data-r2 <dati>/processed/rete_contesti_r2 \
    --out reports/modelli/rete_contesti_r2_2026-09-28/lettura_a_shard{0,1}
```

I numeri della sessione Orion coincidono con quelli che la sessione `f4f38e58` aveva riportato nella scheda R-V2
(«Pomeriggio del 28 settembre»).

**`none` su r2 − `none` su r1**, skill nello spazio degli effetti, stessi 1.000 bersagli, stessi geni:

| Verità E1 | r2 − r1 | Geni |
|---|---|---|
| K562 | **+0,0036** [+0,0028; +0,0046] | 11.794 |
| HCT116 (disegno E1 Orion) | **+0,0018** [+0,0005; +0,0030] | 9.749 |
| CD4 a riposo | −0,0015 [−0,0023; −0,0007] | 10.885 |

Descrittivo: HEK293T nel disegno E2 −0,0072 [−0,0096; −0,0050].

**Per la regola delle 04:00: passa, provvisoria.** Positivo su 2 verità su 3, con l'intervallo sopra zero su entrambe, e
l'intervallo di CD4 non sta interamente sotto −0,002. Lettura registrata: più contesti CRISPRi aiutano la rete sulle
linee tenute fuori, **provvisorio con un seme**. Valgono i limiti scritti prima:
- r2 cambia anche i geni conservati e la calibrazione, non solo il numero di contesti: A misura «il dataset r2»;
- i guadagni sono di pochi millesimi di skill, e la discriminazione della rete fra i bersagli di prova resta vicina al
  caso (0,50–0,51, `r2_shard*/arms.csv`).

Serve la conferma con i semi 1 e 2 prima di crederci.

**E2 Orion** (`lettura_a_shard0/e2.csv`): rete di r1 0,0027 [−0,0008; +0,0065], rete `none` di r2 0,0026
[−0,0010; +0,0061], quantile 97,5 % delle permutazioni 0,0039. Nessuna passa. Il valore scritto sopra per r2
(0,0027 [−0,0008; +0,0064]) non coincide esattamente né con questo file né con `r2_shard0/e2.csv` (0,0027
[−0,0006; +0,0061], quantile 0,0046, di `compare.py` su Kaggle). La conclusione non cambia.
