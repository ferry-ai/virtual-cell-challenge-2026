# Confronto RPE1 contro K562 sul banco HepG2 — note scritte prima dei risultati

- **Scritto:** 2026-09-18, intorno alle 12:50 ora di Roma, da un agente.
- **Stato dei dati in quel momento:** nessun `bench.json` esiste per questo confronto.
  I job 018 e 019 (messi in coda il 17 alle 23:57) sono partiti alle 22:09 UTC e non hanno
  scritto alcun output; l'ultimo battito del dispatcher in `runs/jobs/dispatcher.log` è
  delle 22:09:37 UTC del 17. Rimessi in coda come **020** (`s_k562_gwps_r2`) e **021**
  (`s_rpe1_r2`) alle 12:48 del 18, stesso pannello, stesso seme, stessi bracci.
- **Revisione del proprietario:** no.

Questa nota **non cambia** la regola pre-registrata `configs/source_lineage_rule.yaml`
(versione 1): metrica primaria, bracci primari, soglia 0,03 e cancello di validità restano
come scritti lì, e il verdetto primario resta quello che lo stadio 87 calcola. Cambiano
solo i percorsi di ingresso: `s_k562_gwps_r2/bench.json` e `s_rpe1_r2/bench.json` al posto
dei nomi senza `_r2`, che non esistono.

Aggiunge due letture **secondarie**, dichiarate qui prima dei numeri perché non si possa
sceglierle dopo averli visti.

## 1. Volume delle chiamate contro qualità delle direzioni

**Misurato** ([CP-0021](../../docs/checkpoints/0021-ancore-ufficiali-e-troppe-chiamate.md) §3,
`reports/bench_2026-09-17/hepg2_h002_bench.json`): su questo banco la fedeltà grezza cresce
con il numero di geni dichiarati significativi — 0,1187 a 8,5 chiamate per bersaglio,
0,2878 a 126,6, 0,4855 a 523,7.

**Misurato** (conteggio da `obs/num_cells_filtered` dei due file bulk, righe NaN contate
come zero come fa `effects_from_bulk`): cellule NTC 75.328 in K562 contro 11.485 in RPE1;
mediana di cellule per riga-bersaglio 168 contro 70.

**Interpretazione.** In `effects_from_bulk` l'errore standard scende con il numero di
cellule e la contrazione empirical Bayes è tanto più forte quanto più l'errore è grande.
A parità di ampiezza, quindi, gli effetti RPE1 vengono contratti di più; d'altra parte le
risposte grezze di RPE1 potrebbero essere più ampie. Il segno netto sul numero di chiamate
**non è noto**. Ne segue che una differenza di fedeltà **alla stessa ampiezza** può venire
da quante chiamate fa ciascuna sorgente e non da quante direzioni azzecca.

**Lettura secondaria dichiarata.** Per ciascuna sorgente i tre bracci primari danno tre
punti (`sig/t`, fedeltà grezza). Si interpola la fedeltà di ciascuna sorgente in modo
lineare a tratti in `log(sig/t)`, **solo dentro l'intervallo di `sig/t` comune alle due**,
e si confrontano le due curve a parità di chiamate.

- Se il verdetto primario è una vittoria ma a parità di chiamate lo scarto scende sotto
  0,03 o cambia segno, si scrive che **il vantaggio si attenua correggendo
  approssimativamente per il volume**. Non si scrive che è «dovuto al volume»: vedi §4.
- Se gli intervalli di `sig/t` non si sovrappongono, le due cose **non sono separabili** con
  questo banco, e va detto.

Il banco non registra `k` e `n_pred` per bersaglio, quindi la precisione diretta non è
disponibile. Aggiungerli a `Bench.score` è una proposta, non fatta.

## 2. Lo stato di TP53 è un secondo candidato, oltre al lignaggio

**Dalla letteratura, non misurato in questo progetto:** hTERT RPE-1 e HepG2 hanno TP53
selvatico; K562 ha TP53 inattivo. Nelle cellule con TP53 funzionante, il knockdown di un
gene essenziale attiva spesso un programma p53 comune (per esempio `CDKN1A`, `MDM2`), che
K562 non può mostrare.

**Interpretazione.** RPE1 differisce da K562 per il lignaggio, ma anche per TP53, cariotipo,
crescita aderente e profondità dello screen. Una vittoria di RPE1 sul banco HepG2 è
compatibile con «stesso stato di TP53» quanto con «lignaggio più vicino», e questo banco non
separa le due spiegazioni. Una vittoria di RPE1 **non basta** a confermare la strategia «una
sorgente per lignaggio»: confermerebbe che una sorgente diversa da K562 trasferisce meglio
su HepG2.

**Misura che le distinguerebbe (proposta, non fatta):** ripetere il confronto escludendo dal
punteggio i bersagli del programma p53, oppure misurare nei due bulk e nella verità HepG2
quale frazione di knockdown fa salire `CDKN1A`. Se il vantaggio di RPE1 sparisse senza quei
geni, sarebbe un **indizio** a favore di TP53, non una dimostrazione causale: vedi §4.

## 3. Cosa resta come nella regola

Il confondente di profondità (favorisce K562), quello dello spazio dei geni (favorisce di
poco RPE1) e il limite di fondo (HepG2 non è A, B o C) restano come scritti in
`configs/source_lineage_rule.yaml`, ed entrano nel resoconto accanto al verdetto.

## 4. Revisione del proprietario, 18 settembre intorno alle 13:00, ancora prima dei risultati

Il proprietario ha letto questa nota quando i job 020 e 021 erano appena partiti (dispatcher
riavviato alle 10:56 UTC) e non esisteva alcun output. Tre correzioni, recepite qui.

1. **Una vittoria di RPE1 su HepG2 non dimostra che «una sorgente per lignaggio» funzioni.**
   Fra le due sorgenti cambiano insieme profondità, spazio dei geni e altre caratteristiche
   biologiche. Inoltre i 300 bersagli di questo confronto sono quelli del banco HepG2, **non
   quelli della gara**: la buona copertura misurata qui non dice nulla della copertura che
   serve per una sottomissione, che va misurata a parte.

   **Misurato, subito dopo, ancora prima dei risultati.** Dei 300 bersagli di
   `vcc2026-val-1` (`raw/controls/pert_counts.csv`), RPE1 ne ha perturbati **0**, K562
   genome-wide **272**, K562 essential **0**. Lo aveva già misurato lo stadio 11
   (`scripts/11_check_target_coverage.py` → `<VCC2026_DATA_ROOT>/interim/target_coverage.json`,
   11 settembre); il conteggio è stato rifatto il 18 sui file correnti con la stessa lettura
   dei simboli dello stadio 75 (`gene_transcript.split("_")[1]`) e dà gli stessi numeri.
   **Interpretazione:** qualunque sia il verdetto, RPE1 non può fornire la firma specifica di
   nessun bersaglio ufficiale. Una sua vittoria sarebbe utilizzabile solo attraverso ciò
   che non dipende dall'identità del bersaglio (una risposta comune) o attraverso una
   correzione appresa e applicata alle firme K562. Per questo la domanda «specifico o
   comune» del passo successivo decide.
2. **Il confronto a parità di chiamate non dimostra la causa.** Interpolare tre punti sul
   numero **medio** di chiamate non tiene uguale la **distribuzione** delle chiamate fra i
   bersagli. La prima stesura diceva che in quel caso la vittoria andava «riportata come
   dovuta al volume, non alle direzioni»: la frase era troppo categorica ed è stata
   sostituita in §1. Per distinguere meglio servono `k`, `n_pred` e `n_conf` **per
   bersaglio**, che il banco oggi non registra. Per la stessa ragione la prima stesura di §2
   diceva che, se il vantaggio sparisse senza i geni p53, «la spiegazione è TP53, non il
   lignaggio»: anche quello sarebbe un indizio, non una dimostrazione, ed è stato corretto.
3. **La soglia 0,03 è una regola pratica, non una misura dell'incertezza.** Resta, per
   leggere questo esperimento senza spostare il criterio dopo i risultati. Ma le tre ampiezze
   leggono gli stessi dati e non sono tre repliche indipendenti: una vittoria secondo la
   regola **merita un approfondimento, non un'adozione automatica**.

Passo successivo concordato, **dopo** questo confronto:
- se RPE1 vince, verificare se il vantaggio sta nelle risposte specifiche dei bersagli o in
  una risposta comune a tutti;
- se non vince, non dichiarare morto il trasferimento fra contesti.
