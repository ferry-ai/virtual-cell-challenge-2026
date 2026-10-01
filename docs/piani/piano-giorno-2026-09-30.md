# R-LAB — corpus e artefatti cellulari disponibili

- **Stato:** in attesa delle verifiche P0–P4 di R-LEAD per scegliere un nuovo training.
- **Aggiornato:** rinnovo del 1 ottobre 2026, dopo r1–r3 e t29.
- **Assegnazione:** esecuzione precedente Claude; proprietario conferma Claude e teammate
  fermi. La ripresa si registra in [R-LEAD](strategia-scientifica.md), con file e output.
- **Prossimo passo:** inventario di input, pesi e esposizioni effettive P0/P1;
  correzioni e nuovo protocollo P3/P4. Il nome storico «piano-giorno» non indica una scadenza.
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

H1 train/val e HIPSCI sono già stati usati nel corpus; non riaprire acquisizioni sulla base
di vecchie liste d'attesa. H1 test resta riserva chiusa e non è un contesto nuovo per un
modello che vede H1 train/val. Presenza nel catalogo e uso nel fit sono cose diverse:
il replay dopo QC di P1 determina che cosa ogni modello ha visto davvero.

## Chiusura e alternative

Questa scheda si aggiorna quando cambia l'inventario o termina un'esecuzione di R-LEAD.
Una consegna si chiude con manifest, hash, esito e dipendenze mancanti espliciti; non deve
acquisire ogni sorgente possibile. Nuovi dati entrano per una domanda misurabile di P5.
Un altro training tecnico non soddisfa il ramo c di t29.

[Cronologia integrale e incarichi precedenti](../storico/rinnovo_2026-10-01/docs/piani/piano-giorno-2026-09-30.md).
