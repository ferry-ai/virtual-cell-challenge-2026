# R-V2 — il modello per il set finale, costruito adesso

- **Stato:** in corso.
- **Aggiornato:** 29 settembre 2026, 11:35 (ora italiana).
- **Assegnazione:** regia e filoni F1, F2 e F4: Claude (app, sessione `f4f38e58`), dal
  26/09 alle 00:20. Filone F3: codex via agent hub, lancio annotato qui sotto. Gli altri
  filoni sono liberi: prenderli annotando agente, sessione e ora in questa scheda.
- **Origine:** richiesta del proprietario del 25/09 notte: le architetture di lungo periodo
  si applicano adesso, con molti agenti, due ingegneri a tempo pieno e calcolo in cloud.
- **Dal 28/09, 12:40:** la scheda [R-REV](revisione-critica.md) raccoglie le azioni della revisione
  critica, su richiesta del proprietario. La prova generale F8 è la sua azione 3 (la presa in carico si
  annota anche nella riga F8 qui sotto); la misura decisiva della «Proposta per quando si riparte» è la
  sua azione 6. Questa scheda resta in pausa finché il proprietario non la riprende.
- **Ripresa il 28/09 alle 19:22** dal proprietario, in chat alla sessione Claude `f2abd9a6` (app desktop, sul
  portatile), che continua il lavoro della sessione `f4f38e58` fermata dal limite di spesa: «vogliamo sfornare un
  modello il prima possibile», con la scelta «entrambi in parallelo». Cioè:
  - la misura decisiva (azione 6 di R-REV) su Kaggle, con la regola scritta prima;
  - intanto disegno e codice della rete relazionale, pronta da addestrare se la misura dice sì;
  - sul portatile, la prova generale del 22 ottobre (F8, azione 3 di R-REV) con la ricetta del t22.

  Assegnazione di questi tre filoni: Claude, sessione `f2abd9a6`, dalle 19:22.
- **Rapporto con le altre schede:** esegue ciò che [R-MODELLI](trasferimento-modelli.md)
  proponeva; usa i dati di [R-DATI](dati-affidabilita.md); i punteggi ufficiali restano in
  [S-INVII](invii-finale.md).

## Obiettivo

Un modello che predice la risposta a un knockdown CRISPRi in un contesto nuovo (D/E/F) per
bersagli nuovi, con componenti biologiche esplicite, scelto su un banco che calcola i sei
membri ufficiali con lo scorer vero su contesti pubblici tenuti fuori. Il 22 ottobre deve
produrre un invio in poche ore.

## Architettura di destinazione

`effetto(t, c) = trasferimento(t, c) + cis(t) + programmi(z_t, z_c) + residuo`, dove:
- **trasferimento:** l'effetto dello stesso bersaglio misurato in altre sorgenti, ristretto
  per affidabilità, pesato per somiglianza fra contesti (H6) invece che a pesi uguali;
- **cis:** la repressione CRISPRi dei geni vicini al TSS, già nel t20
  ([banco](../../reports/trasferimento/modulo_cis_2026-09-26/RISULTATI.md));
- **programmi:** per i bersagli che nessuna sorgente ha misurato, coordinate sui programmi
  predette da descrittori del bersaglio (reti, complessi, embedding), modulate dallo stato
  del contesto letto dai controlli. La proiezione lineare dell'effetto trasferito sui
  programmi è già stata provata e perde
  ([programmi](../../reports/trasferimento/programmi_2026-09-26/RISULTATI.md)): i programmi servono dove
  manca l'effetto del bersaglio, non al posto del dettaglio misurato;
- **emissione:** un generatore di cellule calibrato sui controlli del contesto.

## Filoni

| ID | Filone | Chi | Stato | Consegna |
|---|---|---|---|---|
| F1 | Cache "universo": effetti di **tutti** i bersagli di ogni sorgente, non solo dei 300 | Claude | K562 fatto (9.866 bersagli, [report](../../reports/sorgenti/universo_2026-09-26/RISULTATI.md)); CD4 fatto il 26/09 sera (12.238 bersagli, parità esatta sul pannello, [CD4](../../reports/sorgenti/universo_2026-09-26/CD4.md)); Orion: HCT116 fatto il 26/09 alle 21:37 (16.438 bersagli con effetti, parità esatta sul pannello), HEK293T fatto il 27/09 alle 01:44 (17.270 bersagli con effetti, parità esatta sul pannello) ([ORION](../../reports/sorgenti/universo_2026-09-26/ORION.md)); K562 essential e RPE1 di Replogle per i confronti descrittivi dell'[atlante](../../reports/trasferimento/atlante_2026-09-26/RISULTATI.md) | cache nella radice dati, report con copertura |
| F2 | Banco con lo scorer vero su un contesto pubblico tenuto fuori (HepG2 a cellule singole): i sei membri, non proxy | Claude; job Colab `046_bench_hepg2_v2`, finito il 27/09 alle 16:16 UTC | fatto (r1) | [r1](../../reports/generatore_e_banchi/banco_hepg2_v2_2026-09-26/RISULTATI.md): la forma t19 batte la t16 (+0,026); raddoppiare la t19 dà +0,015 con l'intervallo sullo zero; testa cis nulla su HepG2 |
| F3 | Motore di valutazione C/T/J e basi di confronto (nullo, risposta comune, trasferimento, modello lineare con embedding dei geni) | codex, run `20260926-001005-v2-f3-ctj`: fermato dopo 3 min per quota ChatGPT esaurita, ha lasciato un `ctj.py` parziale non applicato; il prosieguo lo fa Claude | in corso | patch rivista e test |
| F4 | Modulo cis e pesi per contesto nel modello d'invio | Claude | cis fatto (t20) | t20 registrato |
| F5 | Descrittori dei bersagli nuovi: STRING, CORUM, GO, reti TF con segno, embedding di proteine | libero | serve il via ai download | tabelle sull'asse ufficiale |
| F6 | Contesti: stato dai controlli (p53, IFN, ciclo, linea) e somiglianza con le sorgenti | Claude (H6 su Mixscale) | somiglianza basale intera: non predice il trasferimento e pesarla peggiora ([report](../../reports/trasferimento/contesti_2026-09-26/RISULTATI.md)); restano aperte somiglianze per programma o per bersaglio | pesi per contesto provati sul banco |
| F7 | Calcolo in cloud: ambiente, dati, esecuzione di F2 e degli addestramenti | Claude, con Colab (dispatcher su Drive) e Kaggle (notebook privati via API) | Colab e Kaggle autorizzati dal proprietario il 27/09; RunPod solo chiedendo | job 046, 048, 049 e 050 su Colab; sonda e somme di VIPerturb-seq su Kaggle |
| F9 | Modello bersaglio × contesto a quattro parametri (precursore della rete): prove E1 ed E2 | Claude; `gated.py` di codex | r1 fatto il 27/09 sera con la regola delle 18:21: E1 non passa, E2 parziale (Orion sì, CD4 no, r ≈ 0,002); lo scambio di contesto vale quanto il contesto giusto | [report](../../reports/modelli/modello_contesto_2026-09-27/RISULTATI.md) |
| F10 | La rete su molti contesti: encoder del bersaglio e del contesto, decoder sui geni, via diretta sul trasferimento | claude2 (disegno e codice, 27/09 dalle 20:42; sessione interrotta dal limite d'uso a lavoro finito, messaggio finale mancante); autoverifica e addestramento su Kaggle/Colab | disegno e codice scritti, nulla eseguito | [DISEGNO](../../reports/modelli/rete_contesti_2026-09-27/DISEGNO.md) |
| F8 | Prova generale del 22 ottobre: 300 bersagli finti e contesti tenuti fuori, dall'input al .vcc | Claude, sessione `f2abd9a6`, dal 28/09 alle 19:22 (azione 3 di [R-REV](revisione-critica.md)) | prova fatta il 29/09 in forma ridotta, `.vcc` di D/E/F verificato ([CP-0044](../checkpoints/0044-prova-generale-22-ottobre.md)); restano i difetti D4, D9 e gli altri | tempo e copertura misurati |

## Esiti della notte del 26 settembre

- **Bersagli nuovi** ([report](../../reports/trasferimento/bersagli_nuovi_2026-09-26/RISULTATI.md)): per un
  bersaglio che nessuna sorgente ha misurato, il modulo cis da solo dà 0,555–0,579 di PDS proxy
  e 0,1 × STRING + cis fino a +0,035; lo stesso bersaglio misurato in K562 dà 0,711–0,755. Il
  modello lineare con embedding dei geni non discrimina nemmeno in campione.
- **Priorità che ne segue:** la copertura. Estrarre tutti i bersagli delle sorgenti genome-scale
  (CD4: file pseudobulk di 44,6 GB su S3 pubblico; Orion HCT116 e HEK293T: 109 e 223 file in
  streaming, accumulatori troppo grandi per il portatile) vale più di qualunque modello per
  bersagli senza misure. Poi cis + associazione per quelli che restano scoperti.
- **Ripiego per i bersagli scoperti, nello stadio 100:** blocco `association` (0,1 × media dei
  partner STRING nella cache universo, gene proprio di ogni partner escluso) prima del modulo
  cis; identico bit per bit sui 300 bersagli di oggi, provato con una ricetta solo-K562 (13 dei
  28 bersagli scoperti hanno partner).

## Esiti del pomeriggio del 26 settembre

- **Architettura a due canali** ([report](../../reports/trasferimento/trasferimento_appreso_2026-09-26/RISULTATI.md)):
  la direzione specifica del bersaglio viene dal trasferimento (t20); un modello di gradient
  boosting, addestrato solo su sorgenti pubbliche, impara quali geni si muovono in ogni contesto e
  ripesa il trasferimento (`src/vcc2026/transfer_model.py`, stadio 104; `src/vcc2026/priors.py`
  spostato dallo stadio 100, uscita identica bit per bit). r3/r4 davano +0,008…+0,010 di PDS
  attraverso il generatore, ma l'audit di codex ([audit_piani_dati_2026-09-26](../../reports/analisi/audit_piani_dati_2026-09-26/RISULTATI.md), recuperato e committato il 28/09: [R-020](../REGISTRO.md#r-020--evidenza-citata-ma-assente-dal-repository))
  ha trovato centri calcolati prima degli split (R-019). **Nel banco isolato (r5) il guadagno sulle
  linee nuove scende a +0,004…+0,008 (un intervallo su tre sopra zero) e l'nMAE proxy peggiora di
  +0,017…+0,051: per la regola fissata prima, niente t21.** Lo stadio 104 resta sperimentale,
  fuori dalla pipeline d'invio; la sua sorte si decide sul banco F2 con lo scorer vero.
- **Risposta comune** ([report](../../reports/trasferimento/risposta_comune_2026-09-26/RISULTATI.md)): la parte di
  risposta condivisa da tutti i knockdown vale l'1–14 % dell'energia nelle sorgenti pubbliche e non
  si trasferisce fra linee (correlazione 0,05–0,11); aggiungerla non abbassa l'errore quadratico.
  La `mse` ufficiale non si recupera da lì.
- **Pesi per contesto:** né la somiglianza del profilo basale (H6) né lo stato di p53 letto dai
  controlli migliorano in modo coerente ([contesti](../../reports/trasferimento/contesti_2026-09-26/RISULTATI.md)).
- **Agenti:** revisione di codex (due perdite trovate e corrette), critica di claude2, letteratura
  di grok, dataset di antigravity: in `reports/trasferimento/trasferimento_appreso_2026-09-26/agenti/`. La sessione
  `76a3a45e` lavora in parallelo sui prior dei bersagli nuovi.

- **Trasferimento gerarchico con Bayes empirico** ([report](../../reports/trasferimento/trasferimento_gerarchico_2026-09-26/RISULTATI.md)):
  risposta condivisa + deviazione di linea + rumore, CD4 con la varianza fra donatori. Non passa la
  regola: con tre o quattro linee la parte condivisa, gene per gene, si stima male.
- **Quattro sorgenti** ([report](../../reports/trasferimento/quattro_sorgenti_2026-09-26/RISULTATI.md)): il t20 con
  HEK293T a peso uguale passa la regola (errore sulle ampiezze più basso, discriminazione mista):
  candidato **t22**, registrato alle 13:34 UTC.
- **Membro `mse`** ([report](../../reports/trasferimento/risposta_comune_2026-09-26/RISULTATI.md), r2): la `mse`
  ufficiale dei nostri invii è 1 + E/4786, con E l'energia prevista; le previsioni sono quasi ortogonali
  agli effetti reali. Serve direzione migliore, non un'ampiezza diversa.
- **Regola D-045** del proprietario: niente stime dei tempi, niente giornate chiuse per un candidato fallito.

## Piano del 26 settembre sera: l'atlante multi-sorgente

Richiesta del proprietario: usare molti dati insieme, non un dataset alla volta. Download autorizzati
alle 15:25: universo CD4 genome-wide (44,6 GB, in corso) e universi Orion HCT116 e HEK293T (46,6 e 79,7 GB
in streaming, sottoagente di questa sessione, `reports/sorgenti/universo_2026-09-26/`). Con K562 fanno quattro linee
per circa 10.000 bersagli ciascuna, contro i 300 di oggi. Su quella base:
1. **Varianze della risposta stimate su migliaia di bersagli**: il modello gerarchico (già nello stadio 100,
   blocco `pooling`) con σ² e τ² per gene stimati sull'universo, non sul pannello.
2. **Coefficienti di trasferimento per gene** fra coppie di linee, appresi su tutti i bersagli condivisi
   tranne il pannello (regime C pulito per i 300).
3. **Programmi di risposta** da decine di migliaia di knockdown, per ridurre il rumore dei profili.
4. **Banco con migliaia di bersagli per linea tenuta fuori**: intervalli molto più stretti di quelli di oggi.
5. Poi HIPSCI (34 linee iPSC, catalogo in `reports/sorgenti/ricerca_sorgenti_2026-09-26/`), se il proprietario dà il via.

## Esiti della sera e della notte del 26–27 settembre

- **Universi:** CD4 genome-wide (12.238 bersagli) e Orion HCT116 (16.438) completi, con parità esatta sul
  pannello; HEK293T (17.270) completo il 27/09 alle 01:44, con parità esatta; K562 essential e RPE1 per i confronti
  ([universo](../../reports/sorgenti/universo_2026-09-26/CD4.md), [ORION](../../reports/sorgenti/universo_2026-09-26/ORION.md)).
- **Atlante r1** ([report](../../reports/trasferimento/atlante_2026-09-26/RISULTATI.md)): nessun braccio passa la regola
  su 1.000 bersagli fuori dal pannello per linea tenuta fuori. Programmi di risposta e accordo per bersaglio
  perdono ovunque; il modello gerarchico non separa la deviazione di linea dal rumore (τ² mediano 0); il più
  vicino è la quota condivisa per gene, che sul pannello passa una regola nuova fissata prima
  ([quota condivisa](../../reports/trasferimento/quota_condivisa_2026-09-27/RISULTATI.md)): candidato **t23**, registrato
  il 26/09 alle 23:14 UTC ([previsione](../../reports/invii/prediction_t23_2026-09-27/prediction.json)); l'invio
  aspetta il via del proprietario.
- **t22 valutato** il 26/09 alle 23:40 UTC: non conclusivo contro il t20 per la sua regola, punteggio
  ufficiale più alto finora ([confronto](../../reports/invii/prediction_t22_2026-09-26/comparison.json)).
- **t24** registrato il 27/09 alle 00:02 UTC e impacchettato alle 12:02: il t22 con un altro seme del
  generatore, per misurare il rumore del punteggio ufficiale fra due estrazioni della stessa previsione
  ([previsione](../../reports/invii/prediction_t24_2026-09-27/prediction.json)). t23 e t24 aspettano il via.
- **Atlante r2** (replica con HEK293T, finita alle 13:04 del 27/09,
  [report](../../reports/trasferimento/atlante_2026-09-26/RISULTATI.md)): la quota condivisa guadagna con le linee Orion
  tenute fuori, non con K562 e CD4. Stimata anche su HEK293T accanto a HCT116 si appiattisce: prima di
  usarla nel set finale va provata la stima con una linea per laboratorio (punto aperto).
- **Linea contro stato (descrittivo, stessi bersagli):** stati diversi delle stesse cellule CD4 0,20–0,25 di
  coseno mediano fra profili, due esperimenti K562 0,16, un'altra linea dello stesso laboratorio circa 0,07,
  un'altra linea e laboratorio 0,02. È la prova misurata più forte sulla domanda strategica qui sotto, ma
  confonde biologia, laboratorio, protocollo e rumore: non dimostra che la parte propria del contesto non si
  possa imparare ([revisione di codex](../../reports/analisi/revisione_codex_2026-09-27/REVISIONE.md), punto 4).
- **SE delle sorgenti Replogle:** calibrato sulle guide non mirate per i geni tipici; le ricette non
  restringono troppo il K562 (ipotesi chiusa).

## Pomeriggio del 27 settembre

- **Artefatto dello stimatore pseudobulk** ([report](../../reports/sorgenti/pseudoconteggio_2026-09-27/RISULTATI.md)):
  con il pseudoconteggio costante un gene senza conteggi vale ln(L_c/L_t); i geni Y delle donatrici CD4
  risultavano indotti da ogni knockdown (5,3–5,5 % dell'energia del t22 sui geni espressi in A e C).
  Correzione `min_expected` (cache r9); **t25** = t22 su r9, registrato alle 11:41 UTC, in generazione.
- **Revisione di codex** ([sintesi e risposta](../../reports/analisi/revisione_codex_2026-09-27/REVISIONE.md)):
  accettati i sei punti. Consegne: dati corretti e ablazioni (Claude: [ablazione del
  t23](../../reports/trasferimento/ablazione_t23_2026-09-27/RISULTATI.md), universi corretti); banco C/T/J congelato (codex);
  modello bersaglio × contesto (disegno a claude2).
- **Base di lancio:** modelli fissati in `agent-hub/control/agents.toml` su richiesta del proprietario
  (claude2 Opus 5.5 con sforzo massimo, codex GPT-6-Astra medio); in corso codex, grok (revisione della
  correzione), claude2 e antigravity (ricerca di dati multi-contesto).
- **Istruzione del proprietario:** per ora niente invii al server e niente push; t23, t24 e t25 restano
  impacchettati o in preparazione.

## Sera del 27 settembre: molti contesti in pipeline, e la rete

Direzione del proprietario: usare e analizzare quanti più dati possibile, per reti che imparino davvero.

- **Universi nuovi e corretti (misurato):**
  - CD4, HCT116 e HEK293T ricostruiti con lo stimatore corretto, con parità esatta sul pannello
    ([universi corretti](../../reports/sorgenti/universo_corretto_2026-09-27/RISULTATI.md));
  - **KOLF2.1J** (iPSC) con 10.985 bersagli, letto a intervalli di byte dal file di 189 GB;
  - **A549** (knockout, un'altra modalità) con 1.000 bersagli
    ([ingestione](../../reports/sorgenti/universo_nuovi_2026-09-27/RISULTATI.md)).
- **In corso:**
  - HIPSCI, 34 linee iPSC, schermo mirato per linea;
  - Southard, CRISPRa di 1.836 fattori di trascrizione in fibroblasti e RPE-1;
  - VIPerturb-seq, K562 letto con Flex come i contesti di gara: un ponte di chimica sulle risposte.
- **Controllo sul bersaglio (misurato):** il gene silenziato scende in ogni universo. La profondità mediana va da
  −1,81 (K562) a −0,62 (HEK293T) in log naturale.
- **Profondità e risposta** ([report](../../reports/sorgenti/profondita_silenziamento_2026-09-27/RISULTATI.md)):
  - bersaglio per bersaglio, un silenziamento più profondo va con una risposta più grande in tutte e dieci le
    coppie di linee, ma debolmente (misurato);
  - fra sorgenti la relazione non tiene (misurato);
  - quindi la profondità entra nella rete come covariata, non come normalizzazione delle sorgenti
    (interpretazione).
- **Banco HepG2 con lo scorer vero (F2):** fatto; vedi la riga F2.
- **Il piano (proposta):**
  - F9, il modello a cancelli, prova se il contesto letto dai controlli porta segnale (E1, e E2 sulle differenze
    fra due linee tenute fuori);
  - F10, la rete, lo generalizza:
    - encoder del bersaglio dalle sue risposte in tutte le linee, e dai prior per i bersagli mai misurati;
    - encoder del contesto da caratteristiche dei controlli robuste alla piattaforma, pre-addestrabile su
      profili basali di molte linee (DepMap 24Q4 è già in locale, 484 MB di espressione);
    - decoder sui geni, con una via diretta sul profilo trasferito, perché la proiezione su programmi ha
      perso;
  - valutazione sul banco C/T/J congelato, con le versioni cieca, scambiata e permutata come controlli.
- **Nota di disegno (misurato nel passaggio di prova e in r1):** sui bersagli presi a caso la risposta di una
  linea segue poco quella delle altre (A_fit 0,01–0,03), e molti bersagli non essenziali hanno pochi geni
  significativi oltre il caso. I prossimi banchi e l'addestramento vanno ponderati sui bersagli con risposta
  reale, come ha fatto chi ha scelto il pannello.

## Notte e mattina del 28 settembre: esiti e stato al momento della pausa

Stato scritto alle 10:40, quando il proprietario ha messo in pausa questo filone. Le istruzioni agli altri agenti
le dà il proprietario; la ripresa del filone è con lui, da qui.

### Misurato stanotte (dettagli nei report citati)

- **Encoder di contesto, prima tornata** ([RISULTATI](../../reports/modelli/encoder_contesto_2026-09-28/RISULTATI.md)), seme 0,
  regola registrata alle 03:10. Parte Orion:
  - nessuna condizione passa;
  - contro `none` guadagni di un millesimo di skill;
  - con l'embedding di un'altra linea la rete va meglio che con quello giusto;
  - E2 non passa.

  La parte K562/CD4 è finita su Kaggle ma non è scaricata né letta.
- **T1 ridotto sui farmaci di Tahoe** ([RISULTATI](../../reports/modelli/tahoe_bracci_2026-09-28/RISULTATI.md)), 48 linee:
  - non passa;
  - i vicini giusti battono quelli sbagliati (+0,06);
  - ma copiarli perde contro la media di tutte le linee (−0,14).
- **La rete su r1**, varianti descrittive ([r2/varianti_r1](../../reports/modelli/rete_contesti_r2_2026-09-28/RISULTATI.md)):
  la perdita sulla famiglia tenuta fuori è minima entro i primi 100 passi in ogni variante che può imparare.
- **Il ponte Flex–3'** ([RISULTATI](../../reports/sorgenti/ponte_flex_2026-09-28/RISULTATI.md)): VIPerturb-seq concorda con
  sé stesso 0,110 (metà contro metà), col 3' 0,030 sugli stessi bersagli.
- **Dati nuovi:**
  - corpus basale ([SORGENTI](../../reports/sorgenti/corpus_basale_2026-09-28/SORGENTI.md): una decisione per sorgente);
  - dataset della rete r2 con 12 contesti CRISPRi;
  - effetti per 19 linee HIPSCI (`reports/sorgenti/universo_hipsci_2026-09-27/linee_p2/`): il gene silenziato scende in 15;
    in fiaj_3, tolg_4, pipw_5 e oikd_2 poco o nulla.

### In corso o sospeso

- **r2** (la rete con più contesti, regola delle 04:00): due sessioni GPU su Kaggle partite alle 10:06, kernel
  `vcc-r2-s0-shard0` e `vcc-r2-s0-shard1`. La lettura A (r2 contro r1) si fa con
  `reports/modelli/rete_contesti_r2_2026-09-28/cross_compare.py`.
- **Da scaricare e leggere:**
  - la seconda sessione dell'encoder (`vcc-enc-s0-shard1`: K562 e CD4);
  - il seme 1 di r1 (`vcc-rete-r1-s1`).
- **Non lanciato:** il seme 2 di r1 (`vcc-rete-r1-s2`). Senza di lui la regola di r1 non si legge.
- **L'estrazione completa dei DMSO di Tahoe** (`vcc-tahoe-dmso`) gira ancora su Kaggle.
- **Dove stanno le cose.** Dati e uscite scaricate sono nella radice dati del portatile (`C:/Users/ferra/vcc2026-data`,
  fuori dalla repo). Kernel e dataset privati sono sul conto Kaggle del proprietario: servono le sue credenziali, che
  non vanno mai nella repo.

### Direzione del proprietario (28/09 mattina)

- **Usare tutti i dati**, anche quelli fermi, e non trasferire il comportamento. Una rete che impari **relazioni**:
  - «spengo x, y si muove perché è legato a x»;
  - geni che si muovono insieme in molti knockdown formano **gruppi di comportamento** che si ritrovano nel contesto
    successivo.
- **I dati farmacologici** (Tahoe) non devono prevalere nei dati di addestramento, almeno all'inizio.

### Proposta per quando si riparte (da decidere con il proprietario)

1. **Misura decisiva, con i dati che ci sono:** chi si muove con chi (la correlazione fra geni delle risposte, su
   molti bersagli) è conservato fra linee più dell'effetto del singolo bersaglio? Se sì, la rete relazionale ha una
   base; se no, non trasferirà nemmeno lei.
2. **Disegno della rete relazionale:**
   - carte dei geni imparate da tutti i knockdown;
   - moduli;
   - contesto come modulazione dei moduli;
   - stesse prove (famiglie tenute fuori, cieco, scambio, E2);
   - i farmaci con peso limitato.
3. **Ingestione per contesti nuovi**, prima le perturbazioni genetiche:
   - Mixscale (più linee con citochine);
   - lo schermo Jurkat;
   - neuroni iPSC;
   - microglia.

   Poi, con peso contenuto, Tahoe completo e LINCS L1000.

## Pomeriggio del 28 settembre: gli esiti in attesa, letti con le loro regole

Claude, sessione `f4f38e58`, dopo l'unione del branch della revisione (scheda [R-REV](revisione-critica.md), §0).

**Misurato:**
- **Encoder, prima tornata:** nessuna condizione passa, su tre verità E1
  ([RISULTATI](../../reports/modelli/encoder_contesto_2026-09-28/RISULTATI.md)).
- **r2** ([RISULTATI](../../reports/modelli/rete_contesti_r2_2026-09-28/RISULTATI.md)):
  - l'encoder su r2 crolla;
  - la rete da sola ha ancora il minimo sulla famiglia tenuta fuori alla prima valutazione;
  - lettura A su Orion, stessi bersagli: r2 − r1 +0,0018 [+0,0005; +0,0030] su HCT116 e −0,0072 [−0,0096; −0,0050]
    su HEK293T (disegno E2). K562 e CD4 in corso.
- **r1, i tre semi:** in tutti e tre i semi la rete batte la sua versione cieca su tutte e cinque le verità E1, nello
  spazio degli effetti; l'E2 non passa in nessun seme. La lettura con la regola (proxy combinato sulle previsioni
  mediate) è in corso.
- **Tahoe:** T1 ridotto non passa ([RISULTATI](../../reports/modelli/tahoe_bracci_2026-09-28/RISULTATI.md));
  l'estrazione completa dei DMSO è finita su Kaggle.

## Sera del 28 e mattina del 29 settembre: la misura decisiva, e che cosa resta

Claude, sessione `f2abd9a6`. Letti con le loro regole (misurato):
- **r1 sui tre semi** ([lettura](../../reports/modelli/rete_r1_lettura_2026-09-28/RISULTATI.md)):
  - uso del contesto ed E2 non passano;
  - la rete perde contro il trasferimento `excl` su K562, HCT116 e HEK293T;
  - passa solo J, di un millesimo.
- **r2, lettura A** ([r2](../../reports/modelli/rete_contesti_r2_2026-09-28/RISULTATI.md)): passa, provvisoria con un
  seme. Più contesti CRISPRi aiutano la rete di pochi millesimi.
- **La misura decisiva** (azione 6 di R-REV, [CP-0043](../checkpoints/0043-misura-decisiva-relazioni.md)):
  inconclusiva per W1, lettura «uso» no. La via delle relazioni non prevede la risposta a un knockdown nemmeno nella
  stessa linea. **La rete relazionale non parte**: codice e autoverifica (12 su 12) restano in
  [rete_relazionale](../../reports/modelli/rete_relazionale_2026-09-28/RISULTATI.md).
- **t23 inviato** con il via del proprietario ([CP-0042](../checkpoints/0042-t23-esclusione-pds.md)): non conclusivo
  sulla media, ma il PDS ufficiale sale di +0,011 grezzo e i membri DE scendono.

**Scelta del proprietario (29/09, 11:25):** la prova generale del 22 ottobre (F8, azione 3 di R-REV) e il banco con lo
scorer vero sui bersagli del pannello (azione 4 di R-REV), che serve a scegliere il prossimo invio senza il proxy
(CP-0041).

## Domanda strategica aperta

Le squadre in testa hanno PDS 0,82–0,87 con mse 0,6–0,85, molto oltre quello che il trasferimento
da linee diverse ci ha dato finora. Una spiegazione possibile (**ipotesi**, non verificata) è
l'uso di dati pubblici della **stessa linea** dei contesti, dopo averla identificata. Per D/E/F
significherebbe: identificare le tre linee dai controlli (lo stadio 99 fa impronte genetiche),
cercare Perturb-seq pubblici di quelle linee, trattarli come sorgenti. La regola del proprietario
ammette dati della stessa linea solo come esperimento dichiarato, con le identità fuori dal
repository pubblico: serve la sua decisione su se e come farlo.

## Che cosa serve dal proprietario

- Fatto il 27/09: claude2 e grok lavorano dalla base di lancio; Colab e Kaggle sono autorizzati. RunPod resta
  da chiedere, e il suo connettore va autorizzato nelle impostazioni.
- Via ai download non ancora autorizzati, con dimensioni e licenze prima di scaricare:
  - DepMap CRISPRGeneEffect (428,7 MB), per sapere quali geni contano in quale linea;
  - profili basali per l'encoder di contesto: MIX-seq controlli (0,37 GB), Kinker 2020 (dimensione non
    indicata), DepMap 26Q1 (305 MB);
  - De Simone 2025, Flex contro 3' sugli stessi PBMC;
  - il dataset completo della gara 2025 (H1);
  - vedi [ricerca](../../reports/sorgenti/ricerca_sorgenti_2026-09-27/RISULTATI.md).
- Via agli invii: nessun filone invia da solo; per ora niente invii né push.

## Protezioni

Valgono [GENERALIZZAZIONE](../GENERALIZZAZIONE.md) e D-044: nei regimi T/J nessuna risposta
dei bersagli di test entra in training, basi, embedding o pesi. Un proxy non è un punteggio.
Ogni affermazione su un dataset va controllata da una seconda famiglia di modelli prima di
arrivare al proprietario.

## Criterio di chiusura

Un modello scelto sul banco F2 con regola registrata prima, pronto a produrre un invio D/E/F
in poche ore, e un checkpoint che confronta i filoni con il t20.
