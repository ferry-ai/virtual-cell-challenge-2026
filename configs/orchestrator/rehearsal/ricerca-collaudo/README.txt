Risposte preparate a mano per la prova a secco della modalita' scientific_research.

NON VENGONO DA NESSUN MODELLO. Sono state scritte per far passare il motore attraverso
otto situazioni che devono restare distinguibili nel dossier e nel rapporto:

  1. lo stesso paper trovato da entrambi i worker, con titolo diverso e DOI scritto in
     due modi (prefisso https://doi.org/ e maiuscole) -> deve contare come una fonte sola;
  2. una fonte non accessibile (paywall), che resta tale e non diventa "consultata";
  3. una query proposta e non eseguita, che non deve confondersi con una eseguita;
  4. una contraddizione fra i due sulla stessa fonte, che deve restare aperta fino in
     fondo: il programma non ne chiude nessuna;
  5. un'ipotesi nuova presentata come risultato di un paper -- attribuita agli autori di
     una fonte solo "trovata", senza localizzatore. Il programma la segnala per la sua
     forma; NON e' in grado di stabilire che sia falsa, e il rapporto lo dice;
  6. una richiesta del worker di superare il budget, piu' due campi inventati
     (`max_rounds`, `budget`) che devono essere scartati senza effetto;
  7. una fase senza evidenze nuove, con una dichiarazione di saturazione che deve
     restare una dichiarazione;
  8. un errore di formato nella fase 2 di solver_a (nessun blocco di risultato), la
     riparazione unica, e la ripresa senza doppi invii.

I DOI sono finti di proposito -- prefisso 10.0000/finta- -- e le accessioni GEO non
esistono. Se qualcuno legge il rapporto di questa prova credendo che sia un esito di
ricerca, i numeri devono tradirsi da soli.

Come si serve la riparazione: l'adattatore scriptato, alla seconda chiamata sullo stesso
posto, cerca prima `<nome>-try2.txt`. Per questo esistono
`research_phase2-R1-solver_a-2.txt` (illeggibile) e
`research_phase2-R1-solver_a-2-try2.txt` (la risposta riparata).

Comando:

  .\scripts\orch.cmd --config configs/orchestrator/offline-ricerca.yaml ^
      start --brief configs/orchestrator/briefs/ricerca-collaudo.yaml
