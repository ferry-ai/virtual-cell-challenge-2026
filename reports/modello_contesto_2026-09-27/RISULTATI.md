# Un modello bersaglio × contesto: il disegno, la letteratura e la prima prova

27 settembre 2026, pomeriggio. Nella scheda [R-V2](../../docs/piani/modello-v2.md), consegna (c) della
[revisione di codex](../revisione_codex_2026-09-27/REVISIONE.md). Il disegno è di claude2 (base di lancio,
Opus 5.5 con sforzo massimo), in [agenti/disegno_claude2.md](agenti/disegno_claude2.md). La letteratura è
stata verificata da grok sulle fonti primarie ([agenti/verifica_grok.md](agenti/verifica_grok.md)).
**Proposta e letteratura, nessuna misura nuova.**

## Che cosa dice la letteratura, in breve (pubblicato; verificato da grok)

- Nessun modello pubblicato ha mostrato di prevedere l'interazione bersaglio × contesto per una linea vista
  solo attraverso le cellule di controllo. Nelle quattro linee degli schermi essenziali (K562, RPE1, HepG2,
  Jurkat) un preprint del 2026 (Molina e Zhang) scompone la varianza in stampo di linea 27,8 %, effetto
  conservato 29,4 %, interazione 23,5 %, rumore 19,3 %. Lo stampo si ricava dai controlli; l'interazione non la
  recupera nessuno dei modelli che provano senza dati della linea (ridge, MLP, State, MORPH), mentre il 30 % delle
  perturbazioni della linea stessa la fa recuperare. Un MLP dai profili DepMap recupera in parte l'effetto
  conservato (r 0,25–0,39; ridge 0,10–0,13).
- Nei confronti onesti le baseline semplici (media, lineare) battono o eguagliano i modelli profondi e di
  fondazione (Ahlmann-Eltze 2025, Systema, Kernfeld, il resoconto della VCC 2025). I risultati positivi nel
  regime C vengono dall'industria, con numeri solo nelle figure.
- Nessuno studio pubblicato prova il regime della gara: bersagli non essenziali, una linea nuova di un altro
  laboratorio, chimica Flex, PDS e metriche DE.

Correzioni di grok al disegno, che non ne cambiano la direzione: le cifre di Nadig (0,61 contro 0,35) valgono
solo per il 44 % delle perturbazioni, su 1.660 geni filtrati; la r media 0,32 di Zhu e Marson è su 1.880
perturbazioni, non 3.081; l'avvertenza su dati proprietari di TxPert non è sostenuta dal testo; lo zero-shot di
State non si limita a ordinare le perturbazioni per forza.

## Il modello proposto (proposta)

ŷ(t, g, c) = A · s(t, c) · h(g, c) · m(t, g) + k(t, g, c):
- **m**: il trasferimento di produzione, invariato;
- **s**: quanto conta il bersaglio nel contesto, dall'espressione del bersaglio nei controlli del contesto;
- **h**: un cancello per gene, dall'espressione del gene nel contesto e dalla quota condivisa; con la sola quota
  riproduce il t23, che è quindi un caso particolare;
- **k**: la testa cis.

Il contesto entra solo attraverso ciò che si legge dai suoi controlli, con circa sei parametri comuni a tutti i
contesti: nessun vettore imparato per contesto, che con due contesti di training è già fallito (CP-0013,
CP-0026).

## La prova che il modello usa il contesto (da registrare prima di eseguirla)

- **E1:** il modello contro la sua versione «cieca» (ogni contesto con le caratteristiche medie delle sorgenti),
  con la regola dei banchi: Δ positivo su almeno tre famiglie tenute fuori su quattro, intervallo sopra zero su
  almeno due.
- **E2, decisiva:** tenere fuori due contesti insieme (HCT116 e HEK293T; CD4 a riposo e stimolato) e
  correlare, bersaglio per bersaglio, la **differenza prevista** fra i due con quella osservata, sui geni lontani
  dal bersaglio. Il trasferimento e il modello cieco danno 0 per costruzione.
- E1 senza E2 vuol dire ripesatura dei geni, non effetto bersaglio × contesto.

## Passaggio di prova smoke r0 (misurato, finito alle 18:02 del 27/09)

Uscite in `smoke_r0/`. Codice del commit 19dc948, opzione `--smoke`: 60 bersagli di prova, 120 di fit per
sorgente, 400 di stima; un disegno E1 (HEK293T fuori) e uno E2 (HCT116 con HEK293T), entrambi con K562 e CD4 come
training. Universi del 26/09, **non corretti**. Serviva a provare che il banco gira dall'inizio alla fine.

| Misura | Valore |
|---|---|
| E1, `gated` − `transfer` | +0,0015 (−0,014…+0,017) |
| E1, `gated` − `gated_blind` | −0,0084 (−0,020…+0,0008) |
| E1, `gated` − `excl` | −0,0057 (−0,019…+0,007) |
| E2, correlazione media di `gated` | −0,0007 (−0,005…+0,003); permutazioni: p 0,70 |
| Ampiezza di fit A_fit | 0,027 (E1) e 0,022 (E2) |
| Parametri α1, α2, β1, β3 | E1: −1,05, 1,98, −0,41, 0,02; E2: +0,28, 0,34, −0,83, 0,01 |

**Nessuna lettura:** 60 bersagli non bastano, e questo passaggio non decide nulla. Due osservazioni sul banco
(misurate), non sul modello:
- i due fit hanno le stesse sorgenti di training e bersagli di fit estratti a caso in modo diverso, ma parametri
  molto diversi: con 120 bersagli per sorgente i cancelli sono poco identificati;
- A_fit ≈ 0,02 concorda con l'accordo per bersaglio misurato dall'atlante su bersagli presi a caso (0,016–0,024):
  su bersagli qualunque la risposta di una linea segue poco quella delle altre.

## Regola di r1, fissata alle 18:21 del 27/09 (prima di eseguire r1, dopo aver visto smoke r0)

**Che cosa gira.**
- `gated_bench.py`, con le dimensioni predefinite: 1.000 bersagli di prova, 400 di fit per sorgente, 6.000 di
  stima; sei disegni:
  - E1 con K562, CD4 (`cd4_mix`), HCT116 e HEK293T tenuti fuori uno alla volta (una linea Orion tenuta fuori
    porta fuori tutta la famiglia Orion);
  - E2 con le coppie HCT116 + HEK293T e CD4 a riposo + CD4 stimolato 48 ore.
- Universi:
  - CD4, HCT116 e HEK293T quelli corretti (`*_2026-09-27_me1`, `min_expected` 1);
  - K562 quello del 26/09, che passa per `effects_from_bulk` e non ha l'artefatto
    ([pseudoconteggio](../pseudoconteggio_2026-09-27/RISULTATI.md)).

**Cambiato dopo smoke r0, e niente altro.** Tre cose, dichiarate qui:
1. Lo **strato forte**: i bersagli di prova nel quartile più alto per numero di geni significativi nella verità
   tenuta fuori (|Z| ≥ 3 sui geni rilevabili in A/B/C, gene proprio escluso; in E2 il minore fra le due verità).
   I motivi: gli organizzatori hanno scelto perturbazioni forti, e l'A_fit di smoke r0, una diagnostica del
   training, dice che su bersagli qualunque il segnale è poco. Smoke r0 non ha calcolato lo strato, quindi nessun
   confronto fra bracci ha guidato la scelta.
2. Un seme per disegno: la stessa estrazione anche se si esegue un sottoinsieme di disegni.
3. Un disegno il cui fit non converge non viene valutato e conta come non passato.

**Letture.** Δ = 0,36 ΔPDS_gen − 0,27 ΔnMAE_gen, intervallo bootstrap appaiato al 95 %.
- **E1, uso del contesto:** `gated` − `gated_blind` su tutti i bersagli.
  - Passa se Δ è positivo su almeno tre delle quattro verità tenute fuori, con l'intervallo sopra zero su almeno
    due e nessun intervallo interamente sotto −0,002.
  - Il contrario passa con la stessa regola a segni invertiti.
- **E1, candidato:** `gated` − `excl`, con la stessa regola. Riportato sempre. Diventa un candidato per il banco
  del pannello (con una regola sua, da registrare) solo se passano anche E1 uso del contesto ed E2.
- **E2, decisiva:** per coppia, la correlazione media di `gated` è positiva se l'intervallo sta sopra zero e la
  media supera il quantile 97,5 % delle permutazioni.
  - E2 passa se è positiva su entrambe le coppie.
  - È **parziale** se è positiva su una: un'ipotesi da replicare su coppie nuove (KOLF, HIPSCI), non un'adozione.
  - Il contrario passa se l'intervallo sta sotto zero su entrambe.
- **Strato forte:** stesse regole, riportate accanto; da solo non decide. Se la regola su tutti i bersagli fallisce
  e lo strato forte passa, è un'ipotesi da provare su un campione nuovo (r2, altri semi), non un'adozione.
- **`gated_swap`**, diagnostica: se `gated` batte `gated_blind` ma non `gated_swap`, il guadagno viene dalla forma
  dei cancelli e non dal contesto giusto.

| E1 uso del contesto | E2 | Lettura |
|---|---|---|
| passa | passa | i cancelli leggono qualcosa del contesto dai controlli: prima prova interna di un'interazione bersaglio × contesto recuperabile |
| passa | non passa | ripesatura dei geni, non interazione |
| non passa | passa | differenze prese ma nessun guadagno di livello: ipotesi per la rete |
| non passa | non passa | esito negativo per questa forma a quattro parametri; la rete con encoder appresi e più contesti si prova con la stessa E2 |

**Cautele.**
- Sono proxy contro sorgenti pubbliche, non punteggi VCC.
- La testa cis è la stessa in ogni braccio e si annulla nei contrasti. Questo risponde anche alla domanda di grok
  sulla curva cis del K562 quando il K562 è tenuto fuori.
- I bersagli sono estratti a caso fra quelli non del pannello e non essenziali, più lo strato forte.

## Stato

- Prima versione (quattro parametri: espressione del bersaglio e del gene, quota condivisa): `gated.py` (codex),
  autoverifica 5 su 5; banco `gated_bench.py`, rivisto da grok e corretto.
- Universi corretti: HCT116 e HEK293T fatti; CD4 in ricostruzione. r1 parte quando CD4 è pronto, con la regola
  qui sopra.
