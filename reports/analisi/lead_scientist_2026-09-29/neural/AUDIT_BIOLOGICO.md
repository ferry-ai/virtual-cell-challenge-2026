# La rete ha bisogno di distinguere le sorgenti e ciò che sa del bersaglio

29 settembre 2026. **Misure esplorative e proposta**, nessun training o punteggio
nuovo. Input: CSV già prodotti il 27 settembre e metadati del dataset neurale r2.
Riproduzione: `audit_neural_metadata.py`; uscita valida `metadata_r3.json`.
Le uscite r1/r2 documentano l'estrazione incompleta delle chiavi numpy della mappa
Arc; il confronto genetico va letto solo in r3, dopo decodifica UTF-32.

## Una rete complessa riceveva prior biologici molto poveri

**Misurato:** `processed/rete_contesti_r2/targets.csv` contiene 19.265 bersagli e
soltanto sette prior `p_*`: media/deviazione dell'espressione basale, ampiezza fra
contesti, presenza sull'asse, vicini cis a 5/20 kb, grado STRING. Non contiene
annotazioni GO, CORUM, pathway, attività TF, sequenza proteica o embedding funzionali.
`data.py:245–271` costruisce questi descrittori; `pool.py:299` usa esclusivamente
colonne `p_*`/`x_*`. Il campo `essential` descrive l'appartenenza a una screen e non
entra nel vettore dei prior. Il modello ha anche profili di risposta dei partner;
questo non trasforma il grado scalare in un'annotazione di funzione.

**Misurato:** nei 300 bersagli il grado STRING fisico mediano è 2, contro 16 nei
2.057 bersagli della screen essenziale; il pannello non ha intersezione con questa
screen. Non segue che i 300 siano biologicamente non essenziali. Il mediano di
`p_expr_breadth` è 1 nel pannello: il bersaglio spesso è espresso in tutti i contesti,
quindi la sola presenza del suo RNA discrimina poco lo stato della rete a valle.

**Interpretazione:** il fallback ai partner ha supporto molto diseguale. Le metriche
devono riportare numero e peso dei partner effettivamente disponibili e separare
bersagli con 0, 1–2 e almeno 3 partner. Una rete che riesce sugli hub non ha ancora
dimostrato di riuscire sul pannello a basso grado.

## Efficienza del silenziamento: informazione di sorgente, non divisore globale

Misure sul pannello presenti nei piccoli CSV `per_target_*` del report
`reports/sorgenti/profondita_silenziamento_2026-09-27/r1/`. La profondità è il negativo
dell'effetto raw sul bersaglio; il segnale chiaro è z ≤ −3. Il denominatore della
percentuale comprende soltanto le misure finite del gene proprio.

| Sorgente | Bersagli con misura finita | Silenziamento chiaro | Profondità mediana |
|---|---:|---:|---:|
| K562 | 229 | 193 (84,3%) | 2,010 |
| CD4 Rest | 289 | 258 (89,3%) | 1,981 |
| HCT116 | 260 | 187 (71,9%) | 1,171 |
| HEK293T | 277 | 213 (76,9%) | 0,712 |
| KOLF | 261 | 144 (55,2%) | 0,870 |

**Misurato:** l'energia mediana del pannello in KOLF è 0,00616, contro 0,00337 in
K562; dunque la maggiore energia della sorgente non certifica un silenziamento
più affidabile. L'energia include biologia, rumore e differenze dello stimatore.
I risultati precedenti sulle coppie avevano pendenze log-energia/log-profondità
0,09–0,48, lontane da 2. Dividere gli effetti per la profondità non è sostenuto.

**Proposta attuabile:** fornire all'attenzione, per ciascuna sorgente visibile,
`clip(depth,0,4)`, `clip(-z,0,10)`, indicatore di disponibilità. Stessi ingressi in
training e inferenza: nessuna profondità del contesto da prevedere. Nel regime J,
nessun outcome del bersaglio, compreso il suo knockdown, può rientrare; il canale
diretto è mancante. Per i partner si possono riassumere le sole misure ammesse.
Il vecchio `--use-depth` non è equivalente: `pool.py:687–688,724–735` usa parte delle
misure proprie in training e il riferimento delle sorgenti in inferenza.

## Una feature biologica locale falsificabile

**Ipotesi:** per un bersaglio, la sorgente utile è quella dove anche i suoi partner
sono nello stato di attività appropriato. La somiglianza globale del basale o il
solo RNA del bersaglio possono non catturarlo.

**Proposta**, usando soltanto i controlli e il grafo STRING già locale:

1. Per ogni coppia destinazione/sorgente e bersaglio, prendere i partner fisici
   presenti sull'asse comune; pesi proporzionali allo score STRING, senza outcome.
2. Aggiungere all'attenzione la media pesata del rango basale dei partner nelle due
   linee, la differenza firmata e RMS fra ranghi, la quota di peso con CPM > 5 in
   entrambe, il peso misurato e il numero di partner. Per supporto insufficiente
   mantenere valore mancante esplicito, non zero biologico.
3. Confrontare rete attuale, rete con questi ingressi, e stessi ingressi permutati
   fra bersagli mantenendo fasce di grado. Usare gli stessi split familiari e seed,
   senza riaprire i test esterni per scegliere le opzioni.

La feature costa una tabella piccola bersaglio × coppia di contesti e non richiede
nuove matrici di effetti. Nel pannello a basso grado può non aiutare: è una ragione
per misurare il supporto, non per assumere un vantaggio. Non implementata nel job
congelato da questa analisi; comunicata all'agente scientifico prima del training.

## Revisione del nuovo protocollo source-attention

La ritenzione delle sorgenti separate corregge un limite rappresentazionale reale
del pooling precedente. La loss direzionale è coerente con la discriminazione, ma
non basta per rivendicare un miglioramento VCC. Prima del training sono stati
segnalati tre controlli:

- negativi contrastivi distinti, stesso contesto e identico insieme di geni/mask
  per tutti i confronti; altrimenti si può apprendere la mancanza di misura;
- norma per bersaglio e confronto con effetto nullo: metà baseline più metà
  attenzione limitata non garantisce che cancellazioni fra sorgenti non riducano
  molto la norma;
- il confronto primario è con la baseline degli stessi input, ma l'eventuale
  candidatura di gara richiede anche confronto con t25 e scorer cellulare.

Queste sono condizioni di interpretazione e implementazione. Non sono nuovi
risultati né una certificazione che la rete generalizzi.
