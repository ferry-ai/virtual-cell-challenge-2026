# Ibrido selettivo D-056, versione 1: transfer congelato, correzione neurale regolarizzata, selettore fuori fold

**Stato: congelato** con il commit che contiene questo testo, il 4/10/2026 notte, prima di ogni training di questo
protocollo e prima di leggere qualunque sua uscita. Scritto da Claude Code, sessione `2b35612c`, programma
[R-LEAD](../../../docs/piani/strategia-scientifica.md), mandato del proprietario del 4/10 (D-056). Da quel commit regole,
soglie, bracci e linee non cambiano. Un difetto trovato dopo si corregge con un emendamento datato, scritto prima di
leggere le uscite che tocca.

## 0. Che cosa è e che cosa non è

- È il **primo candidato D-056**: `ibrido = T + w · R`. T è il transfer di riferimento, congelato. R è la correzione
  proposta da una rete addestrata sulle singole cellule. w ∈ [0, 1] è il peso deciso da un selettore parsimonioso,
  appreso su predizioni fuori fold. Con w = 0 l'ibrido è il transfer, bit per bit, anche dopo generazione e
  normalizzazione (§7).
- È un **pilot dichiarato** sul corpus cellulare a 8 gruppi della v4 (A549, H1, HepG2, Jurkat, K562, RPE1, iPSC,
  Neuron), con gli stessi stati dei pre-passi r1. Le stesse lacune del §0 del
  [protocollo v4](../rete_ancorata_v4_2026-10-03/PROTOCOLLO.md) valgono qui: le cellule di CD4T, HCT116, HEK293T, KOLF
  pan-genome e delle altre voci del catalogo non entrano. Gli aggregati di 10 gruppi entrano nelle ancore. Il pilot non
  sostituisce il percorso completo D-053 e non si presenta come addestramento su tutte le linee.
- **Non è** la v4 ribattezzata. La v4 aveva un guadagno libero e nessuna separazione della risposta comune; la sua
  correzione è entrata così com'era nelle previsioni. Qui il guadagno è fisso, la risposta comune ha una testa che non
  entra nella previsione, la correzione è penalizzata, ci sono arresti preregistrati e il peso viene da un selettore
  validato fuori fold.

## 1. Ipotesi

Esiste una parte della correzione neurale, specifica del bersaglio, che migliora il transfer su linee mai viste. Un
selettore costruito solo da informazioni disponibili per una linea nuova (supporto e concordanza delle sorgenti,
espressione del bersaglio nei controlli, ampiezza e direzione della correzione) sa riconoscere i casi in cui applicarla.
Se nessun caso è riconoscibile, il selettore sceglie w = 0 e l'esperimento lo dichiara.

## 2. Precedenti

- **S-006** (v4: ancora più correzione libera). Il meccanismo ipotizzato è che la correzione impari uno spostamento
  comune a tutti i bersagli, tipico delle linee di training. Indizio a sostegno: nel log di H1, al passo 100,
  `shift_minus_anchor_rms` valeva già 0,33 contro 0,13 dell'ancora. Differenze di disegno: (a) una testa comune per
  contesto e modalità assorbe la risposta comune durante il training, non è penalizzata e non entra mai nella previsione
  esportata; (b) guadagno fisso a 1; (c) penalità L2 sulla correzione delle sole cellule ancorate; (d) arresti
  preregistrati su discriminazione, ampiezza e componente comune, misurati su coppie di validazione interne (§5); (e)
  esportazione dello stato migliore in validazione interna.
- **S-001, S-002** (reti al posto del transfer). Qui la rete non sostituisce mai il transfer: propone una deviazione.
  Il peso è zero se il selettore non trova beneficio fuori fold.
- **S-003** (miscele a posteriori). Una miscela a peso fisso scelta dopo il test non dimostra la selettività. Qui la
  miscela fissa è un braccio di confronto. Il suo peso e il selettore si stimano su linee diverse da quella valutata
  (§6), e i due si confrontano sugli stessi sei membri.
- **S-004** (cancello effetto/nessun effetto). Il selettore è un peso fra T e T + R, stimato dopo il training da
  predizioni fuori fold. Non entra nella verosimiglianza e non toglie gradiente alla rete. Il training resta con
  `--gate-mode off` (π = 1).
- **S-005, S-007** (esposizione; correzioni dai controlli medi). Restano batch bilanciati, ricevute `exposure.json`,
  gemelli verificati e budget separati. In più c'è una ricevuta delle quote di loss effettive, senza le cellule di
  validazione. Il braccio gemello `ibrido_mean` (contesto dai soli controlli medi) misura il contributo dello stato
  cellulare a parità di dati e batch.

**Segnale precoce e arresto:** ogni 2.500 passi, sulle coppie di validazione interne (§5), la rete primaria si ferma
se per due controlli consecutivi vale almeno una di queste condizioni: il rango di discriminazione peggiora di oltre
0,05 rispetto all'ancora sola; RMS(R)/RMS(ancora) supera 1,0; la componente comune di R supera il 50 % della sua
energia. È l'arresto che sulla v4 avrebbe fermato i training dopo minuti invece che a fine corsa.

## 3. Dati, split e linee

- **Corpus e stati:** pre-passi r1 `rcell-prepass-<linea>-r1` (sha256 nel §2 della v4) per H1, HepG2, RPE1. Per Jurkat
  si usa `rcell-prepass-jurkat-r1`, lanciato alle 02:38 del 4/10 con gli argomenti dei tre precedenti; cambia solo
  `--holdout-group`. Il gruppo è escluso intero, in tutti i suoi studi. Fold nascosta: hash fold 0 di 5, come nella v4.
- **Ancore:** `anchors.py` della v4, regola `all`, medie del regime J, rango 32. Sono quelle del kernel
  `rcell-v4-anchors-r1` per H1, HepG2 e RPE1; per Jurkat le produce un kernel nuovo con lo stesso codice
  (`anchors_Jurkat_all`).
- **Ruoli delle linee, fissati ora:**
  - **sviluppo**: H1, HepG2, RPE1. Sono già lette (v4, r3); servono a costruire e validare il selettore con
    leave-one-line-out. Non sono una conferma indipendente;
  - **conferma**: Jurkat, poi K562 se quota GPU e tempo lo permettono. Su queste linee nessuna rete né selettore di
    questo protocollo è stato tarato. Il transfer su Jurkat è stato visto nel banco P3 del 2/10, ma solo sugli indici
    degli effetti e senza alcuna correzione neurale;
  - **H1 test** resta chiusa (riserva protetta).
- **Coppie di validazione interne (§5):** coppie (chiave di training, bersaglio) con almeno 40 cellule perturbate
  ammesse e un'ancora (modalità ancorata, supporto > 0). Si scelgono con sha256(`d056-val|chiave|simbolo`) < 0,08, al più
  25 per chiave (gli hash più bassi) e 600 in tutto. Le loro cellule passano nei batch ma hanno peso 0 nella loss: non
  danno gradiente. Servono solo alle guardie e alla scelta dello stato esportato.

## 4. Componenti

- **T, transfer congelato:** `transfer_all_J` della v4 (`bench_effects.py`, `lane_b.py`): la media a pesi uguali sui
  gruppi del cubo diversi dalla linea esclusa dell'effetto dello stesso bersaglio, meno la media della tabella nel
  regime J, per l'ampiezza t25 (1,576). È la definizione dell'ancora della rete.
- **N, rete D-056** (`train_cellnet.py` e `cellnet.py` di questa cartella, copie v4 con quattro opzioni):
  - `--gain-mode fixed`: lo spostamento è `ancora + Δ`, senza testa del guadagno;
  - `--common-head`: una testa `C(z_c, modalità)`, con l'ultimo strato a zero, aggiunta ai logit di ogni cellula
    perturbata nel training. Non è penalizzata e non entra nelle previsioni esportate (`eval_shifts.npz`), che usano
    `softmax(β + ancora + Δ)`;
  - `--delta-l2 0.05`: penalità `λ · media(Δ²)` sui geni misurati delle cellule perturbate ancorate. Il valore è
    scelto a priori, dall'ordine di grandezza del guadagno di verosimiglianza per gene della v4 (0,005 al passo 5.000);
  - le coppie di validazione, le guardie e lo stato migliore (§5).
  Gli altri argomenti sono quelli della v4: `--epochs 2 --batch 256 --ctrl-k 64 --min-own 8 --dim 128 --rank 128
  --lr 1e-3 --pi-floor 0.01 --seed 0 --workers 2 --roles 2 --eval-workers 3 --checkpoint-minutes 15 --delta-bound 6
  --gate-mode off --health-check-step 5000 --health-window 5 --sampler balanced --unit-buffer 2 --share-window 500
  --share-tolerance 0.02 --time-every 50 --train-budget-minutes 150 --eval-budget-minutes 90
  --reserve-export-minutes 5`, gemelli `rcell-v4-fast-{a,b,c}-r1`. Ci sono due bracci sugli stessi batch: `ibrido`
  (contesto `cells`, codice `both`, cuda:0, il primario) e `ibrido_mean` (contesto `mean`, cuda:1, il gemello senza
  stato).
- **R, correzione:** `R = s(N) − s(A)`, dove s è lo stimatore dello spostamento della v4 (`cell_data.shift` sulle
  proporzioni medie), applicato alla rete e all'ancora sola con lo stesso β. Una rete non addestrata dà R = 0
  esattamente.
- **Miscela fissa:** `T + w_fix · R`, con un solo peso per linea valutata, stimato sulle altre linee (§6).
- **Selettore:** `w = σ(b0 + Σ_k b_k · z_k)`, con cinque ingressi standardizzati calcolati senza le risposte
  perturbate della linea valutata:
  1. `log(1 + supporto)`: i gruppi sorgente che hanno il bersaglio;
  2. concordanza delle sorgenti: media dei coseni a coppie fra gli effetti per gruppo (medie J), sui geni finiti in
     entrambi; 0 se i gruppi sono meno di 2;
  3. `log(RMS(R) / RMS(T))`: l'ampiezza relativa della correzione;
  4. `cos(R, T)`: la direzione della correzione rispetto al transfer;
  5. espressione del gene bersaglio nei controlli della linea (basale log1p CPM della tabella del cubo); 0 se manca.
  Sono 6 parametri, con penalità L2 α = 1 su b1…b5 nella scala standardizzata.
  La familiarità con un bersaglio è un ingresso da validare, non una garanzia. w non è una probabilità calibrata.

## 5. Guardie, arresto precoce e stato esportato

Ogni 2.500 passi dal passo 2.500, per ogni braccio, sulle coppie di validazione con almeno 20 cellule nella finestra
dall'ultimo controllo, si calcolano lo spostamento osservato (stimatore v4 contro la media dei controlli della chiave) e
quelli previsti `s(N)` e `s(A)`, senza la testa comune. Poi:
- **discriminazione:** nelle chiavi con almeno 5 coppie, si centrano osservati e previsti sulla media delle coppie
  della chiave. Per ogni coppia i si calcola la frazione delle altre coppie j della chiave con
  `media|prev_i − oss_j| < media|prev_i − oss_i|` (0 = perfetto). Si misura `rank_N − rank_A`;
- **ampiezza:** `RMS(R) / RMS(s(A))` su coppie e geni;
- **componente comune:** per chiave, `‖media_i R_i‖² / media_i ‖R_i‖²`, mediata con peso uguale fra le chiavi;
- **beneficio:** media su coppie di `cos(N, oss) − cos(A, oss)` sui 200 geni con |oss centrato| più grande, dopo la
  centratura per chiave.

**Arresto:** il training si ferma (`stop: guard`) quando il braccio `ibrido` viola la stessa condizione in due
controlli consecutivi: `rank_N − rank_A > 0,05`, ampiezza > 1,0, oppure componente comune > 0,5. Le violazioni di
`ibrido_mean` si registrano soltanto. **Stato esportato:** per ogni braccio, lo stato del controllo con il beneficio
più alto fra quelli senza violazioni; senza controlli validi, l'ultimo stato. Si registra se quel beneficio è ≤ 0
(«nessun beneficio interno»). La linea esclusa non entra mai in queste scelte.

## 6. Selettore e miscela fissa: dati fuori fold e convalida

- **Righe:** le righe C del cubo della linea esclusa (corsia A della v4), con verità `y` (log fold change del cubo), T,
  R e i cinque ingressi. R viene da una rete che non ha visto quella linea; T dalle tabelle delle altre linee.
- **Obiettivo:** per riga, `L_r(w) = Σ_g ω_g [(T + wR − y)² − (T − y)²] / Σ_g ω_g`, con ω i pesi genici del banco
  (`gene_weight` del basale), sui geni dove T, R e y sono finiti. È quadratico in w: `a_r w² − 2 b_r w`. Il selettore
  minimizza la media di `L_r` più la penalità. La miscela fissa è `w_fix = clip(Σ b_r / Σ a_r, 0, 1)`.
- **Convalida del selettore (sviluppo, leave-one-line-out):** per ogni linea di sviluppo H si stimano selettore e w_fix
  sulle righe delle altre due e si applicano ad H. È la stima onesta del selettore su linee intere non viste, ma
  quelle linee sono già lette: è sviluppo.
- **Sistema congelato per la conferma:** selettore e w_fix stimati sulle righe di tutte e tre le linee di sviluppo,
  scritti in un file con sha256 prima di leggere qualunque uscita delle linee di conferma.

## 7. Misure e bracci

Stesso generatore (trial-01, seme 20260912), stesse cellule vere e stessi bersagli C della corsia B della v4 per le
linee di sviluppo. Per le linee di conferma: bersagli C scelti con la regola di `choose_targets.py` (150, sale
`six-member`), estratti prima di generare.

| Braccio | Effetti |
|---|---|
| `transfer` | T (`transfer_all_J`) |
| `ibrido_w0` | T + 0 · R, controllo di parità: deve dare cellule identiche a `transfer` e punteggi uguali |
| `rete` | T + R (w = 1, nessuna selezione) |
| `miscela_fissa` | T + w_fix · R |
| `ibrido_selettivo` | T + w(t) · R |
| `rete_mean`, `selettivo_mean` | gli stessi con R del gemello `ibrido_mean` (secondari) |
| `transfer_cells_J`, `transfer_prod_J` | riferimenti della v4, riportati |

- **Corsia A** (indici degli effetti sulle righe C e J del cubo): PDS, coseno, coseno specifico, rapporto MSE, segno.
  Diagnostiche: ampiezza e componente comune di R sulle righe C; beneficio medio delle righe con w > 0,5 e di quelle
  con w < 0,1; distribuzione di w.
- **Corsia B** (sei membri in scala locale): PDS, MSE, NMAE, FID, REACH, JAC e la loro media.
- **Regime J** (solo corsia A): il riferimento generico ammesso è `generic_pseudobulk` della v4 (medie delle tabelle
  senza i bersagli nascosti, dai gruppi diversi dalla linea esclusa); `rete_J` è la previsione della rete per i bersagli
  nascosti, senza ancora. È riportato separato e non entra in nessuna regola di questo protocollo.

## 8. Regole di lettura

**Sviluppo (H1, HepG2, RPE1, selettore in leave-one-line-out):**
- **contributo neurale nello sviluppo** se, nella corsia B, `ibrido_selettivo − transfer` sulla media dei sei membri
  è > 0 in almeno 2 linee su 3 e la media delle tre è > 0, **e** il peso medio sui bersagli della corsia B è ≥ 0,05;
- **selettore a zero** se il peso medio è < 0,05 su ogni linea: non è dimostrato alcun contributo neurale, anche
  quando i punteggi coincidono con il transfer;
- in ogni caso si riportano `rete − transfer`, `miscela_fissa − transfer`, `ibrido_selettivo − miscela_fissa`,
  `ibrido − ibrido_mean` e le guardie.
**Conferma (Jurkat, poi K562; sistema congelato):** `ibrido_selettivo − transfer` sulla media dei sei membri della
corsia B > 0 su ogni linea di conferma valutata, con la guardia della corsia A (PDS delle righe C,
`ibrido_selettivo − transfer` ≥ −0,02). Con una sola linea l'esito si scrive «confermato su una linea», non «generale».
**Esito negativo:** nessuna ritaratura sulle linee lette. La variante successiva parte dal meccanismo osservato, con
un emendamento o un protocollo nuovo, senza ripetere lo stesso training immutato.

## 9. Invii ufficiali (regola del proprietario del 4/10, trascritta in autorizzazioni)

- **Punteggio del banco** di un candidato: per ogni contesto, la media dei sei membri scalati della corsia B
  (colonna `avg` di `scaled_local.csv`, scala locale: replicato = 1, baseline = 0); poi la macro-media a peso uguale
  sui contesti preregistrati. **Contesti preregistrati:** H1, HepG2, RPE1 (selettore leave-one-line-out) e le linee di
  conferma valutate con il sistema congelato. **Regime:** C, cioè l'uso previsto per A/B/C, dove la ricetta di
  produzione trasferisce lo stesso bersaglio. J si riporta a parte e non entra nel punteggio.
- **Soglia:** ≥ 0,100, con risultati completi e validi su tutti i contesti preregistrati, senza leakage, valori
  mancanti o errori dello scorer. Non contano il miglior contesto, il miglior membro, il solo PDS o la sola loss.
- **Che cosa si invierebbe:** un candidato ibrido si invia solo se l'esito di sviluppo non è «selettore a zero». Con il
  selettore a zero, l'ibrido coincide col transfer e un suo invio non darebbe informazione. Il candidato inviato
  richiede un refit preregistrato qui: rete con gli stessi argomenti su tutti i gruppi del corpus pilot, nessuna linea
  esclusa; ancore `all` per i contesti di gara; selettore congelato; T = la ricetta di produzione t22/t25 per A/B/C;
  generatore e seme del t22. Prima dell'invio servono una previsione registrata con la regola di lettura e i
  controlli di PROCEDURE §1–2.
- Uno score locale non è uno score VCC ufficiale: la scala del banco locale non si trasferisce numericamente al sito.

## 10. Accettazione tecnica

Una linea è accettata se valgono le condizioni del §5 della v4 (uscita 0, gemelli verificati, nessuna cellula non di
training, esposizione passata, salute al passo 5.000, valutazione completa, ancore a regime J) e in più: nessuna
cellula delle coppie di validazione con peso diverso da 0 nella loss (`val.json`); quote di loss effettive entro
±0,02 da 1/G; `guard.json` con ogni controllo. Un arresto per guardia non rende la linea inaccettabile: è un esito,
valutato con lo stato esportato. Il controllo di parità del §7 deve passare in ogni corsia B; se fallisce, la corsia
non è valida.

## 11. Che cosa non si fa

Niente ESM2, niente corpus ampliato, niente generatore diverso. Nessuna soglia del selettore scelta guardando le
linee di conferma. Le uscite della v4 non entrano nel selettore. La riserva H1 test resta chiusa.

## 12. Emendamento del 4/10, 03:16, prima di leggere qualunque uscita di questo protocollo

I training H1 e HepG2 erano in corsa dalle 03:00 e nessuna loro uscita era disponibile. Un test sintetico di
`selector.py` (`test_selector.py`) ha mostrato un difetto della forma congelata al §4 e al §6. L'obiettivo
`media_r(a_r w² − 2 b_r w)` non è invariante di scala: con la penalità α = 1 sui coefficienti standardizzati, il
selettore resta una miscela costante qualunque siano i dati. Nel test la correzione aiuta nel 38 % delle righe,
riconoscibile da un ingresso, eppure il peso imparato era ≈ 0 ovunque. Sui dati veri a e b sono piccoli (differenze di
errori quadratici di log fold change) e la penalità dominerebbe ancora di più. La correzione è stata scelta sul solo
test sintetico, prima di ogni dato reale:
`J(θ) = Σ_r (a_r w_r² − 2 b_r w_r) / Σ_r a_r + α ‖β‖²`, con α = 0,01 e l'intercetta libera.
Sullo stesso test il selettore pesa l'ingresso giusto (coefficiente 2,62 contro |·| ≤ 0,03 degli altri), dà w medio
0,60 dove la correzione aiuta e 0,06 dove nuoce, e batte la miscela fissa fuori campione. Restano immutati gli
ingressi, la stima su righe di altre linee (§6), la miscela fissa, le regole di lettura (§8) e quella degli invii (§9).

## 13. Emendamento del 4/10, 09:50: il candidato per A/B/C, scritto prima di leggere le linee di conferma

Al momento della scrittura l'esito di sviluppo è letto («contributo neurale nello sviluppo»). Delle linee di conferma
esistono i training accettati e le righe di K562, usate solo per applicare il sistema congelato, che non ne legge l'esito.
Nessun indice, nessuna corsia e nessuna statistica di esito di Jurkat o K562 è stata aperta.

Il refit del §9, cioè la rete su tutti i gruppi senza linea esclusa, non si può eseguire con il codice attuale: il
pre-passo rifiuta sia l'assenza di una linea esclusa sia una linea esclusa senza cellule (prova su un corpus sintetico,
4/10 mattina). Il candidato per A/B/C allora **non è un refit**: usa una rete già valutata, scelta con una regola che non
guarda alcun esito, cioè il fold con più cellule di training ammesse. È il fold con HepG2 esclusa (3.970.762 cellule),
braccio `ibrido`. Il resto, fissato ora:
- **T:** gli effetti della ricetta di produzione t25 per A/B/C (stadio 100, ricetta `configs/recipes/t25.json`, cache
  r9), come preregistrato al §9;
- **R per ogni contesto di gara:** `s(N) − s(A)` della rete, con le cellule di controllo del contesto (file ufficiale
  dei controlli) e con l'ancora `all` dei bersagli del pannello: il transfer dai gruppi del cubo, medie delle tabelle nel
  regime J come nel training;
- **peso:** il selettore congelato (`esito/selector_final_r1/selector_final.json`, sha256 `00758778…`). Gli ingressi
  sono calcolati come nelle righe: supporto e concordanza dai gruppi del cubo; ampiezza e direzione di R rispetto
  all'ancora; espressione del gene bersaglio, cioè il log1p CPM medio nei controlli del contesto;
- **effetti dell'ibrido:** `T + w · R` sui geni dove T è definito; altrove come T;
- **generazione e pacchetto:** gli argomenti degli stadi 45 e 48 del t25, identici, con i soli effetti cambiati.
Un refit su tutti i gruppi resta possibile dopo una modifica del pre-passo: sarebbe un candidato diverso, con un
protocollo suo. L'invio resta soggetto al §9: punteggio di banco ≥ 0,100 su tutti i contesti preregistrati (sviluppo
in leave-one-line-out e conferma con il sistema congelato), risultati completi e validi, previsione registrata prima.
