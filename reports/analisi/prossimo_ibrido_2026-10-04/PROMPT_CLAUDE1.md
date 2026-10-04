# Consegna a Claude1 — chiudere t30 e verificare il banco

Progetto: `C:/Users/ferra/OneDrive/Desktop/vcc2026`.

Leggi prima `CLAUDE.md`, `git status --short`, PROGETTO §0, PIANI §2–3 e R-LEAD; poi soltanto le sezioni della tabella dei compiti pertinenti. Per lo score segui PROCEDURE §2 punto 7, per job §3 ed ERRORI. Prima di modificare file leggi la guida della loro cartella. Checkout condiviso: non modificare né committare lavoro altrui.

Il t30 ha ottenuto **0,135248601985599**. Codex prende in carico l'audit informativo del prepasso e il piano del prossimo ibrido in `reports/analisi/prossimo_ibrido_2026-10-04/`: lascia questa cartella a Codex. Il tuo compito è completare la chiusura dell'esperimento t30 e diagnosticare banco, esportazione e trasferimento alla gara; conserva la regia dei job già tuoi, senza rilanci duplicati. Il prepasso diviso eventualmente in sviluppo resta un'attività distinta: coordina il suo autore, non riscriverlo durante la diagnosi.

Esistono già `status_lDMSYUZU5cFYHcRqI0lq.json` e `comparison.json` nei percorsi dell'invio. Delta t25 = −0,00498945892923655, ramo b; perdita soprattutto nel PDS, compensata in parte da fedeltà e Jaccard. Leggi prima questi file e riusa il lavoro già fatto: non richiedere uno score nuovo né duplicare la chiusura. La diagnosi delle cause rimane aperta.

Leggi anche il passaggio delle 12:30 della sessione `2b35612c` in R-LEAD: riferisce prime misure della componente comune di R e un problema di ingestione CD4. Mantieni quelle misure esplorative, pubblicane la ricevuta riproducibile prima di usarle come causa. Codex ha verificato il lungo intervallo di log fra le due letture del prepasso: non assumere che dividere soltanto gli shard risolva la pianificazione globale; profilare prima. La regia dei job legge gli stati reali e le autorizzazioni valide della sessione, non deduce un via da questo passaggio.

## 1. Chiudi la lettura ufficiale del candidato appena inviato

- Associa entry, ricevuta, modello, hash degli effetti, generazione e pacchetto. La ricevuta è `reports/invii/trial_2026-10-04/submit_t30_raw.json`; la previsione è `reports/invii/prediction_t30_2026-10-04/prediction.json`.
- Usa lo status completo già salvato. Leggi i sei membri scalati pubblicati, verifica la loro media, registra i grezzi quando disponibili. Confronta t30 con t25 e t28 membro per membro e, se disponibili, per contesto. Non ricostruire membri ufficiali mancanti dalle ancore aggregate.
- Applica la regola originale al valore **non arrotondato**. La soglia inferiore è `0.14023806091483554 - 0.005 = 0.13523806091483554`: il solo “0,1352” non permette di scegliere con certezza il ramo, perché l'arrotondamento attraversa la soglia. Anche un esito formalmente non conclusivo non è un miglioramento.
- Completa comparison, indice invii, checkpoint e STRADE; aggiorna stato/direzione dove richiesto. Non riscrivere CP-0062: il suo esito locale resta datato, con un nuovo checkpoint che delimita ciò che non si è trasferito.

## 2. Ricostruisci che cosa il banco ha effettivamente provato

Verifica il codice e gli output, non solo il riassunto. La base del banco era `transfer_all_J`; il t30 ha aggiunto R agli effetti **t25**, con le impostazioni del generatore t25, non t28. R e gli ingressi del selettore erano definiti rispetto all'ancora del fold HepG2. Questa discrepanza è un'ipotesi di fallimento da misurare, non una spiegazione già provata.

Produci una tabella training → banco → export → generazione: fonti/maschere/assi, stimatore e unità, baseline, R, selettore, bersagli corretti/fallback, scala, cis/clipping, controlli, numerosità, seed e checkpoint. Ricontrolla la parità a w=0 lungo la catena completa, non solo sugli array degli effetti.

Esamina inoltre:

- validità delle ancore locali e amplificazione del JAC negativo di K562; MSE troncata a zero; metriche grezze, denominatori e contributi alla media;
- gruppi/target esclusi, numero di cellule reali e simulate, controlli condivisi, potenza dei test DE e integrità degli split;
- scelta/obiettivo del selettore: vantaggio fuori fold piccolo o negativo sulle righe contro vantaggio sui sei membri; distribuzione delle sue feature fuori dai fold;
- differenza di ampiezza/direzione R/T fra sviluppo e A/B/C, risposta comune e specificità del target, guardie interne e loro rappresentatività;
- riuso delle linee già viste nello sviluppo: dopo questa diagnosi non chiamare Jurkat/K562 una nuova riserva intatta;
- differenze di assay e di contesto come ipotesi separate; non attribuire automaticamente il problema a Flex né al prepasso.

## 3. Confronti diagnostici controllati

Prepara prima i confronti riutilizzando pesi e predizioni disponibili, quando possibile. Qualunque nuovo calcolo pesante segue autorizzazioni e runtime della sessione.

Sul medesimo banco, stessi dati/seed/supporti, separa: baseline della ricetta t25 adattata al fold senza leakage; stessa baseline + R appresa rispetto a un'altra ancora (caso t30); baseline e correzione coerenti fra loro; impostazioni di emissione t25 contro t28. Un incrocio con vecchi pesi è diagnostico, non equivale a riaddestrare una correzione sulla baseline coerente. Conserva i limiti, soprattutto quando una sorgente di produzione coincide con la linea esclusa.

Non cambiare scala, clipping, corpus e rete insieme per poi attribuire il risultato a una sola modifica. Non scegliere una nuova regola dopo aver letto i nuovi esiti. La soglia locale 0,100 non è una previsione di score VCC e, da sola, non giustifica un altro invio.

## 4. Consegna utile per il prossimo training

In una **nuova cartella tua**, consegna:

1. risultato esatto e sei metriche con ricevute;
2. difetti riprodotti, controlli passati e ipotesi ancora aperte, tenuti distinti;
3. quali elementi del banco sono riutilizzabili e quali vanno corretti prima di promuovere un candidato;
4. confronto che distingue ciascuna causa candidata e risultato che la smentirebbe;
5. vincoli concreti per il protocollo successivo e percorso del resoconto per il proprietario/Codex.

Aggiorna solo le tue righe negli indici e nella scheda condivisa, rileggendoli prima della patch. Commit dei soli tuoi file/righe per nome. Nessun nuovo download, acquisto, job, push o invio è autorizzato da questo prompt oltre alle autorizzazioni già valide nella tua sessione. Prosegui nel frattempo con le verifiche locali e la gestione già autorizzata dei tuoi job.
