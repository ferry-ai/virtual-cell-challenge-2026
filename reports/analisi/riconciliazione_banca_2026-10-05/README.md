# Riconciliazione della banca e del rifit

Verifica del 5 ottobre 2026, Codex. Stato operativo solo in
[R-LEAD](../../../docs/piani/strategia-scientifica.md). Le misure qui sono datate;
non costituiscono un launcher né certificano la copertura completa D-053.

**Aggiornamento del freeze:** storage [r11](../../modelli/percorso_riusabile_2026-10-05/cloud_catalog_r11/manifest.json), 45 unità; coverage [r3](frozen/expected_r3.json) conserva tutte le voci r2 e aggiunge GWPS. Cache K562 e controlli già caricati; sei adapter corretti verificati. [Lancio finale](../../modelli/percorso_riusabile_2026-10-05/ESECUZIONE_r15.md). Le fotografie r10/r2 sotto sono precedenti, non stato operativo.

## Identità degli ingressi

| Livello | Riferimento univoco | Perimetro |
|---|---|---|
| Archivio persistente | [storage r10](../../modelli/percorso_riusabile_2026-10-05/cloud_catalog_r10/manifest.json) | 395,75 GB grezzi, 43 unità storage; non 43 contesti né GB consumati dal fit |
| Copertura attesa | [expected r2 congelato](frozen/expected_r2.json) | SHA256 `54e9d5107282f2aeaab8ca7d78dca5d24c6333837453c0af7234eed5fd3c128e`; stesse 43 unità, catalogo e aggiunte, senza rimuovere lacune |
| Primo rifit parziale concluso | [selezione verificata](check_r4/selection.json) | Producer/versione, codice, parametri, mount e alias dei retry; non tutto il catalogo |
| Esito dei controlli | [verification r4](check_r4/verification.json) | 80 pin verificati, zero errori di identità e differenze di byte Git; matrici remote da riverificare nel consumer |
| K562 storico riusabile | [provenienza](../../modelli/percorso_riusabile_2026-10-05/k562_reuse_r1/preparation.json), [pacchetto pronto](../../modelli/percorso_riusabile_2026-10-05/k562_reuse_r1/ready_r3.json) | 28.104.995 byte, SHA storico identico; preparato, non caricato né consumato nel primo rifit |

Le fonti storiche non sono vietate: devono essere scelte esplicitamente per provenienza,
versione, byte, asse, QC, codice e parametri. Nessun fallback al cubo pilot, a `latest`,
a un titolo simile o a un originale ERROR sostituito da retry. K562 essential è distinto
dal GWPS. Banca di statistiche, locatori di cellule e matrici campionate hanno ruoli diversi.

## Correzioni effettuate

**Misurato:** i pin locali e i mount del mix sono riconciliati; non risultano voti duplicati
H1 train/val, CD4 condizioni o originale/retry. Nessun file grezzo byte-identico duplicato
nelle ricevute dei 17 archivi storici controllati. Quest'ultimo controllo non dimostra
l'assenza di cellule o studi biologicamente sovrapposti.

Un inventario congelato puntava a un ledger operativo successivamente ampliato. È stata
[recuperata la versione storica esatta](frozen/restoration.json) dal commit Git, accettata
solo dopo uguaglianza dello SHA originale. Expected r2 riferisce la copia immutabile:
nessuna riscrittura del ledger vivo o dell'inventario r1, nessuna perdita di aggiunte.

Git normalizzava i fine riga di 18 file vincolati da hash, creando byte diversi dopo clone.
Le regole mirate in `.gitattributes` e la rinormalizzazione dell'indice preservano adesso
i byte originali. Il controllo r3 confronta i pin con i blob Git, oltre che con il disco.

Le vecchie code, PID, «training non iniziato» e divieti d'invio non guidano più il lavoro.
I testi completi sono [conservati con hash](../../../docs/storico/consolidamento_banca_2026-10-05/INDICE.md);
registro, README e schede rimandano alla sola coda corrente R-LEAD.

## Portata e lacune

Il primo rifit ha 12 fonti registrate, 8 con target sul pannello; il conteggio non prova
pesi non nulli né miglioramento. Tre fonti del vecchio modello sono presenti; K562 GWPS
non è nel mix concluso, quindi quel mix non è la vecchia banca completa più aggiunte.
Il cache originale K562, 272 target × 18.533 geni, coincide con lo SHA già verificato
nel 27 settembre: riusarlo ripristina la fonte richiesta senza attendere la nuova banca
cellulare. Non sostituisce la chiusura del producer single-cell ancora RUNNING.

HIPSCI, Tian/Norman, SCP/KO/A549, altre aggiunte, QC/componenti/controlli e dedup biologico
rimangono dipendenze esplicite. Zero target nel pannello o adapter mancante non autorizzano
esclusioni scientifiche. La vecchia nota «HEK J repair pending» del mix è una fotografia:
la [riparazione separata è conclusa](../../modelli/percorso_riusabile_2026-10-05/hek_repair_completion_r1/status.json).
Produzione con hidden vuoto non è validazione C/J; H1 test resta protetta.

Il rifiuto iniziale auto-review è conservato. L'utente ha poi autorizzato esplicitamente
entrambi: [K562 privato caricato](../../modelli/percorso_riusabile_2026-10-05/k562_reuse_r1/dataset_create_r1.json)
e [controlli privati caricati](../../modelli/percorso_riusabile_2026-10-05/generation_controls_r2/launch.json).
I primi due lanci effects-only hanno avuto errori tecnici diagnosticati: import path
del bootstrap e import anticipato di `anndata` assente nell'immagine CPU. Nessun
calcolo scientifico era ancora avvenuto. Il terzo lancio ha verificato gli hash del
checkpoint, poi la guardia SE ha rilevato una maschera diversa da quella originale:
[riproduzione indipendente](axis_adapter_repro.json). Correggere l'adattatore senza
indebolire la guardia; seguire R-LEAD per i successori.
Il pacchetto parent di riuso corregge i nomi duplicati dei voti e verifica tutti i file
del checkpoint nel runtime. Originali Grok immutati; codice compresso auto-contenuto,
nessun calcolo pesante locale. La nuova ingestion attiva non viene duplicata o fermata.

## Lettura dei report precedenti

- `DATI_DISPONIBILI_r2.md`: dimensioni e inventario datati utili; «training non iniziato»
  non è stato corrente e non prova consumo dei GB.
- `TRAINER_r1.md`: fixture neurali e reader, non il launcher lineare corrente.
- `TRANSFER_IDENTICO_r1.md`: identità del modello resta il mandato; il vecchio no-VCC
  è superato dall'autorizzazione umana in `INVIO_DIRETTO_r1.md`.
- `RIUSO_r1.md` e `training_coverage_r1/expected.json`: conservati; per i riferimenti
  immutabili usare [RIUSO r2](../../modelli/percorso_riusabile_2026-10-05/RIUSO_r2.md)
  e expected r2. Non riavviare ingestion dai dispatcher storici.

## Tempi e ripetizione

**Misurato:** il mix concluso ha impiegato circa 5 minuti di runtime; il precedente
t28 circa 33 minuti di generazione e 35 di packaging. **Stima**, non SLA: dopo K562
montabile, 10–30 minuti per effetti/rifit, 60–90 per generazione e packaging,
più trasferimenti/upload e coda del servizio. Il riuso elimina la rilettura dei grezzi.

Per ripetere solo i controlli metadata, scegliere una destinazione NUOVA:

```powershell
.\scripts\py.cmd reports/analisi/riconciliazione_banca_2026-10-05/audit.py --coverage reports/analisi/riconciliazione_banca_2026-10-05/frozen/expected_r2.json --expected-sha 54e9d5107282f2aeaab8ca7d78dca5d24c6333837453c0af7234eed5fd3c128e --out <nuova_cartella>
```

[check r1](check_r1/verification.json) e [r2](check_r2/verification.json) conservano
i problemi prima delle correzioni. Non riscaricare matrici o manifest immutati per
ripetere questi controlli; verificare gli hash delle matrici nel consumatore reale.
