# Diagnosi dopo il t30: che cosa il banco aveva provato e che cosa non si è trasferito

4 ottobre 2026, Claude Code, sessione `ba9b8bcb`, macchina `LAPTOP-DLG1LHV1`, partenza `a6f7dd2`, su consegna del
proprietario ([PROMPT_CLAUDE1](../../analisi/prossimo_ibrido_2026-10-04/PROMPT_CLAUDE1.md)). Resoconto per il
proprietario e per Codex, che prepara il prossimo training in
[prossimo_ibrido](../../analisi/prossimo_ibrido_2026-10-04/README.md). Chiusura ufficiale del t30:
[CP-0064](../../../docs/checkpoints/0064-t30-ibrido-selettivo-punteggio-ufficiale.md).

**In una riga.** Il t30 vale 0,135249, −0,004989 contro il t25: ramo b della regola, non conclusivo e non un
miglioramento. La catena dell'invio è integra. Il banco aveva misurato un'altra cosa rispetto a ciò che è stato
inviato: altra baseline, altro modo di calcolare la correzione, altri bersagli, altra geometria. I difetti
riprodotti sono qui sotto; **la causa della perdita non è identificata**.

Tutto ciò che segue è calcolo locale leggero su file già esistenti. Nessun job cloud, download, invio o push.

## Indice

| File | Contenuto | Stato |
|---|---|---|
| [TABELLA_CATENA.md](TABELLA_CATENA.md) | Training → banco → esportazione → generazione, voce per voce, e la parità a w = 0 lungo la catena | letto da codice e ricevute |
| `chain_t30.py`, [esito/chain_t30_r2.json](esito/chain_t30_r2.json) | Entry, ricevuta, modello, effetti, generazione, pacchetto, sei membri, regola | misurato (R1); `r1` è la stessa lettura prima di separare parità del profilo e delle cellule |
| `bench_members.py`, [esito/bench_members_r1.json](esito/bench_members_r1.json) | I sei membri del banco D-056 per linea, denominatori, contributi | misurato (R2) |
| `export_vs_rows.py`, [esito/export_vs_rows_r1.json](esito/export_vs_rows_r1.json) | Correzione esportata per A/B/C contro le righe del banco; ingressi del selettore | misurato (R3) |
| `export_on_line_controls.py`, [esito/export_on_line_controls_r2.json](esito/export_on_line_controls_r2.json) | La procedura di esportazione sui controlli di tre linee del banco | misurato (R4); `r1` è il tentativo fermato dal controllo positivo |
| `panel_vs_rows_targets.py`, [esito/panel_vs_rows_targets_r1.json](esito/panel_vs_rows_targets_r1.json) | I bersagli del pannello contro quelli del banco: sovrapposizione, ampiezze di T e R | misurato, esplorativo (R5) |
| [PROTOCOLLO_CONFRONTI.md](PROTOCOLLO_CONFRONTI.md) | Confronti controllati sulle corsie B: baseline, parte comune, ampiezza e, dal §8, il braccio fedele (R calcolata come nell'invio); §7 è il controllo locale R4 | congelato prima delle uscite; le corsie **non sono eseguite**, serve il via per Kaggle |
| `diag_lanes.py`, `test_diag_lanes.py`, `kaggle_diag.py`, `read_diag.py` | Codice dei confronti: 16 bracci, 10 test rapidi più un controllo positivo lento (la funzione del braccio fedele ridà la R archiviata di A), launcher provato a secco, lettore scritto prima | implementato |

## 1. Risultato esatto

Fonte: status pubblicato `reports/invii/trial_2026-10-04/status_lDMSYUZU5cFYHcRqI0lq.json`, confronto
`reports/invii/prediction_t30_2026-10-04/comparison.json`, rilettura R1. Stesso pannello (`vcc2026-val-1`) e stessa
versione delle ancore (r4) di t25 e t28. Lo status non pubblica membri per contesto: nessuno è stato ricostruito.

| Membro | t30 scalato | t25 | t28 | t30 − t25 | contributo alla media | t30 − t28 | t30 grezzo | t25 grezzo |
|---|---|---|---|---|---|---|---|---|
| PDS | 0,581325 | 0,623562 | 0,622307 | **−0,042237** | −0,007040 | −0,040982 | 0,763058 | 0,782092 |
| MSE | 0 | 0 | 0 | 0 | 0 | 0 | 3,168231 | 3,017171 |
| NMAE | 0,116091 | 0,117985 | 0,049202 | −0,001894 | −0,000316 | +0,066889 | 0,929128 | 0,928019 |
| Fedeltà | −0,044402 | −0,058129 | −0,007409 | +0,013726 | +0,002288 | −0,036993 | 0,499278 | 0,495220 |
| Reach | 0,142214 | 0,144052 | 0,198713 | −0,001838 | −0,000306 | −0,056499 | 0,204634 | 0,206572 |
| Jaccard | 0,016264 | 0,013958 | 0,006258 | +0,002306 | +0,000384 | +0,010005 | 0,036404 | 0,035571 |
| **Media** | **0,135248602** | 0,140238061 | 0,144845205 | **−0,004989459** | −0,004989 | −0,009596603 | | |

- La media dei sei scalati coincide con `score_avg` per i tre invii.
- **Regola registrata, sul valore non arrotondato:** la soglia inferiore è 0,140238061 − 0,005 = 0,135238061; il t30
  la supera di 0,0000105. Ramo **b**, non conclusivo. Con quattro cifre (0,1352) il ramo non si distingue. Un esito
  non conclusivo a un centomillesimo dal ramo c non è un miglioramento e non promuove niente.
- La perdita è quasi tutta nel PDS (141 % del delta); fedeltà e Jaccard ne compensano il 54 %; NMAE e reach perdono
  poco. La MSE scalata resta 0 mentre la grezza peggiora del 5 %.

## 2. Che cosa è riprodotto, che cosa è passato, che cosa resta ipotesi

### 2.1 Difetti riprodotti (misurati, con ricevuta)

1. **`t30 − t25` non è un fattore solo a livello di cellule.** Lo stadio 45 estrae tutti i blocchi da un unico
   flusso casuale. Dei 210 blocchi dei 70 bersagli non corretti (w = 0), il profilo previsto è identico al t25 in 210
   su 210, ma le cellule lo sono in **1 su 210**: il solo blocco che precede il primo bersaglio corretto. Il delta
   ufficiale contiene quindi un cambio di realizzazione del rumore su 899 blocchi su 900, oltre alla correzione.
   L'unica coppia di semi misurata sul sito vale 0,0016 (t24 − t22). Lo stesso vale fra i bracci di ogni corsia B
   («un flusso per braccio»). *R1; `scripts/45_generate_prediction.py`, `generate`.*
2. **La correzione è stata sommata a una baseline diversa da quella rispetto a cui è definita.** Sul banco
   `ibrido = transfer_all_J + w · R`; nel t30 `t25 + w · R`, con R = s(N) − s(A) e A l'ancora `all` a nove gruppi. Il
   coseno mediano fra gli effetti t25 e l'ancora passata per la rete è **0,71**; R è ortogonale al t25 (coseno
   mediano −0,02). Nessun braccio `T_prod + w · R` è mai stato valutato sul banco. È misurata la distanza, **non** il
   suo effetto sul punteggio. *R3; protocollo D-056 §13.*
3. **All'esportazione la correzione è per due terzi uguale per tutti i bersagli.** Quota comune di R: **0,62 (A),
   0,69 (B), 0,66 (C)**; della correzione effettivamente aggiunta 0,59, 0,67, 0,63. Sulle righe del banco: 0,24 (H1),
   0,23 (HepG2), 0,16 (RPE1), 0,13 (Jurkat), 0,07 (K562); nelle guardie interne del training 0,17. La guardia del
   trainer ferma oltre **0,5**: all'esportazione nessuno la applicava. Il vettore comune è quasi lo stesso nei tre
   contesti (coseni 0,81–0,95) e la sua RMS (0,052–0,074) è 13–19 volte quella della parte comune degli effetti t25
   (0,0039). I 70 bersagli non corretti non la ricevono. *R3.*
4. **All'esportazione la correzione è due–quattro volte più ampia che sul banco, e il selettore lavora fuori dal suo
   intervallo.** RMS(R)/RMS(T) mediano 0,71 (A), 0,96 (B), 0,96 (C) contro 0,24–0,42 delle righe. L'ingresso
   `f_log_ratio` sta a +1,5 (A) e +2,2 (B, C) deviazioni standard dalla media di stima; il 45 % dei bersagli di B e
   il 44 % di C sono fuori dalla fascia 1–99 % delle righe di sviluppo. Il peso resta fra 0,09 e 0,49 (medio 0,28):
   su A/B/C il selettore è quasi una miscela costante. Il registro dell'invio riportava la sola A. *R3.*
5. **Sul fold esportato il banco perdeva già PDS, e la media lo copriva.** Rete del fold HepG2, sulla sua linea
   esclusa: corsia B PDS **−0,093** (0,984 → 0,891), corsia A PDS −0,039 (0,886 → 0,847); la media saliva di +0,063
   per NMAE (+0,10), fedeltà (+0,14), reach (+0,17) e Jaccard (+0,06), con i geni chiamati per bersaglio da 83 a 149.
   Sul sito il PDS perde −0,042 e quei guadagni non compaiono (−0,002, +0,014, −0,002, +0,002). HepG2 è l'unica
   linea su cinque in cui il segno del PDS coincide con quello ufficiale; l'NMAE locale ha il segno opposto a quello
   ufficiale in cinque linee su cinque. La guardia sul PDS della corsia A valeva solo per le linee di conferma. *R2.*
6. **Il JAC locale amplifica.** Il denominatore della scala (replicato − baseline) vale 0,047 su K562, 0,124 su
   Jurkat, 0,162 su HepG2: il JAC scalato arriva a −4,7. Il +0,074 di K562, il guadagno più grande dei cinque, viene
   per il **77 %** dal JAC (−4,66 → −4,31); senza JAC è +0,020. Su Jurkat e K562 le chiamate vere mediane sono 8 e 6
   per bersaglio e il transfer ne produce più del replicato. *R2.*
7. **La MSE locale non informa.** Scalata vale 0 per ogni braccio su ogni linea: tutti i bracci hanno MSE grezza
   peggiore della baseline e la scala tronca. Come sul sito. *R2; `src/vcc2026/bench.py`, `scale`.*
8. **Il banco ha un'altra geometria.** 32 cellule per bersaglio, vere e previste, contro 400; 7.679–9.023 geni su
   quattro linee su cinque contro 18.533; 2.048 controlli condivisi fra predetto, vero e riferimento DE. L'effetto di
   ciascuna differenza sul trasferimento dei membri DE **non** è misurato. *`laneB.log`, `bench.json`.*
9. **Il selettore è stato scelto su un obiettivo che non è quello letto.** Sulle righe il suo guadagno fuori fold
   sull'errore quadratico pesato è +0,4 % (H1), **−1,8 %** (HepG2), +0,4 % (RPE1), mentre sui sei membri della stessa
   linea HepG2 «vince» di +0,063. Delle 3.604 righe di stima 72 sono di H1. *R2; `selector_lolo_r1/summary.json`.*
10. **I bersagli della gara non erano nel banco.** Nessuno dei 300 bersagli del pannello è nelle righe o nelle
    corsie di HepG2, RPE1 e Jurkat; 15 su H1, 72 nelle righe e 6 nella corsia di K562. Il selettore è stimato per il
    99,6 % su altri bersagli, con transfer più grande, più fonti e correzione più piccola (§2.4). *R5.*
11. **Due difetti delle ricevute, senza effetto sul numero.** Lo stadio 45 registra i percorsi dei file degli
    effetti ma non il loro sha256: il legame effetti → cellule regge su percorso e data di modifica. La previsione
    nomina lo sha256 dell'esportatore precedente alla correzione della lettura dei geni (già in `INVIO_T30.md`). *R1.*

### 2.2 Controlli passati

- Entry, nome del modello, byte caricati e MD5 verificato dal server coincidono fra ricevuta, status e pacchetto. *R1.*
- `model.pt` (`365bf625…`) e selettore (`00758778…`) sono quelli della previsione registrata e del manifest. *R1.*
- Effetti esportati su disco = manifest; effetti t25 rigenerati = sha256 del t25 inviato; parità a w = 0 sugli array
  vera in A, B, C. *R1.*
- Argomenti dello stadio 45 uguali al t25 salvo i file degli effetti; stessi controlli; stesso seme. *R1.*
- Lo stadio 48 legge il file dello stadio 45; il pacchetto su disco ha dimensione e sha256 campionato registrati. *R1.*
- Il punteggio di banco del §9 si ricalcola identico (0,13364541…) dalle corsie archiviate. *R2.*
- Parità `ibrido_w0` = `transfer` sulle cinque corsie; nessuna lettura delle tabelle della linea esclusa per un fit;
  2.239 chiavi nascoste coerenti fra ancore, righe ed esportazione. *`parity.json`, `rows_summary.json`, M.*
- Nel training nessuna guardia è scattata; allo stato esportato ampiezza 0,65 e quota comune 0,17. *`guard.json`.*

### 2.3 Ipotesi aperte (non riprodotte: nessuna è «la causa»)

| Ipotesi | Che cosa la sostiene oggi | Che cosa manca |
|---|---|---|
| H-baseline: R nuoce perché sommata al t25 invece che alla sua ancora | la differenza è reale e grande (difetto 2) | il confronto C1 del protocollo; sul sito non è separabile |
| H-comune: la parte comune toglie discriminazione | difetti 3 e 5; precedente S-006 | il confronto C2 (dose) e C3 del protocollo |
| H-dominio: i controlli di gara portano la rete fuori dal suo regime | difetti 3 e 4 | R4 la indebolisce come spiegazione necessaria: una linea non di gara mai vista dà gli stessi valori. Resta aperto se saggio e profondità aggiungano qualcosa: serve un contesto Flex con verità |
| H-procedura/bersagli: R calcolata come nell'invio, sui bersagli del pannello, è un'altra correzione | R4 e difetto 10 | il braccio fedele sul banco (§2.4, conseguenza pratica), che separa procedura e bersagli |
| H-rumore: parte del −0,005 è realizzazione | difetto 1 | più semi dello stesso candidato, o un generatore con flusso per blocco |
| H-potenza: i guadagni DE del banco sono un effetto di 32 cellule | difetti 5 e 8 | il banco a 400 cellule previste, o a numerosità variata |
| H-selettore: fuori intervallo il peso è arbitrario | difetto 4 | bracci a peso fisso sul sito non esistono; sul banco, C1–C3 a pesi congelati |

### 2.4 Controllo locale R4: controlli di gara o procedura di esportazione?

Lettura scritta prima dell'esecuzione ([protocollo §7](PROTOCOLLO_CONFRONTI.md)); controllo positivo passato (la R di A
si riproduce identica). Stessa rete, stesse ancore dei 230 bersagli corretti, stessa procedura e stesso seme
dell'esportazione; cambiano solo i controlli. *R4.*

| Controlli | Ruolo per la rete | Geni | Quota comune di R | RMS(R)/RMS(s(A)) | A / B / C sugli stessi geni: quota comune | A / B / C: rapporto |
|---|---|---|---|---|---|---|
| HepG2 | linea esclusa, non di gara | 9.023 | **0,61** | **0,88** | 0,65 / 0,72 / 0,70 | 0,95 / 1,28 / 1,25 |
| H1 | linea di training | 18.077 | 0,30 | 0,39 | 0,63 / 0,70 / 0,67 | 0,77 / 1,03 / 1,04 |
| RPE1 | linea di training | 8.259 | 0,32 | 0,74 | 0,64 / 0,72 / 0,69 | 1,01 / 1,36 / 1,30 |

- **Esito con le regole registrate:** quota comune → **non distinto** (non è ≤ 0,35 su tutte e tre le linee, né
  ≥ 0,55 su due); ampiezza → **segue la procedura o i bersagli del pannello** (≥ 0,6 su due linee).
- **Osservazione esplorativa, letta dopo:** sui controlli di HepG2, linea non di gara che questa rete non ha visto, la
  procedura di esportazione dà quasi la stessa quota comune e la stessa ampiezza di A/B/C. Sulla stessa linea e con
  la stessa rete il banco misurava 0,23 e 0,42. Il vettore comune su HepG2 ha coseno 0,74–0,89 con quello di A, B e
  C (RPE1 0,61–0,72; H1 circa 0). Quindi la quota comune alta **non richiede** i controlli di gara: compare su una
  linea nuova qualunque quando R si calcola come nell'invio e sui bersagli del pannello. Sulle due linee di training è
  la metà. È una linea esclusa sola: l'effetto «linea mai vista» è un indizio, non una misura.
- **Perché il banco non l'aveva vista (misurato, `esito/panel_vs_rows_targets_r1.json`):** i bersagli del pannello
  **non sono fra quelli del banco**. Dei 300, nelle righe ce ne sono 0 su HepG2, 0 su RPE1, 0 su Jurkat, 15 su H1 e 72
  su K562; nelle corsie B 0, 0, 0, 15 e 6. Delle 3.604 righe su cui è stimato il selettore, 15 (0,4 %) sono di
  bersagli del pannello. Sui bersagli del pannello il transfer è più piccolo (RMS mediana 0,107 contro 0,120–0,135
  delle righe) e ha meno fonti (5 gruppi contro 6–8), e la correzione è più grande (0,078–0,109 contro 0,030–0,060).
  Procedura e bersagli cambiano insieme: questo controllo non li separa. In più, il 17–21 % delle righe di HepG2,
  RPE1, Jurkat e K562 ha l'ingresso di espressione a 0 («gene non misurato nella linea»), valore che su A/B/C non
  compare mai.
- **Conseguenza pratica:** il braccio fedele si può costruire oggi, dove la verità esiste: R calcolata con la
  procedura di esportazione sui controlli della linea esclusa, per i bersagli della corsia B, e poi i sei membri.
  Aggiunto come §8 del protocollo (bracci `all_wRexp`, `prod_wRexp`, `all_wRexpspec`, causa C4), con codice e test,
  prima di qualunque esecuzione delle corsie.

## 3. Che cosa del banco si riusa e che cosa va corretto prima di promuovere un candidato

**Riutilizzabile così com'è:** lo scorer vero sui sei membri; le linee escluse intere con il controllo delle letture;
la parità a correzione nulla; la separazione righe / corsia A / corsia B; il launcher Kaggle con codice e pesi
sotto sha256; le ricevute del training e le guardie interne.

**Da correggere prima di promuovere:**

1. **Un solo contratto di baseline** in fit, banco ed esportazione: il candidato inviato deve essere un braccio del
   banco, non un suo analogo. Se la baseline dell'invio è la ricetta, il banco valuta `ricetta_senza_linea + w · R`.
2. **Le guardie del trainer applicate all'esportazione**, come rifiuto: quota comune, ampiezza relativa, ingressi
   del selettore dentro l'intervallo di stima. Con le soglie di oggi il t30 sarebbe stato fermato sulla quota comune.
3. **Una guardia per membro su ogni linea**, sviluppo compreso: una perdita di PDS non si compensa in media.
4. **Flusso casuale per blocco** (seme derivato da contesto e bersaglio) nel generatore del banco e in quello
   dell'invio, perché un bersaglio non corretto dia le stesse cellule; e **più semi** per avere il rumore di un braccio.
5. **JAC e MSE:** riportare i grezzi e i denominatori; fissare prima come entrano nella media quando il denominatore
   è sotto una soglia. Non eliminarli dopo aver visto i numeri.
6. **Geometria e bersagli di gara:** R calcolata con la procedura dell'invio anche sul banco; bersagli del pannello
   (o del loro stesso regime di supporto e ampiezza) fra quelli valutati e fra le righe del selettore; cellule
   previste per bersaglio e asse dei geni come nell'invio, o la prova che non contano.
7. **Selettore valutato sull'obiettivo che si legge** (sei membri dopo generazione), con possibilità reale di w = 0.
8. **Linee:** le cinque linee sono sviluppo. Jurkat e K562 non sono più una conferma intatta.

## 4. Confronti che distinguono le cause

| Causa candidata | Confronto | La sostiene | La smentisce | Stato |
|---|---|---|---|---|
| Baseline incoerente | `prod_wR − prod` contro `all_wR − all`, stesse cellule e seme (C1) | il guadagno sparisce su `T_prod` in ≥ 4 linee su 5, media ≤ −0,010 | guadagno uguale o maggiore su `T_prod` | pronto, non eseguito |
| Parte comune | `all_wRdose` (quota comune a 0,65) e `all_wRspec` contro `all_wR`, sul PDS (C2) | il PDS scende con la dose in ≥ 4 linee su 5, media ≤ −0,020 | PDS invariato o più alto con la dose | pronto, non eseguito |
| Guadagno di banco non specifico | `all_wRcom` e `all_wRspec` contro `all` (C3) | la sola parte comune dà ≥ metà del guadagno | la parte specifica da sola guadagna ≥ 0,010 | pronto, non eseguito |
| Dominio dei controlli | la procedura di esportazione su controlli non di gara (R4) | quota comune bassa sulle linee, alta su A/B/C | quota alta anche sulle linee | eseguito, §2.4: non distinto sulla quota comune (alta su HepG2, bassa su H1 e RPE1), ampiezza dalla parte di procedura/bersagli |
| Procedura e bersagli dell'invio | corsia B con R della procedura di esportazione sui controlli della linea esclusa, contro R del banco, stessi bersagli e pesi | il guadagno locale si riduce o il PDS scende con la R dell'invio | stessi membri con le due R | pronto (§8, C4), non eseguito |
| Rumore di realizzazione | lo stesso candidato con due semi; t25 rigenerato con flusso per blocco | differenze fra semi dell'ordine di 0,005 | differenze ≪ 0,005 | da disegnare; sul sito costa invii |
| Potenza DE del banco | corsia B con 400 cellule previste per bersaglio | i guadagni NMAE/fedeltà/reach si riducono | restano | da disegnare |
| Ampiezza dell'emissione | `prod_wR_x15 − prod_x15` accanto a `prod_wR − prod` | — (descrittivo) | — | pronto; la dispersione del t28 non è coperta |

Le righe «pronto» sono un solo kernel Kaggle CPU per linea ([protocollo](PROTOCOLLO_CONFRONTI.md) §3–4), con pesi e
reti congelati. Un incrocio con vecchi pesi è diagnostico: non equivale a riaddestrare una correzione sulla baseline
coerente, e nessun esito autorizza un invio.

## 5. Vincoli per il protocollo successivo

- Il candidato che si invia è **esattamente** un braccio valutato; ogni differenza residua fra banco e invio è
  elencata prima, con la prova che non conta o con il rischio dichiarato nella previsione.
- La previsione ufficiale si registra **per membro**, non solo sulla media, e dice quale membro deve muoversi.
- Rifiuto dell'esportazione se quota comune > 0,5, se RMS(R)/RMS(T) esce dall'intervallo delle righe di stima, o se
  più del 5 % dei bersagli ha un ingresso del selettore fuori dalla fascia 1–99 % di stima. Soglie da confermare nel
  protocollo, prima dei numeri.
- Correzione a media nulla sui bersagli (o testa comune tenuta fuori anche all'inferenza **e verificata** sul
  contesto di destinazione), applicata identica in banco ed esportazione, compresi i bersagli a w = 0.
- Regola di banco: delta appaiato contro la baseline coerente, per linea e per membro, con guardia sul PDS; nessuna
  soglia assoluta sulla macro-media finché il JAC locale non è stabile.
- Più semi di generazione per ogni braccio decisivo; flusso per blocco.
- Almeno una linea mai letta da questo processo di selezione, e un contesto Flex con verità se esiste nel corpus
  (CD4T è Flex secondo i metadati degli autori): il dominio di gara oggi non è rappresentato nel banco.
- Una soglia locale (0,100 o altra) non è una previsione dello score e da sola non giustifica un invio.

Coordinamento: il piano di Codex ([PIANO_TRAINING §5–7](../../analisi/prossimo_ibrido_2026-10-04/PIANO_TRAINING.md))
chiede già contratto unico, parità a residuo nullo nell'esportatore e delta appaiato; qui ci sono le misure che lo
motivano e due vincoli in più (guardie all'esportazione, flusso per blocco).
