# R-LEAD — piano implementativo dopo t29

- **Stato:** aperto; piano pronto per Claude, implementazione nuova non iniziata.
- **Aggiornato:** rinnovo richiesto dal proprietario il 1 ottobre 2026, dopo t29.
- **Mandato:** recuperare controllo dell'esperimento e cercare un miglioramento verificabile
  rispetto al transfer. Questo è l'unico piano di esecuzione del programma R-COMP.
- **Assegnazione:** destinatario Claude nella sessione scelta dal proprietario. Claude e
  teammate sono fermi, confermato in chat durante il riordino. La futura presa in carico
  registra sessione, macchina, commit base, file e output secondo [PIANI §3](../PIANI.md#3-lavorare-in-una-cartella-condivisa).
  Il precedente incarico al teammate è conservato nello storico; non c'è una seconda
  implementazione da avviare in parallelo.
- **Prossimo passo:** P0–P1 e riproduzione dei difetti P3 su CPU; poi P2/P4 sugli input disponibili.
  Prima consegna: manifest di esposizione, diagnosi applicabili, codice corretto con test
  e protocollo del banco. Non basta un'altra sintesi o un training che completa.
- **Dipendenze:** corpus e artefatti in [R-LAB](piano-giorno-2026-09-30.md),
  [GENERALIZZAZIONE](../GENERALIZZAZIONE.md), D-050, procedure e preflight pertinenti.
- **Chiusura:** decisione motivata sul candidato, prove riproducibili e consegna operativa;
  se nessun candidato passa, conservare il riferimento e indicare quale limite è misurato.
  Nessun punteggio o piazzamento è promesso.

## 1. Punto fermo e domanda da risolvere

Il t29 prova **r2, braccio `desc`, generatore t22, effetti non riscalati**. Fallisce la sua
regola: prima di un altro invio neurale serve un banco locale a sei membri almeno al livello
del transfer ([CP-0055](../checkpoints/0055-t29-rete-cellulare-punteggio.md)). Il collasso
del gate `ident` in r3 è un'altra osservazione: non identifica la causa del t29.

La domanda iniziale è: il divario nasce dagli effetti appresi, dall'esportazione, dal
generatore, dalla diversa distribuzione dei dati o da più fattori? Split mobili, pesi
effettivi diversi dal dichiarato e controlli non appaiati impediscono già alcuni confronti.
Le diagnosi riproducibili sono in [NOTA_TRAINING](../../reports/analisi/lead_audit_2026-10-01/NOTA_TRAINING.md)
e [AGGIORNAMENTO_R3](../../reports/analisi/lead_audit_2026-10-01/AGGIORNAMENTO_R3.md).
Sono verifiche locali ed esplorative, non una prova che le correzioni renderanno competitiva la rete.

**Riferimenti distinti:** ricostruire t22/t24 dai manifest per la replica storica; preservare
la correzione dello stimatore di t25 nel confronto con la pipeline corretta. L'emissione
t28 è un fattore separato, con esito ufficiale non conclusivo. Un nome di ricetta da solo
non identifica cache, stima, generatore, scala e seme. La tabella degli [invii](../../reports/invii/README.md)
è la fonte degli esiti; non scegliere il riferimento dopo aver visto il banco.

## 2. Contratto dei nuovi output

Creare una cartella nuova `reports/analisi/diagnosi_cellnet_<data>/` per P0–P2 e una
`reports/modelli/cellnet_corretto_<data>/` per codice e prove P3–P5, aggiungendo un suffisso
se il nome è occupato. I percorsi sono proposti, le cartelle non esistono per effetto di
questo piano. Registrarle negli indici e nel registro. Copiare il codice di ricerca da
`reports/modelli/risposta_biologica_2026-09-30/` senza modificare l'originale importato da
altri report; fissare hash e versione di ogni dipendenza usata per la replica.

Ogni esecuzione ha una directory nuova e un manifest con commit, comando, ambiente,
input/hash, ruoli, parametri, seed e output/hash. Dati e pesi pesanti restano nella radice
dati. Gli output minimi seguenti sono contratti di consegna, non risultati già prodotti:

| Passo | Output minimo | Evidenza per avanzare |
|---|---|---|
| P0 | `preflight.json`, `input_manifest.json` | Runtime e input necessari verificati sul sistema che eseguirà il passo |
| P1 | `exposure_manifest.json`, `split_manifest.json`, `cohort_audit.json` | Ruoli effettivi C/T/J dopo QC, esclusioni e riserva controllabili |
| P2 | `export_parity.json`, `diagnosi.md` | Replica del percorso r2 oppure differenze e input mancanti identificati |
| P3 | Nuova versione, test di accettazione, `fix_matrix.json`, smoke e pilot | Ogni correzione passa il suo controesempio senza cambiare il problema valutato |
| P4 | `PROTOCOLLO.md`, sei membri per braccio/contesto/seed, `decision.json` | Regola congelata prima della misura; nessuna promozione dal solo proxy |
| P5 | Ablation del residuo o dei dati, conferma separata | Beneficio del componente identificato e ripetuto nel regime dichiarato |
| P6 | Manifest della pipeline, prova a forma piena, verbale dei controlli | Artefatto valido e riproducibile dal pannello all'impacchettamento |

Distinguere in ogni consegna **implementato**, **eseguito**, **misurato**, **adottato**.
Un passaggio mancante blocca le conclusioni che ne dipendono, non il lavoro indipendente.

## 3. P0 — ambiente, input e riferimento riproducibile

1. Verificare Git e file condivisi; registrare ambiente reale, spazio, RAM, GPU se usata,
   interpreter, dipendenze e API dello scorer. Verificare `cell_eval2.config` e il preset
   `vcc2026`, non il solo import del pacchetto. In [CP-0054](../checkpoints/0054-visibilita-scorer-e-consegna.md)
   lo stesso Python passa i 287 test fuori dal sandbox: confrontare visibilità e percorsi
   prima di reinstallare. Non sostituire lo scorer con un proxy per aggirare un errore.
2. Inventariare copie leggibili e hash di controlli, asse, pannello, shard, descrittori,
   prepass, pesi r2/r3, cache del transfer e generatori. `eval.json` non prova che esista
   `model.pt`. Distinguere file mancanti da permessi mancanti e da manifest fuori data.
   Su un'altra macchina applicare [CONSEGNA_TEAMMATE](../CONSEGNA_TEAMMATE.md).
3. Separare nel manifest replica t22, riferimento corretto t25 e variante di emissione t28.
   Ricostruire le opzioni effettive dalle ricevute di generazione. Non rigenerare l'intero
   pannello per verificare una parità che si può misurare su un ritaglio dichiarato.

**Se manca un input:** completare fixture, letture degli eval e codice indipendenti; elencare
il file minimo da recuperare, locatore, byte, accesso e fase impedita. Non ricreare tutto
il disco della macchina originale. Download, quota, nuovi agenti, invii e push seguono
CLAUDE.md e le autorizzazioni della sessione, senza inferirle da un vecchio protocollo.

## 4. P1 — split e esposizione effettiva ai dati

Ricostruire per ciascun checkpoint r2/r3 quali contesti, studi, target, guide e modalità
sono entrati nel fit, nella selezione e nelle valutazioni già lette. Salvare ruolo previsto,
QC e ruolo effettivo; verificare alias di geni, duplicati, repliche e descrittori/pretraining.

- **C:** target già osservato, contesto perturbato escluso; **T:** target escluso, contesto
  osservato; **J:** target e contesto esclusi. Congelare identità e, quando dichiarato,
  famiglie funzionali. Un holdout per identità non prova extrapolazione di famiglia.
- Gli split r2/r3 sono cambiati: il confronto dei loro aggregati non isola l'effetto di
  più dati. Un confronto retrospettivo usa solo gruppi con esposizione ammissibile per
  entrambi, con numerosità e supporto comuni; resta sviluppo, non conferma.
- **K562 è stato usato nel training r2/r3:** il banco K562 di R-REV valuta transfer e
  generatore secondo il suo protocollo. Non è un contesto neurale mai visto; per tale
  dichiarazione serve un nuovo fit che lo escluda, comprese le dipendenze dei prior.
- **H1 train/validation sono nel corpus; H1 test è la riserva chiusa.** Non aprirla per
  debug o onboarding e non chiamarla nuovo contesto se il modello ha usato H1 train/val.
- Le risposte perturbate del contesto escluso non entrano in fit, preprocessing appreso,
  early stopping o scelta dei parametri. I suoi controlli possono essere input; dichiarare
  separazione/incrocio delle librerie per stimare il basale e misurare il contrasto.

**Accettazione:** aggiungendo sorgenti/target, riordinando shard o applicando QC, i ruoli
congelati non cambiano; eventuali gruppi diventati non valutabili sono riportati, non
riassegnati. Esclusioni globali e provenienza sono testate con fixture e audit sul corpus.
Se non resta un contesto indipendente, dichiararlo: non fabbricare C/J rinominando gruppi.

## 5. P2 — seguire il segnale fino alle cellule generate

Costruire una replica piccola del percorso r2 `desc` → effetti esportati → generatore t22
→ scorer. Confrontare implementazione nativa e export con gli stessi input e checkpoint.
Registrare tolleranze numeriche prima del confronto; bitwise dove il percorso lo permette.

Controllare ordine/identità dei geni, maschere, log naturale/log2, denominatore dei CPM,
profondità, ponderazione della miscela, correzione cis, scala, clipping, selezione dei
controlli e seed. Registrare supporto assente e fallback. Confrontare prima gli effetti
trans e la discriminazione dei target, poi le popolazioni generate con le sei metriche.
Usare lo stesso generatore per isolare gli effetti; eventuali generatori diversi sono
bracci separati. La perdita media della rete non è questa prova.

**Accettazione:** nessuna differenza di export lasciata senza spiegazione; rapportare
misure prima/dopo generazione per distinguere perdita del predittore e perdita di emissione.
Su dati pubblici dichiarare che questa è diagnosi di sviluppo: non conosciamo le risposte
vere A/B/C e non possiamo isolare con certezza la causa dello score ufficiale.

Se manca un peso, la replica di quel checkpoint resta non verificata. Il nuovo codice può
essere provato su fixture; un nuovo fit non sostituisce retroattivamente la replica r2.

## 6. P3 — correggere soltanto difetti dimostrati

Partire dai controesempi dell'audit. Per ogni riga registrare `riprodotto`, `già corretto`,
`non applicabile` o `non verificabile`, con hash del codice effettivo. I vecchi test restano
prova del vecchio comportamento: i test di accettazione devono esercitare la nuova copia.

| Componente | Implementazione richiesta | Prova di accettazione |
|---|---|---|
| Split (`cell_data.py` e prepass) | Manifest immutabile, assegnazione dei soli nuovi gruppi, QC senza riassegnazione | P1; nessuna fuga fra famiglie/alias/repliche e ruoli effettivi esportati |
| Pesi (`train_cellnet.py`, sampler) | Definire l'obiettivo globale e combinarlo correttamente col campionamento; non rinormalizzare in ogni batch annullando i pesi dichiarati | Coefficienti aggregati corretti nel replay, incluso studio vuoto; riordino/chunking degli stessi esempi non cambia l'obiettivo aggregato; varianza stocastica distinta dall'invarianza esatta |
| Controlli (`cell_data.py`) | Reservoir riproducibile e stratificato per libreria, selezione senza prime righe privilegiate, fallback dichiarati | Copertura prima/dopo cap, appaiamento possibile preservato, assenza di cellule perturbate; fixture con librerie tardive e controllo della dipendenza dall'ordine |
| Miscela (`cellnet.py`) | Log-pesi stabili; verificare il gradiente del gate e del ramo di risposta agli estremi | Gradienti finiti e direzione corretta, recupero nel controesempio, monitor di quantili per studio; ablation di floor/prior/warm-up se introdotti |
| Baseline | Generico senza identità del target realmente addestrato e bilineare regolarizzato con gli stessi input ammessi | Test di indipendenza dal target per il generico; stesso split, supporto e opportunità di tuning; unknown non addestrato resta diagnostica |
| Export/runner | Manifest completo, compatibilità dei checkpoint dichiarata, resume e seed ripristinati | Smoke end-to-end, parità export e ripresa su fixture, poi pilot reale ammesso prima del job completo |

`--pi-floor` esiste già dal commit `39f451d`: non ricrearlo. Un minimo imposto può cambiare
il bias; non è prova di apprendimento. Il clamp può impedire il recupero del gate, ma questo
non prova la causa iniziale del collasso. L'uso congiunto di controlli e perturbate per
imparare il basale è un'ipotesi da ablare, non un errore universale già dimostrato.

Il quarto training già descritto in R-LAB mescola pavimento e nuovi dati: rimane un
protocollo tecnico datato, non è il prossimo job automatico e non isola questi fattori.

## 7. P4 — banco di sviluppo con sei metriche e confronti equi

Congelare il protocollo dopo i controlli tecnici e prima di misurare i nuovi bracci. Il banco
deve salvare i gruppi effettivi e la provenienza di ciascuna verità, non soltanto medie.

1. Confronti: nullo, generico addestrato, transfer dove ammissibile, bilineare, rete corretta.
   Aggiungere descrittori/target permutati e contesto ignorato/scambiato per attribuire il
   contributo dei due input. R2/r3 e identity sono confronti diagnostici con i loro limiti.
   In J il transfer non accede alle risposte dei target esclusi: dichiararne il fallback.
2. Stessi target valutabili, geni misurati, verità, controlli ammessi, numerosità e seed di
   generazione; registrare differenze di informazione. Fit e tuning hanno regole comparabili.
   Nessuna selezione dei «400 gruppi più numerosi» che elimini silenziosamente contesti.
3. Riportare PDS, MSE, NMAE, FID, reach e Jaccard grezzi, per contesto/regime/seed.
   Per MSE rispettare l'aggregazione dello scorer e conservare numeratori/denominatori:
   il rapporto di somme non è la media dei rapporti. Assi e esclusioni dei target seguono
   il preset. Non usare il solo coseno top-200 per decidere.
4. Qualunque normalizzazione locale dichiara ancore, stima su dati indipendenti e limiti.
   Se non disponibili, presentare i sei grezzi e una regola esplicita, non uno score VCC
   inventato dalle ancore aggregate del 17/09. Media operativa e macro scientifica per
   contesto/regime restano distinguibili, con supporti e risultati dei singoli contesti.
5. Prima dei numeri fissare metrica primaria, aggregazione, miglioramento pratico richiesto,
   regressioni ammesse e gestione di confronti multipli. Usare il pilot per progettare
   numerosità e incertezza; non assumere che 0,005 misuri il rumore. Per stabilità al seme,
   almeno tre seed dei finalisti; intervalli appaiati per gruppi realmente indipendenti.
   Tre seed da soli non rendono indipendenti gli studi e non garantiscono potenza.

**Avanzamento:** il candidato passa la regola nuova nel regime dichiarato. D-050 permette
un beneficio C con protezione preregistrata del ramo J; per rivendicare generalizzazione
congiunta serve J. Le soglie di r2/r3/t29 rimangono quelle originali. Nessun nuovo invio
neurale aggira il requisito del ramo c di t29.

**Se perde:** pubblicare la matrice degli errori e conservare transfer e baseline semplici.
Se il difetto è tecnico tornare a P2/P3; se è di informazione, motivare il confronto P5.
Non aumentare automaticamente dati, capacità o numero di training.

## 8. P5 — residuo, dati e distribuzioni, solo con una domanda verificabile

La prima estensione candidata è transfer + residuo bilineare regolarizzato; confrontare
poi il residuo neurale sugli stessi input. Stimare residuo e peso di affidabilità out-of-fold,
senza scegliere per target il vincitore osservato nel test. Il ramo senza memoria ha un
fallback addestrato e verificato. Tenere la parte soltanto se supera il riferimento.

Più dati si provano con ablation annidate e split fissi: qualità, guide/repliche, assay,
modalità, numero di contesti/target/cellule. Non cambiare contemporaneamente corpus e
architettura per attribuire un miglioramento ai dati. R-DATI si attiva per una lacuna
specifica del banco, con costo e accesso espliciti; CRISPRi/a/KO non sono intercambiabili.

Le popolazioni R-SWITCH si aprono se resta un limite misurato a pari effetto medio:
miscela compatta contro generatore attuale, stati e proporzioni separati. Attenzione su
insiemi e flow restano alternative successive. Non inventare coppie di cellule mai misurate
insieme né dedurre bistabilità dalla sola bimodalità.

Congelare infine candidato, adattamento, fallback e regola prima di aprire una riserva
realmente mai valutata; aprirla una volta. I gruppi già letti nell'audit sono sviluppo.
Una bocciatura non si sana cambiando la soglia: diventa evidenza per il confronto successivo.

## 9. P6 — consegna finale indipendente dal successo delle reti

La prova generale a forma piena di [R-REV](revisione-critica.md) è necessaria anche se resta
il transfer. Verificare risorse attuali, inferenza completa, estrazione su nuovi target,
assi, maschere, controlli e packaging bitwise; una prova ridotta non la sostituisce.
Portare in produzione solo componenti adottati, con test di parità e tracciabilità.

Al rilascio D/E/F del 22 ottobre applicare l'audit e l'adattamento preregistrati ai soli
input leciti: un pannello nuovo non significa automaticamente target mai osservati.
Registrare supporto C/J, fallback, hash e scelte per ciascun target. [S-INVII](invii-finale.md)
presidia preparazione e invio entro il 5 novembre secondo le autorizzazioni della sessione.

## 10. Consegna di Claude e alternative

Claude consegna commit locali, test eseguiti e log, manifest, misure, decisione secondo la
regola e prossimo passo concreto. Aggiorna questa scheda, gli indici e il registro;
checkpoint soltanto per eventi scientifici/operativi significativi. Non riscrive i report.
Se un passo richiede accesso mancante, completa quelli indipendenti e chiede il minimo
necessario per quel passo. Questo piano non assegna tempi né limita a priori il lavoro.

La strategia precedente, con le idee di lungo periodo e gli incarichi datati, resta
[nello storico](../storico/rinnovo_2026-10-01/docs/piani/strategia-scientifica.md).
La prima domanda rimane aperta: quale modifica migliora una previsione completa su dati
correttamente esclusi? Un esito negativo ben identificato è utile; non chiude tutte le reti.
