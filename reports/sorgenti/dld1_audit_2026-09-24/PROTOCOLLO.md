# Audit esplorativo DLD-1 e prossime sorgenti

Scritto il 24 settembre 2026 prima del calcolo delle correlazioni di questo audit.
Sono già stati letti manifest, intestazioni e una riga delle matrici Low1.

## Domande e metodo

1. Verificare dimensioni e SHA256 dei quattro file locali contro il manifest ricevuto.
   Questo prova coerenza locale, non autenticità indipendente del download.
2. Contare colonne, bersagli distinti, copertura dei 300 bersagli e dell'asse ufficiale.
   Separare bersaglio biologico e suffisso della colonna (`_P1`, `_P2`, ...).
3. Per un primo confronto riproducibile usare solo le colonne `_P1`, senza trattare
   suffissi diversi come repliche indipendenti. Nessuna media fra guide in questa prova.
4. Allineare per simbolo esatto, segnalare duplicati, conservare i mancanti come NaN.
   Confrontare DLD-1 e K562 solo su geni finiti per tutti i bersagli confrontati,
   escludendo tutti i geni del pannello bersaglio per ridurre il contributo cis.
5. Misurare correlazione Pearson, coseno e accordo di segno sui primi 100 geni
   per effetto assoluto K562. Confrontare l'abbinamento corretto con tutti gli
   abbinamenti a bersaglio diverso sul medesimo asse e con gli stessi geni selezionati.
   Riportare mediana per bersaglio e distribuzione: non sono punteggi ufficiali.
6. Ripetere coseno e Pearson sottraendo, separatamente per ogni sorgente, la media
   sui bersagli condivisi. È diagnostica trasduttiva, non validazione zero-shot.
7. Non convertire l'ampiezza né alimentare la pipeline finché base del log,
   significato dell'errore standard e semantica dei suffissi non sono verificati.
   Pearson, coseno e segno non dipendono da un fattore di scala positivo.

## Regola di lettura

Una copertura positiva rende DLD-1 tecnicamente esaminabile. Un vantaggio rispetto
ai bersagli sbagliati indica specificità descrittiva, non miglioramento VCC.
Questa analisi non adotta né scarta una sorgente e non sceglie una ricetta.
Low1 da solo non dà una stima della riproducibilità. Un controllo successivo
deve includere Low2 e chiarire se le due stime condividono cellule o controlli.
