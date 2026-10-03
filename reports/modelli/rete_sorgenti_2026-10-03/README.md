# Rete sulle sorgenti: impalcatura (3 ottobre 2026)

**Stato: impalcatura con prove sintetiche. Nessuna corsa su dati reali, nessun protocollo registrato.** Alfredo ha
chiesto in chat di preparare una rete da presentare dal 22 ottobre.

## Che cosa fa

Per una linea L mai vista perturbata, un bersaglio t e un gene g, la rete **pesa gli effetti già misurati** in altre
linee:

    ŷ[t, g] = A_L · Σ_k α_k(L, g) · E_k[t, g]

- **I pesi α** dipendono:
  - dal profilo basale di L e della sorgente k, cioè dai soli controlli, che il 22 ottobre ci saranno per D, E, F;
  - da un piccolo embedding per gene, che rappresenta i moduli;
  - dalla differenza d'espressione basale del gene fra L e k.
- **L'ampiezza A_L** è la regola norm-match del banco della strada C, per un fattore appreso dal profilo di L.
- **Al passo 0 è la media a pesi uguali:** gli strati d'uscita partono da zero. La rete può solo imparare di quali
  sorgenti fidarsi:
  - non inventa effetti che nessuna sorgente ha misurato;
  - non ha parametri per bersaglio, quindi vale anche per i bersagli nuovi del set finale;
  - ha poche migliaia di parametri, più 8 per gene.

## Perché questa e non un'altra

- **Non duplica Davide.** Dal suo aggiornamento del 3/10, la rete *cellulare* che parte dal transfer e lo corregge è
  sua. Qui non c'è nessuna componente cellulare né una miscela: il collasso di r1 (la `pi` della miscela) non può
  succedere.
- **Evita il difetto delle reti del 27–28/09:**
  - [rete_contesti](../rete_contesti_2026-09-27/) peggiorava sulla famiglia tenuta fuori appena imparava oltre il
    trasferimento;
  - [encoder_contesto](../encoder_contesto_2026-09-28/) e [modello_contesto](../modello_contesto_2026-09-27/) non
    passavano.

  Quelle imparavano effetti; questa impara solo pesi su effetti misurati.
- **È la versione appresa della strada C.** Il [banco della strada C](../../trasferimento/strada_c_banco_2026-10-03/ESITO.md)
  ha mostrato che una scelta delle sorgenti fissa a mano non vale su tutte le linee:
  - `same` vince su KOLF e perde su H1;
  - `cross` vince su HepG2 e `k562` su Jurkat.

  Se la scelta giusta dipende dalla linea, una regola appresa dai profili basali è la domanda successiva. **È
  un'ipotesi:** nessun numero reale qui la sostiene ancora.

## File

| File | Che cosa |
|---|---|
| [`dati.py`](dati.py) | Una passata sugli shard rlab con l'accumulatore del banco della strada C (`banco_tipo.Sums`, importato senza modifiche). Scrive un file per chiave: effetti, profilo basale, geni misurati, gruppo e tipo. Gira su Kaggle |
| [`rete.py`](rete.py) | Modello, episodi lascia-una-chiave-fuori con le esclusioni della strada C, addestramento, monitor ed esportazione degli effetti nel formato dei banchi |
| [`esporta_abc.py`](esporta_abc.py) | Effetti della rete per i contesti della gara (A/B/C ora, D/E/F dal 22/10) nel formato dello stadio 45: profilo basale dai controlli con la formula di `dati.py`, sorgenti = chiavi di addestramento, ripiego a 0 non osservato per un bersaglio che nessuna sorgente copre. Uscite solo nella cartella dati. Previsione del t30 in [prediction_t30](../../invii/prediction_t30_2026-10-03/prediction.json) |
| [`test_esporta.py`](test_esporta.py) | Due prove sintetiche dell'esportatore: file letti come li legge lo stadio 45, ripiego del bersaglio scoperto, nessuna sovrascrittura, profilo basale uguale a `dati.py`. Hanno trovato un difetto (asse dei geni salvato come oggetti, che lo stadio 45 rifiuta), corretto prima del commit |
| [`test_rete.py`](test_rete.py) | Tre prove sintetiche: al passo 0 la rete è la media a pesi uguali; esclusioni KOLF/HipSci; con tipi che contano, la rete impara a fidarsi delle sorgenti dello stesso tipo (coseno di validazione da 0,40 a 0,65, a 400 passi) |

## Salute durante tutta la corsa

Ogni valutazione scrive una riga in `monitor.jsonl`:
- perdita e coseno della rete **e della media a pesi uguali** sulle linee di validazione;
- entropia normalizzata dell'attenzione (1 = pesi uguali, 0 = una sola sorgente);
- sorgenti effettive e quota massima;
- ampiezza e norma del gradiente.

**Checkpoint:** quelli ai passi 0, 100, 300, 1.000 e 3.000 restano, mai sovrascritti; in più il migliore e l'ultimo.

**Arresto:** dopo `min_steps`, cinque valutazioni di fila peggiori della media a pesi uguali.

**Separazione delle linee:** le linee di validazione e di test non sono mai bersaglio né sorgente in addestramento
(`split.json`). Il test H1 2025 resta chiuso: la chiave `h1_vcc2025_train` è un training della gara 2025, non il suo
test.

## Che cosa manca prima di una corsa vera

1. **Registrare un protocollo:** linee di validazione e test, regola di lettura sul banco con lo scorer vero (sei
   membri, contro `cross` e `k562` della strada C), previsioni.
2. **Lanciare `dati.py` su Kaggle,** insieme alla corsa r2 della strada C. Serve un lancio fatto da Alfredo.
3. **Collegare l'esportazione** (`export_effects`) al banco della strada C, come braccio esterno.
