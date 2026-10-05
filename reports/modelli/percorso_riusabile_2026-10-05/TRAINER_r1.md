# Collegamento reale dei reader e confronto transfer

Implementato, verificato su fixture piccole; non ancora eseguito sul corpus reale.
`trainer_stream_v1.StreamFit` chiama training_contract e release_lock, confronta
contesti montati/previsti prima del fit, integra SampleReader e PopulationParts,
e aggiorna realmente i parametri tramite loss di popolazione e cellule campionate.
I controlli sono risolti fra tutte le parti BIO/target senza duplicarli.
Hash e righe vengono verificati nel consumatore, con union completa obbligatoria.
Le probabilità d'inclusione e la numerosità della popolazione correggono il peso
delle cellule; contesti e target richiedono pesi gerarchici congelati dal protocollo.
Ricevute derivano da letture/loss; resume conserva identità della release e manifest,
split e cellule uniche. Due fixture verificano aggiornamento dei pesi, consumo,
resume senza gonfiare conteggi, controlli fra parti e rifiuto delle unioni parziali.

**Manca ancora per il launcher del training esteso:** manifest del catalogo intero
con ruoli/QC e split risolti, feature del transfer e descrittori congelati/hash
verificati (interfaccia `features.verify`), asse e componenti compound riconciliati,
accesso dei tre account, checkpoint modello/optimizer e pesi/bilanciamento fissati.
I ruoli ausiliari devono produrre proprie ricevute d'uso: il loop attuale copre
supervisione di popolazioni/cellule; il contratto rifiuta ausiliari dichiarati e non usati.
Gli attuali manifest cloud sono indici di storage, non manifest ammessi al fit.
Il numero di cellule/contesti su fixture non è evidenza di copertura reale D-053.

## Confronto richiesto dal proprietario il 5 ottobre

Prima del nuovo ibrido, aggiornare il transfer lineare con le banche persistenti.
`configs/recipes/t25.json` fissa effetti t25; t28 mantiene tali effetti e cambia
emissione (CP-0052). Confrontare t25 originale e nuova banca con la stessa emissione
t28, 400 cellule × 5 semi appaiati, stessi fold C/J e target nascosti globali.
Non confrontare solo loss né scegliere il fold dalla numerosità. Conservare separati
nuovi dati, nuovi pesi/fonti e generatore: per la prima ablation cambiano solo le fonti
ammissibili, lasciando fissa la ricetta; calibrazioni nuove hanno prova separata.
Preregistrare soglie e metriche prima dell'esecuzione; S-010 già mostra che più fonti
non garantiscono miglioramento. Nessun invio VCC autorizzato da questo confronto.

Archiviazione: HIPSCI era già nei 395,75 GB grezzi. I derivati aggiungono spazio;
non sono nuova acquisizione e non implicano che un training legga tutti i grezzi.
