Risposte preparate a mano per la prova a secco dell'orchestratore.

Non sono uscite di un modello: sono fixture scritte dall'operatore per far percorrere al
motore un caso con una soluzione giusta, una sbagliata, un'obiezione e una correzione.
Servono a collaudare il ciclo senza inviare niente a nessun servizio esterno.

Lo scenario:
  round 1  solver_a risponde 24 (corretto), solver_b risponde 20 (dimentica i multipli di 25)
  round 2  solver_a obietta indicando l'errore, solver_b corregge e la risoluzione viene
           riconosciuta; i tre controlli automatici passano su entrambe le proposte
           -> completamento verificato
