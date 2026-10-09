# Routing AMMI: distinzione tra studi prima del fit

9 ottobre 2026. Informazione comunicata da DATI-TRANSFER, da collegare alla sua
ricevuta verificata. Integra la richiesta `RICHIESTA_GUARDIA_AMMI_r3.md`.

Per C-K562 i dodici contesti interni CD4T mantengono l'identità del donatore:
quattro Rest verso la tabella cd4_Rest primaria, quattro Stim8hr e quattro
Stim48hr verso le rispettive tabelle secondarie. Non si aggregano i donatori
in funzione dei risultati. È ancora necessario fissare la mappa completa.

Per C-iPSC i due contesti interni K562 provengono da GWPS ed essential; il secondo
non ha bersagli del pannello nella propria supervisione. La verità primaria
`k562` del manifest indipendente è BULK storica, non uno dei due studi single-cell.
Confrontarla con predizioni condizionate su quei controlli è un confronto tra
studi, non su campioni abbinati. VALIDAZIONE deve confermare il suo ruolo nella
guardia e quello del contesto essential, che resta nominato ed esportato.

Non si cambia split, ancora, controllo o tabella dopo una guardia fallita.
Non sono stati letti nuovi risultati AMMI e non è stato avviato un fit AMMI.
Il codice accetta i cache originali senza array `genes` usando l'asse CSV
ufficiale verificato per hash e ordine; non ricrea i cache per aggiungere l'asse.

Il pacchetto di codice r3 è conservato come prima versione. La revisione seguente
include il controllo di tutte le parti NTC previste, anche quando una parte
mancante non cambierebbe l'elenco dei context_id, e l'asse esterno dei cache.
