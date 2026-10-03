# R-LAB — corpus e artefatti cellulari disponibili

- **Stato:** in corso, per l'**ingestione completa** chiesta dal proprietario in chat il 3/10 dopo le 15:28 CEST:
  tutti i dataset per intero, in fretta, anche su più runtime. Il corpus idoneo va su Drive; che cosa entra nel
  training lo decide R-LEAD con i ruoli registrati. Piano, sorgenti e stato:
  [ingestione completa](../../reports/sorgenti/ingestione_completa_2026-10-03/README.md).
- **Aggiornato:** 3 ottobre 2026, 15:50 CEST circa (ora letta con `date`).
- **Assegnazione (PIANI §3), sottoattività disgiunte:**
  - **Regia, job e archivio:** Claude Code, sessione «R-LEAD implementazione vcc2026» (`22d21f`), dal 3/10 15:28.
    Comprende Southard r3 (job 132), le verifiche dell'archivio riprese (133–134), Orion completo, Mixscale e
    VIPerturb con R, e i metadati di microglia, PerturbFate e DLD-1. Lavora in
    `reports/sorgenti/ingestione_completa_2026-10-03/`, fuori da `adattatori_codex/`.
  - **Adattatori per l'acquisizione completa:** Codex, tramite la relay `vcc2026-1c`, dal 3/10 15:50. Due compiti:
    `h5csc` con bucket compatti e intervalli di cellule (KOLF pan-genome); `h5rows` con filtro di idoneità CD4 ed
    esclusioni contate. Copie con fixture in `reports/sorgenti/ingestione_completa_2026-10-03/adattatori_codex/`;
    nessun job Colab o Kaggle. Non tocca:
    - `reports/sorgenti/corpus_cellulare_2026-09-30/` (codice dei job in corso);
    - `G:/Il mio Drive/vcc2026/runs/`;
    - `reports/modelli/rete_*_2026-10-03/`;
    - il resto di `ingestione_completa_2026-10-03/`.
- **Prossimo passo:** il proprietario riavvia i due dispatcher Colab (`queue`, `queue2`); Codex consegna gli
  adattatori; Claude li integra e mette in coda KOLF e CD4, mentre prepara Orion, Mixscale e VIPerturb.
  Il nome storico «piano-giorno» non indica una scadenza.
- **Supervisione:** Codex, dal 3/10 15:47 per scelta del proprietario. Monitora ogni 15 minuti, fa audit e prepara
  fixture su copie isolate, e legge questa scheda: la sua relay non riceve messaggi in modo stabile.
  **Revisione chiesta a Codex, prima del congelamento:** il protocollo in bozza e il codice v3 della
  [rete ancorata](../../reports/modelli/rete_ancorata_2026-10-03/README.md). I punti sono quattro:
  - ancore, controlli di fuga e restrizione a CRISPRi;
  - guadagno e correzione;
  - la regola, con la corsia B primaria e la guardia della corsia A a −0,02;
  - l'esito non promettente delle [miscele](../../reports/modelli/rete_cellulare_2026-10-03/esito/miscele_r3/LETTURA.md).
- **Collo di bottiglia attuale (3/10, 15:55):** un solo runtime Colab attivo, quello di `queue`, occupato dalle
  verifiche 133–134. Southard (132) aspetta `queue2`. Dopo vengono gli adattatori di KOLF e CD4.

## Ingestione completa: filoni

Per ogni dataset, completo vuol dire tre cose:
- **conteggi riconciliati:** cellule grezze = idonee + esclusioni per motivo, e idonee = righe negli shard;
- **ricevute:** sha256 di ogni shard su Drive;
- **verifica indipendente:** una rilettura da un altro runtime.

Il dettaglio di sorgenti e misure è nel [README](../../reports/sorgenti/ingestione_completa_2026-10-03/README.md).

| Filone | Chi | Dipende da | Prossimo passo | Output |
|---|---|---|---|---|
| Southard RPE1 + Hs27 (CRISPRa), 850.225 + 447.301 cellule | Claude | runtime `queue2` | avvio di `queue2` | `j09_southard_r3` su Drive, `rlab-southard-*` su Kaggle |
| Verifica dell'archivio (816 + 4.334 file) | Claude | runtime `queue` | in corso (133–134) | `archivio_verify_2026-10-03_r2/out_*_r2` |
| KOLF pan-genome, 2.659.209 cellule | Codex (adattatore) → Claude (job) | `h5csc` compatto a intervalli | consegna di Codex | shard per intervallo di cellule |
| CD4 completo, 12 file, 33,6 milioni di cellule | Codex (filtro) → Claude (job) | filtro di idoneità; quota di Drive misurata dal runtime | consegna di Codex; `df` su `/content/drive` | un job per file, esclusioni per motivo e per corsia |
| Orion completo, HCT116 3.409.169 + HEK293T 4.534.299 | Claude | `orion_job.py` corretto | modalità senza campione | shard per lotto GEM |
| Mixscale (5 RDS) e VIPerturb | Claude | R sul runtime | job di conversione | shard di contratto |
| microglia, PerturbFate, DLD-1 | Claude, o Grok per la sola ricerca web | — | elenco di file, dimensioni e formati | decisione registrata |
- **Dipendenze:** [R-LEAD](strategia-scientifica.md), [sorgenti](../../reports/sorgenti/README.md)
  e [modelli](../../reports/modelli/README.md). Dati pesanti esterni a Git.

## Che cosa esiste

| Materiale | Evidenza e limite |
|---|---|
| Corpus, adattatori, QC, inventari e job | [Indice del corpus](../../reports/sorgenti/corpus_cellulare_2026-09-30/README.md). Le versioni descrivono acquisizioni successive: disponibilità e checksum si verificano sulla macchina destinataria |
| Modello, prepass, split, descrittori ed export originali | [risposta_biologica](../../reports/modelli/risposta_biologica_2026-09-30/). Codice usato nei training; preservarlo e correggere una copia nuova |
| R1, primo training | [ESITO](../../reports/modelli/cellnet_tecnico_2026-10-01/ESITO.md): verifica tecnica non interamente passata |
| R2, corpus esteso | [ESITO](../../reports/modelli/cellnet_esteso_2026-10-01/ESITO.md): verifica tecnica con misure; braccio `desc` usato in t29, non promosso |
| R3, seconda ondata | [ESITO](../../reports/modelli/cellnet_completo_2026-10-01/ESITO.md): training completato, collasso `ident`; [diagnosi](../../reports/analisi/lead_audit_2026-10-01/AGGIORNAMENTO_R3.md) |
| Quarto training, terza ondata + floor | [Protocollo](../../reports/modelli/cellnet_terza_ondata_2026-10-01/PROTOCOLLO.md): nessun esito registrato; verifica tecnica che non comprende il banco richiesto dopo t29 |
| Archivio e copie remote (2–3/10) | [Archivio cloud](../../reports/sorgenti/archivio_cloud_2026-10-02/README.md): inventario per file, specchio su Drive in corso, Kaggle verificato; [riconciliazione e ingestione](../../reports/sorgenti/archivio_cloud_2026-10-02/INGESTIONE.md): Jiang 2025 e Mixscale sono un'unica sorgente, Southard incompleto, campioni CD4/Orion e ruoli registrati prima dell'integrazione |

H1 train/val e HIPSCI sono già stati usati nel corpus; non riaprire acquisizioni sulla base
di vecchie liste d'attesa. H1 test resta riserva chiusa e non è un contesto nuovo per un
modello che vede H1 train/val. Presenza nel catalogo e uso nel fit sono cose diverse:
il replay dopo QC di P1 determina che cosa ogni modello ha visto davvero.

## Chiusura e alternative

Questa scheda si aggiorna quando cambia l'inventario o termina un'esecuzione di R-LEAD.
Una consegna si chiude con manifest, hash, esito e dipendenze mancanti espliciti. Dal 3/10 il mandato del
proprietario è acquisire per intero tutte le sorgenti di INGESTIONE §5, e supera la regola precedente («non deve
acquisire ogni sorgente possibile»). L'uso nel training resta legato a una lacuna P0/P1 o a un confronto
preregistrato. Un altro training tecnico non soddisfa il ramo c di t29.

[Cronologia integrale e incarichi precedenti](../storico/rinnovo_2026-10-01/docs/piani/piano-giorno-2026-09-30.md).
