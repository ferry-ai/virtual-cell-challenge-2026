# CP-0058 — Copertura obbligatoria di tutte le linee e i contesti idonei

- **Data:** 2026-10-03
- **Tipo:** cambio-di-strategia
- **Redatto da:** Codex, sessione `01a1027a-0ae4-7c32-9001-e868a2b91698`
- **Revisione umana:** no
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Come usare aggregati e campioni mantenendo tutte le linee e i contesti, e rendere questo
mandato obbligatorio per le sessioni successive.

## 2. Cosa è stato fatto

Il proprietario ha chiesto in chat il 3 ottobre 2026:

> Direi assicuramente di usare tutte le linee e contesti possibili e "forzare" i prossimi
> agenti a non sbagliare mettendo questa informazione come non negoziabile in repo

Registrata D-053 in [DECISIONI](../DECISIONI.md). Aggiunta la regola operativa in
[GENERALIZZAZIONE §2.1](../GENERALIZZAZIONE.md#21-copertura-integrale-vincolo-non-negoziabile),
con richiami nell'ingresso [CLAUDE](../../CLAUDE.md), [AGENTS](../../AGENTS.md),
[PROGETTO](../PROGETTO.md), [R-LEAD](../piani/strategia-scientifica.md) e
[prompt Claude](../PROMPT_CLAUDE.md). Aggiornato il registro; nessun nuovo report parallelo.

## 3. Cosa si è osservato

**Mandato, non nuova misura:** la copertura completa è richiesta dal proprietario. Il
[riconto precedente](../../reports/analisi/candidato_ibrido_2026-10-03/audit.json) distingue
otto gruppi del pilot e 21 gruppi del catalogo proposto: non sono limiti imposti al nuovo
corpus né 21 gruppi dichiarati pronti. Nella stessa evidenza il training H1 perde la guardia
di bilanciamento: avere una sorgente nei file non prova che il modello la abbia letta.
Questi numeri non sono stati rimisurati in questo checkpoint.

## 4. Interpretazione e incertezza

Il mandato richiede copertura e tracciabilità, non prova un beneficio di ogni fonte. Un
aggregato non conserva tutta l'eterogeneità, e un campione piccolo può perdere stati rari.
La nuova regola impone controlli nei runner: non dichiara che siano già implementati. Le
risposte perturbate riservate alla validazione restano escluse da fit e derivati.

## 5. Spiegazione semplice

Per ogni contesto conserviamo sia la fotografia media della risposta, utile al transfer,
sia esempi di singole cellule, utili alla rete per imparare la variabilità. Possiamo
ridurre quante cellule leggiamo di ogni contesto; non possiamo dimenticare un intero
contesto soltanto perché il suo file è grande o arriva tardi nel caricamento.

## 6. Conseguenze

Il corpus principale deve riconciliare l'intero catalogo: fonti, contesti, ruoli, quantità,
lacune, esclusioni motivate e azioni per quelle rimediabili. Il training deve documentare
anche l'uso effettivo, con verifica di copertura e pesi durante l'esecuzione e dopo resume.
Prove ridotte e ablation restano ammesse con perimetro dichiarato. Non sostituiscono il
percorso completo e non giustificano l'abbandono delle altre linee idonee.

## 7. Cosa corregge

Precisa D-044 e D-052 per il mandato sui dati. La proposta 8→11 in
[candidato_ibrido](../../reports/analisi/candidato_ibrido_2026-10-03/README.md) resta una
possibile tappa, non l'obiettivo finale. Non corregge misure o protocolli congelati e non
riapre automaticamente un vecchio modello scartato. Nessuna nuova autorizzazione a job,
acquisti o invii discende da questo aggiornamento documentale.

## 8. Domanda di comprensione

Se un dataset compare nel manifest ma nessuna delle sue cellule contribuisce al training,
possiamo dire che il modello ha usato quel contesto? No: servono ricevute dell'uso effettivo.
