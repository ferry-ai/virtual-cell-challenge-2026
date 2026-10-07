# Archivio → banca pronta → training

**Dal 7 ottobre l'ingresso unico è [banca_canonica_2026-10-07](../banca_canonica_2026-10-07/README.md):** registro canonico, release r1 e fit con ricevuta di consumo. Questa pagina e RIUSO r3 restano la prova della release t36 e dei producer della banca; le righe su HIPSCI «ancora aperto» qui sotto sono superate da quella cartella.

**Ingresso unico per riuso:** [procedura del prossimo training](RIUSO_r3.md).
**Stato e assegnazioni correnti:** [R-LEAD](../../../docs/piani/strategia-scientifica.md).
**Rifit, invio e valutazione della release parziale conclusi:** [candidato completo e invio t36](ESECUZIONE_r19.md) e
[invio diretto autorizzato](INVIO_DIRETTO_r1.md).

[Identità riconciliate e lacune](../../analisi/riconciliazione_banca_2026-10-05/README.md).
[HIPSCI: conteggi persistenti riusabili senza nuova ingestion](HIPSCI_RIUSO_COUNT_SUM_r1.md); adapter e ammissione ancora aperti.
[Adapter count_sum preparato e verificato su quattro fixture](hipsci_adapter_r1/README.md); consumer reale e pesi fra contesti ancora aperti.
[Adapter con pooling congiunto fra cloni](hipsci_adapter_r2/README.md): due fixture aggiuntive passate; conservati anche i cloni con soli controlli, nessuna media post-shrink. Consumer e QC reali ancora aperti.
[Consumer HIPSCI CPU concluso e consumo reale verificato](hipsci_adapter_r3/completion_r1/README.md): cinque effetti dal pooling dei 19 cloni, senza nuova ingestion; candidatura congelata, QC/ammissione e consumo nel mixer ancora aperti.
[QC HIPSCI e correzione p2/pseudo](hipsci_qc_r1/README.md): i manifest storici hanno pseudo0,5 e due pool tecnici; diagnostica sul nuovo pooling preparata, senza riusare cache non equivalenti.
[Righe HIPSCI reali verificate](hipsci_adapter_r1/real_rows_r1/README.md): 19 cloni con controlli e una cellula senza metadata; chimica ignota da trattare esplicitamente prima del fit.
K562 storico disponibile con SHA verificato: [riuso preparato](k562_reuse_r1/ready_r3.json), caricato privato; sei cache corrette pronte per il fit finale.

## Quali dati usare

| Livello | Riferimento | Che cosa certifica |
|---|---|---|
| Archivio grezzi, banche, campioni | [manifest storage r11](cloud_catalog_r11/manifest.json) | Account, versioni, file, hash e provenienza; non ammissione al fit |
| Dimensioni e contesti disponibili | [dati r2, fotografia datata](DATI_DISPONIBILI_r2.md) | 395,75 GB grezzi; non stato corrente né uso nel fit |
| Copertura da riconciliare | [expected r3 congelato](../../analisi/riconciliazione_banca_2026-10-05/frozen/expected_r3.json) | Tutte le unità attese e fonti storiche; lacune da motivare |
| Release t36 eseguita | [impronta congelata](release_t36_reuse_r1.json) | Codice, parametri, input e prove del consumer finale; release parziale |
| Input finali t36 | [parametri](generation_successors_r1/package/params.json) | Sei cache corrette, K562 storico e checkpoint del primo mix; non tutto il catalogo |
| Risultato t36 | [confronto ufficiale](../../invii/prediction_t36_2026-10-06/comparison.json), [stato](ESECUZIONE_r19.md) | 13 nomi registrati, 9 con target sul pannello; fonti, non 9 linee. Invio concluso, consumo completo del catalogo ancora aperto |

Non scegliere dataset per titolo, data o nome più recente. Il manifest individua
la versione e i byte. `rlead-bench-cube-r2` resta input del pilot, mai fallback.
I dati storici utilizzabili restano nel catalogo: non si scartano per età.

## Riuso senza nuova ingestione

Montare direttamente gli output salvati dei producer; non è obbligatorio il
passaggio cloud → locale → cloud. Riutilizzare la banca a parità di input,
asse, QC, codice e parametri. Un nuovo dataset aggiunge il proprio adattatore,
banca/campioni e una nuova release globale; modifica dei soli derivati dipendenti
se cambiano normalizzazione, ancore o split. [Procedura precisa](RIUSO_r3.md).

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

GWPS banca/campioni chiusi; il loro collegamento al transfer, gli altri adapter/QC
e la copertura del catalogo restano aperti. Generazione e risultato della release
t36 parziale sono conclusi; manca il consumo effettivo del catalogo completo.
Manifest o script esistenti, da soli, non sono prova end-to-end.

## Evidenze precedenti

[Indice precedente conservato integralmente](README_storia_r1.md) contiene la
cronologia; non usarne stati, PID o comandi come istruzioni correnti.
[Reader e trainer neurale su fixture](TRAINER_r1.md) documenta un'altra integrazione:
non è il launcher del transfer lineare corrente.
[Prove del pooling corretto](GROK_REVIEW_r6.md), [H1 joint e primo mix](ESECUZIONE_r10.md),
[chiusure e accessi KOLF](ESECUZIONE_r9.md).
