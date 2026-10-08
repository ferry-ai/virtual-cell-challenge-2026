# C/J: pacchetti pronti, non avviati

**Preparazione e audit dei metadata, non fit o valutazione.** Le quattro viste
sono consegnate e verificate da DATI-TRANSFER nel commit `3c705a9f`, con parent
production per C e parent T per J. Nessun dato di verità dei fold è stato letto qui.

| Fold | Righe | Contesti ammessi | Target distinti | Target con ESM2 | Query |
|---|---:|---:|---:|---:|---:|
| C-K562 | 192.383 | 45 | 18.546 | 18.339 | 299 |
| C-iPSC | 182.579 | 23 | 18.368 | 18.191 | 299 |
| J-K562 | 153.913 | 45 | 14.772 | 14.618 | 66 |
| J-iPSC | 146.039 | 23 | 14.624 | 14.491 | 66 |

`feature_coverage_CJ_r1.json` verifica hash di viste/input/split e registra ogni
mancante per contesto, con pesi. Vale la policy congelata in HANDOFF_FIT_r1.md:
nessuna riga esclusa per feature mancante. Sono esclusi soltanto lignaggi/target
richiesti dal rispettivo fold, con i pesi ricalcolati dal proprietario delle viste.

`prepare_cloud_fit_v3.py` aggiunge i quattro fold ai pacchetti privati, controlla
le query contro le etichette effettivamente ammesse e conserva un query_contract.
I file `prepared_<fold>_r1.json` indicano identità, hash e copertura; i quattro
`package_check_<fold>_r1.json` hanno PASS su 14 input ciascuno. I pacchetti con
locator sono solo fuori Git. Gli input privati sono sottoinsiemi del trasferimento
già autorizzato, senza nuovi locator emessi o download in locale.

**TMEM104:** assente dal training dei due C e senza match ESM2. Non viene
presentato come bersaglio visto. La query nativa C contiene 299 target; una
valutazione del pannello intero deve includere TMEM104 con maschera/ripiego
espliciti, non limitarla silenziosamente ai 299. J usa esattamente i 66 hidden
preregistrati. Il context_id C/J identifica il fold a lignaggio escluso; non
afferma uso di una covariata cellulare nel regressore target-only.

Produzione e T restano i due job in corso. I pacchetti C/J non sono una ricevuta
di consumo o un'autorizzazione aggiuntiva di quota. Scorer e revisione della scala
restano a VALIDAZIONE; nessuna lettura dei risultati o promozione anticipata.
