# Confronti diagnostici dopo il t30: baseline, componente comune, ampiezza

**Stato: congelato** con il commit che contiene questo testo, il 4/10/2026 alle 13:23 CEST (ora letta con `date`),
prima di qualunque uscita dei bracci nuovi descritti qui. Scritto da Claude Code, sessione `ba9b8bcb`, su consegna del
proprietario ([PROMPT_CLAUDE1](../../analisi/prossimo_ibrido_2026-10-04/PROMPT_CLAUDE1.md) §3), programma
[R-LEAD](../../../docs/piani/strategia-scientifica.md). **Nessun job è stato lanciato:** le corsie girano su Kaggle
CPU e il lancio richiede il via del proprietario in chat. Tipo: proposta di esperimento diagnostico, non candidato.

## 0. Che cosa era già letto quando è stato scritto

- Il punteggio ufficiale del t30 e i suoi sei membri (`reports/invii/prediction_t30_2026-10-04/comparison.json`).
- Le corsie B esistenti delle cinque linee (`reports/modelli/ibrido_selettivo_2026-10-04/esito/lanes_*_r1/`), con i
  bracci `transfer`, `rete`, `ibrido_selettivo`, `miscela_fissa`, `transfer_cells_J`, `transfer_prod_J`.
- Le misure esplorative del passaggio delle 12:30 nella scheda R-LEAD (quota comune di R su A/B/C 0,63–0,70, riferita
  e non ancora ricalcolata da questa sessione al momento della scrittura).
- **Non letto, perché non esiste ancora:** nessun braccio `T_prod + w · R`, nessun braccio con la parte comune tolta,
  isolata o amplificata, nessun braccio con ampiezza ×1,5 sulle corsie B.

Le soglie qui sotto sono scelte a priori sull'ordine di grandezza delle differenze già viste fra bracci (+0,006…+0,074
sulla media, −0,09…+0,07 sul PDS) e non si spostano dopo.

## 1. Domanda

Il t30 ha aggiunto agli effetti t25 una correzione R definita rispetto a un'altra ancora (`transfer_all_J`, nove
gruppi), e sul sito ha perso PDS (−0,042 scalato) guadagnando poco su fedeltà e Jaccard. Tre cause candidate, tenute
separate:

- **C1, baseline incoerente:** R aiuta quando è sommata all'ancora rispetto a cui è stata appresa e non quando è
  sommata a un'altra baseline.
- **C2, componente comune:** la parte di R uguale per tutti i bersagli toglie discriminazione; sul banco era piccola
  (0,13–0,26 dell'energia), all'esportazione grande (0,63–0,70 riferito).
- **C3, natura del guadagno di banco:** il guadagno locale viene dalla parte comune (più geni chiamati, membri DE) e
  non da un'informazione specifica del bersaglio.

Dominio dei controlli (Flex, linee di gara) e differenze di saggio restano ipotesi distinte che questo banco **non
può** misurare: le cinque linee sono tutte non-Flex e già lette. Un esito qui dice che cosa succede sul banco, non
perché il sito ha dato −0,005.

## 2. Precedenti

- **S-009** (ibrido selettivo D-056 v1). Stesse reti, stessi pesi del selettore, stesse cellule vere, stessi bersagli
  e stesso seme delle corsie B già lette: qui non si riaddestra e non si ritara niente. Cambiano solo gli effetti dei
  bracci. Differenza rispetto al meccanismo ipotizzato in S-009 (la separazione della risposta comune regge): lo si
  mette alla prova alzando la quota comune al livello dell'esportazione.
- **S-006** (v4: la correzione impara uno spostamento comune). Il braccio `…_wRdose` riproduce di proposito quel
  guasto in forma controllata; il braccio `…_wRspec` è la variante «la correzione non può spostare la media sui
  bersagli» che S-006 indica come condizione di riapertura.
- **S-003** (miscele a posteriori). Nessun peso si sceglie qui: w è quello congelato del banco. Togliere la media
  sui bersagli usa solo R, mai la verità della linea.
- **S-010** (fonti del transfer). `T_prod` è la regola `production` di quel confronto: le tabelle della ricetta
  inviata senza la linea esclusa. Non è la ricetta t25 (stimatore con restringimento, testa cis, quattro fonti
  complete) e su K562 perde una delle sue fonti: l'analogo è dichiarato imperfetto.

**Segnale precoce e arresto:** la prima linea è HepG2 (la rete del t30). Se il braccio `all_wR` non riproduce i sei
membri archiviati di `ibrido_selettivo` di quella linea entro 1e-9, o `all` quelli di `transfer`, o la parità
`all_w0` fallisce, ci si ferma: il banco non è riproducibile e questo è il difetto da riferire, prima di ogni altra
linea. Sull'esportazione, il segnale che avrebbe fermato il t30 è la quota comune della correzione aggiunta > 0,5
(`export_vs_rows.py` di questa cartella la ricalcola).

## 3. Disegno

Codice: `diag_lanes.py` (bracci e aritmetica, con test in `test_diag_lanes.py`) e `kaggle_diag.py` (lo stesso
launcher delle corsie D-056, con il solo passo cambiato). Un kernel CPU per linea, con gli ingressi della corsia B
originale di quella linea (training, pre-passo, ancore, cellule vere, bersagli, pesi: quelli elencati in
`reports/modelli/ibrido_selettivo_2026-10-04/lancio_hybrid_r1.jsonl`). Scorer alla versione del venv (0.16.0, come
le corsie archiviate). Linee: HepG2, poi H1, RPE1, Jurkat, K562.

R è la correzione del braccio `ibrido`; w i pesi selettivi del file dei pesi della linea; R̄ la media di R sui
bersagli della corsia, gene per gene. `c` è il fattore su R̄ che porta la quota comune a **0,65**, calcolato da R sola.

| Braccio | Effetti | Che cosa rappresenta |
|---|---|---|
| `all` | T_all | baseline del banco (l'ancora della rete) |
| `all_w0` | T_all + 0 · R | parità: cellule identiche ad `all` |
| `all_wR` | T_all + w · R | il caso del banco; deve riprodurre `ibrido_selettivo` |
| `all_wRspec` | T_all + w · (R − R̄) | correzione senza parte comune |
| `all_wRcom` | T_all + w · R̄ | sola parte comune |
| `all_wRdose` | T_all + w · ((R − R̄) + c · R̄) | quota comune portata a 0,65 |
| `prod` | T_prod | fonti della ricetta senza la linea esclusa |
| `prod_wR` | T_prod + w · R | l'analogo del t30 |
| `prod_wRspec`, `prod_wRcom`, `prod_wRdose` | come sopra su T_prod | |
| `prod_x15`, `prod_wR_x15` | 1,5 · T_prod, 1,5 · (T_prod + w · R) | la sola ampiezza dell'emissione t28 |

**Che cosa non copre:** la dispersione per gene del t28 (non è nel generatore delle corsie), il riaddestramento di una
correzione coerente con T_prod (un incrocio con vecchi pesi è diagnostico, non lo sostituisce), il dominio Flex.

## 4. Letture, fissate ora

Per ogni linea, sulla media dei sei membri locali (`avg`) e sul membro PDS. Tutte le letture sono **diagnostiche**:
nessuna promuove un candidato o autorizza un invio.

- **Validità:** parità `all_w0`; riproduzione entro 1e-9 di `transfer`, `ibrido_selettivo` e `transfer_prod_J`
  archiviati da parte di `all`, `all_wR` e `prod`. Una linea che non riproduce è esclusa e riferita.
- **C1.** D = [avg(`prod_wR`) − avg(`prod`)] − [avg(`all_wR`) − avg(`all`)].
  - *sostenuta sul banco* se D < 0 in almeno 4 linee su 5 e la media di D è ≤ −0,010;
  - *smentita sul banco* se la media di D è ≥ 0;
  - altrimenti *non distinta*.
- **C2.** P = PDS(`all_wRdose`) − PDS(`all_wR`); Q = PDS(`all_wRspec`) − PDS(`all_wR`).
  - *sostenuta* se P < 0 in almeno 4 linee su 5 con media ≤ −0,020;
  - *smentita* se la media di P è ≥ 0;
  - Q si riporta: Q > 0 dice che già la quota comune del banco costa discriminazione.
- **C3.** S = avg(`all_wRspec`) − avg(`all`); K = avg(`all_wRcom`) − avg(`all`); G = avg(`all_wR`) − avg(`all`).
  - *guadagno portato dalla parte comune* se media(K) ≥ 0,5 · media(G) e media(S) < 0,010;
  - *guadagno specifico* se S > 0 in almeno 4 linee su 5 e media(S) ≥ 0,010;
  - altrimenti *misto*.
- **Ampiezza (descrittiva, nessuna regola):** [avg(`prod_wR_x15`) − avg(`prod_x15`)] accanto a
  [avg(`prod_wR`) − avg(`prod`)].
- **Lettura secondaria dichiarata ora:** le stesse quantità sulla media di cinque membri senza JAC, perché sulle
  corsie archiviate il JAC locale di K562, Jurkat e HepG2 è fuori da [0, 1] (denominatore replicato − baseline
  piccolo). Se primaria e secondaria divergono lo si scrive; la primaria non cambia.
- Con meno di cinque linee valide le soglie «4 su 5» diventano «tutte tranne una» e l'esito porta il numero di linee.

## 5. Limiti, scritti prima

Le cinque linee sono già lette e non sono una riserva: dopo questa diagnosi Jurkat e K562 non si possono chiamare
conferma intatta. Un seme, 150 bersagli al più per linea, scala locale. C1 su K562 usa una `T_prod` con una fonte in
meno. Una C1 smentita sul banco non assolve la baseline sul sito: lì la baseline è la ricetta t25 vera.

## 6. Esecuzione e uscite

`kaggle_diag.py … --slug rcell-t30diag-<linea>-r1 --launch-log lancio_diag_r1.jsonl`; uscite scaricate in
`processed/diagnosi_t30_2026-10-04/` e ricevute piccole in `esito/` di questa cartella; lettura con uno script
scritto prima di scaricare le uscite. Esito → checkpoint e aggiornamento di S-009 nello stesso commit.

## 7. Emendamento del 4/10, 13:30 CEST (ora letta con `date`): controllo locale sui controlli delle linee, scritto prima di eseguirlo

Al momento della scrittura sono lette le ricevute locali `esito/chain_t30_r2.json`, `esito/bench_members_r1.json` ed
`esito/export_vs_rows_r1.json` (quota comune di R all'esportazione 0,62–0,69; sulle righe del banco 0,07–0,24;
RMS(R)/RMS(T) mediano 0,71–0,96 contro 0,24–0,42). Nessuna R calcolata con la procedura di esportazione su controlli
diversi da quelli di gara esiste ancora. Le letture del §4 non cambiano.

**Domanda.** La quota comune alta segue i **controlli di gara** (dominio degli ingressi della rete) oppure la
**procedura di esportazione** (1.024 estrazioni di 64 controlli uguali per tutti i bersagli, una sola libreria, i
bersagli del pannello), che sul banco non è mai stata usata? Sul banco R veniva dalle cellule di valutazione di ogni
gruppo, con rumore indipendente fra bersagli, che abbassa la quota comune a parità di rete.

**Disegno.** `export_on_line_controls.py`: la stessa rete (fold HepG2), le stesse ancore dei 230 bersagli corretti del
pannello, le stesse funzioni di `export_abc.py` (importate, non copiate) e lo stesso seme, con al posto dei controlli
ufficiali i controlli `non-targeting` delle cellule vere del banco di tre linee: HepG2 (esclusa dal training di questa
rete), H1 e RPE1 (nel suo training). Calcolo locale leggero (CPU, minuti per linea). Nessun peso, nessuna verità.

**Lettura.** Quota comune di R sui bersagli corretti, sui geni misurati dal file dei controlli della linea; per A/B/C
la si ricalcola sugli stessi geni.
- *segue i controlli di gara* se la quota è ≤ 0,35 su tutte e tre le linee e resta ≥ 0,55 su A, B e C sugli stessi geni;
- *segue la procedura o i bersagli del pannello* se è ≥ 0,55 su almeno due linee;
- altrimenti *non distinto*. Si riporta anche RMS(R)/RMS(ancora) con le due letture analoghe a soglie 0,5 e 0,6.
Limiti: H1 e RPE1 sono linee di training della rete; 2.048 controlli per linea contro 18.400; nessuna di queste linee
è Flex, quindi «controlli di gara» non distingue saggio, linea e profondità.

### 7-bis. Nota del 4/10, 13:38 CEST (ora letta con `date`), prima di leggere qualunque linea

La prima esecuzione (`esito/export_on_line_controls_r1.json`) si è fermata sul proprio controllo positivo: i controlli
ufficiali di A, ripassati per lo script, ridanno la R archiviata con uno scarto massimo di 0,00049 sulle stesse coppie
definite, e lo script pretendeva uno scarto esattamente nullo. **Nessuna linea è stata calcolata o letta.** Lo scarto è
un passo di float16: il file archivia R arrotondata a float16 e s(N), s(A) sono a loro volta arrotondate prima della
differenza. La tolleranza del controllo positivo diventa **un passo di float16, 2⁻¹⁰ ≈ 0,00098**, con le coppie definite
identiche; si riportano anche la quota di coppie identiche e lo scarto quadratico medio. Soglie e letture delle linee
(§7) restano quelle scritte alle 13:30.

## 8. Emendamento del 4/10, 14:09 CEST (ora letta con `date`): il braccio fedele, prima di qualunque esecuzione delle corsie

Nessuna corsia diagnostica è stata lanciata e nessun braccio del §3 esiste. Letti dopo il congelamento:
`esito/export_on_line_controls_r2.json` (sui controlli di HepG2 la procedura di esportazione dà quota comune 0,61 e
ampiezza 0,88, contro 0,23 e 0,42 misurati dal banco sulla stessa linea e rete) e `esito/panel_vs_rows_targets_r1.json`
(i bersagli del pannello non sono fra quelli del banco su tre linee). Ne segue una quarta causa candidata, che il §3
non copriva:

- **C4, procedura dell'invio:** la correzione calcolata come nell'invio (1.024 estrazioni di 64 controlli della linea,
  uguali per tutti i bersagli, una sola libreria) è diversa da quella che il banco ha valutato (media sulle cellule di
  valutazione di ogni gruppo), e vale meno.

**Bracci aggiunti**, stessi bersagli, stesse cellule vere, stesso seme e **stessi pesi w** del banco (un solo fattore:
come si calcola R): `all_wRexp` = T_all + w · R_exp, `prod_wRexp` = T_prod + w · R_exp, `all_wRexpspec` =
T_all + w · (R_exp − R̄_exp). R_exp viene da `export_abc.corrections` (importata, non copiata) con il `model.pt` del
fold, i controlli `non-targeting` delle cellule vere della corsia e l'ancora `transfer_all_J` dei bersagli della corsia
(supporto diviso per il `max_sources` del manifest delle ancore del fold); seme 20261004 come nell'invio. Si
registrano quota comune e ampiezza di R_exp e il coseno medio per bersaglio fra R_exp e R.

**Lettura, fissata ora.** E = avg(`all_wRexp`) − avg(`all_wR`); F = PDS(`all_wRexp`) − PDS(`all_wR`).
- *C4 sostenuta sul banco* se F < 0 in almeno 4 linee su 5 con media ≤ −0,020, oppure E < 0 in almeno 4 linee su 5
  con media ≤ −0,010;
- *C4 smentita sul banco* se le medie di E e di F sono entrambe ≥ 0;
- altrimenti *non distinta*. Con meno di cinque linee valide vale la regola del §4.
- Si riporta avg(`all_wRexp`) − avg(`all`): è il guadagno che il banco avrebbe letto valutando la correzione come
  viene esportata. Non è una regola e non autorizza niente.

Limite: i bersagli restano quelli del banco, non quelli del pannello; i pesi sono quelli stimati con la R del banco.
Procedura e bersagli, che nel controllo del §7 cambiavano insieme, qui sono separati solo dal lato della procedura.

## 9. Emendamento del 4/10, 15:59 CEST (ora letta con `date`): taratura del rumore del banco, prima di eseguirla

Lette le cinque corsie (`esito/read_diag_r1.json`, valide tutte). Il braccio fedele ha dato una R quasi identica a
quella del banco sugli stessi bersagli (coseno medio 0,9998 su quattro linee, 0,977 su RPE1; stessa quota comune),
eppure `all_wRexp − all_wR` vale −0,008…−0,060 sulla media e fino a ±0,16 su un membro. Due bracci con effetti quasi
uguali non dovrebbero differire così: il sospetto è il rumore di realizzazione del generatore (un seme, 32 cellule
previste per bersaglio). **È un'ipotesi finché non si misura**; se è vera, nessuna lettura del §4 e del §8, e nemmeno
la regola di CP-0062, è risolta dal banco a un seme.

**Disegno** (`diag_lanes.py --noise-seeds 5 --noise-n 400`, solo generazione e scorer, niente rete): i bracci `all`,
`all_wR`, `prod`, `prod_wR`, con gli stessi effetti delle corsie r1, rigenerati con 5 semi del generatore
(20260912 + k, k = 0…4) a due numerosità di cellule previste per bersaglio: quella del banco (metà delle cellule vere,
mediana 32) e 400 come nell'invio. Verità, controlli e seme del banco invariati. Il seme k = 0 alla numerosità del
banco deve riprodurre le corsie r1.

**Lettura, fissata ora**, per linea e numerosità, sul guadagno appaiato g_k = avg(`all_wR`) − avg(`all`) allo stesso
seme (e lo stesso su `prod`):
- si riportano media e deviazione standard (n − 1) di g_k sui 5 semi, per la media dei sei membri, per quella senza
  JAC e per ogni membro;
- **«il banco a un seme non risolve il guadagno»** su una linea se la deviazione standard di g_k alla numerosità del
  banco è ≥ metà del valore assoluto del guadagno archiviato di quella linea; l'esito complessivo vale se accade in
  almeno 3 linee su 5;
- **«guadagno risolto»** su una linea e una numerosità se |media di g_k| > 2 · deviazione standard / √5; si riporta
  in quante linee e con quale segno, per `all` e per `prod`, a 32 e a 400 cellule;
- si riporta il rapporto fra le deviazioni standard alle due numerosità: dice quanto rumore tolgono 400 cellule.
Nessuna di queste letture promuove un candidato. Servono a fissare, nel prossimo protocollo, quanti semi e quante
cellule occorrono perché una differenza di banco sia leggibile.
