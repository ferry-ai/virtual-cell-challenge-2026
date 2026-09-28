# Prima misura Mixscale

Scritto dopo l'inventario dei file e prima del calcolo del trasferimento.
L'archivio contiene file di testo separati da spazi: il primo inventario `source_inventory_r2/`
li ha letti come una colonna sola. Nomi dei file e checksum restano validi;
quelle dimensioni di colonna non descrivono la tabella. La lettura qui richiede le
sei colonne esplicite `log2FC_*`, senza confonderle con i coefficienti `beta_*`.

**Prova esplorativa:** per ogni stimolo separato, tenere fuori una delle sei linee
e prevedere ciascun bersaglio con la media non pesata delle altre cinque linee.
Confrontare con una previsione che ignora il bersaglio: media, nelle sole cinque
linee sorgenti, di tutti gli altri bersagli dello stesso stimolo. Nessun tuning.
Usare solo geni finiti in tutte e sei le linee per quel bersaglio e nel controllo,
escludendo tutti i bersagli Mixscale e tutti i 300 del pannello ufficiale.
I mancanti non diventano zeri. Calcolare Pearson, coseno e accordo di segno sui
primi 100 geni per valore assoluto della previsione specifica del bersaglio;
usare gli stessi geni per il confronto col controllo.

Non è un banco sulle cellule né un punteggio ufficiale. I dati DE possono incorporare
scelte di selezione o stime congiunte degli autori: va verificato prima di considerarli
una validazione indipendente. Un vantaggio su questa prova non adotta una sorgente
e non dimostra che una rete generalizzi. I cinque stimoli non sono cinque linee nuove.
