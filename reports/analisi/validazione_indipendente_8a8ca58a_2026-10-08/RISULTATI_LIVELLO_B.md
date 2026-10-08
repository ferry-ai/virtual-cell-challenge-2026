# Risultati del livello B: sei membri con lo scorer vero, su cellule vere del lignaggio escluso

8 ottobre 2026, VALIDAZIONE (Claude Code `8a8ca58a`). **Misurato** su Kaggle CPU con `bench_v2.py` non
modificato, `cell-eval2` 0.16.0, emissione t28, 400 cellule previste per bersaglio, cinque semi appaiati; letto
con il §8 del [contratto v2](PROTOCOLLO_v2.md). [Come si esegue](LIVELLO_B.md), scritto prima dei numeri. Tabelle
scritte dai lettori: [esito per contrasto](TABELLE_LIVELLO_B_r1.md), [fold K562](TABELLE_LIVELLO_B_k562_r1.md),
[fold iPSC](TABELLE_LIVELLO_B_ipsc_r1.md).

**Che cosa sono questi numeri.** Punteggi **locali**: ancore locali, verità a metà delle cellule vere, due lignaggi
di sviluppo. Non sono punteggi VCC; danno il verso di un confronto, non la sua entità sul sito. «±» è la
deviazione standard sui cinque semi del generatore, a verità e modello fissi: non è incertezza biologica.
«Risolto» vuol dire \|media\| > 2·sd/√5.

| Fold | Kernel | Bersagli | Durata della corsa principale | Stato |
|---|---|---:|---:|---|
| C-iPSC, cellule `kolf_strong` | `davidmaisterx/vcc-validazione-banco-ipsc-8a8ca58a-r1` | 55 | 19 minuti | completo |
| C-K562, cellule `replogle_k562_gwps` | `davidmaisterx/vcc-validazione-banco-k562-8a8ca58a-r1` | 272 | 109 minuti | controllo e corsa principale completi; corsa «cambiati» fallita (§4) |

## 1. Controllo del banco: bersagli scambiati

Stesso braccio T0, con le righe degli effetti scambiate fra i bersagli (un seme).

| Fold | Media T0 → scambiato | PDS | NMAE | FID | REACH | JAC |
|---|---|---|---|---|---|---|
| C-K562 | −0,450 → −0,724 | 0,526 → −0,047 | 0,340 → −0,088 | 0,858 → 0,809 | 0,506 → −0,053 | −4,93 → −4,96 |
| C-iPSC | 0,523 → 0,431 | 0,316 → −0,123 | 1,746 → 1,727 | 0,990 → 0,953 | −0,051 → −0,128 | 0,139 → 0,154 |

**Misurato:** su entrambi i fold il banco distingue il braccio vero da quello scambiato (PDS +0,57 e +0,44).
Sul fold iPSC NMAE, fedeltà e Jaccard cambiano poco e il Jaccard sale: lì la media dei sei membri dipende in
gran parte da proprietà che non riguardano il bersaglio. Sul fold K562 il Jaccard locale vale −4,9 per un
denominatore minuscolo (2,9 geni significativi per bersaglio nel replicato): la media dei sei membri è negativa
per quel solo membro, come già visto il 4 ottobre. **Per questo ogni delta si legge con e senza Jaccard e con il
PDS accanto.**

## 2. K1: T1 contro t36

| Fold | Sei membri | Senza JAC | PDS | NMAE | FID | REACH | JAC |
|---|---|---|---|---|---|---|---|
| C-K562 | −0,0008 ± 0,0023 | −0,0010 ± 0,0028 | −0,0000 ± 0,0031 | **−0,0072 ± 0,0060** | +0,0002 ± 0,0011 | +0,0019 ± 0,0097 | **+0,0006 ± 0,0003** |
| C-iPSC | +0,0001 ± 0,0031 | −0,0000 ± 0,0036 | −0,0038 ± 0,0173 | +0,0012 ± 0,0014 | +0,0001 ± 0,0021 | +0,0023 ± 0,0073 | +0,0010 ± 0,0015 |
| **macro** | −0,0003 ± 0,0014 | −0,0005 ± 0,0016 | −0,0019 ± 0,0089 | | | | |

(In grassetto i delta risolti.) Il membro MSE scalato è 0 per tutti i bracci.

**Esito del §8: INCONCLUDENTE.** La macro dei sei membri non è risolta; nessun fold perde in modo risolto la media
o il PDS; il livello A non ferma e non promuove. L'unico membro che si muove in modo risolto è l'NMAE sul fold
K562, **in peggio** (−0,007). **T1 non è promossa.**

## 3. K0: t36 contro le quattro linee, sulle stesse tabelle

| Fold | Sei membri | Senza JAC | PDS | NMAE | FID | REACH | JAC |
|---|---|---|---|---|---|---|---|
| C-K562 | **−0,0260 ± 0,0081** | **−0,0276 ± 0,0099** | **−0,1011 ± 0,0223** | +0,0024 ± 0,0286 | **−0,0119 ± 0,0034** | **−0,0272 ± 0,0227** | **−0,0183 ± 0,0012** |
| C-iPSC | **+0,0274 ± 0,0053** | **+0,0317 ± 0,0066** | **+0,0666 ± 0,0228** | **+0,0101 ± 0,0050** | **+0,0120 ± 0,0011** | **+0,0700 ± 0,0079** | **+0,0056 ± 0,0012** |
| **macro** | +0,0007 ± 0,0035 | +0,0021 ± 0,0043 | **−0,0173 ± 0,0150** | | | | |

**Esito del §8: VALIDO E SFAVOREVOLE**, per la regressione risolta della media e del PDS sul fold K562. Non è una
decisione aperta: t36 è già inviato. È la lettura, con la regola di oggi, di un passo già fatto.

**Misurato.** Sul fold K562 le fonti che t36 aggiunge alle quattro linee (le quattro tabelle KOLF2.1J e H1)
tolgono 0,10 di PDS locale e 0,026 alla media. Sul fold iPSC, dove tutte le tabelle KOLF sono escluse e resta
la sola aggiunta di H1, la media sale di 0,027 e il PDS di 0,067. I due fold dicono cose opposte perché misurano
cose diverse: KOLF su un lignaggio lontano, H1 su un lignaggio vicino.

**Interpretazione.** Coincide con la scomposizione del livello A ([risultati](RISULTATI_LIVELLO_A.md), §5): H1
aiuta, l'ingresso di KOLF costa specificità ai lignaggi non staminali. **Non contraddice il punteggio ufficiale**
del t36 (+0,0024 su t28, PDS in salita): quel confronto è un solo invio su tre contesti di identità ignota,
contiene anche il cambio delle tabelle Orion, e la sua differenza sta dentro la soglia operativa di ±0,005. Dice
però che la superiorità di t36 su una ricetta a quattro linee **non è sostenuta** da questi banchi sui lignaggi
non staminali.

## 4. La corsa «cambiati» sul fold K562

Sui soli 17 bersagli con voti nuovi lo scorer rifiuta il membro MSE: la somma delle distanze non distorte della
verità è −0,0017, cioè su quei 17 bersagli K562 **non ha un effetto aggregato misurabile** a 64 cellule
(`failure/changed.log`). La corsa secondaria non entra nell'esito; il fatto resta: i bersagli che T1 cambia sono,
in K562, perturbazioni deboli. Sul fold iPSC i bersagli cambiati con cellule sono 4: nessun membro risolto.

## 5. Limiti

Due fold su sei lignaggi, entrambi già fonti di ogni ricetta e uno (K562) letto più volte da banchi a sei membri;
metà delle cellule vere fa da verità; le costanti d'ampiezza e di emissione vengono dal sito e da banchi di K562 e
HepG2; la testa cis è stimata su K562. La macro è la media di due contesti, non una stima di generalizzazione.
CD4T, HCT116 e HEK293 non hanno cellule vere estratte per il banco.

## 6. Esplorativo a sei membri: t36 senza KOLF2.1J, fold K562

[Piano scritto prima](ESPLORATIVO_SENZA_KOLF.md) (commit `5bfb5a7`, 19:17:38); kernel
`davidmaisterx/vcc-validazione-banco-k562-8a8ca58a-x1`, lanciato alle 19:34, concluso e letto alle 21:23; corsa
principale di 107 minuti. [Tabelle](TABELLE_LIVELLO_B_k562_x1.md). **Non è un candidato e non entra in nessun
esito del §8:** un fold solo, lo stesso da cui l'ipotesi è nata.

| Coppia | Sei membri | Senza JAC | PDS | NMAE | FID | REACH | JAC |
|---|---|---|---|---|---|---|---|
| P4h − T0: senza le quattro tabelle KOLF | **+0,0299 ± 0,0081** | **+0,0318 ± 0,0099** | **+0,1171 ± 0,0197** | −0,0030 ± 0,0276 | **+0,0137 ± 0,0030** | **+0,0312 ± 0,0210** | **+0,0203 ± 0,0015** |
| P4kh − T0: KOLF vota una volta sola | **+0,0110 ± 0,0058** | **+0,0126 ± 0,0071** | −0,0033 ± 0,0072 | **+0,0473 ± 0,0171** | +0,0013 ± 0,0015 | +0,0175 ± 0,0302 | **+0,0033 ± 0,0007** |
| P4h − P4kh: via anche l'unico voto di KOLF | **+0,0189 ± 0,0043** | **+0,0192 ± 0,0053** | **+0,1204 ± 0,0233** | **−0,0503 ± 0,0246** | **+0,0124 ± 0,0043** | +0,0137 ± 0,0266 | **+0,0169 ± 0,0012** |

**Misurato.**
- Il braccio T0 ridà in questa corsa gli stessi numeri della corsa r1 (media −0,4455, PDS 0,5359, NMAE 0,3603,
  248,9 geni chiamati per bersaglio): il banco è riproducibile fra due kernel.
- Senza KOLF il fold K562 guadagna 0,117 di PDS e 0,030 di media. È quasi lo specchio di K0 (§3: −0,101 e
  −0,026), con H1 tenuta: contro il braccio P4 della corsa r1, P4h ha media +0,004 e PDS +0,016 (differenza fra le
  medie dei bracci di due corse con gli stessi semi; nessuna deviazione calcolata).
- Il costo sul PDS viene dall'**ingresso** di KOLF (`kolf_pan_genome`, un voto su quasi tutti i bersagli), non
  dai voti ripetuti: toglierlo vale +0,120 di PDS e costa 0,050 di NMAE; togliere i soli voti ripetuti lascia il
  PDS dov'è e migliora l'NMAE di 0,047.

**Lettura con la regola del piano.** L'ipotesi cadeva se X1 non era positivo su `disc95` nei fold non staminali o
se perdeva PDS sul fold K562: non cade. **Non è una conferma:** il fold è quello della scomposizione, e K562 è il
lignaggio letto più volte da questi banchi. Dice che vale la pena costruire il contrasto di produzione proposto
nella [raccomandazione](RACCOMANDAZIONE.md), §5, e che lì il PDS e l'NMAE vanno letti separati: su questo fold
tirano in versi opposti.

**Osservazione non indagata.** Il membro MSE scalato vale 0 per ogni braccio (peggio dell'ancora di base), quindi
non pesa su nessuna differenza; il suo valore grezzo però è più basso per i bracci con meno fonti (P4h − T0
−0,60), mentre nel livello A l'errore quadratico nello spazio degli effetti va nel verso opposto in macro. Sono
grandezze diverse (cellule generate contro effetti medi) e non ho cercato la causa.
