# La misura decisiva per la rete relazionale: protocollo e regola

28 settembre 2026. Scrive Claude (app desktop, sessione `f2abd9a6`); orari letti da `date`. Scheda
[R-REV](../../../docs/piani/revisione-critica.md), azione 6; [revisione](../../analisi/revisione_criticita_2026-09-28/REVISIONE.md),
§3.2; proposta 1 della scheda [R-V2](../../../docs/piani/modello-v2.md), ripresa dal proprietario il 28/09 alle 19:22.

Etichette: **misurato**, **interpretazione**, **ipotesi**, **proposta**. Spazio degli effetti, sorgenti pubbliche:
**nessun numero qui è un punteggio VCC.**

**Protocollo fissato alle 19:56 del 28/09, prima di qualunque calcolo sui valori degli effetti.** La mappa dei dati
che lo prepara ha letto solo indici, intestazioni dei file, la finitezza degli SE e i CPM dei controlli: nessun
effetto. Il disegno viene da un sottoagente di questa sessione, rivisto qui.

## Domanda

1. **Mappa.** Chi si muove con chi, cioè la correlazione fra geni delle risposte su molti bersagli, è più conservato
   fra linee dell'effetto del singolo bersaglio?
2. **Uso.** Se lo è, serve a prevedere la risposta di una linea nuova a un knockdown?

La seconda è quella che una rete sfrutterebbe: «spengo x, y si muove perché è legato a x».

## Dati

- **Su Kaggle, dal dataset privato della rete r2** (`processed/rete_contesti_r2`, 13 contesti, `raw`, `se` e `shrunk`
  in float16), senza caricare nulla:
  - k562, k562ess, viperturb, rpe1;
  - cd4_Rest, cd4_Stim8hr, cd4_Stim48hr;
  - orion_hct116, orion_hek293t;
  - kolf, hipsci_fit, hipsci_nonfit, a549.
- **In locale**, perché non stanno in r2:
  - le 19 linee HIPSCI dello schermo mirato (`universe_hipsci_<linea>_2026-09-28_p2`), messe da parte le quattro con
    silenziamento debole: fiaj_3, tolg_4, pipw_5, oikd_2;
  - le due metà di VIPerturb-seq (`universe_viperturb_2026-09-28_halfa|halfb`);
  - le righe delle guide non mirate nei file bulk di Replogle (K562).
- **Bersagli:** esclusi i 300 del pannello (`in_panel`: in r2 sono segnati, non tolti).
  - «Rispondente» in un contesto vuol dire almeno 30 geni di G* con |raw/SE| ≥ 3.
- **Geni: G*,** i 2.887 geni conservati in r2 con CPM ≥ 20 nei controlli di k562, rpe1, cd4_Rest, orion_hct116,
  orion_hek293t, kolf, viperturb e di A, B, C (misurato sulle colonne basali, senza effetti).
  - Sono scelti solo dai controlli.
  - Per ogni bersaglio si tolgono il suo gene e la finestra cis di 5 kb.
- **Effetti:** `raw` è il primario, `shrunk` la sensibilità.

## Coppie

- **P9, la lettura principale.** Altro laboratorio e altra linea: tutte le coppie fra k562, cd4_Rest, orion_hct116,
  kolf e viperturb, tranne k562 × viperturb (stessa linea).
- **Repliche:** hek293t al posto di hct116, rpe1 al posto di k562, cd4_Stim48hr al posto di cd4_Rest.
- **Strati di controllo:**
  - S0, tetti: le metà di VIPerturb; cinque coppie HIPSCI dello stesso donatore (eipl_1/3, iudw_1/4, jejf_2/3,
    kolf_2/3, paab_3/4);
  - S1, stessa linea e stesso laboratorio: k562 × k562ess;
  - S1b, stessa linea e altro laboratorio o chimica: viperturb × k562, hipsci_kolf_2 × kolf;
  - S2, stessi donatori e altro stato: le tre condizioni CD4;
  - S3, stesso laboratorio e altra linea: k562 × rpe1, hct116 × hek293t, le coppie HIPSCI di donatori diversi;
  - S5, altra modalità: a549, descrittivo.

## Preparazione

- **Divisione.** Per ogni coppia, l'insieme P dei bersagli condivisi, fuori dal pannello e rispondenti in entrambi i
  contesti si divide a caso in due metà disgiunte H1 e H2.
  - La divisione è stratificata per `essential` e per decili del numero di geni significativi.
  - Tre semi.
- **In ogni contesto, sugli effetti:**
  - si toglie la media sui bersagli (la risposta comune, che è propria della linea: misurato nella
    [risposta comune](../../trasferimento/risposta_comune_2026-09-26/RISULTATI.md));
  - si standardizza per gene;
  - si normalizza il profilo di ogni bersaglio;
  - si tolgono i primi k assi propri del contesto: k = 3 è il primario; 0, 1 e 10 si riportano.
- **Prima di ogni statistica** si scrive nel registro della corsa quanti bersagli rispondenti condivisi ha ogni coppia
  (controllo W6).

## Misure

- **M1, la mappa.**
  - K è la matrice di correlazione gene × gene sui bersagli di una metà.
  - Q_cov(c,d) è la media di Mantel(K_c^H1, K_d^H2) e Mantel(K_c^H2, K_d^H1). Le metà hanno bersagli disgiunti,
    quindi nessun accordo per bersaglio può entrarci.
  - Il tetto è C_cov(c) = Mantel(K_c^H1, K_c^H2).
  - Il nullo è la media di 100 permutazioni delle etichette dei geni dentro 20 fasce d'espressione.
  - ρ_cov = (Q − nullo) / √[(C_c − nullo_c)(C_d − nullo_d)].
- **M2, l'effetto.**
  - Q_eff è il coseno medio per bersaglio, con la stessa preparazione.
  - Il nullo sono 200 permutazioni dei bersagli dentro strati (decili di geni significativi × `essential`).
  - ρ_eff = (Q_eff − nullo) / media_t √(r_c(t) r_d(t)). r è la quota di segnale del profilo, stimata dagli SE:
    - calibrati per fascia d'espressione con le guide non mirate per Replogle;
    - calibrati sulle metà di VIPerturb per le sorgenti a pseudobulk;
    - con il fattore 2 di CD4 fra famiglie.
- **Contrasto:** D = ρ_cov − ρ_eff, a k = 3. Intervallo con jackknife su 20 blocchi di bersagli, gli stessi per M1 e
  M2.
- **M3a, l'uso.** Per ogni contesto h di P9:
  - i bersagli di prova sono metà dei rispondenti in h il cui gene x è conservato in r2 e ha varianza di segnale
    sopra zero nelle fonti;
  - le loro righe escono da tutte le sorgenti, e da ogni media, deviazione e β (D-044).
  - **Via delle relazioni:** −β_s(x, ·), la pendenza di ogni gene sul gene x attraverso gli altri knockdown della
    fonte s, mediata sulle fonti. Le fonti sono gli altri quattro contesti di P9. Si escludono i knockdown che hanno x
    nella loro finestra cis.
  - **Via dell'effetto:** la media degli effetti dello stesso bersaglio nelle fonti.
  - **Abilità specifica Δ:** il coseno con la verità, meno quello con i bersagli permutati dentro strati:
    - per le relazioni, decili del CPM basale di x e della sua varianza di segnale;
    - per l'effetto, decili di geni significativi × `essential`.

    Questo nullo toglie l'abilità generica: molti x caricano sull'asse della crescita, e molte verità pure.
  - **Tetto interno:** Δ_rel^in, con β imparato in h stesso sui suoi bersagli di addestramento.
  - **Via combinata:** la somma delle due direzioni normalizzate, senza pesi stimati.
  - Intervallo con bootstrap sui bersagli di prova, 1.000 ricampionamenti.

## Controlli di validità

- **W1, tetti.** In ogni contesto di P9, C_cov − nullo ≥ 0,05 e media di √r ≥ 0,2.
  - Un contesto che non passa esce.
  - Con meno di 4 contesti su 5 il verdetto è «inconclusivo».
- **W2, ordine.** Per M1 e per M2 la mediana di S0 ∪ S1 deve superare quella di P9. Se l'ordine non torna, la misura
  non riconosce una struttura nota: «inconclusivo».
- **W3, SE.** Il fattore di calibrazione stimato sulle metà di VIPerturb deve stare in [0,5; 2]. Altrimenti M2
  normalizzato non si legge fuori da VIPerturb, e la lettura «mappa» aspetta la fase B.
- **W4, rumore in M1.** Su viperturb × k562, ρ_cov con le matrici di una metà contro la matrice incrociata metà A ×
  metà B. Se differiscono di più di 0,10, la lettura «mappa» si fa sui geni con quota di segnale ≥ 0,5 in entrambi i
  contesti. La scelta è fissata ora.
- **W5, base basale.** Per le coppie con K562, Q_cov(k562, d) − Q_cov(guide non mirate di k562, d) > 0, con
  l'intervallo sopra zero. Altrimenti la conservazione è quella della co-espressione di base, e la lettura «mappa»
  dice «no».
- **W6, dimensioni.** Almeno 200 bersagli rispondenti condivisi per coppia, cioè 100 per metà. Una coppia sotto
  soglia esce e si dice.
- **W7, semi.** Tre semi per le divisioni e per le permutazioni. Una coppia conta come positiva solo se D > 0 con
  tutti e tre.

## Regola

**Lettura «mappa»**, sulle 9 coppie P9, k = 3, media dei tre semi:
- **sì** se valgono tutte:
  - mediana di D ≥ 0,10;
  - D > 0 con l'intervallo sopra zero in almeno 5 coppie su 9;
  - nessuna coppia con l'intervallo interamente sotto −0,05;
  - mediana di ρ_cov ≥ 0,20;
  - il segno della mediana di D regge togliendo un contesto alla volta (5 prove);
- **no** se la mediana di D ≤ 0, oppure se la mediana di ρ_cov < 0,10;
- **inconclusiva** altrimenti.

**Lettura «uso»** (M3a), sui 5 contesti di P9:
- **sì** se valgono entrambe:
  - Δ_rel > 0 con l'intervallo sopra zero in almeno 4 contesti su 5;
  - Δ_rel^in > 0 con l'intervallo sopra zero in almeno 4 contesti su 5;
- **no** se Δ_rel^in, oppure Δ_rel, ha l'intervallo che tocca o scende sotto zero in almeno 3 contesti su 5;
- **inconclusiva** altrimenti.

**Verdetto:**
- **«Sì, la rete relazionale ha una base»:** mappa sì e uso sì.
  - Se in più la via combinata batte la via dell'effetto con l'intervallo sopra zero in almeno 4 contesti su 5, la
    rete ha anche qualcosa da aggiungere al trasferimento di produzione.
  - Il sì resta **provvisorio** finché non è replicato nella fase B, con le metà per cellule (revisione §3.2: un
    «passa» va replicato prima di essere creduto).
- **«No»:** mappa no, oppure uso no.
  - Con mappa sì e uso no si scrive così: la mappa è conservata, ma non dice che cosa muove un knockdown.
  - Usarla come filtro o prior resta un'ipotesi con una regola sua. La proiezione sui programmi ha già perso PDS
    ([programmi](../../trasferimento/programmi_2026-09-26/RISULTATI.md), atlante r1).
- **«Inconclusivo»:** il resto, o un controllo di validità fallito.
- Il verdetto va al proprietario.
- Non si rigira con altri parametri per cercare un sì. Gli strati S1b e S3 si riportano come scomposizione
  «laboratorio contro linea» e non decidono.

**Che cosa ne segue per la rete** (dal disegno della rete relazionale,
[rete_relazionale_2026-09-28](../rete_relazionale_2026-09-28/RISULTATI.md)):
- **sì:** la prima tornata della rete relazionale parte su Kaggle con la sua regola, già registrata;
- **mappa sì, uso no:** la rete parte solo come filtro dei vicini per carta (`cardnb`) per i bersagli nuovi, e lo
  si dice;
- **no:** la rete relazionale non parte; il lavoro torna alla decisione sulla stessa linea e alle leve di ampiezza e
  `mse` (revisione §3.1).

## Dove gira

- **Parte A su Kaggle, CPU, dal dataset r2:** M1, M2 e M3a su P9, repliche e strati S1, S2, S3 presenti in r2.
- **Parte B sul portatile, a pezzi, in float16:** HIPSCI, metà di VIPerturb, guide non mirate (W3, W4, W5, S0 e le
  coppie HIPSCI).
- **Fase B, metà per cellule di HCT116, HEK293T, KOLF2.1J, CD4 e HIPSCI:** solo se le parti A e B dicono «sì»,
  oppure «inconclusivo» per W3 o W4. Oggi il disco del portatile ha 2,7 GB liberi.
- **Uscite in cartelle nuove;** nulla si sovrascrive.

## Limiti dichiarati prima

- Laboratorio e linea coincidono in P9. Gli strati S1b e S3 li separano solo in parte: HIPSCI è un solo laboratorio e
  un solo tipo cellulare.
- Le coppie di P9 condividono contesti, quindi non sono indipendenti. Per questo contano gli intervalli per coppia e
  la prova che toglie un contesto alla volta.
- La calibrazione dello SE è l'anello debole di M2 fino alla fase B.
- La selezione dei bersagli rispondenti guarda l'esito. È la stessa per tutte le misure, ma favorisce i bersagli
  forti, mentre il pannello è fatto di knockdown tipici: si riportano i risultati per `essential` e a k = 0.
- Le soglie 0,10 e 0,20 sono **proposte**, scelte prima di vedere dati. Come riferimento, l'atlante misura coseni
  grezzi di 0,02–0,03 fra laboratori e di 0,16 nella stessa linea.
- Dopo [CP-0041](../../../docs/checkpoints/0041-proxy-contro-ufficiale.md) nessun esito di banco basta da solo a
  scegliere un invio: questa misura decide se costruire, non che cosa inviare.
