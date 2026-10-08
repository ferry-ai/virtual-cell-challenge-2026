# Transfer rapido parallelo — verifica di riuso

Presa in carico DATI-TRANSFER, 8 ottobre 2026. Mandato umano verificato nella
chat Lead: messaggi `01a11d72-4656-73b3-860c-4455e8c2fa7c` e
`01a11d72-e65d-71b1-8766-94ad1c0876db`. Richiesta: un transfer tipo t36
in parallelo, senza bloccare il training attuale. La preferenza CPU df11 per
questo ramo non implica avviare GPU; le due ore GPU riferite dal proprietario
non sono una quota misurata da questo audit.

## Regola prima di un eventuale nuovo fit

Conservare stage 100, formula, centratura sul pannello, pesi unitari per fonte,
cis e ampiezza 1,576 del t36. Verificare prima T1 e le popolazioni già derivate.
Se gli input aggiuntivi ammissibili sono già compresi in T1, riusare quel
candidato e le sue ricevute: una nuova esecuzione degli stessi byte non crea
un nuovo modello. T2 cambia la popolazione di centratura e rimane un confronto
distinto. Non cambiare l'ammissione dopo aver letto i risultati del banco.

Il controllo confronta identità delle banche, unità, bersagli del pannello e
voti effettivi. CD4 per donatore/stimolo, HIPSCI per clone e K562 GWPS non
diventano automaticamente voti indipendenti in più: verificare il rapporto
con gli aggregati già usati. KO e CRISPRa restano separati. Le sorgenti fuori
pannello conservano il proprio ruolo nel trainer esteso e in D-053.

Un nuovo fit parte solo se l'audit identifica dati compatibili aggiuntivi,
non duplicati, che cambiano il supporto a formula invariata. In tal caso una
nuova release elenca prima i byte, il contrasto e gli adattamenti inevitabili;
il preflight misura uno slot CPU separato e gli input disponibili. Nessun
job ESM2 viene fermato, riavviato o modificato. Nessun invio VCC.

## Precedenti e limiti

- S-010: T1 è già il contrasto di ammissione a formula invariata; non
  attribuire guadagni a un mero aumento del conteggio di righe.
- S-005: una tabella aperta non prova un voto; controllare consumo per fonte
  e bersaglio e mantenere separate cellule nella banca e contributi al pannello.
- S-006: la centratura fuori pannello modifica la risposta comune; non
  presentare T2 come sola estensione degli input di t36.

Segnale di arresto del duplicato: tutte le osservazioni compatibili già
rappresentate nella release T1. Segnale di blocco tecnico: hash, assi o
provenienza incoerenti. Il riuso non promuove il candidato: la decisione
indipendente di VALIDAZIONE e le lacune D-053 restano esplicite.
