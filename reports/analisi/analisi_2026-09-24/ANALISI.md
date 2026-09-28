# Analisi dello stato, di ciò che non vediamo e dei passi futuri — 24 settembre 2026

- **Scritta:** 24 settembre, intorno alle 15:30 UTC, **prima** dei punteggi di t16 e t17 (gli invii
  partono alle 00:05 UTC del 25). Le previsioni del §4 valgono solo per questo: sono registrate
  prima del risultato.
- **Redatta da:** agente (Claude), su richiesta del proprietario in chat («analizza lo stato
  attuale del progetto e cerca nei dati cose che non stiamo vedendo o che stiamo interpretando
  male, pensa anche ad implementazioni future»). Revisione umana: no.
- **Che cosa non è:** non è un checkpoint e non cambia decisioni. Le correzioni proposte al §3
  passano dal proprietario.
- **Materiale usato:**
  - i report già nel repository, citati punto per punto;
  - il codice dello scorer `cell-eval2` 0.16.0, scaricato da PyPI il 24 settembre. È la versione
    del contratto (`reports/scorer/vcc2026_contract.json`); non ho confrontato i file con quelli
    installati sul portatile. I riferimenti al codice sono nella forma `cell_eval2/<file>:<riga>`;
  - i conti sono in `calcoli.json`, in questa cartella, con i file da cui vengono i numeri.
- **I dati grezzi non erano disponibili a questa sessione.** Controlli, cache delle sorgenti e
  previsioni stanno sul portatile, quindi nessun numero qui è ricalcolato dalle cellule.

## 0. In breve

1. **Dove stanno i punti mancanti.** Il divario dalla mediana delle prime dieci del 16 settembre
   è di 0,131 punti. Il PDS, il membro che oggi ci porta, ne vale solo 0,026, il terzo per
   grandezza. Prima vengono la MSE (0,042) e il `reach` (0,027); poi la fedeltà (0,022). §1.
2. **La MSE non è morta: è morta per i nostri effetti.** Tutte le prime dieci stanno sotto la
   base (grezzo 0,65–0,85). Noi stiamo sopra 1,0, che nello scorer vuol dire «peggio che
   prevedere il controllo». Due stime indipendenti dicono la stessa cosa: nello spazio della MSE
   i nostri effetti trasferiti sono quasi ortogonali alla verità (coseno intorno a 0,04). Nessuna
   ampiezza uniforme li porta sotto la base. §3.1.
3. **Il guadagno dell'ampiezza viene soprattutto dal coprire gli artefatti del generatore**, non
   da effetti «più giusti».
   - A effetto nullo il generatore di trial-01 fa 429–675 chiamate per bersaglio, per l'81% «in
     su»: sono il 57–67% delle chiamate del t15.
   - La scomposizione della fedeltà dà per quelle chiamate una precisione di segno di circa
     0,44, cioè sotto il caso; per le chiamate portate dagli effetti circa 0,53, come lo stadio
     103.

   Il rimedio diretto è togliere l'artefatto, non raddoppiare ancora. §3.2.
4. **Il t14 non contraddice il punto 3.** La mediana di chiamate del t14 era 136–218. Nel
   contesto A di validazione i geni significativi di riferimento sono in media circa 336 per
   bersaglio (docstring dello scorer). Il t14 stava quindi con buona probabilità nel regime che
   paga il silenzio. §3.3.
5. **Una frase di D-042 attribuisce all'ampiezza un effetto del generatore.** «Nel t14 alzare
   l'ampiezza ha abbassato `pds_cosine`» confonde due fattori cambiati insieme. Dentro
   `ControlModel`, dal t02 al t03, l'ampiezza doppia aveva alzato il PDS. §3.4.
6. **Tre scelte della ricetta non sono mai state provate da sole:**
   - effetti grezzi invece che ristretti, scelti per parità con trial-01;
   - γ = 1, deciso da una regola di spareggio;
   - gli stessi pesi per A, B e C.

   Per γ, l'unica misura di segno che abbiamo (stadio 103) preferisce γ = 0. §3.5–3.7.
7. **Le docstring dello scorer contengono misure degli organizzatori sui dati di validazione**,
   che il progetto non ha ancora raccolto: quanti geni significativi, quanto pesa il rumore,
   quanto vale il gene bersaglio. Tabella al §2.2.

## 1. Dove stanno i punti

**Misurato.** Mediana delle prime dieci righe della classifica del 16 settembre
(`reports/leaderboard_2026-09-16/rows.csv`) contro gli scalati ufficiali del t15
(`reports/trial_2026-09-24/status_U1K3SZuq7w5cef9lBKsn.json`). Divario in punti del complessivo,
cioè diviso per sei:

| membro | prime dieci, scalato (grezzo) | t15, scalato | divario in punti |
|---|---|---|---|
| MSE | 0,252 (0,749) | 0 (tosato) | **0,042** |
| `reach` | 0,232 (0,284) | 0,067 | **0,027** |
| PDS | 0,761 (0,843) | 0,607 | **0,026** |
| fedeltà | 0,011 (0,516) | −0,119 | **0,022** |
| `nmae` | 0,165 (0,901) | 0,084 | 0,013 |
| Jaccard | 0,008 (0,033) | 0,006 | 0,000 |

La somma, 0,131, più il t15 (0,1075) fa 0,238, contro una mediana delle prime dieci di 0,240.

**Interpretazione.** Dal 16 settembre il PDS è salito da 0,687 a 0,774 e non è più il divario
maggiore. I tre membri su cui le altre squadre prendono punti e noi no sono MSE, `reach` e
fedeltà: sono quelli che leggono le cellule generate gene per gene. La fotografia ha otto giorni;
rileggere la classifica non costa quota.

## 2. Che cosa misura lo scorer, letto nel codice

### 2.1 Cinque punti che cambiano la lettura dei nostri numeri

- **La base non è «nessuna abilità».** È una previsione oracolo: la risposta media delle
  perturbazioni vere del contesto, emessa uguale per tutti i bersagli
  (`cell_eval2/baseline.py:1-14`, «an ORACLE comparator»). Uno scalato 0 vuol dire «bravo quanto
  chi conosce la risposta media vera». Sulla fedeltà la base vale 0,506 / 0,523 / 0,509 in A / B
  / C (`cell_eval2/competition.py:329`).
- **MSE.** Si calcola sui pseudobulk in spazio `log1p(5e4 · frazione)`. Toglie il gene bersaglio
  e corregge il rumore di campionamento con un jackknife. Si aggrega come rapporto di somme, quindi
  pesano i bersagli con gli effetti veri più grandi. **1,0 vuol dire «ha previsto il
  controllo»** (`cell_eval2/metrics/delta.py:1023` e `:1170`). Noi abbiamo 1,13–1,58, la base è
  circa 0,99.
- **PDS.** È il coseno fra il delta previsto (previsione meno controllo **vero**) e i delta veri,
  senza i 300 geni del pannello (`cell_eval2/metrics/discrimination.py`). Il coseno non vede la
  scala: se il delta previsto fosse esattamente `a · effetto`, l'ampiezza non conterebbe nulla.
  Conta perché il delta previsto contiene anche una parte che non scala con `a`: il rumore di
  campionamento delle 400 cellule generate, ed eventuali scarti sistematici del generatore.
  Alzare `a` ne riduce il peso relativo, e questo guadagno satura.
- **Fedeltà.** Vale `k / max(n_pred, n_conf)`. Il numeratore conta **tutte** le nostre chiamate il
  cui segno coincide con quello del log fold change vero, anche quando il gene non è significativo
  nel riferimento (`cell_eval2/metrics/direction.py`, `_components` e `_direction_frame`). Quando
  chiamiamo più geni di `n_conf` è una precisione di segno su tutte le chiamate, artefatti
  compresi.
- **Reach.** Si guardano solo i geni significativi nel riferimento, ordinati per il **nostro**
  `p_adj`. Vale la profondità massima in cui almeno il 90% dei segni è giusto
  (`cell_eval2/metrics/direction.py:905-985`). Conta la purezza della testa della nostra
  classifica.

### 2.2 Misure degli organizzatori sui dati di validazione

**Misurato dagli organizzatori, riportato nelle docstring; non ricalcolato da noi.**

| fatto sui contesti A / B / C | valore | fonte |
|---|---|---|
| coppie significative nel riferimento, contesto A, gene bersaglio escluso | 100.771, cioè ≈ 336 per bersaglio in media | `cell_eval2/de.py:460` |
| bersagli con almeno 10 geni significativi (gli altri escono da `nmae`) | 272 / 229 / 218 su 300 | `cell_eval2/metrics/de.py:646` |
| bersagli senza profondità utile per un errore (N_conf < 10) | 12–30% | `cell_eval2/metrics/direction.py:922` |
| N_conf minimo in A | 4 | `cell_eval2/metrics/direction.py:977` |
| il gene bersaglio è il gene che si muove di più | nel 57–66% delle perturbazioni | `cell_eval2/metrics/delta.py:311` |
| quota del rumore (jackknife) nella distanza grezza | 46–55% | `cell_eval2/metrics/delta.py:1041` |
| quota della distanza dovuta al solo gene bersaglio | 5,5% / 5,0% / 3,2% | `cell_eval2/metrics/delta.py:1173` |
| precisione di segno del replicato sui geni significativi | 0,956 / 0,939 / 0,949 | `cell_eval2/metrics/direction.py:914` |
| `reach` di un predittore a segno casuale | 0,043 / 0,068 / 0,082 | `cell_eval2/metrics/direction.py:929` |

**Interpretazione.**
- La distribuzione di `n_conf` ha una coda lunga: una media di ≈ 336 con il 12–30% dei bersagli
  sotto 10 vuol dire che una parte dei bersagli muove centinaia o migliaia di geni. Sono quelli
  che pesano nella MSE (rapporto di somme), e per la fedeltà sono in regime di copertura se ne
  chiamiamo meno di `n_conf`.
- B e C hanno molti più bersagli deboli di A: 71 e 82 contro 28.
- La stima «mediana di n_conf 30–50» usata in `reports/dispersion_2026-09-23/PRIMA_DEI_RISULTATI.md`
  non è smentita, ma la media è un ordine di grandezza sopra.

## 3. Che cosa non stiamo vedendo, o leggiamo male

### 3.1 La MSE non è morta: i nostri effetti non hanno quasi proiezione sulla verità

**Misurato.** Grezzi ufficiali della MSE, stesso generatore e stessa miscela: t11 a 0,197 vale
1,129, t15 a 0,394 vale 1,579. Alla stessa ampiezza 0,197 la MSE scende quando si aggiungono
sorgenti: K562 da solo (t10) 1,297, K562 + CD4 (t08) 1,152, più HCT116 (t11) 1,129.

**Interpretazione.** Il modello più semplice è quadratico nell'ampiezza:
`MSE(a) = m0 + P·a² − 2·C·a`, dove `m0` è il valore a effetto nullo, circa 1 per il generatore
di trial-01. Il suo rumore di pseudobulk è anzi un po' più basso di quello delle cellule vere:
0,00066 contro 0,00081, `reports/generator_null_2026-09-17/summary.json`. Con `m0 = 1`, dai due
punti:
- `P = 4,14` e `C = 0,080`;
- coseno effettivo fra effetti previsti e veri, `C/√P`: **0,039**;
- ampiezza che minimizza la MSE: **0,019**, con una MSE minima di 0,998, cioè appena sopra la
  base.

Con `m0` fra 0,95 e 1,15 la MSE minima resta fra 0,95 e 1,08 (`calcoli.json`, `mse_curve`).

**Controllo indipendente, misurato.** Lo stesso numero esce dallo spazio degli effetti, senza lo
scorer: fra tipi cellulari diversi l'ampiezza ottima per l'errore quadratico è 0,008–0,05, con un
«skill» di 0,0001–0,0017 (`reports/orion_2026-09-23/r5/transfer.json`). Fra le due metà dei
donatori CD4 è 0,10, con skill 0,005 (CP-0028).

**Interpretazione.**
- Il segnale per bersaglio che trasferiamo è reale, altrimenti il PDS non sarebbe 0,77. Nello
  spazio della MSE però è piccolo rispetto al rumore che portiamo con sé. Gli effetti grezzi,
  moltiplicati per un'ampiezza uniforme, aggiungono varianza su tutti i 300 bersagli, anche dove
  non c'è niente da prevedere.
- La discesa della MSE con il numero di sorgenti (1,297 → 1,152 → 1,129) va nella stessa
  direzione: l'eccesso sopra 1 è soprattutto rumore della previsione, che la media fra sorgenti
  riduce.
- Le prime dieci hanno MSE 0,65–0,85. Con lo stesso modello vuol dire un coseno intorno a
  0,4–0,6, dieci volte il nostro. **Non ci si arriva con l'ampiezza**: serve un'informazione per
  bersaglio di altro tipo (§5, punto 7).
- Non possiamo escludere che una parte del loro vantaggio venga dal modo di emettere le cellule
  (§6).

### 3.2 L'ampiezza sta coprendo un artefatto del generatore

**Misurato.**
- Il generatore di trial-01 (Poisson intorno al profilo del contesto) a **effetto nullo** fa
  460 / 429 / 674 chiamate mediane per bersaglio in A / B / C, per l'81% «in su». Le cellule
  vere, allo stesso test, ne fanno 0 (`reports/generator_null_2026-09-17/summary.json`, braccio
  `g0` contro `real`).
- Le chiamate mediane per bersaglio sono 543 / 582 / 764 nel t11 e 804 / 730 / 1.009 nel t15
  (`reports/prediction_calls_2026-09-23/`).
- L'artefatto è quindi il 74–88% delle chiamate del t11 e il 57–67% di quelle del t15.

**Interpretazione (modello a due popolazioni, `calcoli.json`, `fidelity_decomposition`).** Se le
chiamate da artefatto hanno precisione di segno `p_a` e quelle da effetti `p_e`, i due punteggi
ufficiali danno:
- **`p_a ≈ 0,44`**, sotto il caso;
- **`p_e ≈ 0,53`**.

Il secondo numero coincide con quello che lo stadio 103 misura fra sorgenti pubbliche, 0,52–0,55
sui geni di testa (`reports/direzione_2026-09-24/direction.json`), che è un controllo
indipendente.

Ne seguono tre cose:
- la fedeltà sotto 0,5 di tutti gli invii con questo generatore (0,458–0,477) viene dalle
  chiamate artefatto, che sono sistematicamente dalla parte sbagliata;
- ogni raddoppio dell'ampiezza le diluisce, e questo spiega buona parte di +0,019 di fedeltà,
  +0,026 di `reach` e forse del PDS dal t11 al t15;
- il limite a cui tende il raddoppio è quello che si ottiene togliendo l'artefatto: fedeltà
  intorno a `p_e`, senza pagare `nmae` e MSE con ampiezze sempre più grandi.

**Ipotesi sul perché `p_a` < 0,5.** I geni che il Poisson rende «troppo pieni» sono quelli con
più eterogeneità fra cellule, cioè geni di stato. Nelle cellule perturbate vere potrebbero
muoversi di preferenza verso il basso. Le docstring dello scorer parlano di geni dalla
«direzione abituale» (`cell_eval2/metrics/direction.py:968`). Non è verificato.

### 3.3 Il t14 non chiude la questione della fedeltà

La mappa (`docs/PROGETTO.md` §0) riassume così [CP-0032](../../docs/checkpoints/0032-t14-controlmodel-fedelta.md):
«Si pensava che la fedeltà fosse governata dalle chiamate spurie […] ma la fedeltà scende». Il
checkpoint lasciava aperte due letture; il riassunto le perde.

**Misurato:**
- il t14 aveva 136 / 213 / 218 chiamate mediane (`reports/prediction_calls_2026-09-23/t14/`);
- in A i geni significativi di riferimento sono in media ≈ 336 per bersaglio (§2.2).

**Interpretazione.** Il t14 era con ogni probabilità nel regime `n_pred < n_conf`, dove la
fedeltà vale `k / n_conf` e paga il silenzio: è la seconda lettura di CP-0032, e i numeri del §2.2
la sostengono. Insieme al §3.2 il quadro coerente è questo:
- le chiamate spurie abbassano la fedeltà;
- un generatore pulito aiuta solo se chiama almeno quanto `n_conf`.

**Proposta di correzione della mappa:** riportare le due letture, non «contraddetto».

### 3.4 D-042 attribuisce all'ampiezza un effetto del generatore

D-042, «Che cosa non segue»: «che valga per `ControlModel`: nel t14 alzare l'ampiezza ha abbassato
`pds_cosine`».

**Misurato:**
- il t14 cambia **due** fattori rispetto al t08, generatore e ampiezza, come dice CP-0032 stesso;
- dentro `ControlModel`, dal t02 (× 1) al t03 (× 2) il PDS sale da 0,609 a 0,649. Anche qui con
  un secondo cambio, i bin cis presi da una tabella di coppie.

**Proposta di correzione:** scrivere che l'effetto dell'ampiezza dentro `ControlModel` non è
separato, e che l'unico indizio va nel verso opposto.

### 3.5 γ = 1 è uno spareggio, e l'unica misura di segno preferisce γ = 0

**Misurato:**
- la ricetta del t08 sceglie γ con la proxy di discriminazione: 0,6745 / 0,6782 / 0,6793 per γ
  0 / 0,5 / 1. Stanno entro 0,005, e la regola dà la vittoria al γ più alto
  (`reports/multisource_2026-09-22/PRIMA_DEI_RISULTATI.md`, secondo emendamento);
- lo stadio 103, precisione di segno media sui primi 25 geni, sorgente tenuta fuori:

  | sorgente tenuta fuori | γ = 0 | γ = 1 |
  |---|---|---|
  | HCT116 | 0,564 | 0,495 |
  | HEK293T | 0,571 | 0,541 |
  | CD4 | 0,535 | 0,510 |
  | K562 | 0,529 | 0,532 |

  (`reports/direzione_2026-09-24/direction.json`).

**Interpretazione.**
- Per il PDS γ è indifferente; per il segno, che conta per fedeltà, `reach` e `nmae`, γ = 0 non
  perde mai e in tre casi su quattro vince.
- Il vantaggio di γ = 0 fra le due linee Orion è in parte una firma comune della piattaforma
  Orion: le risposte medie di HCT116 e HEK293T correlano 0,45 (`reports/orion_2026-09-23/r5/coverage.json`),
  e i dati Flex della gara non la condividono.
- Per CD4 la correlazione con Orion è 0,10–0,15: un segnale comune fra laboratori, piccolo ma non
  nullo.

**Proposta:** un invio a un fattore, dopo quelli del §5 che valgono di più.

### 3.6 Gli effetti grezzi entrano a piena ampiezza anche dove sono solo rumore

**Misurato dal codice.** `multisource.mix` pesa le sorgenti con l'affidabilità `n/(n+100)` e poi
**divide per la somma dei pesi**. L'affidabilità decide quanto conta ogni sorgente rispetto alle
altre, ma non restringe mai la miscela verso zero:
- un bersaglio visto da una sola sorgente con poche cellule riceve il suo effetto grezzo intero,
  moltiplicato per l'ampiezza;
- per il bersaglio mediano del t15 i pesi valgono CD4 0,43, K562 0,29, HCT116 0,28
  (`calcoli.json`).

**Misurato dalla storia della ricetta.** La scelta degli effetti grezzi viene dal secondo
emendamento del 22 settembre (`reports/multisource_2026-09-22/PRIMA_DEI_RISULTATI.md`). Serviva a
cambiare un solo fattore rispetto a trial-01, e non è mai stata messa alla prova. La frase
«lo shrinkage per gene è quasi inattivo» (CP-0004) è stata misurata:
- con un altro stimatore, un prior normale unico e non `z_shrink`;
- con un'altra metrica, la MSE su log2FC in pseudobulk da K562 a RPE1.

**Indizio debole, confuso:** trial-01 (K562, `prior_sd = 4`, nessuna risposta media tolta:
`ShrunkTransfer` nel tag `archivio/pre-pulizia-2026-09-24`, `src/vcc2026/models.py`) ha MSE
ufficiale 1,231, il t10 (K562 grezzo, γ 1) 1,297, con PDS quasi uguale (0,687 contro 0,694).

### 3.7 A, B e C ricevono gli stessi effetti

**Misurato:**
- in t11, t15, t16 e t17 le tre voci di contesto della ricetta sono identiche
  (`configs/recipes/`), e i file degli effetti del t15 hanno lo stesso sha256 per A, B e C
  (`reports/trial_2026-09-24/t15_generation_diagnostics.json`, voce `support.effects`);
- l'unica informazione di contesto è il profilo di base del generatore;
- le proxy dello stadio 98 dicono che CD4 trasferisce male sulle linee epiteliali Orion:
  proxy di discriminazione 0,59–0,63, contro 0,76–0,78 di K562 (`reports/orion_2026-09-23/r5/transfer.json`);
- CD4 pesa comunque il 43% anche in B e C.

**Proposta:** pesi per contesto, per esempio CD4 alto in A e basso in B e C. Lo stadio 100 lo
permette già.

### 3.8 Identità dei contesti: B non sembra HEK293T

**Misurato** (`reports/context_fingerprints_2026-09-22/fingerprints.json`):
- **B:** femminile; CDKN2A 2.437 CPM; VIM 6.132, KRT7 2.554, KRT17 1.536; CDH1 ed EPCAM quasi a
  zero; LIN28B 0; 5p +0,95;
- **A:** maschile; CDKN2A, CDKN2B e MTAP a zero; CD3E, DNTT e TAL1 espressi;
- **C:** maschile; KRT5, TP63 e SOX2 alti; 3q +0,26.

**Ipotesi, non verificate:**
- B ha il profilo di una linea cervicale HPV-positiva, del tipo di HeLa: p16 altissimo per E7,
  niente E-cadherina, vimentina alta, guadagno di 5p. L'assenza di LIN28B, espresso in HEK293, va
  contro HEK293T;
- A somiglia a una T-ALL maschile del tipo di Jurkat;
- C somiglia a un carcinoma squamoso maschile con amplificazione 3q/SOX2.

**Interpretazione.** Se è così, nessuna linea di Orion coincide con un contesto di validazione. Il
vantaggio delle prime dieci sulla MSE non verrebbe allora da un trasferimento dalla stessa linea,
a meno di dataset che non conosciamo.

### 3.9 Il t17 cambia anche l'ampiezza dell'8,8%

**Misurato.** 0,4285 / 0,394 = 1,088, cioè 0,121 in log2. Con la pendenza dal t11 al t15 (+0,037
per raddoppio) questo da solo vale circa +0,0045, lo stesso ordine della soglia ±0,005 della
regola del t17 (`calcoli.json`, `t17_amplitude`).

L'ampiezza è stata scelta per pareggiare il q99 di |ln fc|, che è ragionevole. Il q99 però non
misura il numero di chiamate, e l'ampiezza agisce anche coprendo l'artefatto (§3.2).

**Proposta, gratis e prima del punteggio:** stadio 83 sui file di t16 e t17, già generati, e
confronto con il t15. Se il t17 chiama molto più del t15, la sua lettura è confusa con
l'ampiezza.

## 4. Previsioni registrate prima del punteggio del t16

**Proposta di lettura, non misura.** Si aggiungono alla previsione ufficiale
(`reports/prediction_t16_2026-09-24/prediction.json`) e non la sostituiscono.

| membro del t16 | previsto da questo modello | come si legge |
|---|---|---|
| MSE grezza | 3,2–3,8; 3,44 se `m0 = 1` | con i tre punti t11, t15 e t16, `m0 = M11 − Px² + 2Cx`, con `Px² = ((M16−M15) − 2(M15−M11))/6` e `Cx = (3Px² − (M15−M11))/2`, `x = 0,197`. La tabella inversa è in `calcoli.json`. Un `m0` fra 0,95 e 1,05 conferma il §3.1 |
| fedeltà | 0,49–0,51 | dipende dalle chiamate del t16: 0,489 a 1.100, 0,502 a 1.600, 0,508 a 2.000 per bersaglio. Uno scarto oltre ±0,015 dal valore atteso con le chiamate vere (stadio 83) smentisce il modello a due popolazioni |
| PDS | sale meno che dal t11 al t15: da +0,005 a +0,02 | un guadagno uguale o maggiore di +0,035 smentisce la saturazione |
| `nmae` | continua a scendere, 0,90–0,94 | se sale, l'ampiezza è già oltre l'ottimo per `nmae` |
| `reach` | sale | — |

## 5. Implementazioni future, in ordine di valore atteso per unità di quota

| # | che cosa | costo | che cosa decide | atteso (interpretazione) |
|---|---|---|---|---|
| 1 | **Stadio 83 su t16 e t17** prima del punteggio; aggiungere le chiamate alle previsioni | 0 invii, circa 5 minuti per file | se il t17 è davvero a un fattore; il valore atteso della fedeltà del t16 | — |
| 2 | **Generatore senza artefatto nella famiglia di trial-01**: stadio 45 `--gene-dispersion`, già scritto, alla migliore ampiezza. Prima lo stadio 83 su un pilota: `n_pred` ben sopra qualche centinaio e quota «in su» vicina al 50% | 1 invio | se la fedeltà sale verso `p_e` e il `reach` verso il t14 (0,187) | fedeltà 0,51–0,53, `reach` in salita, PDS da −0,01 a −0,02 per più rumore di pseudobulk; complessivo da +0,01 a +0,03. A effetto nullo l'artefatto scende da 429–675 a 5–31 chiamate (`reports/dispersion_2026-09-23/RISULTATO_NULLO.md`): la regola del t13 (≤ 10) lo aveva fermato per B e C |
| 3 | **Grezzi contro ristretti**, prima fuori quota: stadi 101 e 103 sulla cache r5 con `z_shrink` contro grezzo, a pari numero di geni chiamati (proxy PDS, purezza di segno di testa, skill ad `a*`). Poi un invio se la proxy lo giustifica | 0 invii, poi 1 | se lo stimatore conta | ignoto; è la scelta ereditata meno giustificata (§3.6) |
| 4 | **Pesi per contesto**: CD4 alto in A, basso in B e C | 1 invio | se il lignaggio conta nella miscela | piccolo, positivo |
| 5 | **γ = 0 contro γ = 1**, un fattore | 1 invio | segno contro discriminazione | piccolo; vedi le riserve del §3.5 |
| 6 | **Ampiezza per bersaglio** dall'accordo fra sorgenti, tenendone fuori una alla volta: `a_t ∝ max(ρ_t, 0)`. Prima fuori quota, sulla proxy di skill MSE e sulla proxy PDS | giorni di lavoro, 0 invii per decidere | se una parte dei bersagli ha effetti conservati abbastanza da portare la MSE sotto la base | è l'unica strada verso la MSE con le sorgenti attuali. Tensione da misurare: il PDS vuole ampiezze alte anche sui bersagli deboli |
| 7 | **Ipotesi degli «assi di stato»**, da provare su dati pubblici prima di costruire. Nei dati di validazione i delta sarebbero in buona parte su pochi assi condivisi (ciclo cellulare, stress, stato), con carico diverso per bersaglio. Prima prova: nella cache r5, correlazione fra sorgenti dei carichi a livello di insieme di geni contro quella gene per gene (0,01–0,03). Seconda prova, nel K562 a singola cellula: quota del delta di ogni bersaglio nel sottospazio dell'eterogeneità dei controlli | giorni di lavoro, 0 invii | se esiste un'informazione per bersaglio che trasferisce meglio dei singoli geni | spiegherebbe le prime dieci: MSE 0,65–0,85 con PDS solo 0,82–0,87. Un asse condiviso con ampiezze diverse abbassa molto la MSE e aiuta poco il coseno. È un'ipotesi |
| 8 | **Preparazione del 22 ottobre**: (a) verificare se durante la fase finale i punteggi su D/E/F sono visibili; (b) identificare le linee con le impronte genetiche dello stadio 99 contro DepMap/CCLE (espressione e numero di copie per braccio); (c) separare le scelte generiche (generatore, stimatore) da quelle tarate su A/B/C (ampiezza, pesi) | ore | quanta taratura sarà possibile su D/E/F; se esiste Perturb-seq della stessa linea | una sorgente della stessa linea vale ordini di grandezza più delle altre: fra condizioni CD4 degli stessi donatori lo skill è 0,09–0,13, fra tipi cellulari 0,0001–0,002 |
| 9 | **Rileggere la classifica** | 0 invii | dove stanno oggi i punti | — |

## 6. Che cosa non fare

Le docstring dello scorer descrivono diverse emissioni che guadagnano punti senza biologia. Tutte
sono chiuse o limitate nella 0.16.0:
- somme per gruppo bloccate con dispersione per cellula finta, che sfruttano la correzione della
  MSE (#348);
- geni del pannello «accesi» per il PDS (#343);
- geni sotto soglia che rivelano il segno (#351).

La correzione della MSE è limitata, non eliminata, per ammissione degli autori
(`cell_eval2/metrics/delta.py:1010-1030`). Non vanno inseguite:
- sono fuori dallo spirito delle regole;
- l'organizzatore le misura e le chiude fra una versione e l'altra.

Per la stessa ragione, al §3.1 non leggo il vantaggio delle prime dieci sulla MSE come prova di
biologia.

## 7. Limiti

- I due modelli del §3.1 e del §3.2 sono interpretazioni. Stanno su due punti ufficiali, su
  mediane di 20 bersagli per contesto (stadi 72 e 83) e su ipotesi dichiarate:
  - `m0` vicino a 1;
  - `n_pred ≥ n_conf` per la maggior parte dei bersagli;
  - artefatti che non cambiano con gli effetti. La correzione BH per bersaglio può farli variare.
- La MSE del t16 misura `m0` solo se il modello quadratico regge a 0,788: la non linearità di
  `log1p` e della rinormalizzazione composizionale ne è il limite.
- Le identità di linea del §3.8 sono ipotesi da marcatori. Nessun confronto con DepMap è stato
  fatto.
- Nessun numero qui è un punteggio VCC nuovo. I soli punteggi citati sono quelli ufficiali già nel
  repository.
