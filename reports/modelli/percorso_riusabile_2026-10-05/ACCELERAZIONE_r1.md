# Collo di bottiglia operativo e prosecuzione

Misurato: preflight Grok r2 alle 15:59:28 UTC vede un job attivo (K562 GWPS)
fra gli ultimi 20 notebook per account. Non dimostra 15 job simultanei attivi.
La maggior parte delle ingestion lanciate è ormai chiusa. RAM disponibile per
sessione non aumenta di per sé CPU o throughput disco né si somma tra sessioni.

Il parent riesegue i 13 test r2: PASS. Nessuna ricevuta di push né relazione finale
r2 al controllo; PID12704 non esiste più. Il log conserva un timeout del classifier
permessi, ma non prova da solo la causa dell'uscita. Non toccato PID5060 estraneo.

Prima di lanciare i pacchetti r2 occorre correggere: parametri held_groups e
hidden_targets non passati al runtime prima di statistiche; asse con soli indici
numerici senza simboli/hash; componenti assunti singoli dalla sola assenza di
separatori. Le fixture non certificano questi parametri del lanciatore.
R2 conservata e non adottata come percorso completo, nessun dataset alterato.

Stessa sessione Grok ripresa in agenti/grok_transfer_esteso_r3, PID19532, ore
16:12:42 UTC, senza secondo worker concorrente. Priorità: pacchetti eseguibili
per banche chiuse, split/asse/hash verificati; ready_dispatch.json consegnato al
parent, che verifica e lancia sugli slot entro accessi/quote, mentre Grok continua
le altre fonti. Worker non esegue push per evitare collisioni/attese autorizzatore.
Indice input r10 obbligatorio. Nessun nuovo calcolo lanciato da questa ripresa.
