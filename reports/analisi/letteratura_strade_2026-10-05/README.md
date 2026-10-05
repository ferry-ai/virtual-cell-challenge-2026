# Letteratura aggiornata e strade di miglioramento, dopo il banco v2 di Davide

5 ottobre 2026, Claude Code per Alfredo (sessione `42343bb9`). Richiesta: «partiamo dalla letteratura, individuiamo
strade per fare improvement», ora che i file Kaggle e il codice di Davide sono condivisi.

**Che cosa è questa pagina.**
- Aggiorna la [revisione del 2 ottobre](../letteratura_strade_2026-10-02/README.md) e la sua
  [correzione](../letteratura_strade_2026-10-02/CORREZIONE_STRADA_A.md), senza riscriverle.
- Si basa su tre letture nuove:
  - la classifica pubblica del 5 ottobre, con lo stesso
    [`leggi_classifica.py`](../letteratura_strade_2026-10-02/leggi_classifica.py);
  - i risultati di Davide su main fino a `bf6fa6f`;
  - le fonti uscite dopo il 2 ottobre o non lette allora.
- Non ci sono training, invii o download di dati.
- Le strade sono **proposte**: ognuna va registrata prima di misurarla.
- Rispettano la regola del proprietario: **i candidati sono solo modelli appresi**; i transfer servono solo da baseline.

**Quanto ho letto.** Di quasi tutte le fonti nuove solo l'abstract o il README (colonna «Letto»).

## 1. In otto righe

1. **Classifica del 5/10** (1.331 entrate):
   - rango 1: 0,435; rango 20: 0,275; rango 100: 0,229; rango 200: 0,198;
   - il nostro t28 (0,1448) oggi sarebbe **422°**.
2. **Il distacco è quasi tutto nella MSE.** Delle 191 entrate sopra 0,20, 186 hanno la MSE scalata sopra 0,1 e
   nessuna l'ha a 0. Tutti i nostri invii hanno la MSE a 0, e anche il banco v2 di Davide la dà a 0 su tutte le linee
   e tutti i bracci.
3. **Perché.** La MSE esce da zero solo se il profilo aggregato previsto ha un coseno con quello vero di almeno 0,22
   circa ([margini_orizzonte](../margini_orizzonte_2026-10-04/)). Il nostro è circa 0,11–0,13.
4. **Il PDS dipende anch'esso da quella direzione.** Quindi la leva è una sola: **la direzione del profilo
   aggregato su tutti i geni**. L'ampiezza e l'emissione vengono dopo.
5. **Il banco v2 di Davide indica la stessa leva.** Sorgenti in più (`all` contro `prod`) valgono, in scala locale:
   - +0,037 su H1, +0,043 su RPE1, +0,039 su Jurkat;
   - +0,098 su HepG2 e +0,111 su K562.

   Il dato di K562 è gonfiato (§4).
6. **I primi senza dati privati** (rango 16 e 21, 0,274–0,279) dichiarano di aver lavorato proprio su questo:
   - 33 profili sorgente, restringimento con SE da bootstrap, tetto per dataset;
   - smussamento PCA per contesto, energia ripartita per accordo fra sorgenti.
7. **La letteratura del 2026** propone tre modi appresi per migliorare quella direzione:
   - scomporre la risposta (Molina e Zhang);
   - una base a basso rango (Stable-Shift);
   - un filtro dei geni che non rispondono (AdaPert).
8. **Proposta.** Un modello appreso che prevede il profilo aggregato della linea tenuta fuori, addestrato a
   linee escluse sulle tabelle del cubo condiviso. Si giudica prima col **coseno aggregato** sul banco v2 (rapido,
   senza scorer), poi coi sei membri.

## 2. Fonti nuove o non lette il 2 ottobre

| Fonte | Che cosa dice | Che cosa implica per noi | Letto |
|---|---|---|---|
| [Molina e Zhang, bioRxiv 2026](https://www.biorxiv.org/content/10.64898/2026.07.24.740459v1), [codice](https://github.com/xinyizhanglab/perturbation-decomposition) | Δ = μ + α_linea + β_pert + γ, stimati con ANOVA. La parte globale è a basso rango (proliferazione, stress) e **si ricava dai controlli**. Per le linee nuove usano Ridge o MLP con PCA dei profili DepMap. Dati: K562, RPE1, HepG2, Jurkat | Si possono addestrare a parte la parte comune della linea, dai suoi controlli, e quella specifica del bersaglio, sugli effetti centrati. Il t30 ha perso PDS con una quota comune di 0,62–0,69 all'esportazione: è proprio il difetto che questa separazione evita | abstract, README del codice |
| [Stable-Shift, arXiv 2606.24940](https://arxiv.org/abs/2606.24940) | Una base a basso rango delle risposte, costruita sulle perturbazioni di training; le coordinate dei bersagli nuovi vengono da una convoluzione su grafo (STRING, GO, statistiche dei controlli). Coseno 0,592 contro 0,569 di GEARS su K562 | Proiettare il profilo aggregato su una base appresa nelle linee di training toglie il rumore dei geni non strutturati e alza il coseno | abstract |
| [AdaPert, arXiv 2602.18885](https://arxiv.org/abs/2602.18885) (ICML 2026) | Contro il «collasso sulla media»: sottografi sparsi per perturbazione e un filtro sui geni che non rispondono. I guadagni maggiori sono sulle metriche pesate sui DEG | Nella MSE su tutti i geni pesa l'energia dei geni che non rispondono: va appreso dove spegnerla | abstract |
| [Score Distributions, Not Cells, arXiv 2607.04595](https://arxiv.org/abs/2607.04595) | Le metriche per cellula misurano la sovrapposizione delle popolazioni, non la qualità del modello. Propone una CDS a livello di popolazione | Conferma che PDS e MSE vanno ottimizzati sul pseudobulk, non sulle cellule | abstract |
| [X-Cell e X-Atlas/Pisces (Xaira)](https://www.biorxiv.org/content/10.64898/2026.03.18.712807v1) | 25,6 milioni di cellule CRISPRi in 16 contesti (HCT116, HEK293T, HepG2, iPSC, Jurkat a riposo e attivati, iPSC in differenziamento); zero-shot su CD4 | Sarebbe la sorgente più utile in assoluto, ma [il dataset](https://huggingface.co/datasets/Xaira-Therapeutics/X-Atlas-Pisces) è ancora «Coming Soon» (licenza CC-BY-NC-SA-4.0); [nessuna data](https://github.com/Xaira-Therapeutics/X-Cell/issues/3). Da ricontrollare prima del 22/10 | pagina HF, issue, abstract |
| [C3TL, arXiv 2603.13051](https://arxiv.org/abs/2603.13051); [GNN con prior, bioRxiv 2026](https://www.biorxiv.org/content/10.64898/2026.03.23.713780v1) | Modelli leggeri, competitivi coi foundation model, per bersagli o contesti nuovi | Utili solo per i bersagli senza sorgente, che nel pannello sono pochi | abstract |
| [Atlas transfer, rango 82 a settembre](https://github.com/kaipengm2/Virtual-Cell-Challenge-2026) | Cinque sorgenti (K562, HCT116, HEK293T, H1 2025, CD4) in un insieme pesato, correzione dei vicini di promotore, emissione che rispetta la CPM media e il pseudobulk; 0,1546 | Stesse sorgenti della nostra ricetta più H1 2025: il guadagno su di noi è piccolo | README |

### Che cosa dichiarano le entrate che ci interessano (classifica del 5/10)

Sono dichiarazioni degli autori, non verificate.

| Rango | Media | PDS / MSE scalati | Che cosa dichiarano |
|---|---|---|---|
| 16 | 0,279 | 0,761 / 0,334 | Multisorgente con 33 profili; restringimento con SE da bootstrap; almeno 10 cellule perturbate; tetto del 12,5% per dataset, con gli stati CD4 raggruppati; «power lift» dei DEG attesi; allocazione di Poisson moltiplicativa |
| 21 | 0,274 | 0,768 / 0,413 | Smussamento PCA per contesto; energia ripartita per accordo; fold change L1-ottimali neutri per rango; p-value riordinati per probabilità del segno |
| 154 | 0,210 | 0,641 / 0,214 | Ampiezza 1,85 con **la componente comune ai bersagli tolta dal profilo aggregato** |
| 266 | 0,177 | 0,682 / 0 | **L'unica rete appresa dichiarata in alto:** GenePT, STRING e DepMap, decoder lineare, perdita contrastiva di ranking. MSE a 0, come noi |
| 343 | 0,159 | 0,579 / 0 | Pesatura appresa delle sorgenti con attenzione sul contesto: MSE a 0 |

**Lettura.**
- Le reti che imparano «quale sorgente pesare» o un decoder dagli embedding restano con la MSE a 0.
- Le entrate con la MSE alta lavorano sul **rumore del profilo aggregato**: restringimento, smussamento PCA, tetti
  e accordo.
- La nostra rete deve quindi imparare proprio questa pulizia.

## 3. Il punto tecnico: che cosa deve imparare il modello

- **La MSE normalizzata** è ‖p − t‖² / ‖t‖², con p il profilo aggregato previsto e t quello vero, rispetto al
  controllo. Vale 1 se si prevede il controllo; lo zero scalato cade a un grezzo di 0,986–0,992.
- **Con p = a · u** e coseno c fra u e t, l'ampiezza migliore dà un grezzo di **1 − c²**:
  - per scendere sotto 0,99 serve c ≥ 0,1;
  - ma le ampiezze utili ai membri DE spostano la soglia verso 0,22 (margini_orizzonte).
- **Il rango 21** (grezzo 0,595) implica c ≥ 0,64 circa (= √(1 − 0,595), il minimo all'ampiezza ottima); il
  rango 16 (grezzo 0,670) c ≥ 0,57.
- **Da dove viene il nostro coseno basso.** Il coseno è calcolato su tutti i 18.533 geni:
  - migliaia di geni con effetti stimati rumorosi aggiungono energia senza aggiungere direzione;
  - la parte comune ai bersagli, se sbagliata per la linea nuova, sposta la direzione di tutti.
- **Il bersaglio del modello** è quindi la **media a posteriori** del profilo della linea tenuta fuori, dati gli
  effetti delle sorgenti:
  - restringe ciò che non si trasferisce;
  - stima a parte la parte comune;
  - si giudica col coseno aggregato e con la MSE.

  È un problema di regressione, adatto a un modello appreso piccolo, con dati sufficienti: 10 gruppi di linee nel
  cubo, migliaia di bersagli e 18.533 geni.
- **I membri DE** (nMAE, fedeltà, reach) restano all'emissione, che oggi vale già circa il rango 100.

## 4. Come leggere il «+0,04…+0,11» di `all` sul banco v2

- **K562 è gonfiato.** Quando K562 è la linea tenuta fuori, `prod` perde la sua tabella principale (K562) mentre
  `all` tiene RPE1, HepG2, H1, KOLF e HipSci. In gara invece K562 resta nelle sorgenti.
- **Le stime più vicine alla gara** sono H1, RPE1 e Jurkat: circa +0,04 in scala locale.
- **La scala locale amplifica.** Il t28 valeva +0,029 sul suo banco locale e +0,0046 sul sito. Il banco era diverso,
  quindi il rapporto è solo indicativo.
- **Attesa onesta per `all` sul sito:** +0,005…+0,015, non +0,04, finché la MSE resta a 0.
- **Il premio grande** (fino a +0,05–0,07 sulla media, se la MSE scalata arrivasse a 0,3–0,4) passa dal coseno
  aggregato, non dalla sola scelta delle sorgenti.

## 5. Le strade, in ordine di guadagno atteso per giorno di lavoro

Tutte sono modelli appresi, con `all` (e `prod`) come baseline e lo stesso banco: la nostra copia del banco v2, con
le stesse linee, le stesse 400 cellule, i cinque semi appaiati e l'emissione t28.

**Si aggiunge una misura veloce, senza scorer:** il coseno, su tutti i geni, fra il profilo aggregato previsto e
quello vero (metà A), e la MSE grezza all'ampiezza ottima. Serve a scartare in pochi minuti ciò che non muove la
direzione.

| # | Strada | Che cosa si apprende | Fonti | Guadagno possibile sulla media | Costo | Rischio |
|---|---|---|---|---|---|---|
| 1 | **Pulizia appresa del profilo aggregato** («stacker a posteriori») | Per ogni coppia gene × bersaglio, la media a posteriori dell'effetto nella linea tenuta fuori. Ingressi: effetti `shrunk` per gruppo, SE, numero di cellule, accordo di segno fra gruppi, CPM dei controlli nella linea nuova, frazione comune. Uscita: un fattore di restringimento in [0, 1] per l'effetto di T (positivo, che **conserva il segno**: protegge il PDS). Perdita: la MSE normalizzata del profilo aggregato, più una guardia contrastiva sul PDS. Addestramento escludendo una linea per volta sui gruppi del cubo | AdaPert (filtro dei geni che non rispondono); rango 16 (restringimento con SE, tetti); TRADE (distribuzione degli effetti veri) | da +0,02 a +0,06 se il coseno arriva a 0,3–0,5; circa 0 se non si muove | 2–3 giorni; cubo già leggibile, nessuna GPU | Pochi gruppi (10): parametri pochi e condivisi fra geni. Si decide sul coseno delle linee tenute fuori, mai su A/B/C |
| 2 | **Parte comune dai controlli** (scomposizione allineata) | μ + α_linea appresi da regressione Ridge o MLP sull'espressione dei controlli della linea (ed eventualmente DepMap), addestrati a linee escluse. La strada 1 lavora poi sugli effetti **centrati** (β + γ) | Molina e Zhang (codice pubblico); rango 154 (comune tolta, MSE 0,214); diagnosi del t30 (quota comune 0,62–0,69) | da +0,01 a +0,03, in parte sovrapposto alla strada 1 | 1–2 giorni (si riusa `j_table_means` del cubo per le medie comuni per tabella) | Stimare la parte comune è esso stesso un trasferimento; va confrontato col «togliere e basta» |
| 3 | **Base a basso rango** | Base PCA delle risposte delle linee di training, con il numero di componenti e il restringimento delle coordinate scelti a linee escluse; il profilo della strada 1 proiettato sulla base | Stable-Shift; rango 21 (smussamento PCA per contesto) | si somma alla 1 se la 1 lascia rumore strutturato | 1 giorno sopra la 1 | Toglie anche segnale specifico: guardia sul PDS per linea |
| 4 | **Momento DE appreso** (segno e magnitudine) | Probabilità del segno da accordo, forza e risposta generica; magnitudini L1-ottimali; riordino dei p-value per probabilità del segno | Rango 21; la nostra [rete_l1](../../modelli/rete_l1_2026-10-04/) (t35 mai provato sul banco) | da +0,003 a +0,01 sui membri DE | il banco del t35 è già pronto; mezza giornata per portarlo sul banco v2 | Lo spostamento dei conteggi cambia un terzo delle chiamate DE: va letto coi sei membri |
| 5 | **Prior per i bersagli senza sorgente** | Embedding di GenePT, STRING e DepMap verso la base della strada 3 | Stable-Shift, C3TL, rete GNN 2026; rango 266 | piccolo: il pannello è quasi tutto coperto | 2 giorni | Basso, ma rende poco |
| — | **Sconsigliato** | Foundation model (STATE, X-Cell, scGPT); reti per cellula (t29); pesatura delle sorgenti con attenzione (rango 343: MSE 0) | letteratura e classifica concordi | — | — | — |
| — | **Da sorvegliare** | X-Atlas/Pisces: se esce prima del 22/10, HepG2, Jurkat e iPSC CRISPRi diventano sorgenti nuove per il cubo | Xaira | potenzialmente il più grande | ingestione: giorni | Licenza NC-SA, come Orion |

**Divisione con Davide.** Il suo ibrido semplice ([PROTOCOLLO](https://github.com/ferry-ai/virtual-cell-challenge-2026/blob/main/reports/modelli/ibrido_pseudobulk_2026-10-04/PROTOCOLLO.md))
è T_all + w·R, con R una MLP residua addestrata con una perdita KL sulle proporzioni. Le strade 1–3 sono diverse e
complementari:
- non aggiungono un residuo, **restringono e centrano T**;
- la loro perdita è la MSE del profilo aggregato con la guardia sul PDS.

Il fattore della strada 1 si può anche applicare a T + w·R.

## 6. Ordine proposto

1. **Il banco.** Finire il porting del banco v2 sul nostro account, con il coseno aggregato aggiunto come lettura
   rapida.
   - Serve l'ok a scaricare i file piccoli di metadati del cubo (circa 1 MB), chiesto nel messaggio precedente.
   - La verità viene dai frammenti rlab; i bracci sono `all` e `prod` del cubo, in regime C.
2. **La baseline.** Misurare il coseno aggregato di `all` e `prod` sulle cinque linee. È la linea di base: se è già
   ≥ 0,22, la MSE si sblocca solo con l'ampiezza giusta.
3. **Strade 2 e 1.** Prima la 2, che è rapida e dice quanta parte del rumore è comune; poi la 1, sopra gli effetti
   centrati. Protocollo registrato prima.
   - Regola proposta: coseno aggregato medio su almeno 4 linee su 5 sopra `all` di almeno +0,05, senza perdita
     risolta di PDS su alcuna linea;
   - poi i sei membri sul banco v2.
4. **Strada 3**, solo se dopo la 1 resta rumore strutturato.
5. **Strada 4** sul banco v2, in parallelo, perché è già pronta.
6. **Per l'invio:** un solo invio di conferma quando un braccio passa la regola sul banco. La quota resta di due al
   giorno per la squadra.

## 7. Decisioni per Alfredo

1. L'ok a scaricare i metadati del cubo (circa 1 MB) per il porting del banco v2.
2. Se le strade 1 e 2 sono la direzione da prendere. Sono modelli appresi; la base è un transfer, usato come
   ingresso e come baseline.
3. Se mandare a Davide il §4 (la lettura di `all` contro `prod`) e la divisione del §5.
4. Questa pagina descrive la strategia e il repository è pubblico: se pusharla subito o tenerla locale fino al
   5 novembre.
