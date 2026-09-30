# Riapplicare la rete alla ricetta t25: candidato distinto

29 settembre 2026. **Proposta e implementazione**, prima dei risultati della rete.
Non modifica i cinque file congelati del training né la loro regola di lettura.

## Perché non sostituire direttamente la direzione

Il vecchio `reports/modelli/rete_contesti_2026-09-27/to_effects.py` sostituisce il
vettore di t25 con quello della rete e ne eguaglia la norma per bersaglio. Al passo
zero la rete sulle sorgenti restituisce la propria media del dataset r2: non è t25.
R2 usa centri genome-wide, arrotondamento float16, altre sorgenti e bilanciamento per
famiglia; t25 usa quattro sorgenti r9, centri del pannello, gamma 1 e ampiezza 1,576.
La parità di norma non conserva direzione, maschera o identità della baseline.

## Operatore proposto e condizioni

Si mantengono gli input e le normalizzazioni r2 identici a quelli del training.
Da ciascun token si estraggono soltanto `r = exp(2 tanh(logit))` e il cancello
`h = 1 + 0,25 tanh(gate)`. Il trasferimento di produzione usa questi modificatori
come variazioni relative dei propri pesi, con la propria affidabilità cellulare.
Non si usa il rapporto `net / baseline`, instabile quando le sorgenti si cancellano.

- Token `k562` sulla sola sorgente r9 K562 genome-wide. `k562ess` e VIPerturb non
  diventano automaticamente pesi della sorgente K562 di t25.
- Due token Orion sulle rispettive sorgenti. RPE1 e iPSC non hanno contributi in
  t25 e non vengono inventati nell'adattatore.
- CD4 mix è decomposto nei suoi tre stati con gli esatti pesi interni della cache
  (`n/(n+100)` per gene misurato). Ogni contributo sottrae **lo stesso centro di
  cd4_mix**, non il centro r2 o il centro separato dello stato. La piccola differenza
  di arrotondamento float32 della miscela viene distribuita ugualmente fra gli stati;
  differenze superiori a 2e-6 fanno rifiutare la cache.
- Un token privo di osservazione diretta, fuori dall'asse modellato o derivato da
  fallback STRING mantiene modificatori unitari. Un proxy di partner non viene
  interpretato come knockdown misurato nella sorgente della ricetta.

Siano `m0` la media r9 ricostruita e `m1` la stessa media con pesi moltiplicati per r
e valori moltiplicati per h. L'export è:

`effetto_nuovo = effetto_t25_salvato + 0,5 × 1,576 × (m1 − m0)`.

Il cambiamento si applica soltanto alle coppie osservate in t25 fuori dal gene
bersaglio e dalla finestra cis di 5 kb. Tutto il cis, il gene proprio e la maschera
`observed` sono copiati. Nessuna seconda normalizzazione della norma o dell'ampiezza.
Se tutti i modificatori sono unitari, il delta è esattamente zero e gli array degli
effetti sono copiati bit per bit. Anche una rete addestrata che sceglie il passo zero
produce questa identità.

Prima di applicare il delta, l'adattatore ricostruisce il trasferimento t25 dalla
cache e lo confronta con il riferimento salvato fuori dalle regioni protette;
verifica ricetta, ordine dei geni/bersagli e hash del riferimento dal suo manifest.
Registrare l'hash dei file della cache compensa la mancanza del manifest della vecchia
r9; non si finge che la cache avesse già quelle verifiche nel settembre 27.

## Limite scientifico e prova successiva

Questo è **un nuovo candidato**, non l'oggetto misurato dai cinque fold. Cambia la
base, restringe le sorgenti e cambia il centro. Il successo della rete autorizza a
valutarlo, non a ereditarne il punteggio. Non si adattano o selezionano i pesi sul
pannello A/B/C usando outcome nascosti. Gli effetti pubblici r2 restano input consentiti
di un predittore C; nessun outcome del contesto da prevedere entra dopo la selezione.

La prova preferibile è ripetere l'operatore relativo su una baseline pubblica della
stessa famiglia di ricette, escludendo integralmente la famiglia tenuta fuori e
costruendo i centri senza i suoi outcome. Scegliere il solo sottoinsieme favorevole
dei cinque fold non sarebbe una conferma. Prima dell'invio serve comunque il banco
cellulare del candidato completo, con il medesimo generatore del confronto.

## Audit della copertura e delle versioni

La lettura congelata pretende cinque famiglie C: K562, CD4, Orion, iPSC e RPE1.
K562 comprende tre schermi, CD4 tre stati, Orion due linee e iPSC tre schermi: 12
contesti CRISPRi; A549 è il tredicesimo contesto nel file ma viene escluso per modalità
knockout. I 512 bersagli sono un massimo per contesto, scelti fuori dal pannello.
RPE1/iPSC hanno universi più piccoli e non equivalgono a repliche indipendenti di
tecnologia. Gli intervalli ricampionano bersagli nei cinque gruppi osservati; non
misurano l'incertezza su un universo arbitrario di linee nuove.

Il protocollo contiene una riga «macro-contesto», mentre la sua sezione separazioni
e il lettore fissano peso uguale alle famiglie, poi ai loro contesti. La lettura
operativa è quest'ultima, già implementata prima dei risultati; non è mediare tutti
i contesti dando triplo peso alle famiglie con tre schermi.

Il lettore congelato verifica cinque fold e seed/regime/split, ma non confronta da
solo tutti gli hash fra i run. Prima di interpretarli bisogna verificare un'unica
snapshot del codice, del protocollo, del dataset e delle opzioni. I grandi array r2
sono identificati nel manifest corrente da dimensione e manifest del dataset,
non da un nuovo hash integrale: è una limitazione di provenienza dichiarata.

## Verifiche completate e comandi

**Misurato:** otto test sintetici dell'adattatore passano. Coprono identità byte per
byte degli array, decomposizione CD4, ordine gamma/cancello/ampiezza, preservazione
cis, assi permutati riallineati per nome, rifiuto di cache e riferimento incoerenti,
fallback STRING lasciato neutro, CLI `apply` e NPZ con `allow_pickle=False`.

**Misurato sui file reali:** `check_t25_anchor.py` ha letto la cache r9 e i tre file
t25 originali; risultato in `neural_adapter_r1/neutral_t25.json`, concluso alle
18:05:49 UTC. Su **300 bersagli in ciascuno di A/B/C**, gli array `targets`, `genes`,
`lfc`, `observed` sono identici byte per byte dopo l'operatore neutro; coppie cambiate
zero. L'errore massimo della ricostruzione del trasferimento prima della copia è
2,3821e-7, compatibile con l'arrotondamento float32. Picco RSS misurato 356.216.832
byte. Non sono stati eseguiti training, scoring o generazione di cellule.

I comandi separano estrazione dei modificatori e applicazione alla vera ricetta:

```text
python reports/analisi/lead_scientist_2026-09-29/t25_source_adapter.py export --checkpoint PRODUZIONE/model_true.pt --data DATASET_R2 --targets PANEL.txt --contexts A,B,C --device cuda --out NUOVI_MODIFICATORI
python reports/analisi/lead_scientist_2026-09-29/t25_source_adapter.py apply --cache CACHE_R9 --reference EFFETTI_T25 --factors NUOVI_MODIFICATORI --coords COORDINATE.tsv --recipe configs/recipes/t25.json --out NUOVI_EFFETTI
```

L'export richiede un checkpoint C addestrato per produzione (`holdout none`), verifica
codice e identità registrata del dataset e conserva i modificatori unitari dove
manca una misura diretta. Non modifica input della rete per farli assomigliare a r9.
Le inferenze complete vanno eseguite sul runner: ricostruire `SourceView` legge gli
effetti r2 visibili, anche se le matrici restano mmap.

Per i risultati dei cinque fold, il wrapper `read_neural_verified.py` aggiunge la
guardia di provenienza e la correzione meccanica del nome `null` descritta in
`EMENDAMENTO_LETTORE_NEURALE_01.md`; sei test sintetici passano. Il training remoto
versione 1 resta immutato.
