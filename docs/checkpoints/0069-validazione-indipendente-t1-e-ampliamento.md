# CP-0069 — Validazione indipendente: T1 non si distingue da t36; l'ampliamento delle fonti aiuta i lignaggi vicini e costa agli altri

- **Data:** 2026-10-08
- **Tipo:** esperimento
- **Redatto da:** Claude Code (Opus 5.5), sessione 8a8ca58a
- **Revisione umana:** no
- **Stato:** immutabile
- **Strade:** S-010, S-011

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Il candidato T1 (release canonica r1 senza il voto RFK di Tian 2019) migliora il transfer t36, misurato a
linee escluse intere con una regola scritta prima? E che cosa, dell'ampliamento delle fonti fatto fin qui,
aiuta davvero?

## 2. Cosa è stato fatto

Tutto in [validazione_indipendente_8a8ca58a_2026-10-08](../../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/README.md).
Orari letti con `date` o dai commit, Europe/Rome.

1. **Contratto** [v1](../../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/PROTOCOLLO_v1.md)
   (commit `c9fd904`, 18:14) e [v2](../../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/PROTOCOLLO_v2.md)
   (commit `1c206cb`, 18:50), con manifest dei fold: sei fold C a lignaggio escluso sul pannello (K562, CD4T,
   HCT116, HEK293 con HEK293T, iPSC, H1), regola di hash per i bersagli nascosti, interfaccia dei candidati,
   regola di adozione. v2 cambia la misura di discriminazione dopo che il controllo registrato in v1 è fallito
   su un fold; le due letture sono affiancate.
2. **Livello A**, spazio degli effetti: lo stadio 100 di produzione rieseguito su Kaggle CPU con una cache che
   non contiene fisicamente le tabelle del lignaggio escluso; misure per bersaglio contro la tabella di quel
   lignaggio, bootstrap appaiato sui bersagli. Quattro corse (r1–r4), bracci T0 (t36), R1, T1, P4 (le quattro
   linee del t28 sulle tabelle del t36), controlli, bracci d'analisi e regime J.
3. **Livello B**, sei membri con `cell-eval2` 0.16.0: `bench_v2.py` non modificato, emissione t28, 400 cellule,
   cinque semi, su cellule vere estratte oggi per i bersagli del pannello di K562 (272) e di KOLF2.1J «strong»
   (55). Piano di esecuzione committato alle 18:42, prima dei lanci.
4. **Audit** di uso dei dati e leakage e **verifica** del pacchetto t36.

## 3. Cosa si è osservato

- **Riproducibilità.** Gli effetti di produzione ricalcolati hanno gli sha256 registrati di t36, r1 e T1
  ([parity.json](../../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/banco/r1/completion/parity.json));
  in 42 esecuzioni su 42 nessuna tabella del lignaggio escluso è letta
  ([consumption.json](../../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/banco/r1/completion/consumption.json));
  le misure del fold K562 ricalcolate sul portatile coincidono alla precisione di macchina.
- **T1 contro t36.** Livello A, macro su sei fold: `disc95` +0,0004 [−0,0005; +0,0013], `r_spec` −0,0003
  [−0,0007; +0,0000] ([tabelle](../../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/TABELLE_LIVELLO_A_r1_v2.md)).
  Livello B: K562 −0,0008 ± 0,0023, iPSC +0,0001 ± 0,0031, macro −0,0003 ± 0,0014; PDS non risolto; NMAE del
  fold K562 −0,0072 ± 0,0060, risolto in peggio
  ([tabelle](../../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/TABELLE_LIVELLO_B_r1.md)).
  Esito della regola: **inconcludente**.
- **Centratura sul pannello.** Una tabella con n bersagli perde 1/n dell'effetto proprio; quella di Tian 2019,
  con un bersaglio, vota zero: su RFK tutti gli 11.530 geni mossi sono tirati verso zero, rapporto 0,63–0,75
  ([prova](../../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/banco/voto_singolo_rfk_r1.json)).
- **Voti e lignaggi.** T0: 1.523 voti, 1.456 contando un lignaggio una volta per bersaglio; dei 16 voti che T1
  aggiunge, 6 vengono da un lignaggio che su quel bersaglio non votava
  ([table_audit.json](../../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/banco/r1/completion/table_audit.json)).
- **t36 contro le quattro linee, stesse tabelle.** Livello B: fold K562 media −0,0260 ± 0,0081 e PDS −0,1011
  ± 0,0223; fold iPSC +0,0274 ± 0,0053 e +0,0666 ± 0,0228. Scomposizione nel livello A (piano committato prima):
  H1 `disc95` +0,005 [+0,003; +0,008]; ingresso di KOLF2.1J −0,011 [−0,021; −0,001]; voti ripetuti di KOLF −0,002
  [−0,004; −0,001] ([tabelle](../../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/TABELLE_SCOMPOSIZIONE_K0_r2.md)).
- **Esplorativo.** t36 senza le quattro tabelle KOLF: livello A `disc95` +0,012 [+0,002; +0,022], positivo sui
  quattro fold non staminali, `r_spec` risolto negativo su H1, errore quadratico +0,073
  ([tabelle](../../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/TABELLE_ESPLORATIVO_r3.md)).
  A sei membri sul fold K562 (cinque semi, letto alle 21:23): senza KOLF la media sale di +0,0299 ± 0,0081 e
  il PDS di +0,1171 ± 0,0197, risolti; con KOLF che vota una volta sola il PDS non si muove (−0,0033 ± 0,0072)
  e migliora l'NMAE (+0,0473 ± 0,0171)
  ([tabelle](../../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/TABELLE_LIVELLO_B_k562_x1.md)). È lo stesso fold da cui l'ipotesi nasce.
- **Regime J.** Tolti da ogni tabella i 66 bersagli del gruppo nascosto, tutti i bracci coincidono e prevedono
  la sola testa cis: `disc95` 0,54–0,58, macro sopra la previsione nulla di +0,065 [+0,036; +0,099]
  ([tabelle](../../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/TABELLE_REGIME_J_r4.md)).
- **Controllo a bersagli scambiati, sei membri.** Il PDS cade di 0,57 (K562) e 0,44 (iPSC); sul fold iPSC
  NMAE, fedeltà e Jaccard quasi non cambiano.
- **Riserva.** Il pacchetto t36 ha lo sha256 registrato prima dell'upload
  ([verifica](../../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/consegna/riserva_t36_r1.json)).
- **T2 e componente esterna.** Di T2 sono arrivati alle 21:00 i vettori comuni congelati (16 fonti, da 95 a
  18.080 bersagli dietro ogni vettore, hash verificati), non gli effetti di produzione: il fit finale attende il
  consenso del proprietario. Lo stimatore è in valutazione sui fold dalle 21:40, con il
  [piano](../../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/VALUTAZIONE_T2.md) committato alle 21:36; **questo checkpoint non ne legge alcun numero**: avrà il
  suo. La componente esterna non è arrivata alla valutazione: nessun peso acquisito.

## 4. Interpretazione e incertezza

- **Misura:** T1 non è distinguibile da t36 né nello spazio degli effetti né a sei membri. **Interpretazione:**
  i suoi voti nuovi sono pochi, in gran parte ripetizioni di lignaggi già presenti, e distorti dalla centratura
  su tabelle piccole. Che sia questo a togliere il beneficio non è isolato.
- **Misura:** l'ampliamento da quattro linee a t36 perde PDS sul fold K562 e ne guadagna sul fold iPSC.
  **Interpretazione:** con pesi uguali una fonte aiuta i lignaggi che le somigliano e diluisce lo specifico
  degli altri. **Ipotesi:** un voto per lignaggio, o senza KOLF, darebbe più PDS su contesti non staminali.
- **Perché potrebbe non essere così.** I sei lignaggi sono fonti di ogni ricetta e K562 è stata letta più volte:
  è sviluppo, non conferma. Due soli fold hanno cellule vere. Le scale locali non sono il sito: il t36 ha
  +0,0024 ufficiale sul t28, con PDS in salita, in un confronto che cambia anche le tabelle Orion. L'ipotesi su
  KOLF è nata sugli stessi lignaggi su cui è provata. Gli intervalli non coprono contesti nuovi.

## 5. Spiegazione semplice

Il transfer prevede l'effetto di spegnere un gene in una cellula nuova facendo la media di ciò che lo stesso
gene fa in altre cellule. Abbiamo tenuto fuori una cellula alla volta e chiesto alla media delle altre di
prevederla. Aggiungere tre fonti piccole (T1) non cambia la previsione in modo misurabile. Aggiungere una
staminale (KOLF) alla media aiuta a prevedere un'altra staminale e peggiora la previsione di una leucemia: una
media con pesi uguali funziona quando le cellule si somigliano.

## 6. Conseguenze

- La consegna resta **t36**; nessun candidato promosso, nessun invio preparato
  ([raccomandazione](../../reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/RACCOMANDAZIONE.md)).
- Il prossimo contrasto sul transfer riguarda la **composizione delle fonti** (un voto per lignaggio, H1 con le
  quattro linee). T2 si legge con la regola del contratto quando arrivano i suoi due banchi a sei membri: quello
  sul fold K562 non può finire prima del freeze, quindi alla scadenza T2 è inconcludente per regola.
- Il banco a lignaggio escluso e il contratto v2 sono lo strumento per i prossimi candidati; servono cellule
  vere per CD4T, HCT116 e HEK293 per avere più di due fold a sei membri.
- D-053 resta aperto; H1 test non è stata letta.

## 7. Cosa corregge

Nessun checkpoint. Precisa due letture senza cambiarne i numeri: in [CP-0068](0068-banca-canonica-release-r1.md)
il voto «quasi nullo» di Tian 2019 non dipende dal knockdown debole ma dalla centratura, che annulla il voto di
ogni tabella con un solo bersaglio; in [CP-0067](0067-t36-banca-estesa-punteggio-ufficiale.md) il guadagno
ufficiale del t36 resta descrittivo, e i banchi di oggi non lo sostengono sui lignaggi non staminali.

## 8. Domanda di comprensione

Perché una fonte con un solo bersaglio del pannello non può cambiare la direzione della previsione, qualunque
cosa abbia misurato?
