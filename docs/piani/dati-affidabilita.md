# R-DATI — sorgenti, controlli e affidabilità

- **Stato:** aperto; priorità iniziale della ricerca.
- **Aggiornato:** 24 settembre 2026.
- **Assegnazione:** da verificare con gli agenti già attivi; nessuna presa in carico registrata qui.
- **Obiettivo:** rendere fattibili prove indipendenti su bersagli e contesti nuovi.
- **Ipotesi:** H7 rumore, H8 saggio, H9 tempo/sopravvivenza; input per H1–H6/H10.

## Prossima azione

Verificare gli output già prodotti dagli altri agenti, poi costruire un inventario
dei **controlli, repliche, guide e unità delle risposte** nelle sorgenti candidate.
Primo risultato atteso: quali dati permettono una prova indipendente e quale file
manca per ciascuna prova, con costo e destinazione di acquisizione proposti.

| Ordine | Sottoattività | Risultato verificabile |
|---|---|---|
| 1 | Mixscale: tracciare calcolo dei log2FC, selezione genica e dipendenze fra linee; individuare controlli negli oggetti Seurat | Schema e provenienza; dire quali passaggi ricalcolare entro i fold |
| 2 | Microglia GSE335887: audit file e metadati | Fattibilità di R-SWITCH: cellule, guide, controlli, repliche, costo e licenza dei dati |
| 3 | K562 CRISPRi Flex: audit del ponte tecnico | Asse delle sonde, perturbazioni confrontabili, limiti studio/saggio e costo |
| 4 | K562/CD4/Orion/DLD-1: universi completi | Copertura di bersagli e risposte separata; unità, maschere, repliche e qualità senza filtrare ai 300 |
| 5 | Confronti KO/i, tempi, contesti lontani e misure aggiuntive | Quale ambiguità risolvono; compatibilità con gli input disponibili al test |

## Dipendenze e vincoli

[GENERALIZZAZIONE](../GENERALIZZAZIONE.md) è normativa: zero overlap col pannello
non esclude una sorgente. Le sovrapposizioni sono invece necessarie quando si
vuole attribuire un effetto a un cambio di saggio o modalità. Prima di download
verificare disponibilità, dimensioni, licenza e risorse secondo [LAVORO](../LAVORO.md).
Non duplicare acquisizioni già in corso; una scheda degli agenti non sostituisce
manifest, checksum e ispezione dei file. Non scrivere nella cache di produzione.

## Criterio di chiusura

Inventario riproducibile e limitazioni documentate, con decisione motivata per
ciascuna sottoattività: utilizzabile per una prova specifica, da completare o non
valutabile con quei file. Eventuali adozioni/rifiuti richiedono checkpoint.
Non richiedere che tutte le sorgenti risultino utili per chiudere l'audit.

## Evidenze e prossimi passaggi

- [Ipotesi e dati prioritari](../../reports/ipotesi_trasferimento_2026-09-24/IPOTESI.md), §§3/6/7.
- [Schede candidate](../../reports/schede_sorgenti_2026-09-24/SCHEDE.md): leggere anche le correzioni iniziali.
- [Mixscale e DLD-1](../../reports/dld1_audit_2026-09-24/RISULTATI.md);
  [affidabilità DLD-1](../../reports/dld1_ceiling_2026-09-24/RISULTATI.md).
- Sblocca [R-MODELLI](trasferimento-modelli.md) e [R-SWITCH](switch-distribuzioni.md).

**Passaggio di consegne:** nessuna nuova acquisizione o adozione eseguita con questa scheda.
