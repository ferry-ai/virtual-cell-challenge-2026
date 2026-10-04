# Come rendere eseguibile il pre-passo del corpus ampliato: decisione del 4/10

Claude Code, sessione `2b35612c`, R-LEAD, binario dati D-053. Il proprietario ha delegato la scelta («Scegli
autonomamente come rendere eseguibile il pre-passo ampliato … conserva tutti i contesti e impedisci che risposte escluse
influenzino campioni o tetti»). Questa pagina fissa la scelta con le misure che la motivano. Non è un protocollo di
modello: i training che useranno il corpus ampliato avranno il proprio.

## 1. Il problema, misurato

- **Pre-passo del pilot:** 10.049 s per 365 shard e 5.603.629 cellule con 4 processi
  (`prepass.log` di `rcell-prepass-h1-r1`, letto il 4/10). Lo stato pesa 493.480.029 byte.
- **Sorgenti verificate fuori dal pilot** (ricevute di verifica, `*/esito_verifica_*/` di
  [ingestione_completa](../ingestione_completa_2026-10-03/README.md)):

  | Sorgente | Cellule idonee | Perturbate | Controlli | Entro 32 | Entro 64 | Entro 128 |
  |---|---:|---:|---:|---:|---:|---:|
  | CD4T D1 Rest | 1.750.820 | 1.674.277 | 76.543 | 348.975 | 644.649 | 1.076.830 |
  | CD4T D1 Stim8hr | 1.605.685 | 1.536.053 | 69.632 | 355.186 | 655.995 | 1.076.768 |
  | CD4T D1 Stim48hr | 1.646.772 | 1.573.238 | 73.534 | 355.268 | 656.652 | 1.085.656 |
  | KOLF2.1J pan-genome | 2.659.209 | 2.512.462 | 146.747 | 365.813 | 716.099 | 1.376.068 |
  | HCT116 (Orion) | 3.409.169 | 3.243.392 | 165.777 | 570.993 | 1.095.303 | 1.928.136 |
  | HEK293T (Orion) | 4.534.299 | 4.315.461 | 218.838 | 577.066 | 1.125.365 | 2.077.773 |
  | **Totale** | **15.605.954** | 14.854.883 | 751.071 | 2.573.301 | 4.894.063 | 8.621.231 |

  «Entro c» conta le cellule perturbate che restano con al più c cellule per combinazione contesto × bersaglio
  (inventario delle verifiche, dai soli metadati). Le CD4 D2–D4 sono in ingestione e si aggiungono quando verificate.
- **Memoria:** sugli shard Orion (fino a 200 milioni di valori) un processo che codifica i gemelli arriva a 10,9 GB
  (E-20261004-001, revisione 2). Il pre-passo legge gli stessi shard e il suo picco non è misurato: finché non lo è,
  due processi per gli shard sopra 100 milioni di valori.
- **Stima, non misura:** con tutte le cellule (pilot più 15,6 milioni), a parità di velocità, il pre-passo durerebbe
  circa 38.000 s con 4 processi e il doppio con 2, oltre le 12 ore di un kernel Kaggle.

## 2. La scelta

**Campioni annidati scelti dai soli metadati, materializzati in shard campionati con manifest, prima del pre-passo; poi
il pre-passo invariato su quegli shard.**

1. **Selezione** per (studio, contesto, bersaglio), su tutte le sorgenti, pilot compreso. Gli strati sono (libreria,
   guida); dentro ogni strato le cellule seguono l'ordine dello sha256(seme|chiave della cellula), e gli strati si
   alternano a turno. È l'ordine di `nested_samples.py` della v4, applicato alle obs prima del pre-passo. Livelli
   annidati 32, 64 e 128; il corpus ampliato di training usa **64**, il livello «ampliato» della
   [strategia](../ingestione_completa_2026-10-03/STRATEGIA_DATI_TRAINING.md), fissato prima di ogni misura del suo
   effetto. Una combinazione con meno cellule le tiene tutte. **Tutti i controlli** restano: sono il 5 % delle cellule e
   il pre-passo ne estrae comunque il proprio serbatoio.
2. **Nessuna risposta letta:** la selezione usa studio, contesto, bersaglio, libreria, guida, tipo di controllo e chiave
   della cellula, mai i conteggi. Non dipende dal fold né dalla linea esclusa, quindi nessuna risposta esclusa può
   influenzare campioni o tetti. Il tetto non si sceglie guardando i dati. Il QC resta quello del pre-passo, applicato
   dopo sulle cellule selezionate: qualche combinazione può scendere sotto 64 dopo il QC, e la ricevuta lo conta.
3. **Materializzazione:** un kernel CPU per sorgente (o per parte, entro i 20 GB di disco di un kernel) legge le obs,
   applica la selezione e scrive shard di contratto con le sole righe selezionate. Obs, var e uns restano quelli della
   sorgente. Accanto c'è un manifest: shard d'origine, righe, conteggi per combinazione, sha256 degli shard nuovi. Per
   gli shard sopra 100 milioni di valori si usano due processi.
4. **Pre-passo per fold** con il codice di `rcell-code-r1` (sha256 di `train_cellnet.py` `3b54e749…`, lo stesso dei
   pilot) sugli shard campionati, con gli stessi argomenti. Stima: circa 9–10 milioni di cellule a livello 64, quindi
   4–5 ore con 4 processi, sotto le 12 ore di un kernel.
5. **Gemelli compatti** degli shard campionati per i training (`build_fast.py`), poi ancore per fold e training con il
   protocollo del modello che li userà.

## 3. Perché non le alternative

- **Pre-passo completo a blocchi di righe:** risolve la memoria, non il tempo; resta oltre le 12 ore.
- **Pre-passo per sorgente con unione degli stati:** scalabile, ma richiede di dividere il pre-passo in una parte
  indipendente dal fold e una dipendente (classi, somme, gruppi di valutazione) e di riscrivere codice già validato. È
  una strada aperta se il livello 128 o il corpus completo diventano necessari.
- **Selezione dentro il pre-passo:** cambierebbe un codice congelato e mischierebbe due passi che conviene verificare
  separatamente.

## 4. Che cosa resta da fare, nell'ordine

1. `build_sampled_shards.py` con test (selezione dalle obs, scrittura degli shard, manifest, rifiuti) e launcher Kaggle
   CPU.
2. Kernel per sorgente; verifica dei manifest contro gli inventari (le cellule «entro 64» delle verifiche).
3. Pre-passo per fold con picco di memoria registrato, gemelli, ancore.
4. Inventario riconciliato aggiornato: ogni contesto del catalogo con il ruolo e la lacuna.
