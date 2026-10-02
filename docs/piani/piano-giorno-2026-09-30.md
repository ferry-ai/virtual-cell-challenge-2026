# R-LAB — corpus e artefatti cellulari disponibili

- **Stato:** in attesa delle verifiche P0–P4 di R-LEAD per scegliere un nuovo training.
- **Aggiornato:** 2 ottobre 2026, dipendenze allineate al nuovo R-LEAD (D-052).
- **Assegnazione:** esecuzione precedente Claude; proprietario conferma Claude e teammate
  fermi. La ripresa si registra in [R-LEAD](strategia-scientifica.md), con file e output.
- **Prossimo passo:** inventario di input, pesi e esposizioni effettive P0/P1;
  protocollo P2 e confronto semplice P3; riuso neurale condizionato P4.
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
Una consegna si chiude con manifest, hash, esito e dipendenze mancanti espliciti; non deve
acquisire ogni sorgente possibile. Nuovi dati entrano per una lacuna P0/P1 o un confronto P4.
Un altro training tecnico non soddisfa il ramo c di t29.

[Cronologia integrale e incarichi precedenti](../storico/rinnovo_2026-10-01/docs/piani/piano-giorno-2026-09-30.md).
