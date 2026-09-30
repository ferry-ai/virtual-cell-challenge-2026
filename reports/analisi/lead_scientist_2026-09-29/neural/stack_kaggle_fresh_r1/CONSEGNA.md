# Stack, avvio completo su Kaggle

**Pronto per review, non avviato da questo builder.** Il runtime Colab è stato
perso; questo notebook riparte da zero e non presuppone cache, Python o pesi
precedentemente installati. Destinazione privata: `davidmaisterx/vcc-stack-pilot-r1`,
dataset `davidmaisterx/vcc-stack-prompts-r1`. Il data agent gestisce copia e review;
solo il root autorizza upload/push.

Unico input dati: `bundle.tar.gz` pubblico selezionato da 31.984.510 byte,
SHA256 `8c693c8457590edca74e626b08d7318a276c44f4b9737f5d4d4c13272814cf3e`.
Contiene prompt K562, soli controlli HepG2 e transfer congelato. Nessun controllo
riservato A/B/C, perturbato HepG2, token o dato di account. Il codice scientifico,
i dodici target, i pesi e la lista geni restano quelli del pilot.

Ambiente nuovo: uv 0.8.22 in cartella isolata, CPython gestito 3.11.13, requisiti
originali, più `pooch==1.8.2` senza reinstallazioni transitive. Il percorso
imposta `anndata.settings.allow_write_nullable_strings=True` prima dell'inferenza.
Queste sono le due correzioni di errori realmente osservati su Colab; non cambiano
conteggi, parametri o casualità del modello. Import Stack/scvi e due roundtrip
H5AD nullable/CSR precedono il download dei pesi. CUDA richiesta, batch 1.

Guardie: 16 GiB disco all'inizio, almeno 6 GiB RAM disponibili prima dei pesi e
immediatamente prima del loader; spazio pesi più riserva di 2 GiB e checksum
completi. Richiesta GPU T4. Output in `/kaggle/working/lead_stack_r1`, ambiente e
pesi temporanei sotto `/tmp/lead_stack_scratch_r1`. Nessuno scoring nel notebook.

La precedente esecuzione Colab ha caricato 217.806.513 parametri sulla T4 e
completato i dodici target, ma non ha salvato le predizioni finali per l'errore
nullable-string. Questo non è un risultato di qualità del modello. I tempi e
l'esito del nuovo runtime Kaggle restano da osservare.
