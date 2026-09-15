Risposte preparate a mano per la prova a secco del percorso deep_kimi.

Non sono uscite di DeepSeek o di Kimi: sono fixture scritte dall'operatore. Servono a
percorrere il ciclo a due (proposta indipendente, obiezione, revisione) e a vedere come
il motore lo chiude, senza aprire alcuna sessione reale.

Scenario:
  round 1  proposte indipendenti e diverse (CSV con schema fisso contro JSONL)
  round 2  obiezioni precise da entrambe le parti, modifiche dichiarate, convergenza su
           JSONL con compressione
  round 3  nessuna delle due cambia posizione: le proposte restano stabili e vicine
           -> convergenza delle proposte, che NON e' completamento verificato
