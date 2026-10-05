# ARCHIVIO DATI — indice corrente, non reingerire

**Archivio → banca pronta e campioni → training esteso** è il percorso principale.
Manifest immutabile: `manifest.json`; SHA256 `d2cf5e7e88bd5edec7774ec99005a8dde7dc343e623c17adf50fba36d7e6fcd2`.
Contiene account, versioni, percorsi interni, ricevute e hash. Non usare il vecchio cubo del pilot come fallback.

[Tutti i dataset, dimensioni e diversità](../DATI_DISPONIBILI_r1.md) · [Avvio dei quattro Colab e job Kaggle](../PARALLELISMO_r1.md)

| Unità della nuova ingestione | Banca salvata | Campioni |
|---|---|---|
| D1_Rest | [davideferrante11/vcc-bank-cd4-1-3-rest-r2](https://www.kaggle.com/code/davideferrante11/vcc-bank-cd4-1-3-rest-r2) | completi |
| D2_Rest | [davideferrante11/vcc-bank-cd4-1-3-rest-r2](https://www.kaggle.com/code/davideferrante11/vcc-bank-cd4-1-3-rest-r2) | completi |
| D3_Rest | [davideferrante11/vcc-bank-cd4-1-3-rest-r2](https://www.kaggle.com/code/davideferrante11/vcc-bank-cd4-1-3-rest-r2) | completi |
| D1_Stim8hr | [davideferrante11/vcc-bank-cd4-1-3-stim8hr-r2](https://www.kaggle.com/code/davideferrante11/vcc-bank-cd4-1-3-stim8hr-r2) | completi |
| D2_Stim8hr | [davideferrante11/vcc-bank-cd4-1-3-stim8hr-r2](https://www.kaggle.com/code/davideferrante11/vcc-bank-cd4-1-3-stim8hr-r2) | completi |
| D3_Stim8hr | [davideferrante11/vcc-bank-cd4-1-3-stim8hr-r2](https://www.kaggle.com/code/davideferrante11/vcc-bank-cd4-1-3-stim8hr-r2) | completi |
| D1_Stim48hr | [davideferrante11/vcc-bank-cd4-1-3-stim48hr-r2](https://www.kaggle.com/code/davideferrante11/vcc-bank-cd4-1-3-stim48hr-r2) | completi |
| D2_Stim48hr | [davideferrante11/vcc-bank-cd4-1-3-stim48hr-r2](https://www.kaggle.com/code/davideferrante11/vcc-bank-cd4-1-3-stim48hr-r2) | completi |
| D3_Stim48hr | [davideferrante11/vcc-bank-cd4-1-3-stim48hr-r2](https://www.kaggle.com/code/davideferrante11/vcc-bank-cd4-1-3-stim48hr-r2) | completi |
| D4_Rest | [davidmaisterx/vcc-bank-cd4-4-4-rest-r2](https://www.kaggle.com/code/davidmaisterx/vcc-bank-cd4-4-4-rest-r2) | completi |
| D4_Stim8hr | [davidmaisterx/vcc-bank-cd4-4-4-stim8hr-r2](https://www.kaggle.com/code/davidmaisterx/vcc-bank-cd4-4-4-stim8hr-r2) | completi |
| D4_Stim48hr | [davidmaisterx/vcc-bank-cd4-4-4-stim48hr-r2](https://www.kaggle.com/code/davidmaisterx/vcc-bank-cd4-4-4-stim48hr-r2) | completi |
| kolf_pan_genome | [davideferrante11/vcc-bank-kolf-pan-r1](https://www.kaggle.com/code/davideferrante11/vcc-bank-kolf-pan-r1) | completi, unione verificata |
| orion_hct116 | [davideferrante11/vcc-bank-orion-hct116-r1](https://www.kaggle.com/code/davideferrante11/vcc-bank-orion-hct116-r1) | completi, unione verificata |
| orion_hek293t | [davideferrante11/vcc-bank-orion-hek293t-r1](https://www.kaggle.com/code/davideferrante11/vcc-bank-orion-hek293t-r1) | parti 3/6 verificate |

## Archivi precedenti persistenti

17 dataset grezzi nominati nel manifest, 69,58 GB: conservarli e riusarli. Età del dato non è motivo di esclusione; identità e ruolo vanno verificati.
I nuovi job preparano solo pseudobulk e campioni da questi shard. Includono tutte le loro chiavi biologiche; QC e ammissibilità al trainer restano da riconciliare.

## Aggiunte incrementali

Aggiungere sorgente/versione e manifest con hash; eseguire soltanto i derivati mancanti. Se input, asse, QC, codice e parametri coincidono, montare i derivati esistenti.
Una nuova versione del manifest mantiene la precedente. Cambi di QC/asse/normalizzazione rigenerano soltanto i dipendenti.

**Il training esteso non è ancora avviato.** Integrare lettori e guardie nel trainer, con split e ricevute di uso/loss anche dopo resume. Il catalogo contiene ancora lacune aperte.
