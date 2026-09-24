# Verifica

- Lo script ha completato l'analisi e verificato: 1.626 righe, 218 bersagli,
  sei contesti per coppia bersaglio–stimolo, assenza di duplicati e valori non finiti.
- `scripts/31_check_docs.py`: superato, 36 checkpoint e registro coerente.
- Suite del repository: 147 test, un fallimento e un errore. Il controllo
  dell'indice dei report legge soltanto `git ls-files`: la nuova cartella esiste
  ma non è ancora tracciata in Git. Il test della fedeltà del banco fallisce
  perché manca `cell_eval2.config` nell'ambiente. L'analisi non usa quel modulo.
  Nessuna modifica all'ambiente o al codice di produzione per questi due esiti.
