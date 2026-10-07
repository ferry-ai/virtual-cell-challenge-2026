# HIPSCI: QC e riconciliazione dei derivati storici

6 ottobre 2026. **Correzione misurata:** i 19 manifest sotto
`reports/sorgenti/universo_hipsci_2026-09-27/linee_p2/` riportano tutti pseudo0,5,
min_expected1. Il suffisso p2 indica due pool d'archivio non vuoti (gli altri slot
sono zero), non uno pseudocount di 2. [Prova file per file con hash](historic_manifest_reconciliation.json).
L'affermazione generalizzata «HIPSCI mirato p2 usa pseudo2» in ESECUZIONE_r14
e nei successivi riepiloghi è quindi contraddetta per questi specifici derivati.
I documenti originari restano preservati: non usarli per escludere il riuso.

**Non equivale a riuso già validato:** i vecchi effetti erano stimati per clone
su due pool tecnici; la banca nuova conserva il clone come donatore, e la nuova
fonte congiunta applica pooling prima dello shrink. Il cache storico post-shrink
non può sostituire quel consumer solo perché pseudo e asse coincidono.
I controlli storici indicano knockdown più debole in alcuni cloni, ma provengono
da quei vecchi pool: non dimostrano il QC del nuovo derivato.

**Diagnostica preparata:** [pacchetto cloud](prepared.json), hash prima delle
stime, metodo originale per clone e label native, controlli NTC abbinati.
Il job misura il log-fold-change del trascritto colpito su tutti i target nativi
misurabili, distinguendo geni non misurati, min_cells, min_expected e maschere.
Non cambia pesi, non esclude cloni e non decide automaticamente l'ammissione.
I target fuori asse restano inventariati; l'impossibilità di misurare il proprio
trascritto non è un'esclusione dal fit. Due fixture diagnostiche passate.

Questo è QC della banca esistente, senza ingestion né generazione/invio VCC.
Il [derivato r3 concluso](../hipsci_adapter_r3/completion_r1/README.md) resta
immutato; ammissione, hash nel successivo mixer e copertura D-053 restano aperti.
