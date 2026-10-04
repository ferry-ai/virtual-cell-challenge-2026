# GEARS nella nostra rete: anatomia, limiti e primo innesto

4 ottobre 2026. Codex, chat `01a107a9-9c9c-76c2-9161-258f22bd57b1`, da `7b3d410`.
Mandato: studiare GEARS e adattarne le idee al modello del progetto.

**Conclusione progettuale:** riusare la rappresentazione biologica del bersaglio su grafo,
condizionando esplicitamente i messaggi sui controlli del contesto, dentro l'ibrido a
transfer congelato. È un'ipotesi da confrontare, non un miglioramento misurato.
GEARS originale dichiara di non essere progettato per il trasferimento fra tipi cellulari.

| File | Che cosa dimostra |
|---|---|
| [STUDIO.md](STUDIO.md) | Lettura di paper, codice fissato e benchmark; proposta d'integrazione e contrasti |
| [NOTE_INPUTS.md](NOTE_INPUTS.md), [audit locale](audit_local_inputs_r1.json) | Descrittori già presenti verificati; sorgenti GO/STRING/HGNC assenti ai percorsi storici, da recuperare prima del grafo reale |
| [upstream_manifest.json](upstream_manifest.json) | Commit, URL, dimensione e SHA di otto file ufficiali; snapshot fuori repository |
| [audit_upstream.py](audit_upstream.py), [ricevuta](audit_upstream_r1.json) | Esecuzione della loss originale su fixture: `sign` modifica il valore ma non il gradiente; inventario statico degli usi di `x` |
| [graph_adapter.py](graph_adapter.py) | Nuovo modulo PyTorch e ponte alla `CellNet` D-056; messaggi condizionati dal contesto, ramo proprio conservato, nodi isolati mantenuti |
| [test_graph_adapter.py](test_graph_adapter.py) | Sette test CPU: parità col modello vero, ancoraggio, gradienti, batch, identità dei nodi e serializzazione |
| [VERIFICHE.md](VERIFICHE.md) | Test eseguiti, correzione dell'indice preesistente e limiti del prototipo |

Il ponte è verificato sulle fixture, ma non è collegato al trainer o all'esportatore operativo.
Nessun grafo biologico reale è stato costruito o valutato, nessun training avviato.
Nessuna installazione di GEARS/PyG, acquisizione di dataset/pesi, quota cloud o invio.
Il codice nuovo è originale, ispirato a GEARS; gli otto sorgenti consultati sono MIT,
con licenza originale conservata nello snapshot. Fonte primaria e autori restano attribuiti.
