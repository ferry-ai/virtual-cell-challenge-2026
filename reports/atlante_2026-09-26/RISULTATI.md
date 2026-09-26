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
