# Lettori riusabili e sesto campionamento

Heartbeat del 5 ottobre, stato remoto in `progress_r2.json` (00:02 UTC).
Otto job CPU in avanzamento reale: due banche stimolate e sei materializzazioni.
Le banche stanno elaborando D3: 37/125 shard per Stim8hr e 67/131 per Stim48hr.
Sono ancora sei le unità con output finale persistente verificato.

**D3 Rest avviato:** `launch_samples_r2.py` distingue il notebook che restituiva
404: GetKernel conferma una bozza senza versione salvata (versione 0).
Non si afferma che non esista una sessione interattiva; è stato richiesto un
normale quinto job sull'account e Kaggle lo ha accettato applicando le sue quote.
La ricevuta è in `sample_launches.jsonl`; il log prova i primi tre shard prodotti.
Preflight completo in `samples_preflight_r2.json` e relativo `_raw.json`.

**Implementati, non ancora collegati a un fit esteso:**

- `sample_reader.py`: lettura CSR per shard, livelli annidati, metadati biologici,
  maschere e probabilità di inclusione. Rifiuta artefatti modificati. Esclude le
  linee del fold prima di aprire matrici; non emette target nascosti. La
  decompressione fisica di uno shard può includere righe escluse: il conteggio è
  separato dalle cellule emesse e da quelle usate nella loss. `acknowledge`
  registra i pesi solo dopo il consumo effettivo; la semplice iterazione non
  dimostra apprendimento. Tre fixture passate.
- `population_reader.py`: medie dell'intera popolazione e controlli abbinati
  esattamente per studio/contesto/donatore/condizione/modalità/chimica; media dei
  controlli campionati mantenuta distinta. Nessun pooling, pseudocount o asse
  inventato. Segnala la massa della verità fuori dal supporto dei controlli:
  il problema dello stimatore resta esplicito, non viene nascosto per far partire
  la KL. Una fixture passata. `require_sample_link` lega banca e campioni tramite
  ricevuta, maschera, righe e split identici.

Prossimo passaggio: dopo il completamento dei campioni, verificarne i manifest e
montare una coppia banca/campioni sul consumatore per provare questi lettori su
dati reali. Integrare poi normalizzazione/ancore e loss nel trainer con le
ricevute di `training_contract.py`. Non dichiarare il percorso completo dalla
presenza di questi lettori. Restano aperti il catalogo completo oltre CD4/pilot,
l'asse nominale dei geni e la valutazione t28 dei checkpoint preliminari.

Per nuovi campionamenti usare `launch_samples_r2.py`; per lo stato delle banche
`pipeline_state_r2.py`. Non rilanciare i sei consumatori accettati.
