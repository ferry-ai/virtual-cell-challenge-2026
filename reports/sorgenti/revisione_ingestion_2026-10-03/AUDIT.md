# Revisione indipendente del codice di ingestion — 3 ottobre 2026

**Misurato su fixture locali; nessun download o job cloud.** Revisione della consegna parziale
Claude2 del run `20261003-141124-vcc-ingestion-resume`, fotografata prima dei test in una
directory temporanea. Il worktree del worker non è stato modificato. Il suo `result.md`
dichiara correttamente codice scritto, test non eseguiti e pipeline incompleta.

Le copie corrette sono in [corretto/](corretto/); i percorsi `REPO` e `CORPUS` sono adattati
alla nuova profondità e continuano a importare il contratto originale, senza modificarlo.
Queste correzioni non promuovono la pipeline a pronta per il cloud.

## Quattro problemi corretti

| Priorità | Difetto nella consegna originale | Evidenza e correzione |
|---|---|---|
| P1 | `coverage_audit.py:audit` sceglie la chiave separatamente per ogni riga: lo stesso simbolo con e senza `target_id` diventa ENSG in una sorgente e `SYM:` nell'altra. Copertura e fold possono divergere. | Fixture MYC: `ENSG00000136997` è nella fold 2, `SYM:MYC` nella fold 1; togliendo la fold 2, l'originale mantiene MYC come training in un gruppo. La copia riconcilia le identità disponibili nell'intero input prima dello split e rifiuta ID espliciti confliggenti. |
| P1 | `orion_job.py:phase_sample` controlla il checksum del parquet ma ignora il JSON della fase metadati. `phase_meta` scrive parquet e sidecar prima di terminare con parità fallita. | La fixture con `ok=false` e `parity.rows=false` produce comunque un campione nell'originale. La copia richiede ricevuta, stessa linea, hash della tabella e tutte le verifiche di parità vere; rifiuta prima di creare l'output. La fase shard richiede inoltre ricevuta e disegno coerenti con il campione. |
| P1 | Il riuso Orion richiede solo `sample_sha256`; lo stesso campione può essere convertito con un asse ordinato diversamente o con un'altra specifica. Uno shard precedente verrebbe comunque accettato. | L'ispezione identifica il solo requisito nella costruzione di `ShardSink`. La copia aggiunge un'impronta di asse, campione, specifica, manifest delle sorgenti e moduli di conversione. Test: cambiando ordine dell'asse o specifica cambia l'impronta; una ricevuta con impronta differente non viene riusata. Nessun job remoto usato come prova. |
| P2 | `ShardSink.have` aggiunge il riferimento allo shard riusato soltanto in memoria; non pubblica una ricevuta nella nuova esecuzione. Un secondo riavvio che indica solo l'ultima esecuzione perde quel riuso. | Fixture originale: primo riavvio `True`, secondo `False`. La copia conserva la ricevuta e segue il percorso dello shard referenziato dopo nuova verifica di dimensione e sha256. Test con scrittura AnnData reale: entrambi i riavvii riescono. |

Il riuso conserva riferimenti: gli shard di una vecchia esecuzione ancora referenziata **devono
rimanere disponibili**. Non è una copia indipendente né un'autorizzazione a cancellarli.

La riconciliazione dell'audit è calcolata sul corpus fornito. Prima di usarla per addestramento,
Claude1 deve congelare una tabella canonica delle identità insieme allo split: aggiungere in
futuro un ID prima mancante può cambiare una precedente chiave `SYM:`. L'audit non modifica
manifest o fold del pilot.

## Test ed evidenza

[original_repro.txt](original_repro.txt) registra le tre riproduzioni sull'originale:

```text
ORIGINAL_HIDDEN_FOLD_2_SUPPORT {'SYM:MYC': np.int64(1)}
ORIGINAL_FOLDS {'ENSG00000136997': 2, 'SYM:MYC': 1}
ORIGINAL_FAILED_META_CREATED_SAMPLE True
ORIGINAL_RESTART1 True
ORIGINAL_RESTART2 False
```

Il primo caso usa due studi, K562 e HepG2, ciascuno con 5 controlli e 20 cellule MYC;
solo il primo studio dichiara l'ID Ensembl. Il secondo usa un parquet di una cellula con
sidecar corretto e ricevuta di parità falsa. Il terzo usa tre directory nuove e una ricevuta
di uno shard di 7 byte per isolare esclusivamente il meccanismo di riferimento.

La suite della copia comprende i 16 test del worker e 9 nuovi test. Il comando dalla root:

```powershell
.\scripts\py.cmd -m unittest discover -s reports/sorgenti/revisione_ingestion_2026-10-03/corretto -p 'test_*.py' -v
```

**25/25 PASS**, log finale [test_corretto_r3.txt](test_corretto_r3.txt). La fixture di MYC
asserisce esplicitamente che le due chiavi avrebbero fold diverse. La fixture reale scrive
due cellule, rilegge l'AnnData tramite il writer/validator di R-LAB, verifica la somma 7 e
due riavvii consecutivi. `sum_before` e `sum_after` esistono davvero nello schema della
ricevuta: **nessun crash di schema rilevato**. Il log r2 registra la precedente suite passata,
prima di rendere più discriminante il caso di fold diverse.

Il test dei campioni controlla, per entrambi i disegni, disgiunzione delle tranche,
uguaglianza della loro unione al campione più ampio e additività delle probabilità dichiarate.
Non dimostra bontà statistica per ogni sorgente né sufficienza dei tetti proposti.

## Limiti ancora aperti per Claude1

- **Acquisizione integrale assente:** CD4 ha soltanto il controllo della tabella incrociata;
  non c'è un adapter completo CD4, né Mixscale. `k=40` Orion resta una proposta. La capacità
  Drive dichiarata dal proprietario è 5 TB: non giustifica da sola un tetto definitivo; acquisizione
  completa e bilanciamento del training vanno trattati separatamente.
- **Memoria non limitata sul corpus:** `coverage_audit.collect` legge e concatena tutte le
  `obs`; `phase_meta` concatena tutti i file della linea. `read_selected` accumula i conteggi
  selezionati di un intero file GEM. Servono partizioni, aggregazione incrementale e misura
  del picco RAM prima dei dati completi. Nessun OOM remoto è stato misurato qui.
- **QC solo approssimato:** l'audit obs-only non implementa il prepass completo, le maschere
  dei geni e la protezione dei fenotipi. Deduplica qualsiasi `cell_key` ripetuta, mentre il
  prepass distingue collisioni e versioni usando la provenienza e i conteggi. Le esclusioni
  dell'audit non sono decisioni definitive di ammissione al training.
- **Identità di linea e parentele:** la mappa resta proposta; le relazioni sono applicate
  nella direzione dichiarata e per un solo livello. Ad esempio `Neuron -> iPSC` non implica
  automaticamente l'inverso. Congelare le famiglie volute, le esclusioni e gli alias prima
  dell'adozione, senza contare stati/donatori come linee indipendenti.
- **Downloader non completamente verificato:** mancano fixture HTTP per Range ignorato,
  risposte corte, ETag/dimensione cambiati e checksum finale errato. Nel percorso redirect
  `keepalive` chiama ancora `r.read()` senza limite sul corpo del redirect. Su POSIX
  `os.rename` può sostituire una destinazione apparsa tra l'ultimo `exists()` e il rename;
  il caso è limitato dall'uso previsto di uno stage privato nuovo, ma la promessa assoluta
  di non sovrascrittura richiede una primitive di pubblicazione esclusiva.
- **Nessuna orchestrazione multi-Colab pronta:** launcher, snapshot/preflight di runtime,
  partizioni senza duplicazioni, benchmark e ri-verifica corrente delle sorgenti restano da
  completare. Le otto connessioni del downloader sono codice, non uno speedup misurato.

Questa revisione autorizza solo a distinguere difetti corretti e lavoro rimanente. Nessuna
ricevuta cloud, completezza dell'acquisizione, qualità di generalizzazione o risultato del
training è stata dimostrata dai test locali.
