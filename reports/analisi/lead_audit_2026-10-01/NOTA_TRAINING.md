# Consegna tecnica per il prossimo training

1 ottobre 2026. Diagnosi della lead, non istruzioni già applicate al job attivo.
Il mandato e l'assegnazione di R-LAB restano nella sua scheda. Non ho modificato i suoi file,
fermato r3 o inviato messaggi all'altra chat. Il codice esaminato è quello di
`reports/modelli/risposta_biologica_2026-09-30/`; gli hash dei tre file principali coincidono
con quelli registrati da r2. Evidenza e limiti: [REVISIONE](REVISIONE.md), script e manifest
nell'[indice](README.md).

## 1. Prima di attribuire il risultato di r3

- **Congelare la definizione del confronto.** `cell_data.py:92`, `splits`: stesso seed su una
  lista diversa cambia il campione. r5/r7 hanno solo 128 target nascosti in comune.
  R3 è un altro esperimento esplorativo. Valutarlo sul vecchio test sarebbe contaminato
  per i target tornati disponibili nel training; non basta rimettere le vecchie etichette
  dopo il training. Serve un nuovo training con esclusioni comuni per attribuire il guadagno
  ai dati aggiunti. Un confronto ristretto ai target ancora esclusi resta descrittivo,
  con supporto e cambiamenti di corpus espliciti.
- **T29 prova una combinazione precisa:** media degli effetti `desc` r2 e generatore t22.
  Applicare la regola registrata in `prediction.json`; le diagnosi qui non la modificano.
  Un esito positivo non convalida il decoder NB o la miscela come generatore di popolazioni;
  un esito negativo non chiude ogni architettura biologica. Leggere tutti i membri ufficiali.
- **Salvare esposizione effettiva e gruppi di test di r3**, oltre ai totali dei file. Non
  confrontare soltanto le medie T/C/J se i target e le sorgenti che le compongono cambiano.

## 2. Correzioni con test di accettazione

**R3 appena concluso:** leggere anche [AGGIORNAMENTO_R3](AGGIORNAMENTO_R3.md). Riprodotto il
segno errato del gradiente del gate sotto il clamp di probabilità: calcolare i pesi in
log-sigmoid dai logit, quindi verificare il recupero e le eventuali regolarizzazioni. Un altro
clamp rigido non risolve la zona senza gradiente. La causa iniziale del collasso resta da isolare.

| Priorità | Punto verificato | Correzione candidata | Verifica che deve passare |
|---|---|---|---|
| P1 | `train_cellnet.py:1185`: normalizzazione dei pesi nel batch; replay r2 dà 32,61% a K562 GW invece di 16,67% | Definire l'obiettivo gerarchico; normalizzazione globale dei pesi oppure batch bilanciati. Calcolare i pesi sulle sole chiavi attive (`cell_data.py:376`) | Replay delle esposizioni e dei coefficienti della loss; cambiando partizione/ordine degli shard lo stesso corpus conserva l'obiettivo entro il limite prefissato. Non basta il totale di cellule |
| P1 | `cell_data.py:366`: in HepG2 zero librerie con 64 controlli dopo il cap; fallback totale | Reservoir corretto per popolazione e stratificato per libreria; campionamento con reinserimento se sensato; fallback registrato per cellula | Copertura prima/dopo cap, probabilità di inclusione, stabilità rispetto all'ordine, tasso di fallback per studio/libreria; nessuna perturbata nel pool |
| P1 | `cell_data.py:92` e `train_cellnet.py:206`: split instabili e ruoli prima del QC | Manifest immutabile di target/gruppi; assegnazione stabile dei nuovi target; audit C/T/J dopo QC e deduplicazione | Aggiungere una sorgente non riclassifica i vecchi target; alias e repliche esclusi globalmente; il controesempio G2 passa |
| P1 | `train_cellnet.py:609,979,1183`: unknown non addestrato come risposta generica | Modello generico separato con la stessa capacità di leggere il contesto; modello bilineare con gli stessi input; identity solo diagnostica | La baseline generica riceve gradiente da perturbate, si allena e viene selezionata sugli stessi fold; nessuna informazione del target nel ramo generico |
| P2 | `train_cellnet.py:974–978`: baseline riceve gradiente dalle perturbate | Ablazione empirica smussata / testa imparata solo da controlli / testa congiunta | Parità di dati, split e budget; errore sui controlli tenuti fuori, effetti trans e likelihood separati; non cambiare insieme sampler e architettura per attribuire il risultato |
| P2 | Selezione dei 400 gruppi più numerosi e coseno top-200 | Banco stratificato per contesto, regime e numerosità; diagnostica trans e sei metriche | Tabella dei gruppi ammessi/esclusi; ogni contesto previsto rappresentato; nessun gene di test usato per fit/selezione del modello |

I numeri di riga sono del codice verificato durante l'audit; per revisioni successive usare
anche nomi delle funzioni ed hash, non applicare patch alla cieca.

## 3. Esperimento successivo raccomandato

1. Versionare il banco prima dei modelli: fold, livelli di aggregazione, metrica primaria,
   controlli concessi, supporto misurato, riserva e regola di selezione. Le diagnosi HepG2
   di questo audit appartengono ormai allo sviluppo.
2. Su un corpus fisso confrontare baseline generica, transfer, bilineare e rete attuale
   dopo le correzioni. Separare il fix del contratto di valutazione dalle ablation di modello.
3. Verificare l'ipotesi residua: transfer + correzione appresa con predizioni out-of-fold.
   Il selettore vede copertura, incertezza e descrittori; non gli esiti del target di test.
4. Solo sul candidato giustificato, testare l'espansione del corpus su fold invariati,
   con confronto a esposizione comparabile e confronto a piena copertura distinti.

Il prefetch può ridurre l'attesa dati (~58% in r2), ma viene dopo l'identità dell'esperimento.
Un loader più rapido non corregge i pesi; un'epoca completa non garantisce pesi bilanciati.
Nessun nuovo job è avviato da questa consegna.
