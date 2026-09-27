# Una rete che impara come la risposta a un knockdown dipende dal bersaglio e dal contesto

27 settembre 2026, sera. Scheda [R-V2](../../docs/piani/modello-v2.md). Autore: claude2 (agent hub, esecuzione
`20260927-204227-v2-network-design-r2`), in modalità modifica e **senza poter eseguire codice**: né l'autoverifica
né l'assemblaggio dei dati sono stati eseguiti. **Proposta e codice, nessuna misura nuova.**

Etichette usate qui: **misurato** (lo riporta un file del progetto, citato), **interpretazione**, **ipotesi** (da
provare), **proposta** (una scelta di disegno). Le misure citate sono proxy contro sorgenti pubbliche, non punteggi
VCC, salvo dove è scritto «ufficiale».

## 0. In breve

- **Che cos'è (proposta).** Una rete che parte esattamente dal trasferimento di produzione e impara correzioni che
  dipendono dal bersaglio e dal contesto. Il contesto entra solo attraverso caratteristiche lette dai suoi
  controlli, con parametri comuni a tutti i contesti. All'inizio dell'addestramento la rete *è* il trasferimento
  calibrato: ogni differenza dal trasferimento viene da ciò che ha imparato.
- **Che cosa deve dimostrare, e come (proposta).** Tre cose separate, ognuna con un controllo:
  1. che batte il trasferimento su contesti tenuti fuori (contro `excl`, il trasferimento sui geni stimabili);
  2. che usa il contesto (contro sé stessa «cieca», che vede ogni contesto come il contesto medio di addestramento,
     e contro sé stessa con i controlli di un altro contesto);
  3. che prevede la **differenza** fra due contesti tenuti fuori insieme (E2), dove trasferimento e rete cieca
     danno zero per costruzione.
- **Che cosa ci si aspetta (interpretazione).** Un guadagno piccolo, e forse nullo su E2: nessun modello
  pubblicato recupera l'interazione bersaglio × contesto dai soli controlli (§1, punto 5).
- **Che cosa la falsificherebbe:** §6.4. **I comandi e che cosa caricare:** §9. **I file:** §11.

## 1. Le evidenze, e che cosa ne segue

| # | Evidenza (misurato, salvo il punto 5) | Fonte | Che cosa ne segue nel disegno (proposta) |
|---|---|---|---|
| 1 | Proiettare le risposte trasferite sui primi 20/50/150 programmi perde ovunque: Δ combinato da −0,017 a −0,041, PDS da −0,06 a −0,10; i programmi spiegano il 19–29 %, 25–38 %, 39–53 % della varianza | [atlante](../atlante_2026-09-26/RISULTATI.md), r1 e r2 | Il profilo trasferito m entra **a rango pieno** nel decoder (percorso diretto). Il rango basso compare solo come correzione additiva r, che parte da zero |
| 2 | Un vettore di contesto adattato su due contesti peggiora sempre (`compact_mlp`, +9,73 di MSE); la rete condizionata non usa il contesto (−0,001 con i controlli di un'altra linea); il lineare condizionato vale −0,016 ufficiale | [CP-0013](../../docs/checkpoints/0013-hepg2-terzo-contesto.md), [CP-0026](../../docs/checkpoints/0026-predittore-neurale-condizionato.md), [CP-0027](../../docs/checkpoints/0027-t07-punteggio-ufficiale.md) | Nessun parametro per contesto. Il contesto entra da caratteristiche dei controlli **per gene** (identificate dalla variazione fra geni dentro ogni contesto, milioni di coppie) prima che globali (identificate solo da tante osservazioni quanti contesti) |
| 3 | Togliere i geni che meno di due universi sanno stimare aiuta su 4 sorgenti su 4; pesare in più per la «quota condivisa» no | [ablazione t23](../ablazione_t23_2026-09-27/RISULTATI.md), r1 e r2 | Insieme dei geni R = geni che almeno due famiglie di addestramento misurano; fuori da R niente perdita e niente previsione. Nessun peso per quota condivisa |
| 4 | Su bersagli presi a caso l'accordo fra linee è piccolo (rapporto 0,016–0,024); l'ampiezza adattata del modello a cancelli era 0,027 e 0,022 | [atlante](../atlante_2026-09-26/RISULTATI.md); [smoke r0](../modello_contesto_2026-09-27/RISULTATI.md) | Perdita pesata con 1/(k·SE² + τ²); ampiezza iniziale calibrata ai minimi quadrati pesati; valutazione per strati di forza della risposta e con bootstrap appaiato |
| 5 | Pubblicato (verificato da grok): in quattro linee la varianza si divide in stampo di linea 27,8 %, effetto conservato 29,4 %, interazione 23,5 %, rumore 19,3 %; nessun modello recupera l'interazione dai controlli; le baseline semplici eguagliano i modelli profondi | [modello di contesto](../modello_contesto_2026-09-27/RISULTATI.md) | La prova decisiva è E2, non il punteggio; ogni braccio ha il suo controllo semplice (trasferimento, cieco, scambio) |
| 6 | A, B e C sono 10x Flex e si somigliano fra loro più che alle sorgenti pubbliche in 3' | [CP-0028](../../docs/checkpoints/0028-cd4-sorgente-flex-trasferimento.md) | Caratteristiche robuste a uno scarto per gene della piattaforma: ranghi, soglie, attività medie; in addestramento uno scarto per gene casuale sui controlli (ipotesi, con la sua ablazione) |
| 7 | Il modello a cancelli a quattro parametri esiste, con autoverifica 5 su 5; smoke r0 non decide nulla | [gated.py](../modello_contesto_2026-09-27/gated.py), [RISULTATI](../modello_contesto_2026-09-27/RISULTATI.md) | La rete generalizza i due cancelli: s (espressione del bersaglio nel contesto) e h (espressione del gene nel contesto) |
| 8 | La profondità del silenziamento spiega poco della risposta, bersaglio per bersaglio (pendenze 0,09–0,48), e niente della scala di una sorgente | [profondità](../profondita_silenziamento_2026-09-27/RISULTATI.md) | Covariata di disturbo facoltativa (`--use-depth`), mai letta dal contesto tenuto fuori |

## 2. L'architettura (proposta)

### 2.1 La formula

Per una riga i = (contesto c, bersaglio t) e un gene di risposta g:

    ŷ[i, g] = s_i · h[i, g] · m[i, g]  +  s^q_i · h[i, g] · q[i, g]  +  r[i, g]

- **m**: il profilo trasferito del bersaglio (§2.2), usato direttamente;
- **q**: lo stesso per i partner STRING del bersaglio (§2.3): è ciò che resta a un bersaglio mai misurato;
- **s, s^q**: ampiezze per (bersaglio, contesto), exp(log A + 2·tanh(·)): al più e^±2 attorno a un'ampiezza
  globale A imparata;
- **h** = 2·σ(logit) in (0, 2): un cancello per (riga, gene);
- **r**: una correzione bersaglio × gene di rango 32, il cui lato gene dipende dal contesto.

All'inizio h = 1 e r = 0 (i pesi finali sono azzerati), A e A_q sono le pendenze ai minimi quadrati sui dati di
addestramento: la rete parte dal trasferimento calibrato. Codice: `net.py`.

### 2.2 Il percorso diretto m

- Per la riga (c, t), m è la media, gene per gene, degli effetti *shrunk* del bersaglio t nelle **famiglie**
  diverse da quella di c, ciascuno centrato sulla risposta media del suo contesto (è il gamma 1 del t22). Pesi:
  il peso del contesto nel registro × l'affidabilità n/(n + 100), come `mix()` in produzione. Con i pesi del
  registro (le tre condizioni CD4 a 1/3, le due linee Orion a 1) le quattro sorgenti del t22 pesano circa come nel
  t22 (inferito: il t22 centra la media `cd4_mix`, qui si centra ogni condizione e poi si media). Il profilo m di
  ogni riga di prova è scritto nelle uscite, così il confronto «rete contro il proprio m» isola l'architettura.
- **Perché la famiglia e non solo il contesto** (interpretazione): un contesto nuovo di gara non ha fratelli fra
  le sorgenti; se in addestramento m includesse l'altra condizione CD4 o l'altra linea Orion, la rete imparerebbe
  a fidarsi di m più di quanto meriti su un contesto nuovo.
- Il gene del bersaglio e i geni entro 5 kb dal suo TSS restano fuori da m, dalla perdita e dalle previsioni: la
  testa cis li gestisce già, e i banchi la aggiungono uguale in ogni braccio.
- `pool.Phase` costruisce m sul momento da profili per (famiglia, bersaglio) calcolati una volta per fase, dalle
  sole righe visibili.

### 2.3 L'encoder del bersaglio

- **Scelta di default: ammortizzato** (proposta, migliora il suggerimento del brief). Il bersaglio è descritto da:
  1. prior statici, calcolati da `data.py` senza esiti perturbativi: media, deviazione standard e ampiezza (quota di
     contesti a ≥ 5 CPM) dell'espressione del gene bersaglio nei controlli delle sorgenti; se è sull'asse; quanti
     geni hanno il TSS entro 5 e 20 kb; il grado STRING; colonne esterne `x_*` (es. DepMap, se scaricato, §10);
  2. l'embedding del gene bersaglio come gene di risposta (condiviso con §2.5: esiste per ogni gene dell'asse);
  3. la proiezione di m e di q sugli embedding dei geni, cioè «che tipo di risposta ha questo bersaglio altrove»,
     più quattro riassunti (presenza, famiglie, copertura, ampiezza).
- **Perché non un embedding libero per bersaglio come default** (interpretazione): quell'embedding si impara dalle
  righe del bersaglio in *tutti* i contesti di addestramento, compreso quello che la riga predice; m invece esclude
  la famiglia della riga. In addestramento l'embedding vedrebbe il contesto giusto, al test no, e la rete
  imparerebbe a fidarsene troppo. Resta come ablazione (`--target-embedding`): un residuo sommato all'encoder dei
  prior, a zero all'inizio.
- **Dropout del bersaglio** (proposta): una quota delle righe di addestramento (0,2 nel regime C; tutte in T e J)
  si addestra senza m e senza embedding. Lo stesso decoder impara a predire dai prior e dai partner: è il caso dei
  bersagli nuovi, e allinea i due percorsi.
- **Partner** (proposta): per ogni bersaglio, al più 16 partner STRING fisici con punteggio ≥ 700; q è la media
  dei loro profili di famiglia, con il gene proprio di ciascun partner escluso (come `partner_effects` dello
  stadio 100), dalle stesse famiglie ammesse per m. Un bersaglio tenuto fuori (T, J) non è mai partner di nessuno.

### 2.4 L'encoder del contesto

- **Per gene** (proposta), dai controlli del contesto: livello (log1p CPM / 5), rango quantile nel contesto (i pari
  merito dividono la posizione), acceso a 1 e a 10 CPM, rango meno quello del profilo medio di addestramento
  (`drank`), un indicatore d'imputazione. Per riga, in più, `gref`: il rango del gene nel contesto meno il suo
  rango nelle famiglie da cui viene m. È il cancello h di `gated.py` (espressione del gene nel contesto rispetto
  alle sorgenti), con una forma imparata.
- **Per il bersaglio nel contesto:** gli stessi valori al gene del bersaglio, softplus(log1p 5 − livello) (il
  `soft_t` di `gated.py`) e il rango meno quello nelle sorgenti di m: è il cancello s.
- **Globale** (proposta): u_c = MLP(media degli embedding dei geni pesata da `drank`), 8 dimensioni: un'attività
  di programmi imparata. In modalità cieca vale esattamente MLP(0).
- **Perché così si identifica** (interpretazione): le funzioni per gene vedono, in ogni contesto, milioni di
  coppie (bersaglio, gene) con livelli di espressione diversi; il vettore globale vede solo tanti punti quanti
  contesti (nel registro di oggi 7 contesti CRISPRi in 4 famiglie; qualche decina con HIPSCI). Per questo il
  globale è piccolo, limitato da una tangente iperbolica, ed è la prima ablazione architetturale (§7).
- **Robustezza alla piattaforma** (ipotesi): a ogni passo di addestramento i CPM dei controlli si moltiplicano per
  exp(ε_g), ε ~ N(0; 0,5²) per gene e contesto (i geni a 0 CPM restano a 0). Ranghi e soglie da soli non bastano:
  uno scarto per gene sposta anche il rango di quel gene. L'ablazione `--platform-sd 0` dice se serve.
- **Cieca**: le caratteristiche del profilo medio di addestramento (media dei log1p CPM per famiglia, poi fra
  famiglie; `drank` = 0), come il cieco di `gated.py`. **Scambio**: i controlli di un altro contesto; m e q restano
  quelli veri.
- **Nessun dato di perturbazione del contesto tenuto fuori** entra nelle sue caratteristiche: solo i suoi controlli,
  come in gara (GENERALIZZAZIONE §3, punto 3).

### 2.5 Gli embedding dei geni

Una matrice libera G × 32, imparata da tutte le righe: ogni gene compare in ogni riga, quindi è ben identificata.
Nessun embedding precalcolato dalle risposte (in T e J conterrebbe gli esiti dei bersagli tenuti fuori).

### 2.6 Il decoder

- h: logit = b(c, g) + ψ_i · g(c, g) + κ_i · gref[i, g]. b e g vengono da un MLP sulle caratteristiche del gene
  nel contesto e sul suo embedding; ψ e κ dal tronco della riga (bersaglio, bersaglio nel contesto, u_c, riassunti
  di m e q).
- r: α_i · β(c, g), con α dal tronco e β dallo stesso MLP del gene nel contesto: è l'«interazione bersaglio × gene
  modulata dal contesto» del brief.
- Penalità piccole riportano cancelli, correzioni d'ampiezza e r verso il trasferimento (§4).

### 2.7 Dimensioni

Con i valori di default e circa 10.300 geni conservati: **circa 381.000 parametri** (calcolato sul codice, non
misurato: `train.py` stampa il numero esatto), di cui circa 330.000 negli embedding dei geni. Per confronto: 4
parametri il modello a cancelli, 231.857 e 120.385 le reti di CP-0026.

## 3. I dati (`data.py`)

- **Registro** `contesti.csv` (ricreato): `context, universe, prefix, basal, family, group, se_factor, weight,
  modality`. `family` = laboratorio e protocollo (esce intera quando un suo contesto è tenuto fuori); `group` =
  stesse cellule o donatori (le tre condizioni CD4 sono un gruppo; le due linee Orion no); `se_factor` = il k della
  varianza (2 per CD4, donatori); `weight` = peso nel profilo trasferito; `modality` = `crispri` o `ko` (A549, che
  non entra né nel training né in m se non con `--modalities crispri,ko`). Righe: K562, le tre condizioni CD4,
  HCT116, HEK293T, KOLF2.1J, A549.
- **HIPSCI** (proposta, quando sarà ingerito): una riga per linea (`family hipsci`, `group` = donatore, `weight` =
  1/numero di linee, così la famiglia vale una sorgente in m) e una per il braccio genome-scale se è stimato a
  parte; la colonna basale di ogni riga con `basal_from_sums.py`. Coppie di linee di donatori diversi sono la prova
  E2 più pulita: stesso tipo cellulare, stesso laboratorio, stesso protocollo (ipotesi).
- **Due passaggi** sui blocchi npz: il primo legge solo `targets`, `n_cells` e `raw` (righe e, per gene, quanto
  spesso ogni contesto lo misura); il secondo scrive. **Geni conservati**: quelli che almeno due famiglie misurano
  in almeno metà delle loro righe; ogni disegno di addestramento restringe ancora alle proprie famiglie (§1,
  punto 3).
- **Formato** (in `pool.py`): `raw`, `se` e `shrunk` in float16, una riga per (contesto, bersaglio); tabelle di
  righe, contesti, bersagli (con i prior e i flag pannello ed essenziale), geni, asse, controlli di tutti i contesti
  e di A, B, C (CPM); finestre cis e partner in forma compressa; `manifest.json` con gli sha256 degli ingressi e i
  byte di ogni file.
- **Dimensione** (inferito dalle righe dei manifest per il numero di geni): 91.273 righe CRISPRi (K562 9.866, CD4
  3 × 12.238, HCT116 16.438, HEK293T 17.270, KOLF2.1J 10.985) più 1.000 di A549. Con 10.286 geni conservati (il
  numero di geni stimabili del t23, un riferimento, non il valore di questa regola) i tre array pesano 5.694.720.468
  byte; con 12.000 geni 6.643.656.000. Il resto (righe, controlli, tabelle) sta sotto i 10 MB. **Il numero esatto
  lo stampa `--dry-run`**, senza scrivere nulla.
- **Leakage** (D-044). Il dataset contiene tutti i contesti; un disegno è un insieme di righe visibili. `pool.Phase`
  calcola da quelle sole: centri, insieme dei geni, profili di famiglia e dei partner, riferimento basale,
  normalizzazione dei prior. Le sue letture rifiutano una riga del tipo sbagliato (`LeakageError`): etichette e
  profili solo da righe visibili, verità solo da righe invisibili. L'autoverifica sovrascrive con rumore tutte le
  righe invisibili e controlla che tutto ciò che l'addestramento vede resti identico al bit (§6.1). Chi vuole i
  bersagli di un regime T/J fisicamente assenti dal disco usa `--exclude-targets`.
- In `data.py` nessun esito perturbativo diventa una caratteristica: se un universo ha un valore finito per un gene
  lo decide il suo stimatore dai controlli e dalla dimensione del gruppo del bersaglio, non dalla risposta del gene.

## 4. La perdita (proposta)

    L = Σ_i Σ_g w[i,g] · (ŷ[i,g] − ỹ[i,g])² / (W̄ · B)  +  1e-3 · mean(logit²) + 1e-3 · mean(Δlog s²) + 1e-2 · Σ w r² / (W̄ · B)

- ỹ = y grezzo meno la risposta media del contesto sulle sue righe visibili (lo zero dello scorer è la risposta
  media del contesto).
- w = x/(1 + x) · 1/(k·SE² + τ²), con x = 0,05 · CPM del gene nei controlli del contesto della riga (il peso log1p
  dello scorer), k il `se_factor`, τ² = 0,01 (come nel banco a cancelli). Peso 0 dove y o SE mancano, fuori da R,
  sul gene del bersaglio e nella sua finestra cis.
- W̄ = peso totale medio di una riga (calcolato all'inizio): la perdita è un errore quadratico medio pesato.
- `--strong-boost` (ablazione): le righe nel quartile alto per geni significativi del loro contesto pesano di più.

## 5. L'addestramento (proposta)

- **Due fasi.** Fase 1: si tiene fuori anche una famiglia di validazione (la mediana per righe fra le visibili; con
  meno di tre famiglie visibili nessuna), si ferma quando la sua perdita non migliora per 8 valutazioni. Fase 2:
  si riaddestra da capo su tutte le righe visibili per il numero di passi migliore. La validazione è un contesto
  nuovo come il test, per questo è una famiglia e non un campione di bersagli (in T, e con `--val-family targets`,
  bersagli).
- AdamW, lr 1e-3, weight decay 1e-4, 256 righe per passo, al più 20.000 passi, valutazione ogni 250, clip del
  gradiente a 1, dropout 0,1; semi fissi per l'estrazione dei bersagli, i passi e la rete.
- **Riproducibilità.** Su CPU due addestramenti con lo stesso seme danno previsioni identiche al bit (controllato
  dall'autoverifica). Su GPU non è garantito: CP-0026 ha visto una rete non riprodursi. Per questo ogni disegno che
  decide si ripete con tre semi (§7).
- **Memoria** (inferito): profili di famiglia e dei partner in float16 sulla GPU, circa 2 GB con i contesti di
  oggi; il dataset si legge da memoria mappata.

## 6. La valutazione

### 6.1 Autoverifica sintetica (`train.py --selftest`, su CPU, nessun file tenuto)

Un dataset piccolo nel formato vero (10 contesti in 8 famiglie, una con due condizioni dello stesso gruppo, una con
due linee dello stesso laboratorio; 360 geni, 340 bersagli), scritto su disco e riletto. Controlli, una riga
ciascuno, uscita 1 se uno fallisce:
1. il dataset si rilegge identico e i byte del manifest coincidono con i file;
2. **canarino del leakage**: con le righe tenute fuori sovrascritte da rumore, centri, geni, profili, prior, riga
   cieca, un batch di addestramento e le previsioni di test restano identici; due letture del tipo sbagliato
   vengono rifiutate;
3. m coincide con un calcolo a cicli semplici (esclusione della famiglia, pesi, arrotondamento float16);
4. **mondo con interazione** (la risposta di un gene è moltiplicata per un cancello che dipende dalla sua
   espressione nei controlli del contesto, e l'ampiezza del bersaglio dalla sua): su due contesti tenuti fuori la
   rete batte il trasferimento e la sua versione cieca (guadagno ≥ 0,05 di skill, intervallo sopra zero), e
   prevede la differenza fra i due (correlazione media > 0,1 e sopra il 97,5° percentile delle permutazioni);
   cieco e trasferimento prevedono differenza zero;
5. cieco e scambio fanno quello che dicono;
6. due addestramenti dallo stesso seme sono identici;
7. **mondo nullo** (nessuna interazione): la rete non batte la sua versione cieca oltre il rumore (guadagno ≤ 2,5
   deviazioni bootstrap + 0,005) e non perde più di 0,05 di skill sul trasferimento.

Il mondo con interazione è costruito perché la rete *possa* vincere: se fallisce lì, il codice o l'ottimizzazione
sono sbagliati. Il mondo nullo controlla che non vinca per un difetto (fuga di informazione, controllo cieco mal
costruito).

### 6.2 I disegni sui dati veri (proposta)

- **E1, regime C**, una verità alla volta, famiglia intera fuori (`--hold-out-mode family`): `k562`, `cd4_Rest`,
  `orion_hct116`, `orion_hek293t`, `kolf`. 1.000 bersagli di prova misurati nella verità e in almeno due gruppi
  visibili, fuori dal pannello e dallo schermo essenziale K562. Le righe dei bersagli di prova nei contesti visibili
  restano nell'addestramento: nel regime C il bersaglio è noto altrove, come lo saranno i bersagli di D/E/F misurati
  dalle sorgenti. Il banco a cancelli invece li toglieva dall'adattamento dei suoi quattro parametri: è una
  differenza di protocollo, dichiarata (la rete di default non ha parametri propri di un bersaglio).
- **E2**, due verità della stessa famiglia tenute fuori insieme: `orion_hct116,orion_hek293t` e
  `cd4_Rest,cd4_Stim48hr`; con HIPSCI, coppie di linee di donatori diversi.
- **J** (bersaglio e contesto nuovi, la prova principale di GENERALIZZAZIONE): `--regime J` con `k562` e con
  `orion_hct116`; i bersagli di prova e i loro vicini entro 10 kb escono da ogni contesto.
- **T** (facoltativo): `--regime T --truth k562`.
- Ogni disegno è una cartella di uscita; il braccio di rete e i controlli (cieco, scambio, m, q) escono dallo
  stesso modello, quindi i confronti sono appaiati.

### 6.3 Le misure

- **Primarie:** `score_pred.py`, gli stessi proxy del banco a cancelli sugli stessi bersagli: PDS nello spazio degli
  effetti; PDS e nMAE attraverso il modello di profilo del trial-01 e uno pseudobulk di 400 cellule (basali A/B/C, 3
  semi); Δ = 0,36·ΔPDS_gen − 0,27·ΔnMAE_gen con bootstrap appaiato; su tutti i bersagli e sullo strato forte (quartile
  alto di geni con |Z| ≥ 3 nella verità). Nel regime C i riferimenti sono ricostruiti come nel banco (`transfer` e
  `excl` dalle sorgenti di produzione); in J e T, dove gli esiti dei bersagli di prova sono nascosti, il riferimento
  è il ripiego dello stadio 100 (0,1 × partner + testa cis) e la sola testa cis.
- **Secondarie:** `metrics.json` di `train.py`: skill pesata, coseno, discriminazione fra i bersagli di prova, E2;
  diagnostica nello spazio degli effetti, non la regola.

### 6.4 Regola proposta (da registrare prima di eseguire, come per il modello a cancelli) e che cosa falsificherebbe la rete

Regola, sul Δ combinato di `score_pred.py`:
- **uso del contesto (E1):** rete − cieca positivo su almeno 4 delle 5 verità, intervallo sopra zero su almeno 2,
  nessun intervallo interamente sotto −0,002;
- **candidato (E1):** rete − `excl`, stessa regola;
- **E2:** per coppia, correlazione media della rete sopra zero con l'intervallo, e sopra il 97,5° percentile delle
  permutazioni; passa su entrambe le coppie, parziale su una;
- **J:** rete − partner positivo su entrambe le verità con l'intervallo sopra zero su almeno una;
- tre semi: la regola si legge sulla media delle previsioni dei tre semi, e vale solo se il segno di rete − cieca
  è lo stesso nei tre semi su almeno 4 verità su 5.

**Falsificherebbe il valore della rete** (proposta, da fissare con la regola):
1. rete − cieca ≤ 0, o con l'intervallo che contiene zero, su almeno due verità: i controlli non aggiungono nulla
   che la rete sappia usare; resta, al più, una ripesatura del trasferimento;
2. E2 alla pari con le permutazioni su entrambe le coppie: nessuna interazione bersaglio × contesto recuperata;
3. rete − `excl` ≤ 0 su almeno due verità: sul regime C la rete non vale la forma più semplice che già passa;
4. in J rete − partner ≤ 0 su entrambe le verità: nessun valore per i bersagli nuovi;
5. rete − cieca > 0 ma rete − scambio ≈ 0: il guadagno viene dalla forma dei cancelli, non dal contesto giusto;
6. segni diversi fra i tre semi: il risultato non si riproduce (il difetto di CP-0026);
7. un vantaggio solo nello strato forte e non su tutti i bersagli è un'ipotesi da replicare su bersagli nuovi, non
   un'adozione.

Nessun esito qui è un punteggio VCC: un candidato che passa diventa una ricetta solo con una previsione registrata
prima della generazione e il via del proprietario.

## 7. Ablazioni, in ordine di priorità (proposta)

1. **Cieca e scambio**: a costo zero, dallo stesso modello; decidono l'uso del contesto.
2. **Senza cancelli e senza correzione** (`--no-gate --no-inter`): resta solo l'ampiezza per (bersaglio, contesto)
   su m e q; misura quanto vale la parte per gene.
3. **Senza vettore globale** (`--no-global-context`): il sospetto principale di sovradattamento con pochi contesti.
4. **Senza correzione a rango basso** (`--no-inter`): r aiuta o toglie discriminazione (§1, punto 1)?
5. **Più contesti**, sottoinsiemi annidati sullo stesso test congelato (`--test-targets` dal primo giro): le quattro
   sorgenti del t22 → + KOLF2.1J → + HIPSCI → + A549 knockout (`--modalities crispri,ko`). È l'ipotesi «più dati,
   reti che imparano davvero»: GENERALIZZAZIONE §4 chiede di non darla per scontata.
6. **Senza aumento di piattaforma** (`--platform-sd 0`).
7. **Tre semi** del braccio principale (non un'ablazione: un requisito della regola).
8. **Senza partner** (`--no-partners`), in J.
9. **Embedding libero per bersaglio** (`--target-embedding`), il suggerimento del brief.
10. **Perdita:** τ² 0,003 e 0,03; pesi dei geni piatti (`--gene-weight flat`); `--strong-boost 1`.
11. **Profondità del silenziamento** come covariata (`--use-depth`).

## 8. Collegamento allo stadio 105

- `adapter_ctj.py` espone `NetPredictor` con la stessa firma di `vcc2026.ctj.Predictor`: costruttore
  `(name, genes, contexts, basal, k, ridge, gamma, reliability_scale)`, `fit(train_sources, context)`,
  `predict(targets, context)` → (T, G) sull'asse, NaN dove non prevede; in più `predict_blind`. Costruisce un
  `Pool` in memoria dalle `AxisTable` di `training_sources` (una famiglia per etichetta di contesto), addestra per
  un numero fisso di passi e predice.
- **Che cosa servirebbe allo stadio 105** (proposta, non fatto: `scripts/` e `src/` non sono stati toccati):
  1. un modo di registrare un predittore esterno: oggi `Predictor.__init__` rifiuta nomi sconosciuti e
     `--predictors` ha le scelte fissate; per esempio `--adapter PATH:CLASSE`, caricato con importlib e usato come
     gli altri;
  2. torch dove gira lo stadio (sul portatile non c'è: Kaggle o Colab, o la ruota CPU);
  3. un terzo controllo accanto a vero e scambiato: il cieco, perché lo scambio da solo non separa «usa il
     contesto» da «forma dei cancelli»;
  4. il costo: una rete per split. Con le cache del pannello (circa 300 bersagli per sorgente) la rete ha pochi
     dati; la sua scala naturale sono gli universi;
  5. la `cd4_mix` delle cache dello stadio 98 non ha SE: l'adattatore usa la SE mediana della tabella e lo scrive
     nel log;
  6. senza coordinate e STRING (lo stadio 105 non li carica) l'adattatore esclude solo il gene del bersaglio e non
     ha partner.

## 9. Comandi, caricamento e dimensioni

Autoverifica, dove c'è torch (Kaggle, Colab):

    python reports/rete_contesti_2026-09-27/train.py --selftest

Dataset, sul portatile (prima le dimensioni, poi la scrittura, poi un controllo contro il lettore di riferimento):

    scripts\py.cmd reports\rete_contesti_2026-09-27\data.py --out C:/Users/ferra/vcc2026-data/processed/rete_contesti_r1 --dry-run
    scripts\py.cmd reports\rete_contesti_2026-09-27\data.py --out C:/Users/ferra/vcc2026-data/processed/rete_contesti_r1
    (facoltativo, in un'altra cartella) ... --check-reader 20

Su Kaggle, con il dataset caricato come `<dati>` e i file `net.py`, `pool.py`, `train.py` come `<codice>`:

    python /kaggle/input/<codice>/train.py --data /kaggle/input/<dati> --out /kaggle/working/e1_k562 --hold-out k562
    python /kaggle/input/<codice>/train.py --data /kaggle/input/<dati> --out /kaggle/working/e1_cd4 --hold-out cd4_Rest
    python /kaggle/input/<codice>/train.py --data /kaggle/input/<dati> --out /kaggle/working/e1_hct116 --hold-out orion_hct116
    python /kaggle/input/<codice>/train.py --data /kaggle/input/<dati> --out /kaggle/working/e1_hek293t --hold-out orion_hek293t
    python /kaggle/input/<codice>/train.py --data /kaggle/input/<dati> --out /kaggle/working/e1_kolf --hold-out kolf
    python /kaggle/input/<codice>/train.py --data /kaggle/input/<dati> --out /kaggle/working/e2_orion --hold-out orion_hct116,orion_hek293t
    python /kaggle/input/<codice>/train.py --data /kaggle/input/<dati> --out /kaggle/working/e2_cd4 --hold-out cd4_Rest,cd4_Stim48hr
    python /kaggle/input/<codice>/train.py --data /kaggle/input/<dati> --out /kaggle/working/j_k562 --regime J --hold-out k562
    python /kaggle/input/<codice>/train.py --data /kaggle/input/<dati> --out /kaggle/working/j_hct116 --regime J --hold-out orion_hct116
    (i tre semi: stessi comandi con --seed 1 e --seed 2 e cartelle nuove; le ablazioni: i flag del §7)

Punteggio, sul portatile, per ogni cartella scaricata:

    scripts\py.cmd reports\rete_contesti_2026-09-27\score_pred.py --run <cartella> --out <nuova cartella> ^
        --universe k562=<dir> --universe cd4_mix=<dir CD4> --universe orion_hct116=<dir> --universe orion_hek293t=<dir> ^
        --universe cd4_Rest=<dir CD4> --universe cd4_Stim48hr=<dir CD4> --universe kolf=<dir>

Che cosa caricare e quanto pesa:
- **Dati:** la cartella scritta da `data.py`, intera (inferito: 5,6–6,7 GB secondo i geni conservati; il numero
  esatto da `--dry-run`, e dopo la scrittura nel `manifest.json`).
- **Codice:** `net.py`, `pool.py`, `train.py` (sotto i 150 KB in tutto).
- **Uscite di un disegno** (inferito): per contesto di verità un `pred_<contesto>.npz` con cinque matrici
  1.000 × 18.533 in float32, 370.660.000 byte prima della compressione; i checkpoint circa 1,5 MB ciascuno.

## 10. Limiti, cose non verificate, richieste

- **Nulla è stato eseguito.** Il codice è stato scritto e riletto, non fatto girare: il primo passo è
  l'autoverifica. Se fallisce, il resto non si esegue.
- **Assunzioni sul formato controllate sul codice, non sui file** (i dati del portatile non erano leggibili da qui):
  chiavi degli npz e nomi dei blocchi da `k562_universe.py`, `cd4_universe.py`, `orion_universe.py`,
  `kolf_effects.py`; lettura di STRING da `vcc2026.priors`. `data.py --check-reader` confronta le righe scritte con
  `atlas_bench.Universe`.
- **Osservazione** (misurato): il `manifest.json` di `universe_a549_2026-09-27_me1`
  (`reports/universo_nuovi_2026-09-27/a549_me1/manifest.json`, riga 6) dice `"line": "KOLF2.1J"`: è la costante
  `LINE` di `kolf_effects.py` (riga 78) rimasta nel manifest di A549. L'etichetta è sbagliata; i dati no, per quanto
  se ne sa.
- **Non implementato:** attività di programmi da insiemi di geni (GO locali) come caratteristiche di contesto;
  uno scarto Flex/3' per gene stimato davvero (VIPerturb-seq lo permetterebbe); la testa cis dentro la rete; una
  previsione della profondità per un contesto nuovo.
- **Richieste di dati** (servono il via del proprietario, dimensioni dai rapporti del 26 e 27 settembre):
  - DepMap `CRISPRGeneEffect.csv` (428.678.699 byte) ed espressione 26Q1 (305 MB): prior dei bersagli `x_*`
    (co-essenzialità, indice di housekeeping);
  - CORUM 5.1 (26,4 MB): complessi, per i prior e per raggruppare i bersagli nei fold;
  - VIPerturb-seq (oggetto filtrato genome-wide 3,6 GB): K562 in Flex, un ponte di chimica sulle risposte;
  - il dataset completo della VCC 2025 (H1), ora pubblico: un contesto in più (dimensione da verificare).
- **Righe da aggiungere fuori da questa cartella** (non toccate qui): una voce in `docs/REGISTRO.md` e una in
  `reports/CLAUDE.md` per questa cartella; una voce «Dati» per il dataset quando sarà scritto.

## 11. I file di questa cartella

| File | Che cosa fa |
|---|---|
| `DISEGNO.md` | questo documento |
| `contesti.csv` | il registro dei contesti (ricreato dal primo tentativo, con `weight` e `modality` in più) |
| `data.py` | assembla il dataset dagli universi e dalla tabella dei controlli (locale, importa il progetto) |
| `pool.py` | formato del dataset, scrittore a flusso, lettore, e le viste senza fughe (`Phase`) |
| `net.py` | la rete in PyTorch, senza import del progetto |
| `train.py` | disegni, addestramento, previsioni, diagnostica, `--selftest` |
| `score_pred.py` | i proxy del banco a cancelli sulle previsioni di una cartella di uscita (locale) |
| `adapter_ctj.py` | l'adattatore per lo stadio 105 |
