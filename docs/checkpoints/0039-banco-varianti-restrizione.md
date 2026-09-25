# CP-0039 — Banco a sorgente esclusa: gli effetti ristretti aiutano il PDS proxy, ma meno di quanto scritto prima della revisione

- **Data:** 2026-09-25
- **Tipo:** osservazione
- **Redatto da:** agente (Claude Opus 5.5); revisioni di claude2 e grok (agenti dell'hub)
- **Revisione umana:** no
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Quali varianti della ricetta del t15, provate su sorgenti pubbliche tenendone fuori una alla
volta, possono alzare il punteggio prima di spendere invii? E che cosa dice lo scorer
installato su come si guadagnano i membri?

## 2. Cosa è stato fatto

Tutto in `reports/banco_varianti_2026-09-25/`, sulla cache `processed/multisource_2026-09-23_r5`:
- **Proxy dallo scorer.** Letto `cell_eval2` 0.16.0: `pds_cosine` (coseno sui delta pseudobulk
  in `log1p` a 5·10⁴, geni del pannello esclusi, rango fra i bersagli) e la fedeltà
  (k / max(chiamati, veri DE), con k che conta il segno giusto anche sui geni non significativi
  nel vero). Due proxy nello spazio degli effetti imitano questi due membri.
- **Varianti** (`analyze.py`, r1): γ, restrizione della cache (k 4), consenso fra sorgenti,
  bersagli rimescolati. **Filtro dei bersagli difficili** con stima annidata (`gating.py`, r3).
- **Forza della restrizione e rumore del generatore** (`shrink_sweep.py` r2, `noise_sim.py` r4,
  `controls.py` r5, `noise_sim2.py` r6): queste quattro esecuzioni hanno un difetto,
  trovato dopo il commit `2308ee7` da due revisioni indipendenti (`revisioni/`).
- **Rifacimento corretto** (`sweep_v2.py` r7) con il `load_table` dello stadio 100, un solo
  insieme di bersagli per sorgente esclusa e bootstrap appaiato sui bersagli; **confronto col
  t16** a parità di geni rilevabili (`sweep_v3.py` r8); coerenza per bersaglio (r9).
- **Stadio 100:** opzione `"effect": "zshrink"` con `"shrink_k"`, attraverso
  `multisource.zshrink_table` e `zshrink_mixture`, con test in `tests/test_multisource.py`.

## 3. Cosa si è osservato

**Misurato dagli organizzatori**, nelle note dello scorer (`cell_eval2/competition.py`,
`metrics/de.py`, `metrics/direction.py` nel venv): sul pannello val A 102.786 coppie
bersaglio–gene significative, circa 340 per bersaglio in media; il 12–30% dei bersagli ha meno
di 10 geni DE e il 46–61% meno di 40; un invio che incolla i controlli ha fedeltà 0,001, quindi
quasi nessun bersaglio ha zero geni DE.

**Il difetto.** `cd4_mix` salva l'SE tutto NaN (già notato in CP-0034). Il ricalcolo
z²/(z² + k) delle esecuzioni r2, r4, r5 e r6 dava z = 0, quindi effetto 0: CD4 diventava un
voto per zero a peso pieno in `mix`, e i bersagli coperti solo da CD4 sparivano, così le
varianti erano valutate su insiemi diversi. Il primo `zshrink` dello stadio 100 in `2308ee7`
aveva lo stesso difetto; non è mai stato usato per generare. Le righe grezze di r2, r4 e r6, tutto
r1 e r3 non ne dipendono: lo `shrunk` della cache per `cd4_mix` è la media delle tre condizioni
ristrette, e la ricostruzione dalle parti lo riproduce entro 2,4·10⁻⁷ (`CORREZIONE.md`).

**Misurato, corretto (r7).** PDS proxy senza rumore, differenza appaiata sui grezzi con
IC95 bootstrap:

| Sorgente esclusa | bersagli | k 4 | k 16 | k 64 | grezzi senza CD4 |
|---|---|---|---|---|---|
| K562 | 257 | +0,022 [0,011; 0,033] | +0,033 [0,017; 0,048] | +0,036 [0,017; 0,055] | −0,031 [−0,055; −0,007] |
| CD4 | 292 | +0,014 [0,003; 0,025] | +0,024 [0,008; 0,040] | +0,032 [0,014; 0,051] | — |
| HCT116 | 242 | +0,011 [0,001; 0,022] | +0,017 [−0,002; 0,036] | +0,017 [−0,008; 0,042] | +0,002 [−0,031; 0,034] |
| HEK293T | 254 | +0,017 [0,005; 0,030] | +0,027 [0,009; 0,045] | +0,032 [0,008; 0,056] | +0,052 [0,010; 0,092] |

Con un modello del generatore (taglio a 6 log2, spostamento compositivo, rumore di Poisson di
400 cellule): gli effetti ristretti all'ampiezza 0,394 **perdono** da −0,03 a −0,13, perché
restano sotto il rumore; riscalati al q99 del t15, con tetto |ln fc| 2, battono i grezzi a 0,394
di +0,014…+0,036 e i grezzi a 0,788 (il t16) di +0,003…+0,013, muovendo circa 600 geni invece
di circa 2.600.

**Misurato (r3, r9).** Il PDS proxy per bersaglio è coerente fra sorgenti escluse (Spearman
0,46–0,69) e il 20–28% dei bersagli sta sotto 0,5; azzerare i bersagli stimati difficili con
una stima annidata perde PDS a ogni soglia provata.

**Misurato nel modello, dopo il punteggio del t16 (r8).** A parità di geni "rilevabili"
(|ln fc| realizzato oltre 4/√(400 μ)), lo `shrunk` della cache (k 4) all'ampiezza 1,576 muove
321–495 geni per bersaglio contro 335–525 del t16, e ne batte il PDS proxy di +0,004…+0,019
e la precisione dei segni rilevabili di +0,003…+0,008. I grezzi a 1,576 (il t18) muovono
1.246–1.797 geni con PDS proxy piatto (−0,005…+0,002). Tabella in `CORREZIONE.md` §3.

## 4. Interpretazione e incertezza

**Interpretazione:** negli effetti delle sorgenti molti geni sono rumore, e restringerli verso
zero rende più riconoscibile il bersaglio; il guadagno onesto sul proxy è +0,01…+0,04, non i
+0,08…+0,12 scritti prima della revisione. La trasferibilità dipende in buona parte dal
bersaglio, ma non abbastanza da prevedere quali azzerare.

**Incertezza:** la verità del banco è una sorgente pubblica rumorosa, non A/B/C; il modello del
generatore ignora sovradispersione ed eccesso di zeri; il proxy della fedeltà non è il Wilcoxon
dello scorer. Il t16 ha mostrato che il modello sovrastima il guadagno di PDS dovuto
all'ampiezza (+0,005…+0,026 previsti, +0,0037 misurati, [CP-0037](0037-t16-ampiezza-quadrupla.md)).

## 5. Spiegazione semplice

Prima di fare la media fra esperimenti, abbiamo "abbassato il volume" ai geni che ogni
esperimento misura male. Sui dati di prova il riconoscimento del gene spento migliora un po'.
Una prima versione del conto sembrava molto migliore, ma aveva un errore: un esperimento
veniva contato come se dicesse "nessun effetto" su tutto. Due revisori indipendenti l'hanno
trovato, e i numeri giusti sono più piccoli.

## 6. Conseguenze

- **Secondo candidato del 26 settembre, proposta:** il t16 con `"effect": "shrunk"` (k 4
  della cache) all'ampiezza 1,576, da registrare prima di generarlo. Con il t18 (grezzi a
  1,576) forma un confronto a una sola differenza, la forma degli effetti.
- La fedeltà non migliora cambiando il mix: la precisione dei segni resta vicina al caso
  (0,51–0,54 nei proxy); servono previsioni di segno migliori, non un'altra media.
- Lo stadio 100 ha l'opzione `zshrink` con `shrink_k`, che ricostruisce le miscele dalle parti
  e rifiuta le sorgenti senza SE; k 16 resta un passo successivo se k 4 regge.
- Un banco su sorgenti pubbliche va rivisto da un'altra famiglia di agenti prima di spendere un
  invio: stanotte ha evitato un invio costruito su un difetto.

## 7. Cosa corregge

- `reports/banco_varianti_2026-09-25/RISULTATI.md` e il messaggio del commit `2308ee7`: le
  colonne ristrette delle tabelle 2 e 4, i +0,026…+0,080 con k 64, la frase «raddoppiare quel
  q99 non aggiunge nulla» (falsa per K562 anche nei numeri difettosi) e la proposta di k 64 con la
  regola del q99. Scheda R-017 nel registro; correzione in `CORREZIONE.md` nella stessa cartella.
- Il paragrafo sul candidato della scheda S-INVII, riscritto il 25 settembre.

## 8. Domanda di comprensione

Perché un effetto "ristretto" può aiutare il riconoscimento del bersaglio ma peggiorare la
fedeltà direzionale, se lo si invia alla stessa ampiezza?
