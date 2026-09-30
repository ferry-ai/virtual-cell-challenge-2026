# Dipendenza dagli output rifiutata da Kaggle

**Misurato, 29 settembre 2026.** Un solo push, dopo revisione della lead, ha
restituito sia il rifiuto della sorgente
`davidmaisterx/vcc-lead-neural-sources-r1/1` come non valida sia la creazione della
versione 1 del notebook CPU privato. La risposta è conservata in `push_raw_r1.txt`.

Il successivo pull read-only, `pull_after_push_r1/kernel-metadata.json`, conferma
`kernel_sources=[]`, CPU, Internet spento e dataset r2 invariato. Il formato
owner/slug/version era ammesso dalla validazione della CLI locale, ma il server
non ha aggiunto questa sorgente. Non si attribuisce senza prova il rifiuto al solo
stato ERROR, alla sintassi della versione o a un'altra regola del backend.

Gli output seed 0 esistono e sono accessibili dal servizio statico SDK: i report
piccoli sono già stati scaricati e verificati. Il limite osservato riguarda il
collegamento degli output a questo nuovo notebook, non il completamento dei fold.

Il runner richiede i 15 hash dei report nei cinque fold montati e deve fermarsi
prima della diagnostica se mancano. Al primo probe, 19:46 UTC, Kaggle lo riportava
ancora RUNNING; questo non dimostra che la diagnostica sia partita. L'esito terminale
resta da conservare separatamente. Non sono stati tentati nuovi push, cambi della
sorgente, upload sostitutivi o rigenerazione delle predizioni.

La replica seed 1 è indipendente e include già la diagnostica dopo il proprio
readout completo. La soglia primaria negativa di seed 0 resta invariata.
