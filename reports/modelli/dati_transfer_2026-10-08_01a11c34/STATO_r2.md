# Stato DATI-TRANSFER — aggiornamento r2

Evidenza dell'8 ottobre 2026, successiva a T1. La fotografia quantitativa è
[campaign_snapshot_r1.json](campaign_snapshot_r1.json), ore 17:12:54 UTC:
14 unità con ricevute verificate, 17 lanci accettati. La campagna continua;
questi numeri non sono uno stato in tempo reale.

## Release e consumo

- **T1 consegnata:** 16 fonti, effetti A/B/C identici, 300 bersagli. Manifest,
  hash e limiti in [CONSEGNA_T1_r1.md](CONSEGNA_T1_r1.md) e
  [candidate_t1_r1.json](candidate_t1_r1.json). Nessun beneficio comparativo
  attribuito; t36 resta riserva.
- **Produzione e T/J:** pacchetti congelati `alltargets/01a11c34-r3/` e
  `alltargets/01a11c34-tj1/`, 41 unità ciascuno. La regola hash di VALIDAZIONE
  esclude anche bersagli fuori pannello e ogni componente, prima delle statistiche.
- **Correzione di visibilità:** Xu2023 e Tian iPSC hanno revisioni private nuove
  in `alltargets/01a11c34-r4private/`. I tentativi pubblici rifiutati restano
  conservati. Il servizio richiede verifica telefonica per pubblicare sul terzo
  account; le elaborazioni private sono accettate.
- **Pilot per consumer esterno:**
  [training_view_production_pilot_r1.json](training_view_production_pilot_r1.json),
  8.819 righe target-contesto, quattro contesti CRISPRi, 18.533 geni e 73 chunk.
  È un contratto sui metadati, con mount da risolvere per hash e array da verificare
  al consumo. Non è un training, un fold valutato o un corpus completo.
- **T2:** preparazione del pooling prima dello shrinkage in `joint_rows.py` e
  `joint_runtime.py`. CD4 conserva donatori e condizioni, HIPSCI i cloni; H1
  deduplica soltanto controlli identici, K562 somma i blocchi dello stesso
  esperimento. Nessun rilascio T2 completo ancora disponibile.

Il consumer legge pseudobulk già acquisiti, non singole cellule. La ricevuta
separa cellule di banca, contributi delle perturbazioni e righe realmente usate.
La quantità di dati elaborata non dimostra miglioramento del modello.

## Runtime, blocchi e coordinamento

`dispatch/r2/` contiene preflight e ondate della campagna autorizzata. Il worker
mantiene almeno uno slot non allocato da DATI-TRANSFER per account, conserva
gli errori e non cambia account per aggirare restrizioni. Il preflight considera
anche job attivi già osservati che escono dalla finestra degli ultimi venti.
Colab non è attestato attivo: l'ultima ricevuta del dispatcher disponibile era
del 3 ottobre. Nessun calcolo pesante è spostato sul portatile.

Un errore del verificatore multia­ccount è stato isolato: il modulo SDK Kaggle
riusava la configurazione importata dal primo account. Le query di identità sono
ora in processi separati (`remote_identity.py`); la ricevuta HIPSCI già scaricata
è stata verificata senza ripetere il calcolo né il download.

L'utente ha autorizzato la condivisione privata del solo pacchetto Xu2023
`davideferante/dt-xu2023-private-01a11c34-r1` con lettori `davideferrante11` e
`davidmaisterx`. Stato e verifiche si aggiungono in `private_share_xu_r1/`;
la preparazione o l'autorizzazione non equivalgono alla condivisione riuscita.
I permessi delle sorgenti restano invariati.

MODELLI-ESTERNI ha ricevuto il contratto dei chunk e implementato un consumer
con array mmap e blocchi di geni; nessun fit esterno attestato da questa cartella.
VALIDAZIONE può integrare questo stato nei soli documenti condivisi di sua
competenza. Nessun file degli altri incarichi è stato modificato.

## Controlli e limiti

11 test scientifici locali passati: esclusioni invarianti con controllo positivo,
parità del calcolo a chunk, maschere, identità biologica, donor pooling e
deduplicazione H1. La suite generale eseguita prima aveva tre errori di ambiente
`cell_eval2.config` e due errori di indice durante la creazione concorrente delle
cartelle. Non si dichiara una suite globale verde.

Copertura D-053 incompleta: quattro unità canoniche richiedono mapping o un
riferimento di controllo diverso; rimangono inoltre riconciliazione del catalogo
oltre la banca, consumo effettivo del trainer e supervisione cellulare. Le medie
di contesto già derivate non sostituiscono il pooling di sorgente per T2.
