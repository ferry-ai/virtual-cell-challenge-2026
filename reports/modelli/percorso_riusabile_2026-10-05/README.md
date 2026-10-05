# Archivio → banca pronta → training

**Ingresso unico per riuso:** [procedura del prossimo training](RIUSO_r1.md).
**Stato e assegnazioni correnti:** [R-LEAD](../../../docs/piani/strategia-scientifica.md).
**Rifit/invio in corso:** [retry del mix](ESECUZIONE_r11.md) e
[invio diretto autorizzato](INVIO_DIRETTO_r1.md).

## Quali dati usare

| Livello | Riferimento | Che cosa certifica |
|---|---|---|
| Archivio grezzi, banche, campioni | [manifest storage r10](cloud_catalog_r10/manifest.json) | Account, versioni, file, hash e provenienza; non ammissione al fit |
| Dimensioni e contesti disponibili | [dati r2](DATI_DISPONIBILI_r2.md) | 395,75 GB grezzi; storage e contesti distinti |
| Copertura da riconciliare | [expected congelato](training_coverage_r1/expected.json) | Tutte le unità attese e fonti storiche; lacune da motivare |
| Release del rifit corrente | [params congelati](extended_mix_launch_r2/vcc-effects-mix-t25-bank-r1-retry1/params.json) | Input specifici del primo mix esteso parziale; non tutto il catalogo |
| Esecuzione del rifit | [ricevuta di lancio](extended_mix_launch_r2/vcc-effects-mix-t25-bank-r1-retry1.json) | Codice e parametri, account, alias del retry; non risultato scientifico |
| Uso effettivo | `fit_receipt.json`, `source_manifest.json`, `checkpoint.json` del consumer concluso | Fonti realmente votanti, contributi, file e hash; ancora da recuperare per il rifit corrente |

Non scegliere dataset per titolo, data o nome più recente. Il manifest individua
la versione e i byte. `rlead-bench-cube-r2` resta input del pilot, mai fallback.
I dati storici utilizzabili restano nel catalogo: non si scartano per età.

## Riuso senza nuova ingestione

Montare direttamente gli output salvati dei producer; non è obbligatorio il
passaggio cloud → locale → cloud. Riutilizzare la banca a parità di input,
asse, QC, codice e parametri. Un nuovo dataset aggiunge il proprio adattatore,
banca/campioni e una nuova release globale; modifica dei soli derivati dipendenti
se cambiano normalizzazione, ancore o split. [Procedura precisa](RIUSO_r1.md).

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
