# Guardia interna AMMI: collegamento proposto prima del fit

9 ottobre 2026. Destinatari: VALIDAZIONE e DATI-TRANSFER. Nessun fit AMMI eseguito.
Implementato, ancora da accettare per il runtime biologico: `ammi_guard_v3.py`.
Il protocollo scientifico resta `PROTOCOLLO_AMMI_r2.md`; nessuna nuova soglia di beneficio.

## Codice indipendente e decisione esplicita

Si importa il file `banco/metrics.py` di VALIDAZIONE verificandone byte e SHA256.
La fixture confronta direttamente ogni numero e intervallo di `disc95` con
`banco/bench_core.py:measure`: stessa esclusione dei geni del pannello, stessi target,
supporto 95% definito dalla sola ancora, permutazione dell'intero pannello, maschere
del controllo permutato, bootstrap 10000 e seme 20261008. Non è una seconda metrica.

Proposta operativa da confermare: prima del training, ancora contro le proprie
righe permutate con limite inferiore dell'intervallo > 0 sulle verità primarie.
Se fallisce, la guardia non è identificabile e non si avvia il fit su quel fold.
A ogni epoca si verificano ampiezza e quota comune del residuo, con le soglie r2;
si riportano disc95 della previsione, dell'ancora, del controllo permutato e il
contrasto previsione meno ancora. Quest'ultimo non seleziona epoca, seme o parametri
e non ha una nuova soglia. I risultati esterni restano a VALIDAZIONE.

La scelta di usare il controllo dell'ancora annidata prima del fit è qui nominata
come proposta, non come decisione già presa da VALIDAZIONE. Il wrapper richiede
un riferimento verificato all'accordo prima di accettare `review_status=agreed`.
Serve confermare questa applicazione al pilot o fornire la regola esatta da collegare.

## Mappa dei contesti

DATI sta fissando la mappa dalle NTC alle verità del banco. Per C-K562 si leggono
soltanto le verità interne CD4T; per C-iPSC soltanto K562. Ogni context_id interno
deve apparire nel contratto, con verità primaria o stimolo descrittivo dichiarato.
I contesti esterni sono esportati separatamente; nessun pooling o scelta del
contesto a posteriori. Il trainer non legge la verità del lignaggio esterno.

La mappa deve identificare: context_id, lignaggio, tabella di verità, ruolo,
pin dei dati raw/shrunk/se e percorso privato risolvibile su davidmaisterx.
Se un contesto non ha una verità corrispondente, deve essere dichiarato e risolto
nel contratto prima del fit; non si elimina silenziosamente.

## Integrazione ESM2 distinta dal pilot

La regola congelata resta T0 dove predice, ESM2 come ripiego. Il Lead segnala che
t36 copre già 300/300 target: la semantica per target intero potrebbe non cambiare
alcun valore. Occorre chiarire se il contratto usa righe o coppie target-gene e
contare il delta, senza reinterpretare la regola dopo i risultati. Le maschere
di t36 non misurano quelle del refit T3. AMMI resta sopra l'ancora T0 congelata;
non si sostituisce con T3 senza un nuovo protocollo. Nessuna submission implicita.

## Precedenti e arresto

S-009: una misura senza controllo positivo non sostiene la lettura; confronto
esatto contro il banco e blocco del fold se il controllo primario è inefficace.
S-006: guardie del residuo e quota comune della previsione intera riportata.
S-013: audit di massa e loss per lignaggio; nessuna dominanza dedotta dal solo
numero di contesti. Il codice e le fixture non dimostrano beneficio biologico.
