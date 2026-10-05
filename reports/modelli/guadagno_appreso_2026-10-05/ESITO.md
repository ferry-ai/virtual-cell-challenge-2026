# Esito dello stadio 1: il guadagno appreso non passa; la direzione cresce col numero di linee sorgente

5 ottobre 2026, 16:04–16:09 la corsa registrata, poi tre diagnostiche dichiarate a posteriori. Claude Code per
Alfredo (sessione `42343bb9`).

Riferimenti:
- protocollo [PROTOCOLLO.md](PROTOCOLLO.md), commit `cb728ec`, registrato prima di ogni numero;
- codice [guadagno.py](guadagno.py), commit `32c0d73`, committato prima della corsa;
- cubo `davideferrante11/rlead-bench-cube-r2`, con i 139 hash verificati contro il suo manifest;
- valori in [esito/](esito/). Le chiavi dei bersagli sono tolte dai file pubblici; il file completo resta nella
  cartella dati.

**Sono indici sugli effetti del cubo, non punteggi VCC né membri dello scorer.**

## 1. Regola registrata: non passa

| Linea | Bersagli | Coseno `all` | `guadagno − all`, coseno [IC 90%] | `guadagno − all`, indice PDS |
|---|---|---|---|---|
| H1 | 96 | 0,166 | +0,011 [+0,008; +0,014] | −0,000 |
| HepG2 | 400 | 0,255 | **+0,022** [+0,018; +0,026] | −0,007 |
| RPE1 | 400 | 0,181 | +0,012 [+0,009; +0,015] | **−0,017** |
| Jurkat | 400 | 0,231 | +0,011 [+0,009; +0,014] | −0,009 |
| K562 | 400 | 0,175 | +0,010 [+0,007; +0,012] | +0,000 |

Le tre condizioni della regola:
- **linee sopra +0,02:** 1 su 5, ne servivano 4;
- **media delle differenze:** +0,013, serviva +0,03;
- **guardia del PDS:** violata su RPE1 (−0,017, oltre −0,01).

**Il `guadagno` in questa forma si chiude**, come previsto dal protocollo.

**Perché.** Il guadagno appreso è quasi uniforme: i quantili 5–95% di g stanno fra 0,24 e 0,75, con mediana circa 0,6.
La rete ha imparato soprattutto un'ampiezza, che la norma riportata a quella di T cancella. La direzione si muove poco,
cioè con caratteristiche per coppia il limite è l'informazione, non il restringimento.

**Previsione registrata** («+0,00…+0,04, fiducia 0,35 che passi»): avverata.

## 2. Che cosa si riporta senza che decida

- **`all − prod`, coseno:**
  - H1 +0,038, HepG2 +0,094, RPE1 +0,047, Jurkat +0,039, K562 +0,055;
  - tutti con il limite inferiore all'IC 90% sopra 0.
- **`all − prod`, indice PDS:** positivo su quattro linee (da +0,045 a +0,064); Jurkat −0,006.
- **Conferma il banco v2 di Davide** con una misura indipendente dal generatore.
- **`centrato − all`:** il coseno sale solo su H1 (+0,010) e scende sulle altre linee (da −0,009 a −0,038); il PDS
  scende su quattro linee. Togliere la parte comune del pannello non aiuta.
- **MSE alla norma della ricetta (T × 1,576):** da 2 a 11 volte quella del «non fare niente». A quel coseno l'ampiezza
  della ricetta è troppo grande per la MSE.

## 3. Diagnostiche a posteriori

Sono dichiarate dopo aver visto la §1. Leggono gli stessi effetti e non decidono niente.

### 3.1 Il tetto: due studi della stessa linea ([tetto.py](tetto.py))

| Coppia | Bersagli | Coseno medio |
|---|---|---|
| K562 gwps contro essential (stesso laboratorio, 3′) | 362 | 0,95 (mediana 0,90) |
| K562 3′ contro Flex (VIPerturb) | 236 | 0,60 |
| CD4 a riposo contro stimolate 8 h | 400 | 0,54 |
| **Transfer fra linee diverse (`all`)** | — | **0,17–0,25** |

La direzione si trasferisce bene **dentro** una linea, anche fra chimiche e stati diversi, e male **fra** linee.

### 3.2 Pesi dei gruppi ([gruppi.py](gruppi.py), [esito/diag_gruppi_r1.json](esito/diag_gruppi_r1.json))

- **Un gruppo da solo** dà un coseno da 0,05 a 0,20. I migliori sono K562, RPE1, Jurkat e, sui pochi bersagli che
  copre, H1; i peggiori CD4, iPSC e i neuroni.
- **I pesi «oracolo»** sono scelti guardando la verità, quindi sono un tetto e non un modello. Danno solo da +0,004 a
  +0,013 su `all`.
- **Quindi una pesatura appresa delle sorgenti** (attenzione, similarità dei controlli) può aggiungere al massimo
  circa +0,01.

### 3.3 Il coseno contro il numero di gruppi sorgente ([curva.py](curva.py), [esito/diag_curva_r1.json](esito/diag_curva_r1.json))

Media su 12 sottoinsiemi casuali di k gruppi (seme 0), senza i neuroni (pochi bersagli). Valori: coseno / indice PDS.

| Linea | k = 1 | k = 2 | k = 4 | k = 6 | k = 8 |
|---|---|---|---|---|---|
| H1 | 0,088 / 0,71 | 0,109 / 0,76 | 0,126 / 0,81 | 0,148 / 0,88 | 0,166 / 0,91 |
| HepG2 | 0,132 / 0,67 | 0,166 / 0,69 | 0,193 / 0,73 | 0,228 / 0,76 | 0,254 / 0,78 |
| RPE1 | 0,091 / 0,67 | 0,094 / 0,59 | 0,135 / 0,69 | 0,162 / 0,75 | 0,181 / 0,77 |
| Jurkat | 0,134 / 0,67 | 0,147 / 0,64 | 0,187 / 0,72 | 0,213 / 0,75 | 0,230 / 0,77 |
| K562 | 0,134 / 0,75 | 0,129 / 0,65 | 0,143 / 0,62 | 0,163 / 0,65 | 0,175 / 0,67 |

**Lettura.**
- **La curva non satura a 8 gruppi:** ogni linea sorgente in più vale circa **+0,01 di coseno**, e anche il PDS sale.
- La soglia di circa 0,22 per far uscire la MSE da zero (margini_orizzonte) è già vicina su HepG2 e Jurkat.
- **La leva è il numero di linee indipendenti che misurano ciascun bersaglio**, non il numero di righe né un modello più
  ricco sugli stessi dati.

## 4. Che cosa implica per «usare tutta la mole di dati Kaggle»

**Che cosa leggiamo dal nostro account:** circa 67 GB di cellule rlab. Il cubo contiene già **quasi tutte le linee
CRISPRi** di quei dati: K562 ×3, RPE1, HepG2, Jurkat, H1, KOLF, 18 tabelle HipSci e i neuroni Tian.

Restano fuori, e porterebbero linee o unità in più:
- **iPSC di Tian e HipSci gwfit/gwnonfit:** sono ancora gruppo iPSC, che è fra i gruppi che trasferiscono peggio.
  Guadagno atteso piccolo.
- **A549 (knockout):** una linea nuova. Il knockout è anch'esso una perdita di funzione, ma è un'altra modalità:
  - va provato come decimo gruppo con la stessa misura;
  - la curva suggerisce circa +0,01 se trasferisce come una linea media.
- **Hs27 (CRISPRa):** effetto di segno opposto, da non usare come sorgente diretta.

Le cellule CD4 per donatore e Orion (solo da Davide, 403 per noi) non aggiungono linee: CD4 è già un gruppo.

**Fuori da Kaggle**, la sorgente che conterebbe davvero è X-Atlas/Pisces: 16 contesti CRISPRi, ancora «Coming Soon».
Sulla curva, raddoppiare i gruppi varrebbe molto più di qualunque modello provato qui.

**Le righe in più (tutte le chiavi) servono a un modello con parametri per gene o per bersaglio,** non a questo. È la
strada 3 della revisione (base a basso rango), il cui tetto va misurato come in §3.2 prima di costruirla.

## 5. Proposte

1. **A549 come decimo gruppo.** Si costruiscono le sue tabelle sulle chiavi del cubo dai frammenti `rlab-a549` (7,7 GB)
   e si rimisura questo banco con `all` + A549. Il protocollo va registrato prima. Costo: mezza giornata.
2. **Base a basso rango (strada 3):** prima il suo tetto, con la proiezione della verità sulla base delle linee di
   training, poi il modello. Costo: mezza giornata per il tetto.
3. **Ampiezza per la MSE:** al coseno di `all` (circa 0,2) l'ampiezza della ricetta dà una MSE da 2 a 11 volte il
   controllo.
   - Sul banco v2 si può misurare quanto costa ai membri DE un profilo aggregato meno ampio. È la vecchia strada 1,
     riletta: con il coseno a 0,2 la MSE non esce da zero, ma vicino a 0,22 sì.
   - Va legata alla 1.
4. **Pisces:** ricontrollare la pagina prima del 22/10.
