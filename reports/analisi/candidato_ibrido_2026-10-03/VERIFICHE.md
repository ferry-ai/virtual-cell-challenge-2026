# Verifiche della consegna

3 ottobre 2026, Codex. Verifiche di metadati e documentazione, non validazione del candidato.

- `inspect_training.py`: lettura autenticata delle ricevute di due training già conclusi;
  sei JSON tecnici per kernel, hash e dimensioni conservati. Nessun avvio, modifica o
  arresto di job. URL firmati e credenziali non sono salvati.
- `audit_inputs.py`: eseguito su metadati locali; riconta otto gruppi nel pilot e 21 nella
  proposta di catalogo. Riproduce la guardia di bilanciamento ±0,02 già nel protocollo:
  H1 non passa, HepG2 passa. Non sostituisce la decisione completa né legge metriche scientifiche.
- Nessuna matrice di espressione aperta sul portatile; nessun nuovo dataset acquisito.
- Integrità: ricalcolati e confermati i sette hash di input di `audit.json`, 83.114 byte in
  tutto. Nelle ricevute non compaiono marcatori di credenziali o URL firmati.
- `scripts/31_check_docs.py`: OK, 57 checkpoint, registro, decisioni e link coerenti;
  197 percorsi accettati come archiviati. Controlla la struttura, non la verità delle tesi.
- `git diff --cached --check`: nessun errore.
- Suite completa: **287 test passati**, 431,796 secondi, codice di uscita 0. Eseguita con
  `.\scripts\py.cmd -m unittest discover -s tests` nell'ambiente nativo; [log](tests_r1.txt).
  I numeri dello scorer nel log sono fixture sintetiche, non punteggi del candidato.

Il primo accesso API nel sandbox ha incontrato il blocco di rete Windows; la lettura
autenticata fuori dal sandbox è riuscita. Non si sono modificate dipendenze o credenziali.
