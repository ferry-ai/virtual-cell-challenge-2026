# Rete cellulare ancorata al transfer: protocollo del pilot

**Stato: congelato** con il commit di questo testo, il 3/10 verso le 16:10 CEST, prima di ogni training. La bozza è
del 3/10 dopo le 14:40 (ora letta con `date`), scritta da Claude Code, sessione «R-LEAD implementazione vcc2026»
(`22d21f`), programma [R-LEAD](../../../docs/piani/strategia-scientifica.md). Da questo commit le soglie non
cambiano.
- Il congelamento viene dopo la lettura delle miscele: l'esito è nel §8.
- La revisione chiesta a Codex, supervisore dalle 15:47, non era arrivata. Le sue osservazioni, se arrivano prima
  della lettura dei risultati, diventano emendamenti registrati, come nel pilot r3. Il congelamento è anticipato
  perché un limite di spesa dell'account ha fermato claude2 alle 16:01 e può fermare questa sessione: i training
  su Kaggle continuano anche senza di essa.

La decisione del proprietario che motiva il pilot è al §11 del
[protocollo del pilot r3](../rete_cellulare_2026-10-03/PROTOCOLLO.md).

## 1. Domanda

Una rete addestrata sui conteggi delle singole cellule, che parte dal transfer del banco e impara solo una correzione,
fa meglio del transfer sulle linee escluse intere?

Il pilot r3 ha misurato due fatti:
- la rete che prevede da sola lo spostamento resta molto sotto il transfer: PDS da 0,52 a 0,61 contro 0,87–0,97 in
  corsia A, e locale a sei membri da −0,39 a −0,24 contro 0,22–0,25 in corsia B;
- le cellule di controllo della linea portano informazione oltre il loro profilo medio (Q1 passata, +0,014).

Qui il punto di partenza è il transfer stesso. La rete deve solo imparare dove e come correggerlo.

## 2. Modello

Per una cellula del contesto *k* (linea *L*), perturbata sul bersaglio *t*, i logit delle proporzioni attese sono

    logit = β_k + g_θ · a(L, t) + Δ_θ(controlli di k, t, a(L, t))

- **β_k** è la baseline dai controlli del contesto, come nella versione 2.
- **a(L, t)** è l'**ancora**: il transfer t25 del banco (`group_mean`, `combine_groups`, ampiezza 1,576, le medie di
  tabella della linea esclusa *H*). Le sorgenti sono i gruppi del corpus cellulare tranne *L* e *H*; per le righe di *H*
  in valutazione, i gruppi tranne *H*. È esattamente il `transfer_cells` della corsia A, senza la tabella VIPerturb
  perché le sue cellule non sono nel corpus.
- Per una cellula di training della linea *L* l'ancora non usa mai *L* né *H*. Dove nessuna sorgente ha il bersaglio,
  l'ancora vale 0 e un indicatore lo dice alla rete. I bersagli nascosti (J, fold 0) e i T non hanno ancora.
- L'ancora vale solo per le cellule **CRISPRi**, la modalità degli effetti del banco. Le cellule CRISPRa (Norman in
  K562, Tian nei neuroni) e KO (A549) si addestrano senza ancora, come in r3: un'ancora CRISPRi potrebbe puntare nel
  verso opposto, e il guadagno non può cambiare segno.
- **Δ_θ** è la correzione: la rete della versione 2 (stesso contesto, stessi codici del bersaglio, stessa testa a
  rango 128). Tre cose cambiano:
  - il tronco riceve in più la proiezione dell'ancora sulle 32 direzioni geniche principali delle ancore di training,
    il numero di sorgenti e l'indicatore;
  - lo strato d'uscita parte da zero, quindi al passo 0 la rete coincide con il transfer;
  - la correzione è limitata a 6·tanh(·/6).
- **g_θ** è un guadagno scalare per cellula, cioè un'ampiezza della risposta per contesto e bersaglio: vale
  1 + tanh(·) dal tronco, con la testa a zero, quindi parte da 1 e resta fra 0 e 2. È la correzione più semplice che il
  transfer non può fare: la stessa risposta più forte o più debole in una linea.
- **Niente miscela** (`pi` = 1), come r3.

Le ancore sono calcolate da un kernel CPU separato a partire dal cubo `rlead-bench-cube-r2` e dagli stati dei pre-passi
r1. Il training le legge verificandone lo sha256 e controlla che nessuna riga usi la propria linea o *H* tra le sorgenti.

## 3. Dati

**Primo passo (questo pilot):** lo stesso corpus, gli stessi pre-passi r1 e gli stessi batch di r3, sulle stesse tre
linee escluse intere: H1, HepG2 e RPE1. Così la differenza da r3 è solo l'ancora.

**Secondo passo:** il corpus ampliato dalla sessione d'ingestione (claude2), quando sarà pubblicato e verificato, con
la stessa ricetta e la stessa regola. Le linee nuove possono entrare solo come linee di sviluppo dichiarate prima del
training. La riserva resta chiusa: test H1 2025 e D/E/F.

## 4. Bracci

Tutti in un solo processo per linea esclusa, sugli stessi batch e dagli stessi pesi.

| Braccio | Correzione | Ruolo |
|---|---|---|
| `ancorata` | contesto `cells`, codice `both` | il candidato |
| `ancorata_mean` | contesto `mean`, codice `both` | gemello senza informazione di stato |
| `ancora_sola` | nessuna (g = 1, Δ = 0), solo in valutazione | l'ancora passata per lo stesso stimatore della rete |

Gli argomenti sono quelli di r3: `--epochs 2 --budget-minutes 180 --batch 256 --ctrl-k 64 --min-own 8 --dim 128
--rank 128 --lr 1e-3 --gate-mode off --delta-bound 6 --health-check-step 5000 --health-window 5 --seed 0 --workers 3
--eval-workers 3`. Si aggiungono le ancore (`--anchors`, rango di proiezione 32). Training su GPU T4×2
(`davideferrante11`).

## 5. Misure

**Corsia A** (`bench_effects.py`): le righe C e J del cubo della linea esclusa. Contiene:
- `ancorata`, `ancorata_mean` e `ancora_sola`;
- `transfer_cells`, che coincide con l'ancora;
- `transfer_all` e la risposta generica, riportati.

**Corsia B** (copia di `lane_b.py`): gli stessi bersagli e le stesse cellule vere di r3, con i sei membri in scala
locale.
- Effetti nel generatore trial-01: `ancorata_shift`, `ancorata_mean_shift` e `ancora_sola_shift`. Il transfer entra in
  due definizioni: quella della corsia A (`transfer_cells`, senza VIPerturb) e quella usata dalla corsia B r3
  (`transfer_cells_r3`, gruppi interi), per continuità.
- Le cellule generate dalla rete ancorata, campionate dalla NB.

## 6. Regola (si congela con il commit)

**Accettazione tecnica:** quella di `decide_pilot.py`, cioè:
- codice di uscita 0, `verify.json`, non-contaminazione, quote della loss entro ±0,02;
- prova di salute al passo 5.000;
- valutazione completa.

In più, il controllo delle ancore deve passare: nessuna sorgente uguale alla linea della riga o a *H*, e nessuna ancora
per bersagli J o T. Una linea senza accettazione rende il confronto **incompleto**, non fallito.

**Primaria, corsia B:** Δ = `ancorata_shift` − `transfer_cells` (definizione della corsia A) sulla media locale dei
sei membri. Passa se Δ > 0 in almeno 2 linee su 3 e la media delle tre è > 0. La corsia B è la primaria perché in
corsia A il PDS del transfer è vicino al tetto (0,87–0,97), mentre i sei membri sono la misura della gara.

**Guardia, corsia A:** la media sulle tre linee del PDS delle righe C, `ancorata` − `transfer_cells`, deve essere
≥ −0,02. Se la primaria passa e la guardia no, l'esito è «non concluso». Una correzione che peggiora gli effetti medi
non si espande.

**Secondarie, riportate senza soglia:**
- `ancorata` − `ancora_sola` in entrambe le corsie: il valore della correzione appresa, a parità di stimatore;
- `ancorata` − `ancorata_mean`: lo stato delle cellule nella correzione;
- le cellule generate contro le cellule vere;
- le righe J;
- i membri uno per uno.

**Esito e passo dopo:**
- Se l'accettazione è completa e la primaria e la guardia passano, la stessa ricetta va sul corpus ampliato (§3), con la
  stessa regola, e poi alla conferma del programma (P5).
- Se fallisce, nessuna ritaratura sulle stesse tre linee, che da quel momento sono lette. Un nuovo candidato richiede un
  nuovo protocollo.

**Attese, ipotesi e non prove:**
- al passo 0 `ancora_sola` riproduce il transfer, salvo la normalizzazione dello stimatore;
- la correzione resta piccola sulle righe C;
- la primaria è incerta;
- l'esito delle miscele, scritto qui al congelamento, è l'unico indizio disponibile prima.

## 7. Cosa non cambia da r3

Corpus, pre-passi, gruppi di linea, fold nascosta, pesi della loss, serbatoio dei controlli, stimatore dello
spostamento, cubo e metriche del banco. Il codice è una copia della versione 2 in questa cartella (versione 3); gli
originali restano intatti.

## 8. Che cosa si sapeva al congelamento

- **Miscele** ([lettura](../rete_cellulare_2026-10-03/esito/miscele_r3/LETTURA.md)): `blend_50` supera il transfer in
  1 linea su 3, con media −0,056, quindi **non promettente**. Lo spostamento della rete r3 non porta un segnale
  complementare ai sei membri. L'attesa a priori per la primaria è quindi bassa. La rete ancorata è comunque
  un'ipotesi diversa: impara la correzione partendo dal transfer.
- **Ancore** (kernel `rcell-anchors-r1`, [lancio](lancio_anchors_r1.json); manifest nella radice dati,
  `out_anchors_r1/`). Tutti i controlli passano: nessuna sorgente uguale alla linea della riga o a *H*, nessun
  bersaglio nascosto con ancora, solo CRISPRi, VIPerturb escluso.

  | Linea esclusa | Righe in tutto | Righe di valutazione C | Righe C della corsia A |
  |---|---:|---:|---:|
  | H1 | 9.270 | 73 | 72 |
  | HepG2 | 9.078 | 1.743 | 1.743 |
  | RPE1 | 9.122 | 1.789 | 1.789 |

  Delle 151 righe C di H1 nella valutazione della rete, le 78 senza fonti nel cubo restano senza ancora: per loro
  la rete ancorata coincide con una rete senza ancora. La regola legge le corsie A e B, i cui bersagli hanno il
  supporto del transfer per costruzione.
- **I training della v3 condividono con r3** pre-passi (`rcell-prepass-<linea>-r1`), dataset, glob, argomenti e
  seme. Cambiano il codice v3 (`rcell-anchored-code-r1`, dal commit `211402e`), le ancore e i due bracci del §4.
