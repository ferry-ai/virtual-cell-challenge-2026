# t28 — upload completato, score in attesa

**Misurato:** il 29 settembre 2026 alle **22:46:06 UTC** (30 settembre, 00:46 CEST) il CLI ufficiale termina con codice 0: 4.161.126.400 byte caricati, MD5 verificato e job di valutazione avviato. Entry **ZvrYZ4UazadAyuq4AsDB**. La ricevuta originale è [submit_t28_raw.json](submit_t28_raw.json); coincide byte per byte con quella del processo in `t28_direct_attempt_r2/`.

Lo [status immediatamente successivo](status_ZvrYZ4UazadAyuq4AsDB_submitted_2246.json) dice `launching`; non contiene ancora uno score. L'upload non dimostra competitività. Valgono la [registrazione](../prediction_t28_2026-09-29/prediction.json) e la [decisione con i limiti](DECISIONE_INVIO_T28.md), senza cambiamenti di soglia.

Il file locale è `C:/Users/ferra/vcc2026-data/artifacts/t28_local_upload_r1/prediction.vcc`, SHA256 `0d70ba92d68817b46383b11c53d513a41c85329230b9ff5524ac51f7bd110b32`. Il recupero conserva gli otto metadata originali e supera nuovamente la convalida prima dell'invio. Il primo tentativo di lettura da Drive è fallito prima di creare un'entry; la copia a blocchi si è fermata sulla guardia spazio e poi è ripresa dal byte 3.019.898.880. Evidenze del recupero in [learning/upload_copy_recovery_r1](../../analisi/lead_scientist_2026-09-29/learning/upload_copy_recovery_r1/).

Su autorizzazione esplicita del proprietario, è stato eliminato **solo** `artifacts/t26gen/prediction.h5ad`, intermedio da 4.254.875.597 byte. Il contenitore t26 è conservato e il suo SHA completo coincide con il packaging originale. Dati, ricette, report, t27 e t28 sono conservati. Ricevute: [prima della rimozione](legacy_t26_cleanup_authorized.json), [esito](legacy_t26_cleanup_result.json).

Il proprietario ha chiesto di completare il seguito autonomamente e con pochi token. È attivo il controllo nella stessa chat **esito-ufficiale-t28**, ogni 15 minuti, silenzioso a stato invariato. Alla pubblicazione applicherà `read_t28_score.py`, scriverà il confronto e aggiornerà checkpoint e documentazione; poi si metterà in pausa. Nessun nuovo esperimento o invio è previsto. L'inibizione temporanea della sospensione si rilascia scrivendo `t28_keep_awake_stop.json`; il processo ha comunque una scadenza massima registrata in `t28_keep_awake_started.json`.

Il [piano per il prossimo modello](../../../docs/piani/modello-competitivo.md) è collegato in testa al README e agli indici del progetto.
