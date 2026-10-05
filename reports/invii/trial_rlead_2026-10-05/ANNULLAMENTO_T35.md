# Annullamento del caricamento del t35 (5/10)

- **12:27 UTC:** il proprietario sceglie il voto ufficiale («Voto ufficiale VCC ora»). Parte il caricamento, con lo
  sha256 del `.vcc` verificato (`f298a764…` = `archive_sha256` di `t35_packaging.json`).
- **Subito dopo, il proprietario chiede:** il t35 è un modello vero? La risposta: in parte.
  - **Apprese:** la rete contrastiva sugli effetti (già nel t34) e la `rete_anti`, che decide solo la magnitudine del
    log2FC per l'nMAE.
  - **Non apprese:** la direzione e il bulk, che vengono dal transfer K562 ×2, e lo spostamento dei conteggi, che è
    una regola del generatore.
- **Il proprietario:** «aspetta allora a gradarlo puoi fermare».
- **12:29–12:31 UTC:**
  - processo di caricamento fermato;
  - lock orfano `submit-default.lock` rimosso, perché il processo 35304 non esisteva più;
  - `vcc cancel` → entry `lqLrMpd2BRmZ7m3w52x2`, stato `cancelled` (`cancel_t35_raw.json`).

  Secondo `vcc cancel --help`, un caricamento annullato **non conta** nel limite giornaliero.
- **Stato:** il t35 non è inviato. Il pacchetto resta in `vcc2026-data/artifacts/t35pack/`. Il banco del t35 sullo
  scorer vero (`reports/generatore_e_banchi/banco_t35_2026-10-04/`) è pronto e non lanciato.
