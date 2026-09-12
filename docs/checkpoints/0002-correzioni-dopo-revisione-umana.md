# CP-0002 — Correzioni dopo la prima revisione umana

- **Data:** 2026-09-12
- **Tipo:** correzione
- **Redatto da:** agente (Claude Opus 5), su revisione del proprietario del progetto
- **Revisione umana:** sì, è la revisione che ha prodotto questo checkpoint
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

La prima versione di questo sistema documentale descrive davvero ciò che è stato
misurato, o ha consolidato come conoscenza alcune ipotesi dei documenti precedenti?

## 2. Cosa è stato fatto

Il proprietario del progetto ha letto i file, rieseguito `scripts/31_check_docs.py` e i
dodici test, e riprodotto due difetti tecnici in cartelle temporanee. Ha segnalato sei
problemi che i test non intercettavano. Questa sessione li ha verificati uno per uno
contro i file citati e li ha corretti.

Verifiche rifatte qui, tutte in sola lettura:

- confronto fra l'affermazione della mappa sulla non essenzialità del pannello e quello
  che `docs/data_strategy_2026-09-11.md` §1 e `docs/revisione_analisi_2026-09-11.md` §2
  dicono davvero;
- lettura di `reports/scorer/vcc2026_contract.json`, campi `input_type`, `control_source`
  e `de`, per stabilire che cosa lo scorer richiede in ingresso;
- esecuzione del validatore con un controllo di copertura ricorsivo sui file di `docs/`
  e `reports/`;
- ispezione di `reports/grok_verification/` e di `scripts/27_verify_grok_leads.py`,
  comparsi dopo CP-0001.

## 3. Cosa si è osservato

**Sei correzioni richieste, tutte fondate.** Nessuna riguarda un numero sbagliato: tutte
riguardano affermazioni giuste che si erano trasformate in affermazioni più forti.

**1 — La catena "non nei pannelli essential → non essenziale → effetti piccoli".** La
mappa classificava come *misura* la non essenzialità dei 300 bersagli, e ne derivava che
gli effetti fossero piccoli per costruzione. La misura è una sola: 0/300 sovrapposizioni
con i pannelli essential di K562 e RPE1. L'essenzialità nei contesti A, B e C non è mai
stata misurata, e l'essenzialità riguarda comunque la sopravvivenza della cellula, non
l'ampiezza della risposta trascrizionale: un gene non essenziale può muovere molti geni.

La cosa notevole è dove si è persa la cautela. Il documento **più vecchio** la
conteneva: «L'assenza dal pannello essential non dimostra che un gene sia biologicamente
non essenziale» (`docs/data_strategy_2026-09-11.md` §1). La revisione dell'11 settembre
l'ha lasciata cadere e ha scritto «**Il pannello 2026 è: espresso ovunque, non
essenziale.** Conseguenza diretta: le risposte sono piccole per costruzione» (§2).
CP-0001 l'ha ripetuta, e la mappa l'ha promossa da interpretazione a misura. Quattro
passaggi, ciascuno leggermente più sicuro del precedente.

**2 — Pseudobulk e valutazione a singola cellula confusi.** Il "prossimo passo" della
mappa proponeva di acquisire pseudobulk CD4 e diceva che da lì si ottiene «sia una
sorgente di trasferimento sia il materiale per un bundle di valutazione». È falso. Il
pseudobulk aggrega le cellule e perde la loro distribuzione; ricostruire somme intere di
conteggi non ricostruisce le cellule che le hanno prodotte. Lo scorer chiede
`input_type: counts` a singola cellula, misura contro le cellule di controllo reali
(`control_source: real`), e la sua correzione del rumore di campionamento sulla MSE
dipende dalla dispersione fra le cellule previste. Un'acquisizione riuscita del solo
pseudobulk avrebbe lasciato il collo di bottiglia dov'era, facendolo sembrare risolto.

**3 — La spiegazione per principianti insegnava una strategia contestata.** CP-0001 §5
dice che prevedere una diminuzione piccola quando quella vera è grande fa perdere poco.
Non è una conclusione generale: dipende dalle metriche e dai dati, e lo stesso CP-0001,
due sezioni più avanti, dichiara quella postura ancora da verificare (D-006). È il punto
più grave dei tre perché la spiegazione semplice è la parte che verrà letta di più.

**4 — La protezione contro la sovrascrittura non reggeva.** `30_new_checkpoint.py`
controllava l'esistenza del file e poi scriveva con `write_text`. Il proprietario ha
simulato un secondo agente che crea il file fra il controllo e la scrittura: il
contenuto del secondo agente veniva sovrascritto. In più, con un indice malformato lo
script falliva **dopo** aver creato il checkpoint, lasciando un file non registrato.

**5 — Il controllo di copertura del registro non faceva quello che dichiarava.**
Guardava solo i Markdown direttamente sotto `docs/` e le voci direttamente sotto
`reports/`, confrontandole per sottostringa. Documenti non registrati dentro
sottocartelle passavano inosservati. Con il controllo ricorsivo appena scritto sono
emersi **36 file non coperti**, fra cui una cartella intera che nessuno aveva
registrato: `reports/grok_verification/`, dieci file prodotti da
`scripts/27_verify_grok_leads.py` alle 15:24 del 12 settembre, dopo CP-0001. Otto sonde
di metadati, tutte con esito 200, che in quel momento nessun documento del repository
citava o spiegava.

Il seguito è successo mentre questo checkpoint veniva scritto, ed è la parte che vale
la pena registrare. Alle 15:32 è comparso `docs/revisione_grok_2026-09-12.md`, che
spiega quelle sonde: è la verifica live di un inventario di dataset fornito da Grok,
con correzioni di accessione (GSE247601 è una SuperSeries, la sottoserie CRISPRi è
GSE249595; l'archivio Zenodo del Multiome è software, non AnnData) e una pista
riaperta, MCF-7. La scheda R-008, aperta come "materiale non spiegato", si è chiusa
otto minuti dopo. Nel frattempo sono arrivati anche `scripts/28_probe_grok_files.py` e
altri undici file di sonda, tutti coperti dalla voce di cartella già registrata: la
convenzione sull'ambito delle voci ha funzionato come previsto.

Le conclusioni di quel documento **non sono state integrate** in `docs/DECISIONI.md`.
Non sono state verificate da questa sessione né riviste da una persona, e cambiarne le
priorità di acquisizione richiede un checkpoint proprio. Il registro lo dice
esplicitamente nella riga del documento.

**6 — Una procedura di revisione proponeva di sovrascrivere l'evidenza.** La scheda
R-005 suggeriva di rieseguire `scripts/20_verify_candidate_accessions.py` per
sostituire i due stub 404 con il contenuto corretto. Ma quella riesecuzione avrebbe
sovrascritto anche `reports/candidate_verification/manifest.json`, che è l'unica prova
che il ramo `main` non esiste — e il contenuto corretto è già conservato in `expanded/`.
La procedura contraddiceva il principio del registro che l'aveva prodotta.

## 4. Interpretazione e incertezza

Il modo di fallire è sempre lo stesso, e non è specifico di questo repository: nel
riassumere, un'affermazione condizionata perde le sue condizioni. «Non compare nei
pannelli essential» diventa «non essenziale» diventa «effetti piccoli». Ogni passaggio
sembra una parafrasi e invece è una deduzione. Il rimedio che questo sistema può offrire
non è la buona volontà di chi scrive: è la colonna "tipo" accanto a ogni affermazione e
l'obbligo di citare il file che la sostiene, perché nel momento in cui si cerca
l'evidenza per «effetti piccoli» si scopre che non esiste.

Quattro dei sei problemi erano già presenti nelle analisi precedenti; questa revisione
avrebbe dovuto fermarli e invece li ha consolidati. Due erano difetti tecnici nuovi,
introdotti qui.

Resta incerto quanto sia generale il rimedio. Le correzioni 1, 2 e 3 sono state trovate
da una persona che leggeva, non dal validatore: il validatore controlla la struttura, e
nessun controllo automatico di questo tipo potrà mai dire se un'affermazione è vera.

## 5. Spiegazione semplice

Due idee, e questa volta senza scorciatoie.

**Sull'essenzialità.** "Essenziale" in questo campo vuol dire una cosa precisa: se
spegni quel gene, la cellula smette di crescere o muore. I 300 bersagli della gara non
compaiono nelle liste di geni essenziali che abbiamo sottomano. Questo non dice che
spegnerli non faccia niente: una cellula può sopravvivere benissimo e intanto cambiare
l'attività di centinaia di geni. Sopravvivere e non cambiare sono due cose diverse.
Quanto cambieranno i nostri 300 bersagli, oggi, non lo sappiamo.

**Sull'ampiezza delle previsioni.** Nella versione precedente qui si leggeva che
sbagliare per difetto costa poco. È una semplificazione che non abbiamo verificato. La
formulazione corretta è: ci sono sei metriche, alcune premiano l'azzeccare la direzione
del cambiamento, altre l'ampiezza; ridurre l'ampiezza delle previsioni può aiutare su
alcune e far perdere punti su altre. **Dobbiamo misurare** quanto conviene ridurla, su
tutte e sei le metriche insieme, prima di adottarla come regola.

**Sul pseudobulk.** Se raccogli l'altezza di mille persone e ne tieni solo la media, hai
un numero utile, ma non puoi più sapere quante persone erano alte più di 180 cm. La
valutazione della gara ha bisogno delle singole persone, non della media.

## 6. Conseguenze

- `docs/PROGETTO.md`: le due righe della tabella sono state separate nelle misure che le
  sostengono; l'ampiezza degli effetti è passata fra le incertezze (punto 3); il
  prossimo passo distingue ora l'acquisizione del pseudobulk da quella delle cellule.
- `docs/DECISIONI.md`: D-003 segnala esplicitamente che il pseudobulk non la sblocca;
  D-004 e D-011 non si appoggiano più alla premessa degli effetti piccoli, ma
  all'argomento della selezione sull'esito, che regge da solo.
- `docs/REGISTRO.md`: R-004 elenca la catena come quinta affermazione contestata;
  R-005 non propone più la sovrascrittura; R-008 apre una scheda su
  `reports/grok_verification/`; la convenzione su che cosa copre una voce è scritta.
- `scripts/30_new_checkpoint.py`: creazione esclusiva, lock sulla numerazione e
  sull'indice, e ogni validazione spostata prima della scrittura.
- `scripts/31_check_docs.py`: copertura ricorsiva con ambito della voce esplicito.
- Nessun risultato scientifico cambia: nessuna di queste correzioni tocca una misura.
  Cambia che cosa ci sentiamo autorizzati a dedurne.

## 7. Cosa corregge

Corregge **CP-0001**, che resta leggibile nella sua forma originale:

| Dove in CP-0001 | Che cosa diceva | Correzione |
|---|---|---|
| §3, «Il pannello dei 300 bersagli è "espresso ovunque, non essenziale"» | presentato come osservazione | La misura è 0/300 nei pannelli essential; la non essenzialità nei contesti della gara non è misurata |
| §4, «gli effetti sono piccoli per costruzione» | presentato come interpretazione della misura | Non segue dalle misure disponibili: l'ampiezza degli effetti in A, B e C è ignota |
| §5, «se dici "questo gene scende un po'" e in realtà scende molto, perdi poco» | insegnato come regola | Dipende dalle metriche e dai dati; è la postura D-006, ancora da verificare |

E corregge la prima versione di `docs/PROGETTO.md` (righe 46–47 e sezione 5), di
`docs/DECISIONI.md` (D-004, D-011) e di `docs/REGISTRO.md` (scheda R-005), tutte del
2026-09-12 e tutte sostituite dalle versioni correnti.

Non corregge, e conferma: le coperture misurate, l'identità di lignaggio dei contesti,
i clamp dello scorer, l'assenza dell'RNA di H1, i vincoli hardware, e il fatto che
nessun modello sia stato allenato.

## 8. Domanda di comprensione

Un collega propone di scaricare il pseudobulk CD4 e dice che con quello potremo
finalmente dare un punteggio alle nostre baseline sulla scala della gara. Che cosa gli
rispondi, e che cosa gli chiedi di scaricare in più?
