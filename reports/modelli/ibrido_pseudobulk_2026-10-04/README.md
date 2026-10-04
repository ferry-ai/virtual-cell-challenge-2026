# Ibrido semplice con pseudobulk e campionamento

Mandato del proprietario del 4 ottobre 2026: ibrido semplice a partire dal transfer
più promettente, con molti contesti, pseudobulk e campionamento. Codex, chat
`01a107a9-9c9c-76c2-9161-258f22bd57b1`, partenza `98545d3`.

**Scelta:** transfer ampliato `all`, con la stessa policy nel fit e nell'export;
pseudobulk completo e campioni stratificati separati. Implementati componenti e fixture,
non ancora una pipeline completa né un training avviato.

| File | Contenuto |
|---|---|
| [PROTOCOLLO.md](PROTOCOLLO.md) | Scelte adottate, precedenti, limiti, contrasti e dipendenze prima del lancio |
| [audit_inputs.py](audit_inputs.py), [ricevuta](audit_inputs_r1.json) | Rilettura all contro prod senza rete; 34 tabelle e 10 gruppi, copertura incompleta |
| [preparation.py](preparation.py) | Momenti completi su asse riconciliato, campioni annidati per strato, esclusioni e pesi gerarchici |
| [hybrid.py](hybrid.py) | Residuo piccolo sul transfer, con/senza contesto; stessa composizione in fit ed export, loss pseudobulk |
| [test_hybrid.py](test_hybrid.py) | Test piccoli di identità, supporti, gradienti, conservazione di contesti e bilanciamento |
| [RISPOSTA_ALFREDO.md](RISPOSTA_ALFREDO.md), [riconti](audit_alfredo_r1.json) | Valutazione in sei punti del messaggio inoltrato; non inviata, accessi non modificati |

QC, deduplicazione globale e riconciliazione dell'asse precedono questi componenti:
non sono sostituiti da essi. L'audit verifica hash delle ricevute scientifiche già
scaricate; nessun nuovo download. Gli esiti di fit reali e l'uso effettivo dei contesti
non sono stati misurati. Stato operativo in R-LEAD.
