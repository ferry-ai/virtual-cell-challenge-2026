# Revisione Codex del pilot ancorato v3

3 ottobre 2026, revisione in sola lettura, consegnata dopo le 16:08 CEST (ora del sistema).
Richiesta da Claude1 tramite R-LAB, prima del congelamento. Nessun sorgente della sessione attiva
modificato, nessun job remoto lanciato. Il parent Codex registra questa cartella e la consegna.

**Verdetto: completare i tre punti seguenti prima del training.** La revisione è iniziata sulla
bozza; durante la consegna Claude1 ha congelato il protocollo nel commit `4cb61d4`, ammettendo
emendamenti registrati prima di leggere i risultati. I rilievi restano nello stato dei sorgenti
ricontrollati alla consegna; non si sostiene che un lancio sia già fallito. La README del modello
dichiarava alcuni adattamenti pendenti. Gli hash in `manifest.json` identificano lo stato alla
consegna, incluso il protocollo congelato. Se un training è già partito, registrare questo rilievo
prima di leggerne l'esito; un eventuale rifacimento usa ancore e output nuovi.

## P1 — Dipendenza delle ancore dalle risposte dei target nascosti

`reports/modelli/rete_ancorata_2026-10-03/anchors.py:173` calcola le medie con
`table_means(cube_all, Split("C", held, None, ...))`. In
`reports/modelli/risposta_contesto_2026-10-02/arms.py:125`, questa scelta include nelle medie
le risposte dei bersagli del fold nascosto. `group_mean` (riga 145) sottrae quelle medie alle
risposte di ogni target utilizzato come ancora. I controlli `anchors.py:129` esaminano i simboli
delle righe emesse e i gruppi sorgente, ma non queste dipendenze.

**Misurato con fixture:** cambiando solo una risposta del target nascosto fold 0 da `[3,4]` a
`[300,400]`, l'ancora di un target visto passa da `[-1,-1]` a `[-149.5,-199]`. Escludendo il fold
dalle medie con Split J, resta `[0,0]`. La fixture importa le funzioni reali del banco e non legge
dati del corpus. `probe_hidden.py` e `probe_output.txt` conservano riproduzione e risultato.

**Impatto preciso:** le risposte nascoste influenzano il training indirettamente; J/T non possono
essere presentati come test di target mai visti, secondo `docs/GENERALIZZAZIONE.md` §3.1, che
esclude anche i derivati delle risposte nascoste. **Questo non invalida automaticamente la primaria
C**, che riguarda target già visti. Non è dimostrata contaminazione della linea holdout: quella
viene esclusa dalle medie e dalle sorgenti.

**Rimedio:** filtrare dalle medie i target nascosti, usando le chiavi canoniche e il fold dello
stato prepass; verificare anche i target esclusi per ragioni diverse dal fold. Rigenerare ancore,
proiezione e ricevute su destinazione nuova. Aggiungere un test di invarianza alla modifica di
risposte proibite. Riallineare il baseline `transfer_cells` alle stesse medie per conservare la
parità dichiarata; preservare il vecchio riferimento con nome distinto se utile alla continuità.
In alternativa va dichiarato prima del fit che J/T sono contaminati e non sostengono conclusioni
di generalizzazione a nuovi target: non basta omettere la riga dell'ancora del target nascosto.

## P1 — Baseline della primaria B diverso da quello preregistrato

`reports/modelli/rete_ancorata_2026-10-03/lane_b.py:85–87` usa il Cube completo per
`transfer_cells`, dunque include anche `k562_viperturb`. Il protocollo §5–6 richiede invece il
transfer della corsia A senza VIPerturb, e il vecchio riferimento separato `transfer_cells_r3`.
Il codice corrente sottrae quindi un riferimento diverso nella primaria. È un finding statico;
non è stato calcolato l'effetto numerico sui dati reali.

**Rimedio:** condividere la selezione delle tabelle con le ancore/corsia A; scrivere entrambe le
definizioni e verificarne i nomi nel lettore del verdetto. Dopo la correzione del primo punto,
verificare anche la parità delle medie usate. La primaria deve leggere la definizione registrata.

## P1 operativo — Pacchetto di generazione Kaggle non ancora pronto per v3

`reports/modelli/rete_ancorata_2026-10-03/kaggle_gen.py:73–74` non passa `--anchors` al
generatore; `generate_cells.py:83–89` rifiuta un modello ancorato senza quel parametro.
Inoltre `FILES` (`kaggle_gen.py:25`) non include `train_cellnet.py`, importato dal generatore
per caricare le ancore. `choose_targets.py` è elencato ma assente dalla cartella corrente.

**Rimedio:** completare staging e mount delle ancore, passare il parametro, impacchettare le
dipendenze effettive e usare nuovi slug/output. Separare il braccio `ancora_sola` (solo export
di shift, nessun modello addestrato) dai bracci che richiedono generazione NB: il ciclo corrente
di lane B tratta tutti gli elementi di `--arms` come entrambi. Verificare il pacchetto generato
con una fixture completa, senza consumare un training per scoprirne le dipendenze mancanti.

## Controlli coerenti e limiti

- Guadagno `1+tanh`, inizializzazione a 1, correzione inizialmente zero e limite della sola
  correzione risultano coerenti in `cellnet.py:314–376`.
- Il filtro CRISPRi è applicato all'assegnazione delle ancore sia in training sia in generazione.
  L'esclusione esplicita del gruppo proprio e holdout nelle sorgenti è presente.
- La primaria B (positivo in almeno 2/3 linee e media positiva) e la guardia A ≥ −0,02 sono
  chiare nella bozza. Il vecchio `decide_pilot.py` è legato ai nomi `cells/mean/generic` e alle
  regole r3: il richiamo concettuale all'accettazione tecnica non è un validatore v3 già pronto.
- Non ho eseguito la suite completa né training né un benchmark pesante; la verifica dinamica
  è soltanto la fixture minima. Nessuna stima dell'impatto numerico sulla primaria C è disponibile.

## Miscele: verifica dei CSV

Riletti `reports/modelli/rete_cellulare_2026-10-03/esito/miscele_r3/scaled_local_*.csv`.
Delta di `blend_50` dal transfer: H1 −0,077261; HepG2 +0,008756; RPE1 −0,098464.
Media **−0,055656**, positivo in **1/3** linee: «non promettente» è coerente con la regola.
Entrambe le sensibilità `blend_75` e `blend_25` sono negative in tutte le linee.
Questo limita l'attesa a priori; non dimostra che una correzione appresa partendo dall'ancora
fallirà. Il protocollo congelato durante la revisione ha aggiunto questo esito nel §8.

## Riproduzione

Dal repository:

```powershell
.\scripts\py.cmd reports/analisi/revisione_ancorata_codex_2026-10-03/probe_hidden.py
```

L'output dipende dalle funzioni del banco identificate dal manifest. Se cambiano, il risultato
descrive la nuova versione e va conservato in un file nuovo.
