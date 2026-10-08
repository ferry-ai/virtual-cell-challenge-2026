# Audit indipendente: uso dei dati e leakage

8 ottobre 2026, VALIDAZIONE (Claude Code `8a8ca58a`). Verifica fatta da questa sessione, **senza rifare
l'ingestione** e senza usare i riassunti degli altri incarichi come prova: ogni riga cita il file o l'esecuzione da
cui viene. Tipi: **misurato** (hash, conteggi, esecuzioni di oggi), **interpretazione**, **non verificato**.

Evidenze: [audit_catena.py](audit/audit_catena.py) → [audit_catena_r2.json](audit/audit_catena_r2.json);
banco di livello A, kernel `davideferrante11/vcc-validazione-logo-8a8ca58a-r1` →
[consumption.json](banco/r1/completion/consumption.json), [parity.json](banco/r1/completion/parity.json),
[table_audit.json](banco/r1/completion/table_audit.json); [voto_singolo_rfk_r1.json](banco/voto_singolo_rfk_r1.json).

## 1. Un percorso completo, fonte → derivazione → training → previsione (misurato)

Per le quattro fonti che la release canonica r1 aggiunge al t36, confronto hash per hash fra ciò che ogni passo
dichiara di leggere e ciò che il passo prima dichiara di scrivere:

| Fonte | Banca = ingressi della derivazione | Uscita della derivazione = pin della release | Letta dal fit di produzione T1 | Letta dal banco con lo stesso sha256 | Assente dai fold del suo lignaggio |
|---|---|---|---|---|---|
| `xu2023` (HEK293) | sì | sì | sì | sì | sì (C-HEK293) |
| `tian2021_crispri` (neuroni) | sì | sì | sì | sì | nessun fold lo tiene fuori |
| `hipsci_targeted_19` (iPSC, 19 cloni) | sì | sì | sì | sì | sì (C-iPSC) |
| `tian2019_neuron` (neuroni) | sì | sì | non è in T1, per scelta | sì, nel braccio R1 | nessun fold lo tiene fuori |

**Riproduzione della previsione:** rieseguendo lo stadio 100 dalle fonti montate per contenuto, gli effetti di
produzione hanno lo stesso sha256 registrato per t36 (`08fdfd28…`), per r1 (`d7a8cb14…`) e per T1 (`28f15de7…`,
il fit di DATI-TRANSFER); la ricetta di riferimento ricostruita ha lo sha256 del t36 (`3109a6d9…`). Il codice
salvato su Kaggle coincide con il pacchetto locale ([verification.json](banco/r1/completion/verification.json)).

## 2. Dati caricati contro dati che influenzano il modello (misurato)

- **Tabelle lette senza alcun voto.** T1 legge 16 fonti; 12 hanno almeno un bersaglio del pannello. `hepg2_nadig`,
  `jurkat_nadig`, `k562_essential` e `rpe1` sono aperte e messe nel manifest, ma hanno 0 bersagli del pannello:
  non influenzano nessun effetto. «16 fonti lette» non sono 16 fonti che contribuiscono.
- **Voti e lignaggi non sono la stessa cosa.** T0: 1.523 voti sul pannello, 1.456 contando una volta ogni
  lignaggio per bersaglio; su 64 bersagli il lignaggio iPSC vota più volte (le quattro tabelle KOLF2.1J). T1:
  1.539 voti, 1.462 di lignaggio. Dei **16 voti che T1 aggiunge, 6 vengono da un lignaggio che su quel bersaglio
  non votava** (i neuroni di Tian 2021); 5 (Xu) raddoppiano HEK293, che vota già con Orion HEK293T; 5 (HIPSCI) si
  sommano a iPSC, che vota già con KOLF.
- **Lignaggi che votano:** sei in T0 (K562, CD4T, HCT116, HEK293T, iPSC, H1 su 17 bersagli), sette in T1.
- **Cellule dietro i voti nuovi**, sulle cellule dell'unità di banca: Xu 7.051 su 98.315 (7,2 %); Tian 2021 1.421 su
  32.300 (4,4 %); HIPSCI 15.824 su 1.161.865 (1,4 %); Tian 2019 18.273 su 179.174 (10,2 %). Il resto sono altri
  bersagli e cellule non assegnate, inventariati e non usati dal transfer.
- **I campioni cellulari non sono letti** da nessuno dei fit valutati (lo dichiarano anche i loro verbali).

### La centratura sul pannello e le tabelle piccole (misurato, meccanismo verificato)

Con `"common": "panel"` e gamma 1 lo stadio 100 toglie a ogni fonte la media delle **sue** righe
(`multisource.mix`, `AxisTable.common`). Una tabella con n bersagli perde quindi 1/n dell'effetto proprio di
ciascuno e riceve, col segno opposto, 1/n di quello degli altri.

| Tabella | Bersagli | Quota dell'effetto proprio tolta | In t36? |
|---|---:|---:|---|
| `tian2019_neuron` | 1 | **100 %: il voto è identicamente zero** | no (solo r1) |
| `kolf_metabolic` | 4 | 25 % | sì |
| `xu2023`, `hipsci_targeted_19` | 5 | 20 % | no (r1, T1) |
| `tian2021_crispri` | 6 | 17 % | no (r1, T1) |
| `kolf_chromatin` | 8 | 12,5 % | sì |
| `h1` | 17 | 5,9 % | sì |

Verifica numerica sul fold C-K562, dove R1 e T1 differiscono per la sola tabella di Tian 2019: l'unico bersaglio
che cambia è RFK; su **tutti** gli 11.530 geni che si muovono l'effetto è tirato verso zero, con rapporto R1/T1 fra
0,63 e 0,75 e mai fuori da (0, 1). È una contrazione pura, **qualunque cosa contenga la tabella**: la release r1
la leggeva come «un voto quasi nullo» dovuto al knockdown debole; il knockdown non c'entra. Togliere quella fonte
(T1) è corretto; lo stesso meccanismo, più attenuato, agisce però sulle altre tabelle piccole, tre delle quali
sono proprio i voti nuovi di T1, e su tre tabelle del t36.

**Interpretazione:** non è leakage, è una distorsione dello stimatore che cresce quando si aggiungono fonti con
pochi bersagli del pannello. Il contrasto T2 (media su tutti i bersagli ammessi di ogni fonte) la toglie per
costruzione, a patto che il numero di bersagli dietro ogni vettore sia dichiarato.

## 3. Duplicazioni, bulk contro singola cellula, pseudo-repliche (misurato)

- **K562 BULK e GWPS a singola cellula:** vota solo la tabella storica; `k562_gwps_sc` non compare fra i file letti
  in nessuna delle 42 esecuzioni del banco. Un esperimento, un voto.
- **CD4:** le tre condizioni votano una volta dentro `cd4_mix`; nessuna parte è letta come fonte. **H1:** train e
  val sono una tabella; nessun file `h1_test` è letto.
- **KOLF2.1J vota fino a quattro volte.** Fra `kolf_pan_genome` e `kolf_strong`, sui 55 bersagli comuni, il coseno
  mediano degli effetti è 0,67 (specifico 0,67): è la stessa linea misurata due volte, contata come due voti a
  peso 1. Fra lignaggi diversi il coseno specifico mediano sta fra 0,00 e 0,03 (K562–HCT116 0,029; HCT116–HEK293T
  0,021; CD4–K562 0,015).
- **Le fonti nuove non mostrano accordo misurabile con quelle dello stesso lignaggio:** HIPSCI contro KOLF 0,06
  (5 bersagli); Xu HEK293 contro Orion HEK293T 0,002 (5 bersagli). **Interpretazione:** con cinque bersagli la
  misura è dominata dal rumore, e fra lignaggi diversi l'accordo è basso comunque; non c'è però evidenza positiva
  che questi voti portino segnale specifico trasferibile.

## 4. Leakage nei fold (misurato dove eseguito)

- **Esclusione fisica.** In ogni fold la cache contiene solo le fonti ammesse; l'elenco dei file di cui lo stadio
  100 calcola l'hash coincide con quello atteso in 42 esecuzioni su 42 e non contiene mai una tabella del lignaggio
  escluso. Copertura: 300 bersagli su 300 in ogni esecuzione, salvo P4 nel fold C-K562 (299).
- **Gruppi del registro e lignaggi.** Il registro tiene distinti HEK293 (Xu 2023) e HEK293T (Orion): un'esclusione
  per `line_group` lascerebbe Xu fra le fonti del fold che dichiara nuova HEK293T. Il manifest esclude per
  lignaggio, con l'alias `HEK293T → HEK293` negli split esportati.
- **Statistiche apprese.** La media comune è per fonte: nei fold C nessuna statistica attraversa le fonti. Per T2
  la stessa proprietà va dimostrata sui fold (righe usate per ogni vettore, nessuna del lignaggio escluso; in J
  nessun bersaglio nascosto prima della media).
- **Testa cis.** Stimata su coppie di K562: nel fold C-K562 usa risposte del lignaggio escluso (dichiarato nel
  contratto). Sugli altri fold il confronto T0 con e senza cis dà `disc` +0,0077 (CD4T), +0,0024 (HCT116), +0,0028
  (HEK293), +0,0029 (iPSC), tutti risolti: la testa cis si trasferisce a lignaggi che non l'hanno stimata.
- **Costanti nate su punteggi e banchi** (ampiezza 1,576, cis ×2, emissione ×1,5): comuni a tutti i bracci, non
  entrano nei contrasti; i livelli assoluti dei fold non sono stime pulite.
- **T e J:** il transfer non ha previsione oltre la testa cis; nessun candidato con una componente che generalizza
  sui bersagli è arrivato alla valutazione. Regola e liste sono nel manifest; nessun confronto T/J è stato eseguito.

## 5. Pesi e memorie esterne (non verificato)

Nessun checkpoint esterno è stato valutato. MODELLI-ESTERNI dichiara pesi non acquisiti e nessuna inferenza reale;
la scheda di esposizione per lignaggio e bersaglio è richiesta dal contratto prima di qualunque confronto. Finché
manca, il contrasto K3 non è valutabile: ignoto vale non ammissibile.

## 6. Copertura D-053: prevista ed effettiva (misurato sui metadati, non rifatto)

45 unità di banca nel registro; 28 stanno dietro le fonti lette; 15 gruppi di linea in banca, 7 lignaggi con
almeno un voto in T1. KO, CRISPRa, HIPSCI genome-wide, Papalexi e Datlinger non arrivano a un trainer; 189 GB di
campioni cellulari non sono consumati. **La copertura non è completa** e nessun artefatto valutato qui lo sostiene.

## 7. Segnalazioni ai proprietari

| ID | A chi | Evidenza riproducibile | Gravità | Criterio di accettazione |
|---|---|---|---|---|
| DT-1 | DATI-TRANSFER | `verifica_voto_singolo.py` sui due file del fold; tabella del §2 | media: distorce i voti delle tabelle piccole, comprese tre fonti nuove di T1 | la ricevuta di T2 riporta, per fonte, quanti bersagli stanno dietro il vettore comune; sotto un minimo dichiarato prima la fonte non sottrae una media propria; i fold si riproducono dal banco |
| DT-2 | DATI-TRANSFER | README della banca canonica, «un voto in più, quasi nullo» | bassa: spiegazione da correggere con una nota nuova | la nota cita il meccanismo; r1 e il suo protocollo restano immutati |
| DT-3 | proprietario | `fit/dt1-01a11c34-r1/public_package/kernel-metadata.json`: kernel **pubblico** che incorpora `pert_counts.csv` e `gene_names.csv` del bundle di gara | da valutare dal proprietario: riguarda le condizioni d'uso dei file di gara, non la validità scientifica | conferma del proprietario, o kernel reso privato |
| VAL-1 | VALIDAZIONE | fold C-K562: un solo gene comune a tutti i bersagli, controllo a bersagli permutati fallito | media: la misura primaria `disc` del contratto v1 non è utilizzabile in quel fold | [emendamento v2](PROTOCOLLO_v2.md), scritto prima di ogni nuovo candidato |
| VAL-2 | VALIDAZIONE | `manifest_fold_v1.json`, `name_patterns` di HCT116 contiene `dld` | nulla sui risultati v1 (nessuna tabella DLD-1 esiste): DLD-1 è un'altra linea | tolto nel manifest v2 |

## 8. Aggiunta delle 22:42: i vettori comuni di T2

Percorso letto: fonte → kernel `dt-all-*` di DATI-TRANSFER → oggetto per fonte (`common`, `mask`,
`contributing_targets`) → `common.npz` assemblato → chiave `common` dello stadio 100 → effetti del fold.
[Verifica](audit/audit_vettori_t2.py), [esito](audit/audit_vettori_t2_r1.json); sola lettura.

| Che cosa | Esito | Tipo |
|---|---|---|
| Oggetti per fonte e loro prove, release di produzione e release `T` | 16 su 16 in entrambe: dimensione e sha256 uguali al manifest | misurato |
| File assemblati | ogni vettore e ogni denominatore uguale all'oggetto della sua fonte, in entrambe le release | misurato |
| Che cosa legge lo stadio 100 | il file trovato per contenuto; modalità `frozen` con quello sha256; i vettori del lignaggio escluso restano inutilizzati in ogni fold | misurato ([risultati di T2](RISULTATI_T2.md), §1) |
| Caricato contro influente | quattro vettori su sedici (`hepg2_nadig`, `jurkat_nadig`, `rpe1`, `k562_essential`) non entrano in nessuna previsione: le loro tabelle non hanno bersagli del pannello | misurato |
| Bersagli nascosti nella release `T` | i bersagli dietro ogni vettore sono fra il 78 e l'84 % di quelli di produzione, contro l'80 % atteso dalla regola a cinque gruppi; quindici split elencano i 66 bersagli nascosti del pannello, K562 dichiara la regola applicata prima della riduzione | misurato sui denominatori; **non** è una prova simbolo per simbolo |
| H1 | 199 bersagli dietro il vettore, con `h1_test` dichiarata unità protetta nello split; questa sessione non ha letto dati di H1 test | dichiarato dal produttore, coerente con i denominatori |
| Medie ricalcolate dalle cellule o da una tabella su tutti i bersagli | **non fatto**: servono gli input dei produttori | limite |

**Segnalazioni.** DT-1 è **chiusa per costruzione**: nessun vettore ha meno di 74 bersagli dietro un gene votato.
Nuova, **DT-4**, informativa: la media su tutti i bersagli non stima meglio la risposta comune del pannello, è la
media di un'altra popolazione di perturbazioni, e lascia negli effetti una riga comune (quota comune da 0,02 % a
0,35–0,63 %). Riproduzione: `banco/comune_t2.py` sugli effetti dei fold. Gravità bassa: nessuna misura migliora,
due secondarie peggiorano di poco. Criterio di accettazione per un fit finale di T2: effetti di produzione con
sha256 `d496a38d…0ab2`, e una dichiarazione, prima dei numeri, di quale popolazione di bersagli definisce la
risposta comune.
