# Atlante: il trasferimento misurato su migliaia di bersagli per linea tenuta fuori

26 settembre 2026, sera. Punto 4 del [piano dell'atlante](../../docs/piani/modello-v2.md) nella scheda
R-V2, su richiesta del proprietario: usare molti dati insieme. **Proxy contro sorgenti pubbliche
tenute fuori, non punteggi VCC.**

## Perché

I banchi del pomeriggio ([r5](../trasferimento_appreso_2026-09-26/RISULTATI.md),
[EB](../trasferimento_gerarchico_2026-09-26/RISULTATI.md),
[quattro sorgenti](../quattro_sorgenti_2026-09-26/RISULTATI.md)) provano su circa 270 bersagli del
pannello per sorgente tenuta fuori: intervalli larghi, e il modello gerarchico stimava le varianze per
gene sugli stessi 270 bersagli. Gli universi genome-wide ([universo](../universo_2026-09-26/RISULTATI.md):
K562 9.866 bersagli, CD4 in estrazione, Orion HCT116 e HEK293T in streaming) permettono di provare il
trasferimento su migliaia di bersagli **fuori dal pannello** per ogni linea tenuta fuori.

## Il banco (`atlas_bench.py`)

Per ogni linea tenuta fuori H, la sua famiglia esclusa da tutto (una linea Orion fuori lascia K562 e CD4):
- **bersagli di prova**: 1.000 bersagli misurati in H e in almeno due sorgenti d'ingresso, estratti con
  seme fisso, nessuno dei 300 del pannello;
- **bersagli di stima**: gli altri bersagli con almeno due sorgenti d'ingresso, fuori dal pannello e
  disgiunti da quelli di prova (al più 6.000). Su di essi, a blocchi, le varianze per gene del modello
  gerarchico (σ² condivisa fra linee, τ² propria della linea; varianza dello SE di CD4 × 2 per i donatori)
  e i programmi di risposta (componenti principali delle risposte di 3.000 bersagli);
- **bracci**, tutti con la testa cis del t20/t22 (prior ristimato senza pannello e senza bersagli di prova):
  `t22like` (la forma del t22: media a pesi uguali degli effetti ristretti, gamma 1, × 1,576);
  `prog_20`, `prog_50`, `prog_150` (la parte trasferita proiettata sui primi k programmi);
  `eb_panel` (media a posteriori con varianze dai soli bersagli di prova, come fa oggi lo stadio 100 sul
  pannello); `eb_atlas` (la stessa, varianze dai bersagli di stima); `share_atlas` (la parte trasferita
  per gene × σ²/(σ² + τ²), la quota della risposta che le linee condividono). Tutti tranne `t22like`
  riportati alla mediana di geni rilevabili di `t22like`;
- **misure** come il banco a quattro sorgenti: PDS, portata e precisione di segno nello spazio degli
  effetti; PDS e nMAE dopo il passo di profilo del trial-01 e uno pseudobulk di 400 cellule (basali A/B/C,
  3 semi ciascuno); Δ = 0,36 × ΔPDS_gen − 0,27 × ΔnMAE_gen contro `t22like`, bootstrap appaiato sui
  bersagli di prova. Il membro `mse` è a zero in tutti i nostri invii
  ([r2](../risposta_comune_2026-09-26/RISULTATI.md)), per questo non entra nel Δ; il rapporto d'energia
  di ogni braccio è registrato.

Prova di funzionamento del codice (non un risultato): alle 19:05 il banco ha girato senza errori su
universi ridotti fatti di pochi blocchi CD4 e K562, nello scratchpad della sessione.

## Regola fissata alle 19:15 del 26/09, prima di eseguire il banco

- **r1** gira sugli universi completi al momento del lancio, almeno K562, CD4 e HCT116, ognuno tenuto
  fuori a turno; con i parametri di default dello script (1.000 bersagli di prova, seme 20260926).
- Un braccio **passa** se il suo Δ è positivo su tutte le linee tenute fuori (su tutte tranne una se sono
  quattro), con l'intervallo sopra zero su almeno due linee, e nessuna linea ha l'intervallo interamente
  sotto −0,002.
- Fra i bracci che passano, il **candidato** è quello con il Δ medio più alto sulle linee. Diventa una
  ricetta (t22 più il braccio, con varianze o programmi stimati sugli universi fuori dal pannello) solo
  con una previsione registrata prima della generazione, e va all'invio solo col via del proprietario.
- Se nessun braccio passa, la forma del t22 resta il riferimento e l'esito è negativo per questi bracci:
  non si rigira r1 con altri parametri per cercarne uno che passi.
- **r2**, con HEK293T quando il suo universo è completo, è una replica: si riporta, non cambia la
  lettura di r1.

**Aggiunta alle 19:19, sempre prima di eseguire il banco:** un braccio in più, `agree_target`, sotto la
stessa regola. È la parte trasferita di `t22like` moltiplicata, bersaglio per bersaglio, per l'accordo fra
le sorgenti d'ingresso: la loro covarianza incrociata diviso l'energia della loro media, sui geni espressi
con i pesi log1p, ristretta verso il rapporto complessivo (pseudo-conteggio pari all'energia del bersaglio
mediano) e limitata a [0, 1]. Motivazione biologica (**ipotesi**): il knockdown di un complesso essenziale
dà risposte condivise fra linee, quello di un regolatore di lignaggio no; dove gli ingressi non concordano,
la linea nuova è meno prevedibile. La prima versione senza restringimento azzerava troppi bersagli e
rompeva la scala a geni rilevabili nella prova su universi ridotti: da qui il restringimento.

**Emendamento alle 20:05, prima di qualunque esecuzione vera del banco:** i bersagli di prova escludono
i 2.057 bersagli dello schermo K562 "essential" di Replogle (`--essential`). Motivo, misurato nei controlli
qui sotto e in `condivisione_r1/`: il pannello non ne contiene nessuno (0 su 300), e sono un'altra
popolazione, con energia mediana doppia (29,5 contro 14,5 degli altri bersagli fuori dal pannello nel K562;
il pannello sta a 17,0) e più trasferibile (coseno K562×CD4 mediano 0,022 contro 0,008; 90° percentile
0,119 contro 0,047). Fra i bersagli comuni a K562 e CD4 fuori dal pannello sono 1.452 su 8.423. I bersagli
di stima restano tutti, come li userebbe una ricetta. La regola non cambia.

**Lancio di r1 alle 23:13 del 26/09** (ora d'avvio del processo). HCT116 è stato finalizzato alle 21:37 (16.438 bersagli con
effetti su 18.293, parità esatta con la cache r5 sui 268 del pannello, `../universo_2026-09-26/orion_hct116/`);
HEK293T è ancora in streaming (108 file su 223). r1 gira quindi su K562, CD4 (`cd4_mix`) e HCT116, con i
parametri di default. Gli universi K562 essential e RPE1, costruiti in serata per i confronti descrittivi,
non entrano: non sono sorgenti della ricetta, e i loro bersagli sono tutti "essential", cioè fuori dalla
popolazione di prova.

## r1: esito (misurato, 27/09 alle 00:21)

Uscite in `r1/` (`summary.csv`, `measurements.json`). Tre linee tenute fuori, 1.000 bersagli di prova
ciascuna (su 6.199 idonei), 6.000 bersagli di stima. Δ = 0,36 × ΔPDS_gen − 0,27 × ΔnMAE_gen contro
`t22like`, intervallo bootstrap appaiato al 95 %:

| Braccio | K562 fuori | CD4 fuori | HCT116 fuori |
|---|---|---|---|
| `prog_20` | −0,041 (−0,046…−0,035) | −0,028 (−0,033…−0,022) | −0,031 (−0,036…−0,025) |
| `prog_50` | −0,037 (−0,043…−0,032) | −0,028 (−0,033…−0,022) | −0,031 (−0,036…−0,026) |
| `prog_150` | −0,037 (−0,042…−0,032) | −0,026 (−0,031…−0,020) | −0,029 (−0,033…−0,025) |
| `eb_panel` | −0,009 (−0,013…−0,004) | +0,007 (+0,002…+0,013) | −0,003 (−0,008…+0,002) |
| `eb_atlas` | −0,006 (−0,011…−0,002) | +0,003 (−0,002…+0,009) | +0,000 (−0,005…+0,005) |
| `share_atlas` | −0,0002 (−0,004…+0,003) | +0,008 (+0,003…+0,012) | +0,009 (+0,005…+0,014) |
| `agree_target` | −0,020 (−0,025…−0,015) | −0,019 (−0,024…−0,014) | −0,022 (−0,031…−0,015) |

**Lettura con la regola:** nessun braccio passa. Con tre linee la regola chiede Δ positivo su tutte;
`share_atlas` è il più vicino (positivo con l'intervallo sopra zero su CD4 e HCT116, zero su K562),
`eb_panel` ha l'intervallo interamente sotto −0,002 su K562, gli altri perdono. La forma del t22 resta
il riferimento. r2 con HEK293T, quando l'universo è completo, è solo una replica.

Che cosa si vede (**misurato**, `r1/`):
- **I programmi perdono discriminazione:** PDS −0,06…−0,10 su tutte le linee. Le prime 20/50/150
  componenti spiegano solo il 19–29 %, 25–38 % e 39–53 % della varianza delle risposte di 3.000 bersagli:
  proiettare toglie il dettaglio proprio del bersaglio.
- **Il modello gerarchico non separa la deviazione di linea dal rumore:** τ² mediano 0 su tutte le linee
  (i momenti y² − k·SE² − σ² vanno sotto zero e vengono troncati), σ² dall'atlante più grande di quello
  stimato sui soli bersagli di prova (5–11 volte). I bracci EB diventano medie pesate sull'inverso della
  varianza; a parità di geni rilevabili hanno 0,20–0,30 volte l'energia di `t22like`.
- **`share_atlas`**, dove τ² è positivo, abbassa i geni con varianza propria della linea (quota condivisa
  mediana 1 con K562 o HCT116 fuori, 0,69 con CD4 fuori): PDS +0,013 con
  CD4 fuori e +0,030 con HCT116 fuori, −0,002 con K562 fuori; energia 0,37–0,63 volte quella di `t22like`.
- **L'accordo per bersaglio** è piccolo quasi ovunque (mediana 0,016–0,021, rapporto complessivo
  0,016–0,024): ridistribuire l'ampiezza su pochi bersagli triplica l'energia e peggiora l'nMAE.

**Interpretazione:** la media a pesi uguali del t22 non si batte riponderando sorgenti o bersagli con
quello che le sorgenti dicono di sé; l'unico segnale è una riponderazione per gene (la quota condivisa),
positiva su due linee su tre. Una prova sul pannello con regola nuova sarebbe un'ipotesi nuova,
suggerita da questo quasi-passaggio: va registrata come tale e letta con quella cautela.

## Prima del banco: due controlli descrittivi (misurati, 26/09 sera)

**I bersagli del pannello sono knockdown tipici, non i più forti** (`panel_strength.py`, uscita in
`forza_pannello/`). L'energia degli effetti ristretti sui geni espressi in A/B/C (pesi log1p, gene
bersaglio escluso) mette i bersagli del pannello al percentile mediano 0,54 fra gli altri 9.594 del K562
(quartili 0,34 e 0,71) e 0,59 fra gli altri 11.945 del CD4 (0,32 e 0,76); la coda alta del pannello è
anzi più sottile (90° percentile 37 contro 58 nel K562). Quindi un campione casuale di bersagli fuori dal
pannello rappresenta il pannello, almeno per forza dell'effetto nelle linee pubbliche: la regola non
cambia.

**Che cosa condividono K562 e CD4** (`shared_response.py`, uscita in `condivisione_r1/`), sugli 8.423
bersagli misurati da entrambi fuori dal pannello:
- **Per bersaglio, i profili quasi non si somigliano.** Il coseno fra il profilo K562 e quello CD4 (geni
  espressi, pesi log1p) ha mediana 0,009 (10°–90° percentile −0,022…0,058); solo 340 bersagli superano
  0,1 e 67 superano 0,2. Anche nel decimo più forte per energia la mediana è 0,016. Il coseno è calcolato
  su profili grezzi con il loro rumore, quindi sottostima l'accordo delle risposte vere; ma dice che per la
  grande maggioranza dei knockdown il profilo di un'altra linea porta poca direzione utile.
- **I bersagli che si trasferiscono** sono regolatori generali della trascrizione e dell'RNA: in testa
  MED12 (0,46), CASC3, DHX36, ELOF1, SLC30A1, UFM1, SMG5, SUPT20H, INTS10, MED19, GABPB1, OXA1L, DENR, MED14,
  UPF2; per classe, Mediator (mediana 0,055, 75° percentile 0,156), TFIID (75° percentile 0,134),
  ribosoma mitocondriale (mediana 0,063). Ribosoma citoplasmatico, proteasoma e chaperonina restano vicini
  a zero (mediane 0,002, 0,003, 0,000). **Interpretazione:** si trasferisce il knockdown di macchinari che
  ogni cellula usa allo stesso modo (Mediator, SAGA/TFIID, Integrator, NMD, UFMilazione); quello di
  complessi essenziali con risposte forti ma dipendenti dal contesto (ribosoma, proteasoma) no, forse
  perché in una delle due linee le cellule con quel knockdown sono poche o già selezionate.
- **Per gene**, dei 11.021 geni espressi in A/B/C solo 637 hanno varianza di segnale sopra il rumore in
  entrambe le linee (2.321 nel K562, 2.066 nel CD4, con la varianza dello SE di CD4 × 2). Su quei 637 la
  correlazione fra linee delle risposte, corretta per il rumore, ha mediana 0,30; più alta per la risposta
  a proteine mal ripiegate (0,45), il genoma mitocondriale (0,31) e la sintesi del colesterolo (0,31), bassa
  per il ciclo cellulare (0,11). I geni con più covarianza condivisa sono PHGDH, TXNIP, i geni MT-ND,
  DDIT4, TRIB3, EIF4EBP1, FADS1: in buona parte bersagli di ATF4 (risposta integrata allo stress) e
  trascritti mitocondriali (**interpretazione** sui nomi, non un test di arricchimento).

Conseguenza per il banco (**ipotesi**): la parte trasferibile è piccola e concentrata in pochi programmi e
pochi bersagli; i bracci che la isolano (varianze per gene, accordo per bersaglio) hanno qualcosa da
trovare, ma il margine atteso sul PDS è piccolo.

## Linea, laboratorio e stato cellulare: quanto si somigliano i profili (misurato, 26/09 notte)

Due corse in più di `shared_response.py` (`condivisione_r2/`: le tre condizioni di CD4 fra loro e il K562
contro CD4 a riposo e a 48 ore; `condivisione_r3/`: coppie con gli universi K562 essential e RPE1 di
Replogle, costruiti in serata) e una tabella che le mette **sugli stessi bersagli** (`pair_table.py`,
uscita in `confronto_r1/`). Coseno fra i profili delle due sorgenti sui geni espressi in A/B/C (pesi log1p,
gene bersaglio escluso), **senza correzione per il rumore**; accanto le cellule per bersaglio, perché meno
cellule vuol dire un profilo più rumoroso e un coseno più basso.

Sui 1.242 bersagli "essential" misurati da tutte le coppie:

| Coppia | Che cosa cambia | Cellule (mediana) | Coseno mediano | 75° percentile | Quota > 0,1 |
|---|---|---|---|---|---|
| CD4 Rest × CD4 Stim8hr | stesse cellule e donatori, altro stato | 208 / 213 | 0,254 | 0,357 | 95 % |
| CD4 Stim8hr × CD4 Stim48hr | stesse cellule e donatori, altro stato | 213 / 188 | 0,214 | 0,312 | 93 % |
| CD4 Rest × CD4 Stim48hr | stesse cellule e donatori, altro stato | 208 / 188 | 0,201 | 0,285 | 88 % |
| K562 essential × K562 | stessa linea, altro esperimento (stesso laboratorio) | 122 / 205 | 0,160 | 0,279 | 73 % |
| RPE1 × K562 | altra linea, stesso laboratorio | 80 / 205 | 0,074 | 0,135 | 39 % |
| RPE1 × K562 essential | altra linea, stesso laboratorio e disegno | 80 / 122 | 0,070 | 0,131 | 37 % |
| RPE1 × CD4 | altra linea e laboratorio | 80 / 614 | 0,032 | 0,086 | 21 % |
| K562 × CD4 (media delle condizioni) | altra linea e laboratorio | 205 / 614 | 0,025 | 0,062 | 14 % |
| K562 essential × CD4 | altra linea e laboratorio | 122 / 614 | 0,022 | 0,054 | 9 % |
| K562 × CD4 Rest | altra linea e laboratorio | 205 / 208 | 0,019 | 0,053 | 12 % |
| K562 × CD4 Stim48hr | altra linea e laboratorio | 205 / 188 | 0,018 | 0,051 | 10 % |

Sui 290 bersagli non essential comuni alle coppie che li coprono l'ordine è lo stesso (stati di CD4
0,24–0,28; RPE1 × K562 0,088; K562 × CD4 0,036–0,048).

- **Misurato:** a parità di rumore, K562 contro CD4 a riposo (205 e 208 cellule) dà 0,019, le stesse
  cellule CD4 a riposo contro stimolate 8 ore (208 e 213 cellule) danno 0,254: tredici volte tanto. La
  stessa linea in due esperimenti diversi del laboratorio (K562 essential contro genome-wide) tiene 0,160
  con meno cellule; un'altra linea dello stesso laboratorio scende a circa 0,07; un'altra linea di un altro
  laboratorio a 0,02–0,03.
- **Limiti:** le condizioni di CD4 condividono donatori e guide, quindi 0,20–0,25 è un tetto per "stessa
  linea, altro stato"; K562 essential e genome-wide sono dello stesso laboratorio. Il coseno non è
  corretto per il rumore: la correzione con gli SE fallisce sulle sorgenti Replogle, dove la somma degli
  SE² della formula quasi-Poisson supera l'energia osservata (1,7 volte nel K562, 2 nel K562 essential,
  3 nell'RPE1; `condivisione_r3/summary.json`).
- **Interpretazione:** l'identità della linea (e con essa il laboratorio e il protocollo) pesa molto più
  dello stato cellulare. Dati della stessa linea dei contesti valgono, per bersaglio, molto più dei dati
  di un'altra linea; quanto recuperi la media di molte linee diverse non è misurato qui (lo misura il
  banco). È la prova misurata più diretta sulla domanda strategica aperta della scheda R-V2, che resta
  una decisione del proprietario.

## Lo SE delle sorgenti Replogle: controllo sulle guide non mirate (misurato, 26/09 notte)

La correzione per il rumore della sezione precedente falliva perché la somma degli SE² della formula
quasi-Poisson di `effects_from_bulk` (phi 0,2) superava l'energia osservata. Se lo SE fosse sovrastimato
in generale, `z_shrink` dello stadio 98 restringerebbe troppo gli effetti K562 in ogni ricetta. Controllo
(`se_calibrazione/`): ogni guida non mirata (rumore puro, almeno 20 cellule) contro le altre, varianza
osservata del fold change contro SE² della formula, per fascia di espressione dei controlli (`ntc.txt`).
- **Misurato:** sulle guide non mirate il rapporto osservato/previsto è 0,96–1,08 nelle fasce basse e medie
  del K562 genome-wide, 0,88 e 0,68 nelle due fasce più espresse (3–10 e oltre 10 conteggi per cellula:
  phi 0,2 è troppa sovradispersione lì); K562 essential simile (0,94–1,23, poi 0,77 e 0,71); RPE1 1,09–1,29,
  0,90 in cima. Sui primi 600 bersagli del K562 (`targets_k562.txt`) la mediana per voce di y²/SE² è 0,48,
  quella attesa per rumore puro con SE giusto (0,455), mentre la media complessiva è 0,67 volte quella degli
  SE²: la differenza viene dalla coda di voci con SE grande (pochi conteggi).
- **Conclusione:** lo SE è grosso modo calibrato per le voci tipiche; l'ipotesi che le ricette restringano
  troppo il K562 non è sostenuta. Resta una sovrastima per i geni più espressi (fino a 1/0,68 in varianza),
  che pesa di più con i pesi log1p dello scorer: è la ragione principale per cui la correzione per il rumore
  fallisce, non un difetto delle ricette.

## r2: replica con HEK293T (lancio alle 12:04 del 27/09)

Ora d'avvio del processo: 12:04:54 del 27/09. L'universo HEK293T è completo dalle 01:44 dello stesso giorno:
17.270 bersagli con effetti, parità esatta con la cache r5 sui 281 del pannello
(`../universo_2026-09-26/orion_hek293t/`).

r2 è la replica prevista dalla regola delle 19:15. Usa lo stesso script con i parametri di default di r1:
1.000 bersagli di prova, seme 20260926, bersagli essential fuori dalla prova. Gli universi sono quattro
(K562, CD4 `cd4_mix`, HCT116 e HEK293T), ognuno tenuto fuori a turno; con una linea Orion fuori esce anche
l'altra, che è della stessa famiglia. Con quattro universi cambia l'insieme dei bersagli idonei: per K562,
CD4 e HCT116 i bersagli di prova non sono quelli di r1.

Come dice la regola, r2 si riporta e non cambia la lettura di r1. Nel frattempo il braccio `share_atlas`
è diventato il t23 passando per un banco sul pannello con una regola sua
([quota condivisa](../quota_condivisa_2026-09-27/RISULTATI.md)); r2 non decide nulla neanche sul t23.
