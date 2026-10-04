# Pulizia delle copie locali archiviate — 4 ottobre 2026

Codex, sessione `01a10414-c24f-7130-86ff-82615c92e968`, portatile Windows.
Autorizzazione in chat: eliminare i dati locali superflui quando il lavoro usa Drive o Kaggle.
La verifica non conferma un progetto esclusivamente remoto: le valutazioni recenti
contengono ancora percorsi locali. Si eliminano soltanto copie archiviate delle lavorazioni
precedenti; le dipendenze attive e i file privi di prova remota rimangono.

## Esito misurato

**Conclusa il 4 ottobre alle 02:05 CEST:** rimossi **942 percorsi**, pari a
**135.914.821.686 byte fisici (126,581 GiB, circa 136 GB)**. Ogni rimozione è preceduta
da un nuovo SHA256 locale coincidente con la verifica Colab. Ricevute del
[lotto principale](removal.json), [giornale principale](removal.json.jsonl),
[lotto CSV](tables_removal.json) e [giornale CSV](tables_removal.json.jsonl).

Il [controllo finale](postcheck.json) conferma che tutti i 942 percorsi sono assenti
in locale e presenti su Drive con le dimensioni attese. Nessun file dell'inventario
conservato è assente o cambiato di dimensione. Lo spazio libero su C passa da
22,635 a **144,899 GiB**, incremento netto 122,264 GiB; la differenza rispetto ai byte
rimossi non è attribuita, dato il lavoro concorrente sul portatile. Nei sei alberi dati
esaminati restano circa **85,452 GiB fisici**, oltre agli ambienti e alle cartelle
infrastrutturali escluse dal perimetro.

## Prova e perimetro

**Misurato:** il piano contiene 940 percorsi, 134.013.638.796 byte fisici recuperabili
(124,810 GiB), tenendo conto degli hard link. La prova senza cancellazione è passata:
[dry_run.json](dry_run.json). Il piano immutabile con hash, destinazione remota e ricevuta
per ogni file è [plan.json](plan.json).

Due grandi matrici CSV DepMap (1,771 GiB) erano state conservate dal filtro iniziale
dei metadati. Un controllo esplicito non trova riferimenti in `configs/`, `src/`,
`scripts/`, nel report v4 o nell'ingestione corrente. Hanno una ricevuta Colab e
metadati locali invariati: [piano supplementare](tables_plan.json), preparato da
[plan_tables.py](plan_tables.py). I due piani restano distinti.

Le ricevute indipendenti Colab del 3 ottobre sono [giro r1](colab_a_r1.jsonl) e
[giro r2](colab_a_r2.jsonl). Il [riepilogo r2](colab_summary_r2.json) registra 4.334 file
con SHA256 verificato, includendo 2.363 ricevute precedenti. La presenza e la dimensione
attuali sul mount Drive sono ricontrollate; l'integrità remota si fonda sui byte letti da
Colab, non sul mount locale. Tre campioni non si aprono con `allow_pickle=False`:
[dettaglio](sample_failures.json). Sono esclusi per prudenza; non è una prova di corruzione.

Il controllo dei processi iniziale non trovava lettori Python del progetto. Subito prima
della rimozione è comparso `watch_kernels.py` della sessione R-LEAD: il suo codice è stato
letto e interroga soltanto `kaggle kernels status`, senza leggere i dataset locali.
Non sono stati fermati processi o modificati job remoti.

L'inventario completo prima della pulizia e l'ispezione originale dei campioni
sono conservati fuori dal repository, con percorsi, byte e SHA256 nel
[manifest delle prove locali](local_evidence_manifest.json). Le ricevute e i piani
in questa cartella mantengono i byte originali tramite `.gitattributes`.

## Esecuzione e ripristino

- [plan_cleanup.py](plan_cleanup.py) confronta ricevute, inventario precedente, metadati
  locali attuali, dipendenze attive e presenza remota; non cancella dati.
- [remove_copies.ps1](remove_copies.ps1) verifica l'impronta del piano e delle ricevute,
  valida tutti i percorsi nella sola radice dati, rifiuta reparse point e doppioni.
  Con `-Apply` ricalcola ogni SHA256 sotto un lock che nega scritture, poi rimuove il singolo
  file con `Remove-Item -LiteralPath`. Non usa cancellazioni ricorsive né wildcard.
  [remove_tables.ps1](remove_tables.ps1) è la stessa copia con il solo nome del piano
  sostituito per le due matrici CSV; [prova senza cancellazione](tables_dry_run.json).
- La lettura locale completa serve esclusivamente a verificare le copie da eliminare:
  non è un calcolo scientifico da spostare su Colab. Memoria limitata, nessun training.
- Copie cloud, metadati, codice, ambienti Python, campioni piccoli e lavoro corrente restano.
  Nessuna linea o contesto viene escluso dal corpus D-053; cambia soltanto la disponibilità
  di una copia locale di dati già archiviati.

Ogni file rimosso si recupera da `MyDrive/vcc2026/data/<rel>`, con il percorso relativo e
lo SHA256 del piano. Per un ripristino richiesto usare
`reports/sorgenti/archivio_cloud_2026-10-02/riporta.py --prefix <rel> --manifest C:/Users/ferra/vcc2026-data/processed/archivio_cloud_2026-10-02/r1/manifests/a_specchio_r1.json`
tramite `scripts/py.cmd`: rilegge e verifica l'hash prima di finalizzare, senza sovrascrivere.

## Dati conservati e limite

Le esclusioni del piano distinguono dipendenze attive, ricerche correnti, metadati/fixture,
assenza di prova remota e campioni con errore di apertura. In particolare resta
`external/cd4_gw/GWCD4i.pseudobulk_merged.h5ad`, circa 41,51 GiB, senza copia indipendentemente
verificata. Il mandato di pulizia non giustifica perdere l'unica copia completa.
Gli universi degli effetti, le cache t22/t25, i controlli e il cubo del banco rimangono
disponibili per le dipendenze dichiarate dal lavoro attivo e dalla produzione.

## Controlli del repository

- `31_check_docs.py`: PASS prima della pulizia; PASS anche dopo il commit concorrente
  `af48c2f` (59 checkpoint e 8 strade).
- Suite completa: 287 test in 593,805 secondi, 286 passati; unico fallimento
  `test_this_repository_is_consistent`, perché `docs/STRADE.md` era comparso prima della
  sua riga nel registro durante il lavoro dell'altra sessione. Nessun file altrui corretto
  o rimosso da questa sessione. Dopo il completamento di quel commit, rieseguito l'intero
  `test_doc_workflow.py`: **25/25 PASS**, incluso il controllo fallito.
- Prova negativa del pulitore: un'impronta del piano di 64 zeri produce
  `Plan hash mismatch`, uscita 1, senza creare la ricevuta `must_not_exist.json`.
- Il controllo finale dei dati è [check_result.py](check_result.py): verifica assenza locale,
  corrispondenza dei giornali ai piani, presenza e dimensione di ogni copia remota,
  permanenza dei file conservati e spazio libero effettivo. La prova d'integrità resta
  il confronto SHA256 completo, già eseguito prima di ogni rimozione.
