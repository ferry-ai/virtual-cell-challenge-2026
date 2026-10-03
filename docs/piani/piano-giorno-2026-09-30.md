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
