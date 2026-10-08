# Passaggio di consegne — DATI-TRANSFER

## VALIDAZIONE

Possiedo soltanto `reports/modelli/dati_transfer_2026-10-08_01a11c34/`.
Richiedo il manifest congelato C/T/J con alias dei gruppi esclusi, componenti
target, riserve protette e assi. Non userò H1 test. Il runner rifiuterà un fold
senza manifest esplicito; produzione con hidden vuoto non è validazione.

Aggiornamenti di registri/indici da integrare dall'unico autore autorizzato:
nuova cartella DATI-TRANSFER, sviluppo di release T1/T2 e riconciliazione di consumo;
stato iniziale implementazione in corso, nessun nuovo score o fit.

Assegnazione proposta: Colab CPU al banco/generazione; derivazioni indipendenti su
Kaggle CPU dopo verifica accessi, slot e consenso. Nessuna GPU richiesta dal
contrasto di centratura. Non sono prenotazioni né job avviati.

## MODELLI-ESTERNI

Contratto richiesto: effetti float32 target × gene, maschera bool della stessa
forma, assi ordinati senza duplicati, scala/normalizzazione esplicite, contesto e
modalità, SHA di input/codice/pesi, split ed esposizioni. Il proprio gene non ha
un trattamento aggiuntivo implicito. L'adattatore deve dichiarare fallback e
copertura prima di applicare emitter o calibrazione.

## Blocchi iniziali

- Accesso al log Colab su G: negato nel sandbox; stato non verificato.
- Autorizzazione cloud da verificare sul job concreto; nessuna quota consumata.
- VALIDAZIONE non ancora identificata nella lista chat letta alle 17:52 circa.
- Messaggio a MODELLI-ESTERNI inizialmente rifiutato dalla revisione automatica;
  consenso specifico del proprietario ricevuto successivamente in questa chat.
