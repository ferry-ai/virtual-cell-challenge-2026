# CP-0048 — La rete che pesa le sorgenti non supera la soglia nel primo seme

- **Data:** 2026-09-29
- **Tipo:** osservazione
- **Redatto da:** Codex, sessione 01a0ee03-b357-7012-81a9-e8d7de767478
- **Revisione umana:** no
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

La rete che mantiene separate le sorgenti e ne impara i pesi supera il
trasferimento congelato su famiglie cellulari tenute fuori? Il contesto basale
aggiunge un beneficio misurabile rispetto alla stessa rete resa cieca al contesto?

## 2. Cosa è stato fatto

Il notebook privato Kaggle `davidmaisterx/vcc-lead-neural-sources-r1`, versione 1,
ha eseguito cinque fold C, seme 0, sul dataset r2: famiglie K562, CD4, Orion,
iPSC e RPE1. Protocollo e split sono congelati in
`reports/analisi/lead_scientist_2026-09-29/PROTOCOLLO_NEURALE.md`.

I cinque fold hanno terminato con codice 0 entro le 19:24:12 UTC. Il solo lettore
finale è fallito con `KeyError: 'null'`, già previsto dall'emendamento meccanico.
Sono stati recuperati 61 report piccoli; guardia di provenienza e lettore corretto
hanno elaborato tutti i fold, senza riaddestramento o selezione parziale. Fonte:
`reports/analisi/lead_scientist_2026-09-29/kaggle_neural_r1/results_small_r1/neural_sources_r1/completion.json`
e `readout_verified_r1/` nella cartella `kaggle_neural_r1`.

## 3. Cosa si è osservato

**Misurato:** 6.144 coppie bersaglio–contesto, 12 contesti e cinque famiglie.
Il delta PDS medio a famiglie equiponderate contro transfer è +0,002222,
IC95% registrato [0,000556;0,003907]. È inferiore alla soglia minima +0,01:
`eligible_for_cell_scorer=false`. Delta per famiglia: CD4 +0,005157,
iPSC +0,003278, K562 −0,007229, Orion −0,001313, RPE1 +0,011218.

Contro la rete cieca al contesto, il delta è −0,000416, IC95%
[−0,001044;+0,000213]. Contro i basali scambiati è −0,000223,
IC95% [−0,000438;−0,0000168]. Fonte di tutti i numeri:
`reports/analisi/lead_scientist_2026-09-29/kaggle_neural_r1/readout_verified_r1/verdict.json`.
La provenienza verificata è nel `provenance.json` adiacente; la verifica indipendente
dei punti aggregati è in `kaggle_neural_r1/independent_points_r1.json`.

## 4. Interpretazione e incertezza

**Interpretazione:** il piccolo vantaggio medio non raggiunge l'utilità minima
scelta prima degli esiti. Il confronto cieco e quello con basali scambiati non
sostengono un beneficio utile del condizionamento biologico implementato.
Non dimostrano che la rete ignori ogni informazione di contesto, né che tutte
le reti neurali siano inadatte al problema.

**Limiti:** un solo seme completato; regime C su contesti pubblici, non gara;
gli intervalli originali ricampionano bersagli entro ciascun contesto e non
modellano tutta la dipendenza di bersagli condivisi fra contesti. La diagnostica
con cluster globali è additiva e non modifica retroattivamente la soglia.
La seconda replica era già partita prima di leggere questi esiti.

## 5. Spiegazione semplice

Imparare quali esperimenti ascoltare di più dà qui un miglioramento piccolo e
irregolare. Sapere il profilo basale della cellula destinataria, nella forma
fornita a questa rete, non migliora il risultato rispetto a non conoscerlo.

## 6. Conseguenze

Non si avvia il fit di produzione né si aggiunge questa rete al t28. La replica
seme 1 si legge comunque integralmente, secondo l'emendamento di scheduling
fissato prima dei risultati; non si sceglie il solo seme favorevole.

Prosegue la via distinta Stack preaddestrata, insieme alla generazione t28 già
registrata. Questo esito chiude il primo gate della rete a sorgenti separate,
non il lavoro scientifico della sessione e non ogni modello complesso.

## 7. Cosa corregge

Nessun risultato storico. Risponde al primo esperimento neurale annunciato in
CP-0046. Le proposte di un vantaggio del condizionamento restano non confermate
per questa architettura e questo regime; non diventano risultati positivi perché
l'addestramento è stato eseguito con successo.

## 8. Domanda di comprensione

Perché un delta medio positivo e un intervallo che esclude zero non bastano
a promuovere questa rete secondo la regola fissata prima del test?
