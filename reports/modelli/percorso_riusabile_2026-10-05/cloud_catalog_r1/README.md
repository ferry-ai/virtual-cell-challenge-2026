# Dove sono archivio, banche e campioni

Indice attuale delle 15 unità verificate. Corpus completo e trainer esteso ancora da integrare.

Manifest: `manifest.json`; SHA256: `ea80df9c6cdf0449c1a81b604b586b89b16fb1d8e2b7a3449d8568abd551b077`. Nessuna ingestion eseguita per crearlo.

| Unità | Banca persistente | Campioni |
|---|---|---|
| D1_Rest | [davideferrante11/vcc-bank-cd4-1-3-rest-r2](https://www.kaggle.com/code/davideferrante11/vcc-bank-cd4-1-3-rest-r2) | completi, versione 1 |
| D2_Rest | [davideferrante11/vcc-bank-cd4-1-3-rest-r2](https://www.kaggle.com/code/davideferrante11/vcc-bank-cd4-1-3-rest-r2) | completi, versione 1 |
| D3_Rest | [davideferrante11/vcc-bank-cd4-1-3-rest-r2](https://www.kaggle.com/code/davideferrante11/vcc-bank-cd4-1-3-rest-r2) | completi, versione 1 |
| D1_Stim8hr | [davideferrante11/vcc-bank-cd4-1-3-stim8hr-r2](https://www.kaggle.com/code/davideferrante11/vcc-bank-cd4-1-3-stim8hr-r2) | completi, versione 1 |
| D2_Stim8hr | [davideferrante11/vcc-bank-cd4-1-3-stim8hr-r2](https://www.kaggle.com/code/davideferrante11/vcc-bank-cd4-1-3-stim8hr-r2) | completi, versione 1 |
| D3_Stim8hr | [davideferrante11/vcc-bank-cd4-1-3-stim8hr-r2](https://www.kaggle.com/code/davideferrante11/vcc-bank-cd4-1-3-stim8hr-r2) | completi, versione 1 |
| D1_Stim48hr | [davideferrante11/vcc-bank-cd4-1-3-stim48hr-r2](https://www.kaggle.com/code/davideferrante11/vcc-bank-cd4-1-3-stim48hr-r2) | completi, versione 1 |
| D2_Stim48hr | [davideferrante11/vcc-bank-cd4-1-3-stim48hr-r2](https://www.kaggle.com/code/davideferrante11/vcc-bank-cd4-1-3-stim48hr-r2) | completi, versione 1 |
| D3_Stim48hr | [davideferrante11/vcc-bank-cd4-1-3-stim48hr-r2](https://www.kaggle.com/code/davideferrante11/vcc-bank-cd4-1-3-stim48hr-r2) | completi, versione 1 |
| D4_Rest | [davidmaisterx/vcc-bank-cd4-4-4-rest-r2](https://www.kaggle.com/code/davidmaisterx/vcc-bank-cd4-4-4-rest-r2) | completi, versione 1 |
| D4_Stim8hr | [davidmaisterx/vcc-bank-cd4-4-4-stim8hr-r2](https://www.kaggle.com/code/davidmaisterx/vcc-bank-cd4-4-4-stim8hr-r2) | completi, versione 1 |
| D4_Stim48hr | [davidmaisterx/vcc-bank-cd4-4-4-stim48hr-r2](https://www.kaggle.com/code/davidmaisterx/vcc-bank-cd4-4-4-stim48hr-r2) | completi, versione 1 |
| kolf_pan_genome | [davideferrante11/vcc-bank-kolf-pan-r1](https://www.kaggle.com/code/davideferrante11/vcc-bank-kolf-pan-r1) | parti 3/3 lanciate; chiusura da verificare |
| orion_hct116 | [davideferrante11/vcc-bank-orion-hct116-r1](https://www.kaggle.com/code/davideferrante11/vcc-bank-orion-hct116-r1) | parti 4/4 lanciate; chiusura da verificare |
| orion_hek293t | [davideferrante11/vcc-bank-orion-hek293t-r1](https://www.kaggle.com/code/davideferrante11/vcc-bank-orion-hek293t-r1) | parti 2/6 lanciate; chiusura da verificare |

Grezzi: per ogni unità il manifest conserva notebook sorgente, ricevuta di ingestione e hash.
Ogni banca ha account, versione salvata, percorso interno e hash della ricevuta; questa contiene gli hash dei file.
I campioni CD4 sono matrici autonome; per le nuove sorgenti le parti ancora aperte non sono certificate persistenti.

`rlead-bench-cube-r2` resta il cubo del pilot. Nessun fallback automatico per nomi uguali o file mancanti.

Per aggiungere un dataset: aggiungere la sua voce e i suoi derivati, poi creare una nuova revisione del manifest.
Rigenerare solo ciò che dipende da un asse, QC, normalizzazione o split cambiato. Non ripetere i grezzi invariati.

Il manifest è un indice e un vincolo di identità, non una copia dei dati né un trainer già integrato.
