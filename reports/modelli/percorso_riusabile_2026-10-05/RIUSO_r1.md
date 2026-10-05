# Avviare il prossimo training senza rifare ingestion

Procedura implementata nelle campagne correnti, con parti ancora da provare
end-to-end. Stato e assegnazioni solo in [R-LEAD](../../../docs/piani/strategia-scientifica.md).

1. **Scegliere gli input per identità.** Partire da [storage r10](cloud_catalog_r10/manifest.json)
   (SHA256 `7134c13c741e04b1bb90b15f42afd2a50e653454aca17e49005edcad6f2e7fdf`)
   e [copertura attesa](training_coverage_r1/expected.json)
   (SHA256 `f7edac31784e56fab3a192e74dc0b6b8ea56bc1496dbba5d5c06c753d2e66015`).
   Account/versione/file/hash/lineage prevalgono sul titolo del notebook.
   L'indice storage non decide i ruoli scientifici e non è la release del fit.
2. **Riutilizzare i producer conclusi.** Le chiavi di derivazione fissano input,
   asse, QC, codice e parametri. Se coincidono, montare i derivati esistenti;
   non rilanciare ingestion, sampler o copie locali già verificate.
   Un producer ERROR non montabile richiede una copia byte-identica con hash
   verificati, come Norman/iPSC, non nuova stima. Controllare privacy dal consumer.
3. **Congelare una release nuova e dichiarata.** Elencare unità/ruoli ammessi,
   split, fonti attese/usate/bloccate e motivi; congelare copie dei ledger prima
   di vincolarne gli hash. Risolvere `supersedes_failed` prima dei mount: mai
   due voti per originale e retry. Non mutare release precedenti o cercare `latest`.
4. **Collegare il trainer specifico.** Il transfer lineare legge `count_sum`,
   maschere e controlli per BIO/donatore; effettua pooling prima dello shrink.
   Un trainer cellulare monta anche matrici campionate, probabilità e lineage:
   `samples.jsonl.gz` da solo può essere un elenco di locatori, non una matrice.
   Il contratto globale e le ricevute vanno integrati nel runtime reale; un
   checker locale non sostituisce questo passaggio. [Reader neurali](TRAINER_r1.md)
   e [release lock CD4](release_lock.py) hanno scope limitato, non copertura completa.
5. **Lanciare solo il compute necessario.** Preflight tre account, input
   accessibili, RAM/disco reali, dedup e nuova destinazione. I vecchi dispatcher
   di ingestion sono registrazioni delle campagne, non comandi di avvio ordinario.
   Il nuovo trainer usa le banche montate; copia locale facoltativa.
6. **Conservare prova dell'uso.** Alla chiusura recuperare manifest e ricevute
   piccole: fonti e contesti realmente contribuenti, artefatti/hash, stato del fit.
   Nel lineare non esistono loss o optimizer; nei trainer neurali anche esposizione
   e resume. Parametri/source-code e output della release devono restare rintracciabili.

## Modifiche future

| Modifica | Da fare | Da riusare |
|---|---|---|
| Stessa banca, altro modello | Nuovo launcher/ricetta e ricevute del fit | Archivio, banca e campioni compatibili |
| Nuovo dataset | Solo adapter/derivati della nuova fonte; release globale nuova | Tutte le banche precedenti compatibili |
| Nuovo QC/asse/normalizzazione | Rigenerare derivati dipendenti con chiavi nuove | Grezzi originali e derivati indipendenti |
| Nuove ancore/split/fonti | Nuovi artefatti dipendenti e nuova release | Banche di base invariate dove lecite |
| Cambio di account/accesso | Mount pubblico autorizzato o copia byte-identica, verifica consumer | Stesso calcolo e stessi byte |

Nessuna esclusione per dimensione, comodità o overlap. Adapter mancanti sono
dipendenze tecniche aperte, non esclusioni scientifiche. Fonti storiche restano
utilizzabili se provenienza e ruolo sono riconciliati. Il cubo pilot non è un fallback.

Per l'esecuzione corrente seguire il [README](README.md): il primo mix è
parziale e non prova ancora il percorso completo né l'uso di tutti i 395,75 GB.
