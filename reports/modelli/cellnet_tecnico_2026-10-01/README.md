# Primo training su dati reali della rete cellulare (R-LAB, verifica tecnica)

1 ottobre 2026, Claude Code (sessione `07ebf08b`), scheda [R-LAB](../../../docs/piani/piano-giorno-2026-09-30.md).
**È una verifica tecnica, non un risultato** (il proprietario, 30/09).

Da leggere per primo: [PROTOCOLLO.md](PROTOCOLLO.md), scritto prima di ogni lancio, con la regola di lettura (§4).

| File | Che cosa |
|---|---|
| `PROTOCOLLO.md` | Scopo, dati, ruoli, regola di lettura; scritto prima del lancio |
| `lancio_prepass.json` | Kernel, commit, dataset e argomenti del pre-passo su CPU (`rlab-prepass-r1`) |
| `LANCIO.md` | Il lancio del training su GPU: budget, argomenti dei bracci, ora (scritto al lancio) |
| `esito/` | Gli output piccoli scaricati da Kaggle (piani, copertura, QC, split, valutazione, log); i file pesanti (checkpoint, stato del pre-passo) restano negli output dei kernel, con i loro sha256 in un manifest |

Il codice sta in [risposta_biologica_2026-09-30](../risposta_biologica_2026-09-30/); gli shard nei dataset privati
dell'account `davidmaisterx`, pubblicati dai job Colab di
[corpus_cellulare_2026-09-30](../../sorgenti/corpus_cellulare_2026-09-30/README.md).
