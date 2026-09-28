# Le critiche di Alfredo a vcc-mini: quali valgono, e quali valgono anche per noi

- **Redatto da:** agente (Claude, sessione cloud), su richiesta del proprietario in chat del 28/09:
  «valuta anche se valgono o meno le criticità trovate da Alfredo nella sua chat». Revisione umana: no.
- **Oggetto:** la revisione del 27 settembre di vcc-mini, il banco locale di Alfredo che sta fuori da
  questo repository (scritta da Claude su richiesta di Alfredo, girata qui in chat). vcc-mini riduce
  cinque esperimenti CRISPRi pubblici (Replogle K562 essential e genome-wide, RPE1; Nadig HepG2 e
  Jurkat) a effetti pseudobulk su un asse comune, e addestra TransferNet a prevedere una linea tenuta
  fuori. Il suo codice non è leggibile da qui: giudico le critiche così come sono descritte, con i
  fatti che il repository del team sa già.
- **Tipi di affermazione:** **misurato** (con la fonte nel repository), **verificato nel codice**,
  **interpretazione**, **proposta**.

## 0. Verdetto

**La revisione è onesta e quasi tutta giusta.** Tutti i dodici punti valgono per vcc-mini; due vanno
corretti o completati (P3 e P6), e la regola di lettura del §12 va irrobustita. **Sei punti valgono
anche per il progetto del team** (P1, P2 in forma diversa, P4, P5, P10–P12): lì sono criticità nostre,
non solo del banco di Alfredo. Mancano invece **sei punti** che sistemerei prima del primo run vero;
il più importante è l'assenza di un controllo con il contesto scambiato, la prova che nel team ha
bocciato ogni modello di contesto finora.

## 1. I dodici punti

| ID | La critica di Alfredo | Vale per vcc-mini? | Vale anche per il team? | Correzione o aggiunta |
|---|---|---|---|---|
| P1 | Nessuna incertezza: un numero per metodo, un fold, un seme | **Sì** | **In parte.** I banchi del team hanno il bootstrap appaiato sui bersagli, ma con un seme e senza la correlazione fra bersagli; gli invii ufficiali hanno una sola coppia di semi (t24) | Vedi §2, punto 1: l'unità della generalizzazione a una linea nuova è la linea, non il bersaglio |
| P2 | `transfer_eq` non è la ricetta del t22 | **Sì**, e la correzione di Alfredo è esatta | Il team ha la sua versione del problema (sotto) | Vedi §2, punto 2 |
| P3 | In test più sorgenti che in training; la feature «sorgenti / 4» esce dall'intervallo | **Sì** | Analoga: i banchi a sorgente esclusa provano una ricetta a tre sorgenti, la produzione ne usa quattro; la rete vede 4 contesti di 2 famiglie in training | Fondere i due K562 **non basta**: vedi §2, punto 3 |
| P4 | Controlli normalizzati su insiemi di geni diversi: scarto fra linee nelle feature | **Sì** | **Sì, verificato nel codice**: `basal_profiles.py` calcola i CPM su tutti i geni di ogni sorgente prima di restringere all'asse | Normalizzare sui geni comuni, come propone; resta il divario Flex–3', che la normalizzazione non tocca |
| P5 | Il 91 % dei parametri è legato all'asse del mini-dataset | **Sì** | In forma attenuata: la rete del team prevede 12.477–13.248 geni e sugli altri tiene gli effetti del t25 (`to_effects.py`) | La proposta (embedding da descrittori calcolabili su ogni asse, residuo come ablazione) è giusta; sull'asse di gara serve comunque un ripiego per i geni fuori dal banco |
| P6 | Colonne e contenuto di X sono ipotesi finché `--inspect` non li legge | **Sì** come disciplina | — | **Buona parte è già misurata dal team**: vedi §2, punto 4 |
| P7 | Unione dei geni per simbolo | Sì, minore | Sì: il team unisce per simbolo, e l'asse ufficiale non porta ID Ensembl (contraddizione aperta R-004) | Il numero di geni comuni è misurato dal team: 6.477 per K562, RPE1 e HepG2 insieme (CP-0013); con Jurkat sarà un po' meno |
| P8 | Nessun filtro sull'efficacia del knockdown | Sì, come rapporto | Il team **non filtra la validazione** per efficacia (D-011) e ha trovato che un filtro che guarda l'esito seleziona sull'esito (r8 del pseudoconteggio) | La proposta di Alfredo (riportare la distribuzione, filtro solo come ablazione in training) è coerente con D-011 |
| P9 | Descrittori SVD dominati da K562 genome-wide | Sì, minore | Analogo nei programmi dell'atlante, che perdono comunque a ogni rango | Peso uguale per linea, come propone |
| P10 | Il tetto `replicate` non è la replica dello scorer | **Sì** | Sì: il banco HepG2 del team usa invece metà delle cellule, come lo scorer | Nei file bulk di Replogle non si può dividere le cellule; nei file Nadig (a singola cellula) sì |
| P11 | PDS calcolato fra i bersagli del fold, non fra 300 | Sì | Sì: tutti i PDS proxy del team si calcolano fra i bersagli del banco | Etichetta nel report, come propone |
| P12 | Quattro metriche su sei non misurate | **Sì, strutturale** | **Sì, ed è la criticità principale dei banchi del team**: il proxy vede PDS e nMAE ([revisione](REVISIONE.md) §2.1) | Il banco HepG2 del team con lo scorer vero è il modello da seguire |

Le correzioni del suo §10 (la «ricetta del t22», il milione di parametri, i 16 secondi, i 6–8 mila
geni, i 9.866 bersagli del K562) sono tutte corrette. I 9.866 bersagli sono misurati dal team
(`reports/sorgenti/universo_2026-09-26/RISULTATI.md`); «di forza tipica» è anch'esso misurato, nel
senso preciso di percentile mediano 0,54 dell'energia fra gli altri bersagli del K562
(`reports/trasferimento/atlante_2026-09-26/RISULTATI.md`), non «non scelti per essenzialità».

## 2. Dettagli sui punti da correggere

**1. Incertezza (P1) e regola di lettura (§12).** La regola proposta chiede, in almeno 3 linee su 4,
l'intervallo bootstrap sopra zero per la `mse` e nessun peggioramento del PDS. Tre cose da aggiungere:
- le quattro linee non sono indipendenti: K562 e RPE1 vengono dallo stesso laboratorio (Replogle),
  HepG2 e Jurkat da un altro (Nadig). Con quattro linee, «positivo su 3 di 4» capita per caso circa
  una volta su tre; è l'intervallo per linea a dare la forza, e va detto;
- «il PDS non peggiora» va scritto come numero: per esempio, il limite inferiore dell'intervallo della
  differenza di `pds_rank` sopra −0,01;
- due semi sono il minimo per vedere il segno; il team ha scelto tre nella regola della rete. Con due
  semi la regola va letta sulla media delle previsioni dei due, e i due segni vanno riportati.

**2. La baseline (P2).** Nel repository la ricetta è `configs/recipes/t22.json`: effetti ristretti
(`"effect": "shrunk"`), γ = 1, affidabilità n/(n+100) fra sorgenti, pesi uguali su K562, CD4, HCT116 e
HEK293T, ampiezza 1,576, testa cis (coppie K562 entro 5 kb, scala 2). Tre precisazioni:
- **l'ampiezza 1,576 non è un'ampiezza per la `mse`.** È stata scelta sul punteggio ufficiale, attraverso
  il generatore di trial-01. Nello spazio degli effetti l'ampiezza che minimizza l'errore quadratico è
  0,02–0,16 (`reports/trasferimento/banco_varianti_2026-09-25/MSE.md`). Confrontare la `mse` di un
  modello con una «ricetta t22» a 1,576 sarebbe ingiusto per la ricetta; Alfredo fa bene a stimare
  l'ampiezza sulla validazione;
- **γ = 1 del team toglie a ogni sorgente la sua media sui bersagli del pannello** presenti nella cache;
  in vcc-mini l'equivalente è la media sui bersagli di training di ogni sorgente;
- **la baseline più forte del team oggi è `excl`**: la forma del t22 senza i geni che meno di due
  sorgenti stimano, che ha battuto il t22 su quattro sorgenti tenute fuori
  (`reports/trasferimento/ablazione_t23_2026-09-27/RISULTATI.md`). Il codice di riferimento è
  `reports/trasferimento/atlante_2026-09-26/atlas_bench.py` (braccio `t22like`) e
  `reports/modelli/modello_contesto_2026-09-27/gated_bench.py` (braccio `excl`).

**3. Il numero di sorgenti (P3).** Con quattro linee e una tenuta fuori, una linea di training ha come
sorgenti le altre due linee di training, la linea tenuta fuori ne ha tre. Fondere i due K562 porta il
test da 4 a 3 sorgenti ma il training resta a 2: lo spostamento si riduce, non sparisce. Inoltre i due
esperimenti K562 come sorgenti separate danno al K562 peso doppio in ogni media o attenzione. Proposte:
- fondere i due K562, o pesarli ½ ciascuno come fa la rete del team (1/3 per esperimento K562 in r2);
- togliere la feature «numero di sorgenti», e usare un'aggregazione che non dipenda dal numero;
- riportare il test anche con sottoinsiemi casuali di due sorgenti, per misurare quanto costa
  l'estrapolazione.

**4. Colonne e contenuto dei file (P6): che cosa sa già il team.**
- **Replogle, bulk** (misurato, CP-0003 §3.1): `X` contiene **medie per cellula** dei conteggi grezzi,
  non somme: `X × num_cells_filtered` torna intera. Il numero di cellule è `obs/num_cells_filtered`
  (può essere NaN: il team lo conta come 0). Le etichette sono in `obs/gene_transcript`, nella forma
  `<id>_<SIMBOLO>_…`; i controlli contengono `non-targeting` (più righe, una per guida) e il team li
  media pesando per cellule. I simboli dei geni sono in `var/gene_name`
  (`scripts/98_multisource_effects.py`, `k562_table`). L'ipotesi di Alfredo sulle medie è quindi
  giusta, e il peso per numero di cellule che usa è corretto.
- **Nadig HepG2, mirror scPerturb** (misurato, `reports/storico/hepg2_2026-09-14/nadig_hepg2_audit.json`):
  850.590.740 byte, md5 `af2be47f7477cf32fa6e4bec1c6a4868` uguale a quello pubblicato; `X` denso float32
  con **conteggi grezzi interi**; 9.624 geni (`var/gene_name`), 9.023 sull'asse ufficiale; 145.473
  cellule, 2.393 bersagli, 4.976 controlli. Le colonne candidate sono `perturbation` (i controlli vi si
  chiamano `control`) e `gene` (usata dallo stadio 75, con i controlli `non-targeting`); ci sono anche
  `guide_id` (2.679 guide), `batch` (56 lotti), `UMI_count` e `ncounts`. Le cellule per bersaglio hanno
  mediana 45; 1.061 bersagli hanno almeno 50 cellule.
- **Nadig Jurkat**: mirror da 1,29 GB, 0 dei 300 bersagli del pannello
  (`reports/storico/nadig_reconcile_2026-09-15/`); la struttura non è stata auditata dal team.
- Conseguenza: il filtro dei 20 minimi si applica, e per HepG2 il gruppo di controllo è grande (4.976);
  per i bulk di Replogle il controllo è la media pesata delle righe `non-targeting`.

## 3. Che cosa manca nella revisione di Alfredo

| ID | Critica aggiunta | Perché conta | Proposta |
|---|---|---|---|
| P13 | **Arresto anticipato e ampiezza scelti su bersagli delle linee di training** | Nel team la perdita sulla famiglia tenuta fuori è minima nei primi 50–100 passi e poi sale, mentre quella sulle linee viste continua a scendere (`reports/modelli/rete_contesti_2026-09-27/RISULTATI.md`). Una validazione sulle linee viste sceglie un modello troppo addestrato per una linea nuova | Validazione annidata: dentro il training, una linea tenuta fuori a turno sceglie epoche e ampiezza |
| P14 | **La loss e le metriche premiano l'ampiezza sbagliata per la gara** | L'MSE nello spazio degli effetti vuole ampiezze piccole (0,02–0,16), il punteggio ufficiale le ha premiate grandi (fino a 1,576) per i membri DE. Il gain imparato da TransferNet tenderà a spegnere gli effetti | Separare direzione e ampiezza: valutare la direzione (coseno, PDS, segno sui geni più mossi) a ampiezza calibrata, e non trasferire il gain appreso a un invio |
| P15 | **Manca il controllo con il contesto scambiato (e quello cieco)** | È la prova che ha bocciato ogni modello di contesto del team: dove il modello batte la versione cieca, non batte quella con il contesto di un'altra linea (modello a cancelli, encoder) | Aggiungere `blind` (controlli medi) e `swap` (controlli di un'altra linea) come riferimenti, con la stessa regola |
| P16 | **Il regime CT è quasi tutto fatto di bersagli essenziali** | I bersagli con effetti in almeno due linee vengono dalla libreria essenziale, comune alle quattro linee; i non essenziali stanno solo nel K562 genome-wide, quindi finiscono nel regime J o nel C del solo K562. Nel team gli essenziali hanno energia doppia e trasferiscono di più; il pannello di gara non ne ha nessuno | Riportare i risultati stratificati per essenziale / non essenziale; aggiungere gli universi genome-wide del team (CD4, HCT116, HEK293T, KOLF2.1J: migliaia di bersagli non essenziali in più linee) |
| P17 | **Duplicare l'infrastruttura del team** | Il team ha già, sull'asse ufficiale di 18.533 geni, gli universi di dieci contesti con lo stimatore corretto, un banco C/T/J congelato con lo scambio di contesto (stadio 105, `src/vcc2026/ctj.py`) e i proxy dei banchi | Chiedere al proprietario una copia degli universi (Orion è CC-BY-NC-SA: condivisione interna, non pubblica) e usare gli split congelati dello stadio 105, così i numeri si confrontano |
| P18 | **Laboratorio e linea coincidono** | K562 e RPE1 sono di Replogle, HepG2 e Jurkat di Nadig: tenere fuori una linea tiene fuori mezzo laboratorio. I coseni misurati dal team mostrano che il laboratorio pesa quanto la linea (0,07 nello stesso laboratorio, 0,02–0,03 fra laboratori) | Riportare a parte le linee tenute fuori con e senza l'altra linea dello stesso laboratorio nel training |

## 4. Sulle domande del §13 di Alfredo

Sono decisioni di Alfredo e del proprietario; qui un parere.
- **Correzioni prima del download:** sì a P1–P5 e al test anti-fuga; aggiungerei P13 e P15, che costano
  poco e cambiano la lettura di qualunque risultato.
- **Download:** i cinque file sono pubblici e CC BY 4.0; l'md5 di HepG2 coincide con quello registrato
  dal team. Prima di scaricare, valutare P17: gli universi del team coprono gli stessi bisogni con più
  linee e bersagli non essenziali.
- **Regola di lettura:** con le aggiunte del §2, punto 1, e con i controlli cieco e scambiato di P15.
- **Primo run:** quattro linee tenute fuori, fold 0, almeno due semi; l'esito negativo è plausibile, e
  va scritto come tale, come dice Alfredo.
