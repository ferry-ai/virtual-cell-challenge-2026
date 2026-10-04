# Banco v2 t28: esito delle cinque reti congelate

**Misurato il 4 ottobre 2026; lettura verificata alle 21:04 CEST.** Tutti i cinque
kernel CPU sono completati, incluso K562 r2. Nessun nuovo training o invio.

## Protocollo e verifica

[Protocollo congelato](PROTOCOLLO.md), commit `55ae28b`, prima dei lanci;
[emendamento K562](EMENDAMENTO_K562.md), commit `9cad688`, prima del retry.
Quattro bracci, 400 cellule per bersaglio, cinque semi del generatore, emissione t28,
scorer `cell-eval2==0.16.0`. Stessa casualità per bersaglio e seme fra i bracci.

[read_results.py](read_results.py) verifica ricevute e SHA256 dei sette file decisivi
per ogni linea nelle cartelle `lettura_*`, completamento di export e scoring,
preflight degli input, CPU e risorse, parità a correzione zero, esclusione della linea,
assi e hash degli effetti, codice del banco e parametri. Ricalcola dai membri di
`bench.json` tutte le differenze appaiate, grezze e scalate, e le confronta con
`paired.json`. Esito: cinque verifiche passate; [decisione completa](decisione_r1.json).
Gli stati remoti sono in [stato_avanzamento_r2.json](stato_avanzamento_r2.json).

La regola fissata prima è `abs(media) > 2 * sd / sqrt(5)` per chiamare un guadagno
risolto. Un confronto è favorevole solo se la media dei sei membri è risolta positiva,
lo è anche senza Jaccard e il PDS non è risolto negativo. Nessuna soglia è cambiata.

## Risultati

Differenze correzione meno baseline; media ± deviazione standard sui cinque semi,
in scala locale. **Non sono punteggi VCC.** `all` è la baseline del banco;
`prod` è quella di produzione ricostruita nella stessa emissione t28.

| Linea | Sei membri, all | PDS, all | Regola all | Sei membri, prod | PDS, prod | Regola prod |
|---|---:|---:|---|---:|---:|---|
| H1 | +0,00279 ± 0,00301 | +0,01410 | passa | +0,00443 ± 0,00598 | +0,02021 | non risolto |
| HepG2 | +0,01062 ± 0,00406 | −0,12111 | perde PDS | +0,05652 ± 0,00156 | −0,12533 | perde PDS |
| RPE1 | +0,01804 ± 0,00839 | +0,06162 | passa | +0,00308 ± 0,00497 | −0,07014 | non risolto e perde PDS |
| Jurkat | +0,01944 ± 0,00567 | +0,04151 | passa | +0,02178 ± 0,01166 | +0,02805 | passa |
| K562 | +0,01439 ± 0,01249 | +0,01203 | passa | +0,01649 ± 0,01857 | +0,00819 | non risolto |

- **all: 4/5 favorevoli**, media fra linee +0,013057; HepG2 non passa la guardia PDS.
- **prod: 1/5 favorevole**, Jurkat; media fra linee +0,020458. La media positiva
  nasconde perdite risolte di PDS su HepG2 e RPE1.
- Jurkat è l'unica linea favorevole su entrambe. H1 su all è vicina alla soglia;
  K562 su prod resta appena sotto: +0,016491 contro una soglia di circa 0,016606.
  Gli arrotondamenti della tabella non determinano il verdetto.
- Le medie senza Jaccard, nello stesso ordine H1/HepG2/RPE1/Jurkat/K562:
  all +0,003462/+0,017312/+0,021544/+0,024074/+0,017514;
  prod +0,005382/+0,065216/+0,002618/+0,026916/+0,020906.
  Membri, dispersioni, valori per seme e condizioni booleane sono nella decisione JSON.

## Interpretazione e limiti

**Interpretazione:** il beneficio della correzione dipende dalla baseline. In questo
banco RPE1 guadagna PDS su all ma lo perde su prod. Riutilizzare R appresa contro all
su prod è un contrasto diagnostico: non dimostra il comportamento di una rete nuova
addestrata coerentemente sulla ricetta di produzione. Il prossimo ibrido deve essere
valutato con baseline ed emissione identiche a quelle della sua esportazione.

La dispersione misura soltanto il rumore del generatore: verità, controlli e reti
sono fissi. Cinque semi non misurano l'incertezza biologica, del training o di nuovi
contesti; la regola euristica non è un intervallo di confidenza validato. Le cinque
linee sono già sviluppo. Nessuna selezione automatica del fold Jurkat e nessuna
promozione al sito. Il confronto con CP-0065 non isola l'emissione t28, perché cambia
anche il flusso casuale. CP-0065 resta la lettura del proprio banco.

**Copertura:** pilot a otto gruppi, non corpus completo D-053. K562 conserva tutti i
bersagli: otto senza supporto nella baseline prod restano al basale in entrambi i
bracci, come documentato nell'emendamento e nel manifest. Non vengono tolti dal voto.

## Chiusura operativa

Gli archivi `esito_*` conservano i download estesi. Quello H1 è parziale per un errore
TLS del client durante il recupero di un log; la lettura scientifica usa invece
`lettura_h1_r1`, completa e con ricevuta verificata, come le altre quattro linee.
L'errore di download non è un errore del kernel né un dato mancante nel verdetto.

CD4: tutte le 12 unità sono già verificate nella
[riconciliazione](copertura_cd4_r2.json). Integrazione nel corpus e verifica dell'uso
effettivo nel training restano lavori distinti. Questi cinque banchi sono chiusi;
nessuna GPU consumata dai loro kernel CPU.
