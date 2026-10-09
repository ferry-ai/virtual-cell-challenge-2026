# Emendamento operativo: i due fit none non consumano NTC

9 ottobre 2026, prima di qualsiasi risultato AMMI. I due fit none già previsti
possono partire prima delle NTC, poiché il loro stato di contesto è per
definizione il vettore di uno. Non sono due nuovi fit né una nuova architettura.

Il registro `ControlsNotConsumed` contiene soltanto identificativi di contesto
e dimensione dell'asse genico congelato; non contiene cellule, maschere o RNA
fittizi. Qualsiasi accesso ai suoi valori fallisce. Il forward none non legge
il registro come matrice. La dimensione dell'encoder resta quella dell'asse
genico canonico, conservando architettura e ordine di inizializzazione casuale.

Restano identici righe, target, contesti, query, split, ancore, maschere delle
risposte, pesi, mu_train, seme17, inizializzazione, batch32, due epoche, loss,
AdamW e tutte le guardie. La validation interna usa le vere tabelle aggregate
e il codice indipendente originale, compreso il controllo positivo prima
del training. Non si sostituiscono le verità della guardia con dati sintetici.

La fixture comparativa registra pesi finali, loss, masse e predizioni identici
con NTC arbitrarie, NTC cambiate e registro privo di NTC; include guardie reali
su verità sintetica e parità del checkpoint ricaricato. La fixture non dimostra
beneficio biologico. La prova è `none_equivalence_r1.json` con i pin del codice.

Solo il braccio none può dichiarare `controls_not_consumed=true`; cells e la
produzione continuano a richiedere tutte le parti NTC verificate. Le ricevute
none non dichiarano copertura NTC, né D-053 completa. Il confronto appaiato con
cells conserva le stesse righe e lo stesso seme. Nessun fit aggiuntivo, nessuna
nuova pubblicazione, acquisto, submission o estensione degli accessi privati.
