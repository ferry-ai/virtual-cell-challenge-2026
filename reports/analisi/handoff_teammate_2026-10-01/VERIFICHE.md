# Verifiche della consegna

1 ottobre 2026. Documenti e preflight nuovi, training e invii R-LAB preservati.
Nessun dataset, venv, peso o credenziale incluso nella consegna Git.

## Preflight

Eseguito sulla macchina di origine con `scripts/py.cmd`, radice dati esplicita e destinazioni
nuove. `source_machine_r1.json` è la prima prova nel sandbox: runtime di ricerca individuato,
`cell_eval2.config` non individuabile. Quella prima versione cercava il modulo CLI `vcc_cli`;
verificato dall'entry point installato che il modulo è `vcc`, corretto il preflight e conservata
la prima fotografia. `source_machine_r2.json` ripete l'inventario corretto nel sandbox;
`source_machine_r3_native.json` usa lo stesso Python fuori dal sandbox e individua anche
`cell_eval2.config`. Nessun risultato sulla macchina destinataria è inferito.

Il checker usa libreria standard; individua moduli senza sostituire la prova di import/API.
Non legge risposte H1 test, raw, pesi o credenziali. Il controllo di un file dati verifica
solo presenza e byte. I check scientifici e di runtime completi sono nel prompt.

`preflight_checks_r1.json` registra tre controlli passati: radice mancante segnalata senza
crearla, nessuna radice implicita del proprietario, codice uguale al commit dell'audit dopo
normalizzazione delle sole terminazioni di riga.

## Correzione scorer

**Affermazione corretta:** le verifiche dell'audit precedente osservavano tre errori di
import `cell_eval2.config`; dedurne un ambiente della macchina incompleto era troppo forte.
Il risultato dei processi nel sandbox resta valido e il report originale resta immutato.

**Misura nuova:** stesso eseguibile
`C:/Users/ferra/vcc2026-data/.venv/Scripts/python.exe`, Python 3.12.3, nessuna installazione:
nel sandbox `cell_eval2.__file__` e `find_spec('cell_eval2.config')` restituiscono `None`;
fuori dal sandbox indicano rispettivamente `Lib/site-packages/cell_eval2/__init__.py` e
`Lib/site-packages/cell_eval2/config.py` del medesimo venv. L'inventario nativo del runtime
è conservato in `source_machine_r3_native.json`.

La suite completa eseguita fuori dal sandbox con `scripts/py.cmd -m unittest discover -s tests`
ha concluso: **287 test, 232,940 secondi, OK**. Per i test che leggono i file tracciati è stato
usato un indice Git temporaneo con HEAD e i soli file della consegna: l'indice condiviso e
il lavoro dell'altra sessione sono rimasti preservati. Il codice del modello era ancora
quello dell'audit; le modifiche del training aperte dall'altra sessione dopo la prova non
sono state incluse in quel test. `31_check_docs.py` è passato anche dopo CP-0054:
54 checkpoint, registro, decisioni e link coerenti; 197 percorsi riconosciuti come archiviati.

**Interpretazione:** è misurata una differenza di visibilità fra contesti di esecuzione;
non è isolata la causa precisa nei permessi o nel sandbox. Non occorre reinstallare sulla
macchina di origine. Il teammate deve provare import e API nel proprio runtime, confrontando
agente e terminale nativo quando divergono. Le misure scientifiche e i difetti della rete
dell'audit non sono modificati. Correzione registrata in CP-0054 e nel registro documentale.

## Pubblicazione

`publication_check_r1.json` registra base remota, commit e blob da pubblicare prima del
commit di consegna. Controllati formati riconoscibili di credenziali e dimensioni dei blob;
il controllo non certifica l'assenza di ogni contenuto confidenziale.
`publication_check_r2.json`, prodotto da `publication_check.py`, copre anche i commit
successivi all'audit fino a `39f451d` e i 17 file nominati della consegna: 21 blob nuovi,
massimo 230.844 byte, nessun blob oltre 100 MB e nessun formato di credenziale individuato.
Il primo fetch interattivo non restituiva output: interrotto quel solo processo e ripetuto
senza prompt credenziali; fetch riuscito, nessun commit remoto divergente.
Il primo dry run del push ha raggiunto il timeout per trasferimento lento; il dry run
con `http.version=HTTP/1.1` è riuscito. Nessun force push.

Il push finale e gli esiti dei controlli sono verificati nella sessione e riportati nel messaggio
di consegna. I file t29 non committati appartengono alla sessione R-LAB attiva; non vengono
presi in carico da questa sessione. Le credenziali e configurazioni `.claude/` locali restano fuori.
