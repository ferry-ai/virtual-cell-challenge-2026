# Archivio → banca pronta → training

**Ingresso unico per riuso:** [procedura del prossimo training](RIUSO_r2.md).
**Stato e assegnazioni correnti:** [R-LEAD](../../../docs/piani/strategia-scientifica.md).
**Rifit/invio in corso:** [cache K562, guardia maschere e freeze](ESECUZIONE_r15.md) e
[invio diretto autorizzato](INVIO_DIRETTO_r1.md).

[Identità riconciliate e lacune](../../analisi/riconciliazione_banca_2026-10-05/README.md).
K562 storico disponibile con SHA verificato: [riuso preparato](k562_reuse_r1/ready_r3.json), caricato privato; sei cache corrette pronte per il fit finale.

## Quali dati usare

| Livello | Riferimento | Che cosa certifica |
|---|---|---|
| Archivio grezzi, banche, campioni | [manifest storage r11](cloud_catalog_r11/manifest.json) | Account, versioni, file, hash e provenienza; non ammissione al fit |
| Dimensioni e contesti disponibili | [dati r2, fotografia datata](DATI_DISPONIBILI_r2.md) | 395,75 GB grezzi; non stato corrente né uso nel fit |
| Copertura da riconciliare | [expected r3 congelato](../../analisi/riconciliazione_banca_2026-10-05/frozen/expected_r3.json) | Tutte le unità attese e fonti storiche; lacune da motivare |
| Release del rifit corrente | [params congelati](extended_mix_launch_r2/vcc-effects-mix-t25-bank-r1-retry1/params.json) | Input specifici del primo mix esteso parziale; non tutto il catalogo |
| Esecuzione del rifit | [ricevuta di lancio](extended_mix_launch_r2/vcc-effects-mix-t25-bank-r1-retry1.json) | Codice e parametri, account, alias del retry; non risultato scientifico |
| Rifit e disponibilità sul pannello | [ricevute del mix concluso](extended_mix_completion_r1/model/fit_receipt.json), [inventario](extended_mix_completion_r1/model/panel_inventory.json) | 12 fonti registrate; 8 con target sul pannello. Hash delle matrici nel consumer e copertura completa ancora aperti |

Non scegliere dataset per titolo, data o nome più recente. Il manifest individua
la versione e i byte. `rlead-bench-cube-r2` resta input del pilot, mai fallback.
I dati storici utilizzabili restano nel catalogo: non si scartano per età.

## Riuso senza nuova ingestione

Montare direttamente gli output salvati dei producer; non è obbligatorio il
passaggio cloud → locale → cloud. Riutilizzare la banca a parità di input,
asse, QC, codice e parametri. Un nuovo dataset aggiunge il proprio adattatore,
banca/campioni e una nuova release globale; modifica dei soli derivati dipendenti
se cambiano normalizzazione, ancore o split. [Procedura precisa](RIUSO_r2.md).

Non rilanciare i dispatcher delle campagne chiuse. Prima di rilanciare un
fallimento, seguire il ledger e l'alias `supersedes_failed`; niente doppie voci.
Le privacy modificate dopo r10 sono overlay con prove separate, non nuovi dati:
[Norman/iPSC](cloud_catalog_r9/README.md), [CD4/K562](public_cd4_fragments_r1/consumer_verified.json),
[KOLF pan](public_kolf_pan_r1/consumer_verified.json).

## Portata del percorso

La banca è in gran parte persistente e verificata. Il modello richiesto resta
[transfer t28, sola banca cambiata](TRANSFER_IDENTICO_r1.md). Il lineare consuma
pseudobulk; le matrici cellulari campionate persistenti servono ad altri trainer,
non entrano automaticamente in questo rifit. Un archivio di 395,75 GB non prova
che un singolo fit li abbia usati tutti.

GWPS, adapter/QC e copertura del catalogo restano aperti. Il percorso completo
non è certificato finché mancano consumo effettivo, generazione e risultati.
Manifest o script esistenti, da soli, non sono prova end-to-end.

## Evidenze precedenti

[Indice precedente conservato integralmente](README_storia_r1.md) contiene la
cronologia; non usarne stati, PID o comandi come istruzioni correnti.
[Reader e trainer neurale su fixture](TRAINER_r1.md) documenta un'altra integrazione:
non è il launcher del transfer lineare corrente.
[Prove del pooling corretto](GROK_REVIEW_r6.md), [H1 joint e primo mix](ESECUZIONE_r10.md),
[chiusure e accessi KOLF](ESECUZIONE_r9.md).
