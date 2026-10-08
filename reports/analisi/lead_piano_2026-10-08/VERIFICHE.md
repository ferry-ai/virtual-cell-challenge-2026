# Verifiche dell'analisi lead dell'8 ottobre

## Eseguite

- Letti accordi, ambiti, piani, regole di copertura/validazione e precedenti S-001–S-010.
  Verificato lo stato documentale dei report esterni al percorso obbligatorio usati
  per GEARS, vincitori 2025, pezzi adottabili, Stack e risposta comune.
- Letta integralmente la chat Claude fornita dal proprietario come allegato;
  confrontate le affermazioni con registro, ricevuta del fit e codice stage 100.
  L'allegato personale non è copiato nel repository pubblico.
- Eseguito `audit_metadata.py` con il wrapper del progetto: sei controlli di
  coerenza passati; risultato in [audit_r1.json](audit_r1.json), hash degli input inclusi.
  Il primo tentativo, prima di scrivere l'output, ha rilevato che due campi
  `samples_levels` sono testo anziché dizionari: l'audit li riporta come mancanti
  e i conteggi dei livelli come sottoinsieme, senza convertirli in zero.
- Consultate fonti primarie web di PIE, STATE, Stack e PRiMeFlow. Lettura statica
  di parti del codice PIE, non esecuzione. Limiti delle pagine non recuperate e
  provenienza nel [catalogo esterno](FONTI_ESTERNE.md).
- `python scripts/31_check_docs.py`: passato; [output](docs_check_r1.txt).
- Suite obbligatoria `.\scripts\py.cmd -m unittest discover -s tests`:
  290 test, 286 passati, tre errori `ModuleNotFoundError: cell_eval2.config`
  e un failure del nuovo indice prima di registrare i file in Git; [output](tests_r1.txt).
  I tre errori riguardano due smoke test dello stadio 73 e il confronto delle
  componenti di fedeltà. La sonda di import conferma che il wrapper usa il venv
  del progetto, `cell_eval2` è un namespace e `cell_eval2.config` non è disponibile.
  Nessuna modifica di questa sessione a quei test, allo scorer o all'ambiente.
- Il test dell'indice legge `git ls-files`, non i file ancora untracked:
  il nuovo report va registrato prima del ricontrollo mirato. Nessuna modifica
  al test per aggirarlo.
- Dopo la registrazione, tutti gli **11 test** di `test_live_tree.py` passano:
  [ricontrollo](tree_tests_r2.txt). Risolto il failure dell'indice, restano i tre
  errori dell'ambiente scorer; la suite completa non è stata ripetuta senza
  una riparazione della dipendenza. Anche il [controllo documentale finale](docs_check_r2.txt)
  passa.
- `git -c core.whitespace=cr-at-eol diff --check`: passato. La scheda R-LEAD
  era già tracciata con CRLF; il parametro conserva quel formato, senza
  normalizzare tutte le righe o cambiare la configurazione Git.

## Limiti

Nessuna rilettura delle matrici cellulari, nessuna verifica live dei runtime o
dei file cloud, nessuna inferenza o nuovo confronto predittivo. Non sono
certificati copertura integrale, disponibilità dei pesi sul runtime, compatibilità
di tutte le licenze, durata dei job o miglioramento ufficiale.
Gli esiti scientifici riportati rimangono quelli dei report precedenti.
