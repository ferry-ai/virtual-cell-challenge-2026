# Prossimo training: ingresso completo e pacchetto t36 congelato

6 ottobre 2026. Sostituisce [r2](RIUSO_r2.md), che selezionava storage r10 e
expected r2 anteriori alla chiusura dei due blocchi single-cell K562 GWPS.
Nessun dato perso o ricalcolato: si corregge l'ingresso operativo per il riuso.
Stato e lavoro rimanente solo in [R-LEAD](../../../docs/piani/strategia-scientifica.md).

1. **Catalogo completo atteso:** [storage r11](cloud_catalog_r11/manifest.json),
   SHA256 `d833b8808c69e1d95200ef95ccc60bb76c585ec73b18fdac2fb6d171692fee9d`,
   45 unità; [expected r3](../../analisi/riconciliazione_banca_2026-10-05/frozen/expected_r3.json),
   SHA256 `304e8a660d7f69952c62c2e6ccf3a990da48647a186e179db4584941b4b21a30`.
   Preservare anche le aggiunte successive: queste sono versioni congelate, non
   autorizzano a ignorare nuovo materiale. Non scegliere r10/r2 per il prossimo
   corpus né modificare quei documenti storici.
2. **Per ripetere t36:** [impronta del pacchetto verificato](release_t36_reuse_r1.json)
   vincola codice/parametri/bootstrap/contratto e prove del consumer concluso.
   Usare la copia del pacchetto in una nuova destinazione, cambiare solo ID/output
   del job e i parametri richiesti dall'esperimento autorizzato. Non rilanciare
   l'ID già concluso o il suo upload. Il pacchetto t36 è una release parziale,
   non il manifest del training completo.
3. **Input cloud:** metadata individua i mount; parametri e ricevute runtime
   individuano byte, asse, maschere, controlli e provenienza effettivi. Uno slug
   da solo non certifica una versione: verificare hash nel consumer e arrestarsi
   se il provider monta byte diversi. K562 storico BULK, K562 essential e nuovo
   GWPS single-cell sono tre origini diverse, mai fallback automatici.
4. **Estendere il corpus:** riusare tutte le banche/campioni compatibili, senza
   ingestion nuova degli input già chiusi. Ogni fonte ancora aperta conserva
   motivo, adapter/QC/controlli richiesti e ruolo; nessuna esclusione per dimensione,
   comodità o overlap dei target. Nuova fonte richiede solo i propri derivati e
   una nuova release globale. Cambi di QC/split/ancore rigenerano solo dipendenze.
5. **Identità scientifica:** count_sum per BIO/donatore distinto da mean_proportion;
   pooling prima dello shrink, tutti controlli leciti. H1 train/val condividono il
   pooling; CD4 condizioni condividono il voto dopo pooling dei donatori. Quattro
   KOLF non sono quattro linee. C/J e hidden/componenti esclusi prima statistiche,
   H1 test protetta. Un locatore non è una matrice campionata; il lineare non consuma
   automaticamente quei campioni.
6. **Esecuzione:** preflight di tutti e tre gli account, dedup fra ledger e alias
   dei retry; CPU/RAM/disco/accessi reali, nessuna somma di RAM fra sessioni. Mount
   cloud preferito, copie locali solo per limite dimostrato. Hash dei ledger su
   copie congelate, mai su file operativi ancora mutabili.
7. **Chiusura:** ricevute dei contributi effettivi di fonti/contesti/target e,
   quando applicabile, esposizione/resume/loss. Lineare senza optimizer/loss.
   D-053 richiede copertura attesa e uso reale, non soltanto manifest e codice.

**Misurato:** [t36 pubblicato](../../invii/prediction_t36_2026-10-06/comparison.json),
confronto descrittivo. Pacchetto verificato su runtime reale, non una fixture.
**Aperto:** ammissione/adapter/QC di tutto il catalogo e nuova release completa.
Questa guida non certifica che le fonti mancanti siano già collegate.
