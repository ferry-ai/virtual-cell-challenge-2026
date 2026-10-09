# Chiusura prioritaria ESM2 e AMMI

9 ottobre 2026, 17:20 Europe/Rome (orologio letto: 15:20 UTC).
Lead Codex, sessione `01a11c05-970e-7af2-a07e-3860bd74acbd`.
Tipo: decisione operativa prima dei risultati AMMI, non esito sperimentale.

Il proprietario chiede: «sono del tutto necessarie tutte e 14 le prove? Non
vorrei andare tutto a rilento. Le mie istruzioni in questo momento sono di
portare a termine ESM2 e AMMI il prima possibile».

Questo mandato aggiorna la sequenza del
[mandato reti](MANDATO_RETI_2026-10-09_r1.md). Il corpus non viene ridotto per
accelerare. Restano accessi privati e risorse già autorizzate, senza acquisti,
pubblicazioni o riapertura automatica dell'invio T3. L'obiettivo è produrre
artefatti utilizzabili e un verdetto onesto, non promettere un miglioramento.

## ESM2: chiudere con i fit esistenti

MODELLI riusa i sei modelli e le predizioni della
[consegna verificata](../modelli_esterni_01a11c35_2026-10-08/CONSEGNA_SEI_FIT_r1.md).
Niente nuovo fit bilanciato, griglia, PIE o altra architettura prima di chiudere
questa versione. Eseguire la lettura C/J-iPSC mancante con il banco congelato,
in parallelo alla preparazione AMMI; non attendere indefinitamente una sessione
esterna. Coordinare la proprietà della corsa e usare output separati; il banco
originale e le verità protette non si modificano.

Completare checkpoint, contratto degli effetti, maschere e ponte verso il
generatore; verificare scala, assi e assenza di doppia ampiezza/cis. La lettura
C già congelata resta distinta da una futura combinazione con T3. Se proposta,
quest'ultima richiede delta effettivo rispetto alle maschere T3 e regola fissata
prima dei numeri; non è una copia della copertura del vecchio t36.

Consegna: modello ricaricabile, predizioni native, export verificato, comando
di inferenza e stato della valutazione. Preparazione del file di consegna in
parallelo dove indipendente; nessuna promozione implicita dal solo formato valido.

## AMMI: quattro fit iniziali, repliche differite

Prima dei nuovi risultati, il Lead dispone questa sequenza del
[protocollo r2](../modelli_esterni_01a11c35_2026-10-08/PROTOCOLLO_AMMI_r2.md):

| Fase | Esecuzione |
|---|---|
| Prima lettura | C-K562 e C-iPSC, ciascuno `cells` e `none`, solo seme 17: **4 fit** |
| Controllo funzionale | `swapped` in inferenza dagli stessi checkpoint `cells`: **0 fit aggiuntivi** |
| Successiva conferma | Semi 29/43 e braccio `mean` differiti; non bloccano il primo candidato |
| Produzione | Preparare subito il contratto di **un fit finale distinto**, seme 17, e la sua inferenza |

Una differenza a un seme è preliminare: non dimostra stabilità né superiorità
generale. Nessuna selezione del seme o della configurazione dopo i risultati.
I fold indipendenti partono appena pronti i rispettivi input verificati, senza
attendere una dipendenza esclusiva dell'altro fold e senza omettere contesti
ammessi nel fold che si avvia. Modello e tensori devono usare CUDA reale.

Preservare split, ancora T0, supporto, pesi, normalizzazione, ricetta e due
epoche del pilot. La lettura deve confrontare davvero `cells`, `none`, ancora
e `swapped`; il PASS tecnico delle guardie non è una misura di beneficio.
Controlli di perdita/ampiezza, componente comune, leakage, assi, checkpoint e
copertura rimangono. I confronti a sei membri richiesti per promuovere il modello
possono procedere in parallelo; non vengono sostituiti da un proxy.

Il fit finale non è l'export arbitrario di uno dei fold. MODELLI e DATI devono
specificare prima input, esclusioni, ancore senza auto-inclusione delle risposte,
controlli dei contesti di destinazione e politica di training/guardie coerente.
Non riammettere silenziosamente la validation interna nei fold. Non sostituire
T0 con T3 senza un nuovo contratto e confronto. Preparare questa parte mentre
si estraggono NTC e si esegue il pilot, così non diventa il blocco successivo.
Il candidato tecnico resta preliminare fino alla lettura scientifica: guardie
fallite non si aggirano e un peggioramento non si presenta come successo.

Prima di decidere sul candidato leggere, per entrambi i lignaggi, almeno
`cells - T0` e `cells - none`: la guardia corrente riporta questi numeri ma
`benefit_threshold=None` non impone un beneficio. Per produzione servono
ancore di training che escludano il lignaggio della riga, T0 per le query e
NTC dei contesti di destinazione nello stesso contratto; le ancore annidate
dei fold non si riusano attribuendo loro esclusioni diverse. Pesi e riferimento
ESM2 sono ricalcolati sulla vista ammissibile di produzione. Una risposta
riammessa nel training non rimane una validation indipendente.

Il controllo `swapped` resta diagnostico: se solo quello fallisce una guardia
di export, conservare il checkpoint e l'export nativo valido, registrare il
fallimento dello scambio e non consumare un nuovo fit per ricrearli. Le guardie
sull'export nativo non vengono allentate.

## Responsabilità e primo ostacolo

- DATI: chiudere NTC, recuperando le parti complete; correggere il formato
  `symbol` non supportato nel job davidmaisterx e non interrompere df11.
  Consegna ancore/input verificati e accessibili; predisposizione input produzione
  senza rifare i fit T3 o ESM2. Tutti i contesti idonei restano tracciati.
- MODELLI: emendamento eseguibile 4 fit, chiusura ESM2, lancio AMMI, contratto
  produzione e inferenza. Nessun nuovo requisito puramente procedurale di
  approvazione quando il mandato umano copre già l'azione.
- VALIDAZIONE: letture sui file consegnati e confronto con regole congelate;
  eventuali questioni scientifiche irrisolte sono nominate, non trasformate
  in una falsa ricevuta di completamento. Gli output di altri agenti conservano
  provenienza separata dalla validazione indipendente.

## Precedenti

S-001/S-002/S-006: mantenere il confronto con l'ancora e il segnale specifico,
per non scambiare training riuscito per utilità. S-007: rinviare `mean` limita
le conclusioni sul valore delle singole cellule rispetto alla media. S-009:
parità tra ricetta valutata ed export e guardie anche a destinazione. S-013:
due lignaggi e risultato per lignaggio, evitando una conclusione universale
dal solo segnale iPSC. Il piano riduce repliche, non cambia questi meccanismi.

**Segnale precoce e arresto:** leakage, input mancanti, scala errata, guardie
strutturali fallite o checkpoint non riproducibile fermano la relativa corsa.
Assenza di beneficio resta un esito da registrare; non autorizza clipping,
miscele post hoc o la dichiarazione che il modello generalizzi.

D-053 resta aperto: il pilot AMMI sul pannello non equivale a usare tutto il
catalogo, e la riduzione delle prove non autorizza ulteriori esclusioni.
