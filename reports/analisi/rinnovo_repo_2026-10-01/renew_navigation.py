"""Apply the documentation renewal after snapshot_docs.py; no experiment is run."""

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
TEXTS = {}

TEXTS["docs/piani/strategia-scientifica.md"] = """# R-LEAD — piano implementativo dopo t29

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
"""

TEXTS["docs/piani/modello-competitivo.md"] = """# R-COMP — obiettivo del programma competitivo

- **Stato:** aperto come programma; esecuzione raccolta in R-LEAD.
- **Aggiornato:** rinnovo del 1 ottobre 2026, dopo t29.
- **Assegnazione:** regia precedente Codex lead, chat `01a0ee03-b357-7012-81a9-e8d7de767478`.
  Il nuovo incarico operativo si registra una volta in [R-LEAD](strategia-scientifica.md).
- **Mandato:** costruire una catena utile su nuovi contesti, usando memoria del bersaglio,
  biologia e dati quando il loro contributo è verificabile. Il traguardo resta D/E/F.
- **Prossimo passo:** P0–P4 di R-LEAD; non avviare un programma concorrente da questa scheda.
- **Dipendenze:** D-050, [GENERALIZZAZIONE](../GENERALIZZAZIONE.md), R-LAB per gli artefatti,
  R-REV e S-INVII per la consegna.

## Criterio di successo

Un miglioramento confermato della catena completa rispetto al riferimento, con tutti i
sei membri espliciti e supporto C/J dichiarato. Una loss minore, un corpus più grande o un
massimo isolato non bastano. La classifica finale è la verifica esterna, non una promessa.

Nessuna rete è promossa dopo t29 ([CP-0055](../checkpoints/0055-t29-rete-cellulare-punteggio.md)).
Questo non dimostra che nessuna rete possa funzionare. Il programma può adottare un
miglioramento semplice o mantenere il transfer se i candidati non passano.

## Chiusura e alternative

Chiusura con decisione sul candidato, conferma indipendente e pipeline finale verificata,
oppure rendiconto negativo con riferimento conservato. Residuo biologico, dati ponte e
popolazioni hanno condizioni di apertura in R-LEAD, non una coda automatica di job.

[Programma e assegnazioni precedenti](../storico/rinnovo_2026-10-01/docs/piani/modello-competitivo.md).
"""

TEXTS["docs/piani/piano-giorno-2026-09-30.md"] = """# R-LAB — corpus e artefatti cellulari disponibili

- **Stato:** in attesa delle verifiche P0–P4 di R-LEAD per scegliere un nuovo training.
- **Aggiornato:** rinnovo del 1 ottobre 2026, dopo r1–r3 e t29.
- **Assegnazione:** esecuzione precedente Claude; proprietario conferma Claude e teammate
  fermi. La ripresa si registra in [R-LEAD](strategia-scientifica.md), con file e output.
- **Prossimo passo:** inventario di input, pesi e esposizioni effettive P0/P1;
  correzioni e nuovo protocollo P3/P4. Il nome storico «piano-giorno» non indica una scadenza.
- **Dipendenze:** [R-LEAD](strategia-scientifica.md), [sorgenti](../../reports/sorgenti/README.md)
  e [modelli](../../reports/modelli/README.md). Dati pesanti esterni a Git.

## Che cosa esiste

| Materiale | Evidenza e limite |
|---|---|
| Corpus, adattatori, QC, inventari e job | [Indice del corpus](../../reports/sorgenti/corpus_cellulare_2026-09-30/README.md). Le versioni descrivono acquisizioni successive: disponibilità e checksum si verificano sulla macchina destinataria |
| Modello, prepass, split, descrittori ed export originali | [risposta_biologica](../../reports/modelli/risposta_biologica_2026-09-30/). Codice usato nei training; preservarlo e correggere una copia nuova |
| R1, primo training | [ESITO](../../reports/modelli/cellnet_tecnico_2026-10-01/ESITO.md): verifica tecnica non interamente passata |
| R2, corpus esteso | [ESITO](../../reports/modelli/cellnet_esteso_2026-10-01/ESITO.md): verifica tecnica con misure; braccio `desc` usato in t29, non promosso |
| R3, seconda ondata | [ESITO](../../reports/modelli/cellnet_completo_2026-10-01/ESITO.md): training completato, collasso `ident`; [diagnosi](../../reports/analisi/lead_audit_2026-10-01/AGGIORNAMENTO_R3.md) |
| Quarto training, terza ondata + floor | [Protocollo](../../reports/modelli/cellnet_terza_ondata_2026-10-01/PROTOCOLLO.md): nessun esito registrato; verifica tecnica che non comprende il banco richiesto dopo t29 |

H1 train/val e HIPSCI sono già stati usati nel corpus; non riaprire acquisizioni sulla base
di vecchie liste d'attesa. H1 test resta riserva chiusa e non è un contesto nuovo per un
modello che vede H1 train/val. Presenza nel catalogo e uso nel fit sono cose diverse:
il replay dopo QC di P1 determina che cosa ogni modello ha visto davvero.

## Chiusura e alternative

Questa scheda si aggiorna quando cambia l'inventario o termina un'esecuzione di R-LEAD.
Una consegna si chiude con manifest, hash, esito e dipendenze mancanti espliciti; non deve
acquisire ogni sorgente possibile. Nuovi dati entrano per una domanda misurabile di P5.
Un altro training tecnico non soddisfa il ramo c di t29.

[Cronologia integrale e incarichi precedenti](../storico/rinnovo_2026-10-01/docs/piani/piano-giorno-2026-09-30.md).
"""

TEXTS["docs/piani/revisione-critica.md"] = """# R-REV — verifiche residue della revisione critica

- **Stato:** aperto; alcune azioni concluse, residui distinti sotto.
- **Aggiornato:** rinnovo del 1 ottobre 2026, dopo t29.
- **Assegnazione:** precedenti sessioni Claude `f4f38e58` e `f2abd9a6`; ripresa non avviata.
  Il proprietario conferma gli agenti fermi. Registrare la nuova sottoattività prima di eseguirla.
- **Prossimo passo:** preflight della prova a forma piena (3), indipendente dalla rete;
  raccordare 4/5 a R-LEAD senza ripetere le azioni concluse.
- **Dipendenze:** [PROCEDURE §7](../PROCEDURE.md#7-il-set-finale-22-ottobre), dati e risorse
  effettivi; [R-LEAD](strategia-scientifica.md) per ogni nuovo confronto neurale.
- **Evidenza iniziale:** [revisione del 28/09](../../reports/analisi/revisione_criticita_2026-09-28/REVISIONE.md).

## Azioni: esito, residuo, condizione di avanzamento

| Azione | Stato verificabile | Prossimo passo o chiusura |
|---|---|---|
| 0. Portare la revisione in main | Eseguito il 28/09, cronologia nello storico | Non ripetere merge/stash del vecchio incarico. La divergenza remota si misura oggi, non si copia da una nota |
| 1. Recuperare evidenza mancante | Quattro voci recuperate; resta la preregistrazione t21 citata ma assente, [R-020](../REGISTRO.md#r-020--evidenza-citata-ma-assente-dal-repository) | Documentare l'assenza se non si trova; non inventare una previsione retroattiva |
| 2. Proxy contro ufficiale | Conclusa, [CP-0041](../checkpoints/0041-proxy-contro-ufficiale.md) | Il proxy non promuove candidati da solo |
| 3. Prova generale finale | Forma ridotta valida, [CP-0044](../checkpoints/0044-prova-generale-22-ottobre.md); difetti e correzioni nel [report](../../reports/invii/prova_generale_2026-09-28/RISULTATI.md) | Verificare difetti residui e risorse attuali, poi forma piena in output nuovo; niente invio implicito |
| 4. Banco K562 a sei membri | [Protocollo e bracci](../../reports/generatore_e_banchi/banco_k562_pannello_2026-09-29/RISULTATI.md), nessun esito del job registrato | Preflight e confronto transfer/emissione con le esclusioni dichiarate. `g0:` è già disponibile nello stadio 73; verificare codice e test, non reimplementarlo dalla vecchia consegna |
| 5. Basali sull'asse comune | [Protocollo](../../reports/sorgenti/basali_asse_2026-09-29/), nessun esito registrato | Misurare denominatori e impatto sui lettori che li usano; riscalare non recupera geni non misurati |
| 6. Rete relazionale | Misura conclusa, [CP-0043](../checkpoints/0043-misura-decisiva-relazioni.md); candidato non avviato per la regola | Non riaperta dal fallimento di un'altra rete |
| 7. Stessa linea e Orion | Uso Orion autorizzato dal proprietario; identità private e verifica esterna distinte | Chiarire la decisione pertinente prima di nuovi usi; nessun contatto con organizzatori implicito |
| 8. Portare ricerca in libreria | Proposta subordinata a un componente adottato | Parità e test prima del trasferimento; non migrare in blocco codice sperimentale |

Il banco K562 dichiara anche un prior cis proveniente da target K562 fuori pannello:
conservare questa limitazione. R2/r3 hanno visto K562 in training; il banco non prova
generalizzazione di quelle reti a un contesto mai visto. Un nuovo protocollo richiede
esclusioni coerenti di tutti i componenti (R-LEAD P1).

## Criterio di chiusura e alternative

Ogni azione termina con evidenza, esito e limite; gli esiti negativi sono chiusure valide.
La prova a forma piena richiede un pacchetto verificato. Un input mancante si registra con
il passo impedito, aggiornando i residui senza ripetere il lavoro concluso.

[Mandato, assegnazioni e cronologia completa](../storico/rinnovo_2026-10-01/docs/piani/revisione-critica.md).
"""

TEXTS["docs/piani/invii-finale.md"] = """# S-INVII — presidio della consegna finale

- **Stato:** aperto; t29 valutato e letto, nessun invio avviato dal rinnovo.
- **Aggiornato:** 1 ottobre 2026, dopo t29.
- **Assegnazione:** invii precedenti seguiti da Claude e Codex nelle sessioni registrate
  nelle ricevute; nuova sessione da registrare prima di operare. Agenti confermati fermi.
- **Prossimo passo:** prova generale a forma piena con il riferimento, azione 3 di
  [R-REV](revisione-critica.md), e manifest della pipeline P6 di [R-LEAD](strategia-scientifica.md).
- **Dipendenze:** candidato congelato, risorse e autorizzazione per l'azione concreta;
  [PROCEDURE §1–2 e §7](../PROCEDURE.md), [regole dei report](../../reports/CLAUDE.md).

## Stato e decisioni

Gli esiti e i pacchetti conservati sono nell'[indice degli invii](../../reports/invii/README.md).
Una vecchia previsione o un t27 pronto non costituiscono una coda di invio.
Il riferimento e il massimo osservato sono in [PROGETTO §0](../PROGETTO.md).

Il ramo c di t29 richiede un banco a sei membri almeno al livello del transfer prima
di un nuovo invio neurale ([CP-0055](../checkpoints/0055-t29-rete-cellulare-punteggio.md)).
La scadenza finale resta il 5 novembre, con rilascio D/E/F il 22 ottobre.

## Chiusura e alternativa

Per ogni invio: previsione prima della generazione, manifest e diagnostiche, pacchetto
verificato, ricevuta ufficiale e lettura dei sei scalati secondo la regola registrata.
Per il finale: copertura e fallback sul nuovo pannello verificati, nessun risultato
assunto dalla sola esistenza dei comandi. Se il modello nuovo non passa, resta il
riferimento riproducibile; la sua preparazione non dipende dal successo della rete.

[Cronologia precedente](../storico/rinnovo_2026-10-01/docs/piani/invii-finale.md).
"""

TEXTS["docs/piani/modello-v2.md"] = """# R-V2 — catalogo delle alternative precedenti

- **Stato:** in attesa di una motivazione sperimentale di R-LEAD per riaprire un filone.
- **Aggiornato:** rinnovo del 1 ottobre 2026.
- **Assegnazione:** incarichi Claude/Codex del 26–29/09 conservati nello storico;
  nessun nuovo lavoro assegnato da questa scheda.
- **Prossimo passo:** leggere l'esito del filone pertinente in [AMBITI §5](../AMBITI.md#5-modelli-appresi-e-generalizzazione)
  prima di proporre una variante. La sequenza eseguibile è [R-LEAD](strategia-scientifica.md).
- **Dipendenze:** limite misurato, confronto nuovo e input disponibili; D-050.

## Dove sono finiti i filoni

| Area precedente | Sede attuale |
|---|---|
| Universi, copertura, affidabilità e basali | [R-LAB](piano-giorno-2026-09-30.md), [R-DATI](dati-affidabilita.md), [sorgenti](../../reports/sorgenti/README.md) |
| Transfer, programmi e ripieghi per bersagli nuovi | [trasferimento](../../reports/trasferimento/README.md); confronti ammessi in R-LEAD P4/P5 |
| Contesto, encoder, reti sulle sorgenti, Stack | [modelli](../../reports/modelli/README.md); esiti negativi secondo i rispettivi protocolli, nessuna chiusura universale delle famiglie |
| Rete relazionale | Azione 6 di [R-REV](revisione-critica.md), conclusa; nuova base empirica necessaria per riaprire |
| Popolazioni e switch | [R-SWITCH](switch-distribuzioni.md), subordinata a informazioni indipendenti |
| Finale e prova generale | [S-INVII](invii-finale.md) e azione 3 di R-REV |

## Riapertura e chiusura

Una riapertura nomina problema misurato, input nuovi, baseline e regola prima della prova,
e si registra in R-LEAD. Un nome di architettura o una vecchia riga «libero» non sono un
mandato. Questa scheda resta un catalogo; non deve completare tutti i vecchi filoni.

Le autorizzazioni cloud del 27/09 avevano un perimetro di sessione discusso anche in R-REV:
la contraddizione non si risolve leggendo una riga storica come consenso generale.
Le decisioni su stessa linea e nuovi accessi sono in [PROGETTO §0](../PROGETTO.md).

[Filoni F1–F10, alternative, mandati e risultati datati](../storico/rinnovo_2026-10-01/docs/piani/modello-v2.md).
"""

TEXTS["docs/piani/dati-affidabilita.md"] = """# R-DATI — colmare lacune misurate dei dati

- **Stato:** in attesa della matrice di esposizione e dei bisogni del banco R-LEAD P1/P4.
- **Aggiornato:** rinnovo del 1 ottobre 2026.
- **Assegnazione:** audit del 25/09 completato da Claude `f4f38e58` e collaboratori;
  nessuna acquisizione nuova assegnata dal rinnovo.
- **Prossimo passo:** identificare quale controllo, replica, guida o sovrapposizione manca
  per risolvere un limite specifico; partire dal corpus già prodotto in [R-LAB](piano-giorno-2026-09-30.md).
- **Dipendenze:** P1/P4 di [R-LEAD](strategia-scientifica.md), [GENERALIZZAZIONE](../GENERALIZZAZIONE.md),
  disponibilità e autorizzazioni per l'eventuale acquisizione.

## Consegna utile

Una tabella di lacune con domanda, file necessario, ruolo C/T/J, unità e maschere,
controlli/repliche/guide, accesso, byte e limite che risolve. Distinguere overlap dei target
e copertura dei geni di risposta; zero overlap con i 300 non esclude una sorgente.
Non ripetere l'inventario sulla base delle liste d'attesa del 25/09.

CD4 è già Flex; H1 train/val e HIPSCI sono nel corpus. I risultati e le limitazioni
sono nell'[indice delle sorgenti](../../reports/sorgenti/README.md); presenza e uso reale
si verificano nei manifest e nel replay del training. H1 test resta chiusa.

## Chiusura e alternative

Una lacuna si chiude con file/QC verificati e ablation a split fisso, oppure con la prova
che quei dati non permettono il confronto. Se il problema è campionamento o qualità,
correggerlo prima di aggiungere cellule. Nessun obbligo di acquisire tutte le sorgenti.

[Audit e ipotesi H7–H10 del 24–26/09](../storico/rinnovo_2026-10-01/docs/piani/dati-affidabilita.md).
"""

TEXTS["docs/piani/switch-distribuzioni.md"] = """# R-SWITCH — ipotesi sulle popolazioni

- **Stato:** in attesa di un limite di distribuzione misurato in R-LEAD e di dati identificabili.
- **Aggiornato:** rinnovo del 1 ottobre 2026.
- **Assegnazione:** nessuna presa in carico sperimentale registrata; proposte precedenti nello storico.
- **Prossimo passo:** se P4/P5 di [R-LEAD](strategia-scientifica.md) lo motivano, fissare un
  confronto a pari media tra spostamento uniforme e miscela, usando guide/repliche disgiunte.
- **Dipendenze:** cellule, controlli, supporto misurato e informazioni indipendenti per
  stimare intensità e risposta; [R-DATI](dati-affidabilita.md) per le lacune.

Il gate identity collassato di r3 non prova né smentisce uno switch biologico. Una
distribuzione bimodale non dimostra bistabilità; co-espressione non dimostra causalità.
Non usare lo stesso segnale per definire una soglia e poi dimostrarla.

## Chiusura e alternative

Report che distingua le forme di risposta su guide/repliche escluse, oppure documenti
che i dati non le identificano. Un predittore si confronta poi sui sei membri, con la
stessa media e supporto. Conservare il generatore semplice se la miscela non aiuta.
Flow, reti causali e trasporto non diventano il prossimo job per il solo fallimento di t29.

[Disegno, H4–H5 e alternative precedenti](../storico/rinnovo_2026-10-01/docs/piani/switch-distribuzioni.md).
"""

TEXTS["docs/PROMPT_CLAUDE.md"] = """# Prompt per Claude — attuare R-LEAD

Incollare il testo sotto nella sessione che lavorerà sulla repo. Il piano completo resta
in una sola scheda; questo prompt lo richiama senza crearne una variante.

---

Riprendi VCC 2026 e implementa `docs/piani/strategia-scientifica.md` (R-LEAD, P0–P6).
La repo è stata riallineata dopo il t29: la rete r2 `desc` non è promossa e non può avere
un altro invio prima del banco locale a sei membri richiesto dalla sua regola.

Leggi prima `CLAUDE.md`, `docs/PROGETTO.md` §0, `docs/PIANI.md` §2–3 e R-LEAD.
Segui le letture del tuo compito e le guide di cartella. Registra sessione, macchina,
commit base, file e destinazioni nuove. Il proprietario ha confermato Claude e teammate
fermi durante il rinnovo; verifica solo eventuali cambiamenti successivi rilevanti.

Esegui il lavoro locale autorizzato: P0/P1, riproduzione dei difetti applicabili e nuova
versione con test P3, replica export P2 quando gli input ci sono, protocollo P4 congelato
prima dei nuovi numeri. La prima consegna deve contenere codice e prove, non un altro piano.
Prosegui con le fasi successive quando soddisfano le loro dipendenze e autorizzazioni.

Non correggere l'evidenza storica: crea copie nuove del codice di ricerca e output nuovi.
Ricostruisci l'esposizione reale prima di chiamare un gruppo C/T/J. K562 già visto da r2/r3
non è un contesto neurale nuovo; H1 train/val è nel corpus e H1 test resta riserva chiusa.
Non confondere il collasso identity di r3 con la causa del t29, né il floor già implementato
con una soluzione dimostrata. Nessun riavvio automatico del quarto training.

Confronta transfer, generico addestrato, bilineare e rete agli stessi input e supporti,
usando tutti i sei membri. Distingui replica storica t22, correzione t25 ed emissione t28.
Non ricavare uno score ufficiale dalle ancore aggregate. Se il candidato perde, conserva
il riferimento e usa la diagnosi per scegliere il prossimo confronto verificabile.

Su un'altra macchina leggi anche `docs/CONSEGNA_TEAMMATE.md`: Git non porta dati e pesi.
Se un input manca, completa le attività indipendenti e indica il file minimo e la fase
impedita. Download, quota cloud, nuovi agenti, invii e push seguono le autorizzazioni della
chat e `CLAUDE.md`; un vecchio protocollo non autorizza un lancio nuovo.

Consegna commit locali, test/log, manifest, protocollo, risultati e decisione secondo la
regola. Aggiorna R-LEAD, indici e registro, separando implementato, eseguito, misurato e
adottato. La prova finale a forma piena resta necessaria anche se rimane il transfer.
"""

TEXTS["docs/PROMPT_CLAUDE_TEAMMATE.md"] = """# Prompt Claude sulla macchina del teammate

Usare il [prompt unico per Claude](PROMPT_CLAUDE.md), aggiungendo:

> Lavori sul clone del teammate. Applica `docs/CONSEGNA_TEAMMATE.md` per Git, runtime,
> percorsi, dati e accessi. Non presumere di avere pesi, Drive o processi del proprietario.
> Il programma da implementare resta R-LEAD; non avviarne una seconda versione.

Il vecchio prompt esteso è [conservato nello storico](storico/rinnovo_2026-10-01/docs/PROMPT_CLAUDE_TEAMMATE.md).
Non guida una nuova esecuzione: le specifiche aggiornate sono in R-LEAD.
"""

TEXTS["docs/CONSEGNA_TEAMMATE.md"] = """# Portare R-LEAD sulla macchina del teammate

Questa pagina integra il [prompt unico per Claude](PROMPT_CLAUDE.md) e il
[piano R-LEAD](piani/strategia-scientifica.md) soltanto per il trasferimento di ambiente.
Il t29 è concluso. Non esiste qui una seconda coda di training o invii.

## Git e presa in carico

Repository: [ferry-ai/virtual-cell-challenge-2026](https://github.com/ferry-ai/virtual-cell-challenge-2026).
Verificare remoto, branch, commit e modifiche locali prima di aggiornare senza force/reset.
La presenza dell'audit `53d17fe` non prova di avere il rinnovo: devono esserci
`docs/PROMPT_CLAUDE.md` e R-LEAD con P0–P6. Il commit esatto di consegna si confronta
con quello comunicato dal proprietario; nessun push futuro è implicito in questo documento.

Nel clone separato usare un branch di lavoro `codex/teammate-rlead`, registrando la presa
in carico in R-LEAD. Claude e teammate erano fermi al rinnovo; coordinare eventuali riprese
successive per non eseguire due versioni sugli stessi file o sulla stessa quota.

## Runtime e percorsi

Configurare `VCC2026_DATA_ROOT` fuori dal clone; verificare il valore risolto da
`vcc2026.config.paths()`. Non copiare percorsi `C:/Users/ferra`, mount `G:` o credenziali.
I wrapper `.cmd` sono Windows; su Linux/macOS usare il Python del venv ed esporre `src/`
su `PYTHONPATH`. Ricreare l'ambiente dai requisiti, registrando versioni effettive:
i requisiti hanno intervalli, non un lock esatto; il training richiede anche PyTorch.

Il [preflight portabile](../reports/analisi/handoff_teammate_2026-10-01/preflight_handoff.py)
scrive un inventario con la libreria standard. Exit code 0 significa «inventario scritto»,
non readiness completa. Usare anche `validate_runtime.py` del corpus per il runtime
effettivo, H5AD e risorse. Verificare `cell_eval2.config`, preset e API usate dal banco.
[CP-0054](checkpoints/0054-visibilita-scorer-e-consegna.md) distingue visibilità sandbox
da pacchetto rotto: confrontare il terminale nativo prima di reinstallare.

## Input che Git non trasferisce

| Materiale | Verifica necessaria |
|---|---|
| Codice, ricette, protocolli, eval e diagnostiche | Revisioni e hash; distinguere LF/CRLF da modifiche del codice |
| Conteggi, controlli ufficiali, asse e pannello | Copia lecita, unità, nomi/ordine, maschere e checksum |
| Shard e descrittori | Accesso proprio a Drive/Kaggle, revisione e manifest; presenza nel catalogo non significa presenza sul disco |
| `model.pt`, checkpoint, prepass pesanti | Percorso leggibile e hash; gli eval versionati non li contengono |
| H1 test | Solo provenienza e ruolo dai manifest: non aprire la riserva per onboarding |
| Venv, credenziali, GPU, sessioni cloud, `.claude/`, agent-hub e worktree | Non trasferiti dal clone; nessuna dipendenza privata implicita |

Inventariare con percorsi locali; usare `inventory.py --no-drive` se il mount non è
configurato. Conservare i manifest originali, creando una mappatura nuova degli input.
Per ciascun dato mancante indicare locatore, byte, accesso e fase impedita; proseguire
con fixture CPU e output versionati dove bastano. Il preflight sul portatile non certifica
il runtime GPU remoto: ripeterlo lì prima del job autorizzato.

La consegna scientifica e i test sono specificati soltanto in R-LEAD.
[Consegna precedente integrale](storico/rinnovo_2026-10-01/docs/CONSEGNA_TEAMMATE.md).
"""


def main():
    if not (ROOT / "docs/storico/rinnovo_2026-10-01/docs/PIANI.md").exists():
        raise SystemExit("Create the pre-renewal snapshot first")
    for name, content in TEXTS.items():
        (ROOT / name).write_text(content, encoding="utf-8", newline="\n")
    print(f"Updated {len(TEXTS)} navigation documents")


if __name__ == "__main__":
    main()
