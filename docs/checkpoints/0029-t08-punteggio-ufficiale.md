# CP-0029 — Il t08 in classifica: +0,060, nuovo migliore; a generatore fisso gli effetti K562 + CD4 migliorano tutti e sei i grezzi

- **Data:** 2026-09-23
- **Tipo:** esperimento
- **Redatto da:** agente (Claude Opus 5.5)
- **Revisione umana:** no. Invio autorizzato dal proprietario in chat il 23 settembre
  (`reports/trial_2026-09-22/autorizzazioni.md`).
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

A generatore fisso, quello di trial-01, sostituire gli effetti K562 di trial-01 con la
miscela K562 + CD4 di [CP-0028](0028-cd4-sorgente-flex-trasferimento.md) cambia il punteggio
ufficiale? In che direzione, per ognuno dei sei membri?

## 2. Cosa è stato fatto

- **Effetti** da `configs/recipes/t08.json` (stadio 100, cache dello stadio 98 run r3):
  - K562 0,433 e CD4 0,567;
  - γ = 1;
  - effetti grezzi × 0,197.
  
  La regola e i due emendamenti stanno in `reports/multisource_2026-09-22/PRIMA_DEI_RISULTATI.md`.
- **Generazione:** stadio 45, trial `trial-ext-profile`. Stesso generatore e stesso seme
  (20260912) di trial-01. `reports/trial_2026-09-22/t08_generation_diagnostics.json`.
- **Impacchettamento:** stadio 48. 24 controlli superati, validatore ufficiale del
  contenitore superato, contenuto identico bit per bit (`reports/trial_2026-09-22/t08_packaging.json`).
- **Previsione registrata prima dell'invio:** banda +0,03…+0,06
  (`reports/prediction_t08_2026-09-22/prediction.json`).
- **Invio:** alle 22:12:26 UTC del 22 settembre; risposta alle 22:47 UTC. Output verbatim in
  `reports/trial_2026-09-22/submit_NNUXtdhV4ByiETbolCKJ.json` e
  `status_NNUXtdhV4ByiETbolCKJ.json`.

## 3. Cosa si è osservato

**Misurato — il punteggio.** Media **+0,060370**, rango 547, entry `NNUXtdhV4ByiETbolCKJ`.
Trial-01 aveva +0,045929 (rango 446 il 13 settembre).

**Misurato — i sei grezzi contro trial-01** (`reports/prediction_t08_2026-09-22/comparison.json`):

| membro | trial-01 | t08 | differenza | scalato t08 |
|---|---|---|---|---|
| `pds_cosine` | 0,6870 | 0,7103 | +0,0233 | +0,466 |
| `expr_mse_unbiased_capped_norm` | 1,2313 | 1,1524 | −0,0789 (meglio) | 0 (tosato) |
| `de_wilcoxon_lfc_nmae` | 0,9849 | 0,9774 | −0,0075 (meglio) | +0,039 |
| fedeltà direzionale | 0,4580 | 0,4594 | +0,0014 | −0,178 |
| `reach` | 0,0980 | 0,1099 | +0,0119 | +0,035 |
| Jaccard | 0,0291 | 0,0304 | +0,0012 | −0,000 |

**Misurato — le ancore reggono su un quinto punto.** Applicate ai grezzi del t08
(`reports/anchors_2026-09-17/anchors.json`) riproducono gli scalati pubblicati con uno
scarto massimo di 0,0007.

**Misurato — nello spazio degli effetti il guadagno di PDS non si spiega con γ né con lo
stimatore.** La proxy di discriminazione K562 → CD4 vale:

| stimatore | γ = 0 | γ = 1 |
|---|---|---|
| grezzo | 0,656 | 0,655 |
| ristretto | 0,666 | 0,668 |

CD4 → K562 va da 0,683 a 0,691 in tutte e quattro le varianti. Lettura fatta in sessione con
le funzioni dello stadio 98 sulla cache r3, non salvata su file: è un'indicazione, non una
misura registrata.

## 4. Interpretazione e incertezza

**Interpretazione:**
- **A generatore fisso, gli effetti del t08 migliorano tutti e sei i grezzi.** Il miglioramento
  è modesto ma coerente in segno su ogni membro.
- La MSE grezza scende a 1,152, praticamente il valore che il generatore di trial-01 ottiene
  **a effetto nullo** su HepG2 (1,154, CP-0013). Gli effetti del t08 non aggiungono errore
  quadratico; quelli di trial-01 ne aggiungevano circa 0,08.
- La fedeltà resta sotto la base (0,459 contro 0,512). Come previsto, è governata dalle
  chiamate spurie del generatore.
- **La previsione registrata regge.** Il punteggio sta sul bordo superiore della banda
  (0,0604 contro 0,060), e i grezzi sono tutti nella direzione e nell'ordine di grandezza
  scritti prima.

**Incertezza — l'attribuzione non è risolta.** Rispetto a trial-01 gli effetti differiscono
per tre cose insieme:
- l'aggiunta di CD4 (e con essa 25 bersagli coperti in più);
- la centratura γ = 1;
- lo stimatore K562: grezzo quasi-Poisson dello stadio 98, invece delle firme e001 di
  `ShrunkTransfer`.

La lettura nello spazio degli effetti suggerisce che γ e stimatore contino poco, ma è una
proxy. Il t10 (identico al t08 senza CD4) è l'invio che separa il primo fattore dagli altri due.

**Incertezza — un solo punto per famiglia.** La differenza di punteggio (+0,0144) non ha un
intervallo. Due invii dello stesso file non sono stati fatti.

## 5. Spiegazione semplice

Abbiamo cambiato una sola cosa rispetto al nostro migliore invio: da dove prendiamo la
risposta attesa di ogni gene spento. Prima veniva da una sola linea di leucemia; ora anche da
linfociti T umani, con il doppio del peso. Il modo di fabbricare le cellule è rimasto identico.

Il voto è salito da 0,046 a 0,060. Tutte e sei le pagelle migliorano un po', nessuna peggiora.

## 6. Conseguenze

- **Il t08 è il nuovo riferimento da battere**, al posto di trial-01.
- **Il prossimo invio è il t10**: il t08 senza CD4, per sapere quanto del guadagno viene da
  CD4.
- **Il t09** (stessi effetti, generatore `ControlModel`) resta in coda su Colab. Separa il
  generatore.
- **Orion** si aggiunge come sorgente con la stessa regola appena finito lo streaming.
  Il proprietario lo ha ammesso negli invii.
- **D-039 regge.** La sua condizione di riapertura, «il t08 va sotto trial-01», non si è
  verificata.

## 7. Cosa corregge

- Nessun checkpoint.
- Aggiorna il riferimento di PROGETTO.md §5: il migliore è il t08, non più trial-01.

## 8. Domanda di comprensione

Perché la MSE del t08 può migliorare di 0,08 senza che il suo scalato si muova da zero?
