# Correzioni verificate nella review del generatore

**Revisione statica successiva, 29 settembre 2026.** I due rilievi iniziali
documentati in `REVIEW_PROFILES_TO_CELLS_R1.md` risultano risolti nella lettura
successiva alle modifiche della lead. Quel documento descrive il codice letto
prima della correzione, non lo stato corrente.

`generate` passa ora il contesto atteso a `read_context`, che lo confronta con
`complete.json.context` prima di creare output. Il test aggiunge il rifiuto della
fixture A etichettata come B. Il CLI controlla inoltre i byte di `stack_pilot.py`,
del modulo effettivo di `sample_counts` e del writer tramite SHA256 fissati,
prima di leggere la registrazione. Gli hash di helper e campionamento coincidono
con quelli del payload A congelato.

La lead riporta due test passati in 0,949 secondi. Non li ho rieseguiti e non ho
avviato generazione. Nessun altro difetto concreto identificato nel percorso
previsto; resta necessaria la registrazione concreta prima di qualunque output
ufficiale. La review non modifica il gate scientifico.
