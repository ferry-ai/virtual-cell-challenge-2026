# Banco K562 sul pannello con lo scorer vero: protocollo e regola (azione 4 di R-REV)

29 settembre 2026. Scrive Claude (app desktop, sessione `f2abd9a6`); orari letti da `date`. Scheda
[R-REV](../../../docs/piani/revisione-critica.md), azione 4. Il disegno viene da un sottoagente della sessione che ha
letto il codice e misurato in sola lettura; rivisto qui con quello che t23, t26 e t27 hanno insegnato.

**Protocollo e regola fissati alle 18:10 del 29/09, prima di scrivere il codice dei bracci e di costruirli.** Il
proprietario ha scelto questo banco il 29/09 alle 11:25. Il job su Colab lo avvia lui.

Etichette: **misurato**, **interpretazione**, **ipotesi**, **proposta**. Nessun numero di questo banco è un punteggio
VCC.

## Domanda

Quale variante della ricetta del t22 proporre come prossimo invio, scelta con i sei membri dello scorer vero e non con
il proxy ([CP-0041](../../../docs/checkpoints/0041-proxy-contro-ufficiale.md))? In particolare:
- quale parte del t23 alza il PDS senza perdere i membri DE: l'esclusione, la pesatura o la riscalatura
  ([CP-0042](../../../docs/checkpoints/0042-t23-esclusione-pds.md),
  [CP-0045](../../../docs/checkpoints/0045-t26-soglia-espressione.md));
- quale ampiezza usare per D/E/F (regola R-B della [prova generale](../../invii/prova_generale_2026-09-28/RISULTATI.md)).

## Verità, sorgenti, bersagli

- **Verità:** cellule K562 genome-wide dei bersagli del pannello (uscita dello stadio 71, `k562_gwps_sc/x002` su
  Drive), metà A; la metà B fa da replica.
  - Bersagli con almeno 40 cellule e il gene bersaglio misurato: 224 nel banco b002.
  - 8.000 controlli non mirati.
- **Sorgenti:** CD4 (`cd4_mix`), HCT116 e HEK293T (Orion), dalla cache r5, con lo stadio 100 del commit che registra
  il codice. **K562 non entra in nessuna sorgente né nella quota.**
- **Fuga di contesto dichiarata, uguale in tutti i bracci:** il prior cis viene da bersagli K562 fuori dal pannello
  (cinque mediane per distanza).
- **Quota senza K562:** `quota_condivisa_2026-09-27/r1/share_k562.npy` (universi CD4 e HCT116, bersagli del pannello
  esclusi), convertita in CSV. L'esclusione è la stessa quota portata a 0/1.

## Bracci

Generatore di trial-01 con il percorso dello stadio 45 (profilo previsto con la maschera `observed` e lo spostamento di
composizione, poi campionamento). Tre semi del generatore (1, 2, 3) per braccio. Divisione in metà, controlli e linea
di base fissi (seme 2026).

| # | Nome | Com'è costruito | Serve a |
|---|---|---|---|
| C1 | `t22` | t22 senza K562, ampiezza 1,576 | riferimento |
| C2 | `t23` | C1 + quota, riscalato ai geni rilevabili di C1 sui CPM di K562 | taratura V1 |
| C3 | `t22s` | C1 × la scala di C2 | controllo d'ampiezza di C2 (V2) |
| T26 | `gate` | C1 + soglia d'espressione a 5 CPM di K562 | taratura V4 |
| E1 | `excl` | C1 + quota 0/1, senza riscalatura (la forma del t27) | esclusione sola |
| E2 | `exclrs` | E1 riscalato ai geni rilevabili di C1 | esclusione con i rilevabili recuperati |
| A1 | `t22h` | ampiezza 0,788 | ampiezza; taratura V3 |
| A2 | `t22d` | ampiezza 3,152 | ampiezza |
| RB | `rb` | 1,576 × s_RB (regola R-B sui CPM di K562) | ampiezza per D/E/F; si costruisce solo se dista più del 10 % da 3,152 |
| G1 | `g0d:t22` | C1 con dispersione per gene | generatore (revisione §2.7) |
| D1 | `t22r9` | C1 sulla cache r9 | la cache corretta degli invii da qui in avanti |

## Limiti misurati prima (29/09, in sola lettura, sugli effetti ufficiali del t22: indicativi)

- **L'asse del banco ha 7.681 dei 18.533 geni ufficiali.**
  - Dei 8.602 geni esclusi dalla quota senza K562, 586 sono sull'asse.
  - Dei geni esclusi sotto 5 CPM in A/B/C, dove sta il 53 % dell'energia del t22, 191.
  - Il banco non vede la parte a bassa espressione, che però il t26 ha mostrato pesare poco anche sul punteggio
    ufficiale.
- **Risposte scarse:** nel banco b002, mediana di 3 geni DE confidenti per bersaglio; nMAE calcolato su 32 bersagli su
  224.
- **Cellule previste per bersaglio** = quelle della metà A (mediana 88), non 400 come negli invii. Scala locale.

## Previsioni (ipotesi, registrate)

- **P1:** C2 − C1 alza il PDS con l'intervallo sopra zero, come il t23 ufficiale.
- **P2:** C3 − C1 peggiora l'nMAE e alza `reach`: è l'effetto d'ampiezza, come su HepG2.
- **P3:** E1 − C1 abbassa `reach` e Jaccard, perché escludere geni espressi toglie geni mossi.
- **P4:** T26 − C1 non si distingue da zero su nessun membro, come il t26 ufficiale.
- **P5:** R-B cade fra 2,84 e 3,47, quindi il braccio a 3,152 vale anche per R-B.

## Lettura

Per ogni confronto X − C1 e per ogni seme:
- differenze grezze per bersaglio e per membro;
- media dei membri con i pesi delle ancore ufficiali (`mse` = 0, come negli invii) e con le ancore locali.

La stima è la media sui tre semi. L'intervallo al 95 % è un bootstrap appaiato sui bersagli (2.000 estrazioni, lo
stesso ricampionamento per semi e membri); accanto si riporta la deviazione standard fra semi.

## Controlli di validità (prima di ogni scelta)

- **V1, il t23 com'è.** Su C2 − C1:
  - PDS in su, con l'intervallo sopra zero;
  - nMAE grezzo in su (peggiore) e `reach` in giù, ciascuno con quel segno in almeno 2 semi su 3.
- **V2, oltre l'ampiezza.** Su C2 − C3, PDS o `reach` con l'intervallo che esclude lo zero.
- **V3, ampiezza.** C1 − A1: la media dei membri (pesi ufficiali) sopra zero con l'intervallo sopra zero. È il verso di
  ogni aumento d'ampiezza ufficiale finora.
- **V4, il t26 com'è.** T26 − C1: nessun membro con l'intervallo che esclude lo zero oltre 0,005 grezzo.

**Esiti:**
- **V1 e V2 passano:** il banco può scegliere fra E1 ed E2.
- **V1 non passa con intervalli larghi:** «non conclusivo per risoluzione». I bracci E si leggono solo in modo
  descrittivo.
- **V1 non passa con l'intervallo dalla parte sbagliata:** «il banco contraddice l'ufficiale». I bracci E si leggono
  solo in modo descrittivo.
- **V3 non passa:** nessuna scelta d'ampiezza dal banco.
- **V4 non passa:** il banco vede un effetto che l'ufficiale non ha visto, e lo si dice accanto a ogni scelta.
- **G1 e D1** non hanno una taratura ufficiale: solo descrittivi.

## Regola di scelta del prossimo candidato

Un braccio X fra E1, E2, A2 (o RB), ammesso dal suo controllo, **passa** se la media dei membri (pesi ufficiali)
X − C1:
- è positiva con l'intervallo al 95 % sopra zero;
- è positiva in 3 semi su 3;
- supera due volte la deviazione standard fra semi.

Fra quelli che passano vince il Δ più grande. Se l'intervallo della differenza fra i primi due comprende lo zero,
vince il più semplice: E1, poi E2, poi A2.

**Prima di proporre:**
- si calcola il valore ufficiale atteso con lo stadio 84 (taratura C1 ↔ stato del t22), e lo si registra con la sua
  regola prima di generare;
- se la differenza attesa dal riferimento sta sotto 0,005, l'invio si propone solo come informazione che solo il server
  dà, e lo si dice (regola proposta da R-REV). La soglia non si sposta dopo.

**Nessun braccio passa:** il prossimo invio non si sceglie su questo banco.

**Il t27 è già pronto con la forma di E1.** Se E1 passa, la sua registrazione resta quella del 29/09 alle 15:45 UTC:
il banco non la cambia.

## Chiusura

- Le uscite del job si copiano in `r1/`, log compreso.
- `leggi_banco.py` scrive `r1/contrasti.csv` e `r1/esito.json`.
- L'esito si scrive qui sotto, con il tipo di ogni affermazione, più un checkpoint.
- Nella scheda R-REV va l'esito dell'azione 4; nella prova dell'azione 3, il dato d'ampiezza (R-B contro 1,576).
- Un candidato va al proprietario con la previsione registrata. Nessun invio senza il suo via.

## Codice e deviazioni dichiarate prima di girare (29/09, 19:45)

Codice di un sottoagente della sessione `f2abd9a6`, rivisto da un secondo sottoagente.
- **Stadio 73:** prefissi `g0:` (trial-01) e `g0d:` (trial-01 con dispersione per gene), `--gen-seeds`, e
  `vcc2026.inference.trial01_cells`.
  - `trial01_cells` è identico bit per bit alla sequenza dello stadio 45, contro HEAD e contro il working tree.
  - Senza le opzioni nuove, lo stadio 73 dà risultati per bersaglio identici a quello del commit `5652822`.
- **In questa cartella:** ricette dei bracci (`ricette/`), `build_arms.py`, `job_banco_k562.sh`, `leggi_banco.py`,
  `test_banco_k562.py` (18 prove). Il test del generatore è `tests/test_bench_generator.py` (11 prove).

**Deviazioni:**
1. **Il braccio T26 è identico a C1 sui geni del banco (misurato sulla costruzione di prova).** I 7.681 geni che K562
   misura stanno tutti sopra 8,4 CPM, quindi la soglia a 5 CPM azzera solo geni che il banco non vede. **V4 e P4
   passano per costruzione:** non si leggono come misure. Il braccio resta, come registrato, e serve da controllo che
   l'appaiamento per seme sia deterministico. `esito.json` lo segna (`checks.V4.identical_to_C1`).
2. **R-B sui CPM di K562:** 3,0303 (con gli effetti ufficiali del t22, come registrato), il 3,9 % da 3,152. Quindi il
   braccio RB non si costruisce e P5 cade nell'intervallo scritto. Accanto si riporta R-C (sugli effetti di C1),
   2,8632.
3. **Scale misurate nella costruzione di prova:** s(C2) = 1,6365, quindi C3 = 2,5791; E2 = E1 × 1,1894.
4. **Letture dove il testo lasciava una scelta**, segnate «READING» in `leggi_banco.py`:
   - V1 è «contraddice» se l'intervallo di PDS, nMAE o `reach` sta tutto dalla parte opposta;
   - V4 si giudica sugli intervalli grezzi dei cinque membri contro ±0,005;
   - lo spareggio confronta i primi due bracci che passano;
   - MSE conta 0 nella media, e la sua differenza aggregata si riporta per seme.
5. **Generatore:**
   - il limite di memorizzazione è il numero di geni del banco (8.246);
   - la dispersione di `g0d:` è stimata una volta, con il seme 2026, sugli 8.000 controlli;
   - le cellule previste per bersaglio sono quelle della metà A.
6. **Coda:** lo slot 059 è occupato da un job di Codex (`059_lead_generator_dev_r1.sh`). Questo job va in coda come
   060, dopo il `.done` del 059, perché il banco deve girare da solo.

**Interpretazione, scritta prima:** V2 passerà probabilmente senza dire molto. C3 ha una mediana di 217 geni
rilevabili sui bersagli del banco contro 85,5 di C2, quindi C2 − C3 differirà in `reach` qualunque cosa faccia
l'esclusione.
