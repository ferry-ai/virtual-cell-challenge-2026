# R-DATI — sorgenti, controlli e affidabilità

- **Stato:** aperto; supporto ai confronti di R-LEAD e all'esecuzione R-LAB.
- **Aggiornato:** orientamento riallineato il 1° ottobre; le proposte sotto risalgono al 25/09.
- **Prossimo passo vigente:** partire dall'inventario e dal corpus già prodotti in
  [R-LAB](piano-giorno-2026-09-30.md); individuare controlli, repliche o collegamenti mancanti
  per il banco di [R-LEAD](strategia-scientifica.md). L'aggiunta di dati richiede un confronto
  con split fissi; il t29 non dimostra che la sola quantità di cellule sia il limite.
- **Nota storica del 28/09 (D-046):** la scheda
  non è stata aggiornata dopo il 25; il lavoro sui dati è proseguito nella scheda
  [R-V2](modello-v2.md) (universi genome-wide, KOLF2.1J, HIPSCI, VIPerturb-seq, Tahoe): gli esiti
  sono indicizzati in [reports/sorgenti/README.md](../../reports/sorgenti/README.md).
- **Assegnazione:** sottoattività 1–3, audit su fonti pubbliche: Claude (app, sessione
  `f4f38e58`), con agenti dell'hub, 25/09 00:20–00:45. Nessun download eseguito.
- **Obiettivo:** rendere fattibili prove indipendenti su bersagli e contesti nuovi.
- **Ipotesi:** H7 rumore, H8 saggio, H9 tempo/sopravvivenza; input per H1–H6/H10.

## Prossima azione

Proposta originaria del 25/09, da verificare contro l'inventario R-LAB prima di ripeterla:

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

[GENERALIZZAZIONE](../../../../GENERALIZZAZIONE.md) è normativa: zero overlap col pannello
non esclude una sorgente. Le sovrapposizioni sono invece necessarie quando si
vuole attribuire un effetto a un cambio di saggio o modalità. Prima di download
verificare disponibilità, dimensioni, licenza e risorse secondo [PROCEDURE](../PROCEDURE.md).
Non duplicare acquisizioni già in corso; una scheda degli agenti non sostituisce
manifest, checksum e ispezione dei file. Non scrivere nella cache di produzione.

## Criterio di chiusura

Inventario riproducibile e limitazioni documentate, con decisione motivata per
ciascuna sottoattività: utilizzabile per una prova specifica, da completare o non
valutabile con quei file. Eventuali adozioni/rifiuti richiedono checkpoint.
Non richiedere che tutte le sorgenti risultino utili per chiudere l'audit.

## Evidenze e prossimi passaggi

- [Ipotesi e dati prioritari](../../../../../reports/analisi/ipotesi_trasferimento_2026-09-24/IPOTESI.md), §§3/6/7.
- [Schede candidate](../../../../../reports/sorgenti/schede_sorgenti_2026-09-24/SCHEDE.md): leggere anche le correzioni iniziali.
- [Mixscale e DLD-1](../../../../../reports/sorgenti/dld1_audit_2026-09-24/RISULTATI.md);
  [affidabilità DLD-1](../../../../../reports/sorgenti/dld1_ceiling_2026-09-24/RISULTATI.md).
- Sblocca [R-MODELLI](trasferimento-modelli.md) e [R-SWITCH](switch-distribuzioni.md).
- [Ricerca del 26 settembre](../../../../../reports/sorgenti/ricerca_sorgenti_2026-09-26/RISULTATI.md): HIPSCI CRISPRi (34 linee iPSC, 7.226 bersagli; Figshare MIT verificato nei metadati), da acquisire col via del proprietario. Universi genome-wide di CD4 e Orion autorizzati e in corso il 26/09 ([R-V2](modello-v2.md)).

## Avanzamento del 25 settembre

Evidenza: [ricerca del 25 settembre](../../../../../reports/sorgenti/ricerca_sorgenti_2026-09-25/RISULTATI.md),
con i rapporti integrali degli agenti.
- **1, Mixscale:** i `log2FC` per linea usano le sole cellule della linea (dedotto dal codice
  del pacchetto, citazioni da rileggere sul testo grezzo); `beta` e `p` vengono da una
  regressione congiunta e non sono indipendenti fra linee. Metadati degli oggetti Seurat e
  presenza di cellule non stimolate ancora ignoti.
- **2, microglia:** file e dimensioni noti; la distinzione soglia/gradualità dell'articolo è
  circolare. Prossimo: aprire un h5mu per vedere se ha le etichette delle guide.
- **3, Flex:** VIPerturb-seq è CRISPRi genome-wide in K562 letto con Flex v2 (CC-BY-4.0,
  3,6 GB di `.rds` filtrato). Prossimo: leggere `genome_wide_manifest.txt` e le feature.
- **Nuove sorgenti:** catalogo completo nel report, anche dei dataset lontani dai contesti
  della gara, da conservare per generalizzare e studiare pattern (richiesta del proprietario).
  I più grandi: KOLF2.1J (CRISPRi, 11.739 geni) e GSE345058 (1.000 knockout in A549).

**Passaggio di consegne:** nessuna acquisizione né adozione. Ogni download chiede il via del
proprietario; il disco C: ha pochi GB liberi.

## Integrazione Codex del 25 settembre

Sottoattività documentale completata da Codex, task
`01a0d81b-3495-74d0-9537-eb5254b05002`, iniziata alle 21:32 UTC;
assegnazioni degli audit precedenti invariate. Evidenza:
[CP-0040](../../../../checkpoints/0040-biologia-contesti-donatori.md) e
[report](../../../../../reports/analisi/biologia_architetture_2026-09-25/RISULTATI.md), §5.
Proposta aggiuntiva: contrasti CD4 per donatore e guida, confronti entro/fra
donatori a uguale numerosità e calibrazione della confidenza su donatori esclusi.
Le metà CD4 sono gruppi di donatori, non repliche tecniche; lo z entro gruppo
non misura tutta l'incertezza di trasferimento. Nessuna acquisizione aggiuntiva.
La nota sul disco sopra è datata: verificare spazio attuale prima di un download.

## Audit trasversale Codex del 26 settembre

Sottoattività disgiunta completata alle 12:28 UTC da Codex, task
`01a0dda7-acf9-71a2-bb1a-6a35fb6f3164`: inventario e revisione in sola lettura
di dati/codice, con nuovo output in
[audit_piani_dati_2026-09-26](../../../../../reports/analisi/audit_piani_dati_2026-09-26/RISULTATI.md).
Nessuna riassegnazione del lavoro Claude. Da portare nei prossimi passi:
HIPSCI distinto da KOLF e già censito l'11 settembre; matrici Jurkat locali;
universi CD4/Orion ancora incompleti; controllo dei filtri basati sull'effetto.
Il §4 documenta contaminazione tramite medie calcolate prima degli split nel
banco appreso r2/r3, con controesempio riproducibile. Il §5 corregge la modalità
Mixscale (CRISPRi). Nessun nuovo dataset adottato o job avviato.
