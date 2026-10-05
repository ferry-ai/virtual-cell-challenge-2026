# Dimensioni del blocco corrente — 5 ottobre

`sizes_current_r1.json` riconcilia l'indice con i log osservati circa 13:23 CEST:
326,17 GB grezzi, 27,00 GB di banche e 106,83 GB di campioni CD4 misurati.
Quindici contesti biologici in quattro famiglie: dodici donatore/stato CD4,
KOLF iPSC, HCT116 e HEK293T. Le banche usano 32.583.194 cellule ammesse.

Campioni nuovi: KOLF 7,34 GB misurati e unione verificata in
`snapshot_parts_r3/state.json`; HCT116 circa 17,93 GB ed HEK293T circa 28,17 GB
sono stime da avanzamento, non dimensioni finali. Complessivamente circa
187 GB di derivati pronti o previsti, circa 190 GB arrotondati. Non sommare
i 326 GB grezzi ai dati effettivamente necessari al trainer. Lettura a blocchi;
questi valori non descrivono RAM o quantità usata nel singolo fold.

Ultime parti: estrapolazione dai log 21–24 minuti per HCT116, 47–70 minuti
per due parti HEK293T; le altre due nuove HEK293T ancora senza eventi di
calcolo nel log osservato. Indicazione prudente 45–90 minuti per la lavorazione
cloud residua, soggetta ad avvio, I/O, densità degli shard e guasti. Non è
una previsione verificata dell'avvio del training.

Stato verificato nello snapshot r3: KOLF 3/3; HCT116 2/4; HEK293T 2/6.
Il trainer esteso non è avviato. Collegamento dei lettori, copertura delle
altre linee del catalogo e validazione t28 restano aperti; quindici contesti
non costituiscono il catalogo completo richiesto da D-053.
