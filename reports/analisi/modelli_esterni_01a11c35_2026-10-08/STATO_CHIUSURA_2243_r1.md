# Chiusura AMMI: stato e percorso minimo

9 ottobre 2026, 22:43 Europe/Rome. Orologio letto alle 20:42:46 UTC.
Obiettivo operativo richiesto dal proprietario: circa 00:05 del 10 ottobre,
senza modificare protocollo o copertura per accorciare. Non è una previsione
di completamento sostenuta dalle misure disponibili.

## Misurato

- Due NONE completati. VALIDAZIONE ha verificato i payload e letto NONE−A0:
  nessun delta disc95 risolto sui due fold. Fonte:
  `reports/analisi/validazione_banco_eace4d03_2026-10-09/RISULTATI_AMMI_NONE.md`.
- Due CELLS avviati alle21:57/21:59, ancora RUNNING su T4 nei controlli
  automatici delle22:41. Codice remoto corrispondente, versione1, privati.
- Snapshot dei log delle22:37, `ammi_c-*_cells_progress_r1.json`:
  iPSC ancore completate22:12:46; controlli22:27:18 (871,95s), risposte22:33:50
  (391,14s), baseline interna22:33:57 (7,03s). K562 ultimo evento ricevuto:
  ancore completate22:25:46. Lo stream termina con ConnectionError; il silenzio
  successivo non prova né la fase attuale né un arresto. Nessuna ricevuta di
  fine ottimizzazione è stata ancora osservata.

I tempi degli input sono importanti: le GPU assegnate non implicano che tutto
il tempo trascorso sia training. Non esiste ancora una misura del tempo del fit
CELLS completo con cui promettere l'ETA produttiva.

## Preparazione di produzione eseguita

`ammi_production_draft_prepared_r1.json` punta al pacchetto esterno a Git già
costruito: codice congelato, ancore e vista production, tutte le30parti NTC di
training e le3parti ufficiali,50contesti di controllo.1478chunk di risposte,
1586payload numerici distinti complessivi,36.682.371.278byte compressi dichiarati.
Quest'ultima cifra è l'impronta degli input, non un nuovo trasferimento:
parte dei file è già montabile nativamente, secondo l'account scelto.

Il gate `ammi_production_readout_pending_r1.json` è **chiuso** e dichiara
espressamente che i contrasti non sono stati letti. Due test superati in
`ammi_production_draft_tests_r1.txt`, compreso il vero runner che rifiuta questa
ricevuta prima di creare output o fare calcolo. Nessun job production lanciato.

Configurazione prefissata: cells, seme17, due epoche, batch32, limite64bersagli
per contesto; riferimento ESM2 e pesi ricalcolati sulla vista production.
Ancora di training senza il lignaggio della riga, T0 piena per le query.
Resta un candidato tecnico sul pannello: D-053 non diventa completo.

## Dipendenze e sequenza

1. La continuazione PID22492 resta unico collector dei due CELLS; verifica
   codice remoto e raccoglie metadati appena terminali. Nessun rilancio.
2. Dai metadati verificati congelare i quattro export primari native/swapped
   con hash/byte, oppure conservare l'eventuale fallimento diagnostico swapped
   senza rifit. Tutti gli altri export restano disponibili, non sono eliminati.
3. VALIDAZIONE ha già il lettore e le verità su df11. NONE,A0,T0 sono accessibili
   lì. L'accesso df11 ai nuovi CELLS di MX non è ancora autorizzato: predisporre
   elenco esatto e passaggio privato minimo appena gli export esistono.
   Su MX i checkpoint sono nativi ma il banco richiede input privati mancanti:
   non si assume che un altro job possa usare il consenso riservato ai quattro fit.
4. Leggere realmente CELLS−A0, CELLS−NONE e, separatamente, CELLS−T0 per entrambi
   i fold. A0 e T0 non sono la stessa ancora. Scrivere una decisione tecnica
   esplicita, con pin dei risultati, senza flag positivi fittizi.
5. Con tale decisione ricostruire una destinazione production nuova usando
   `build_ammi_runtime_v4.py --fold production --mode cells --production-readout`;
   confezionare e verificare il pacchetto, preflight accessi/quota e runtime,
   singolo lancio. Il draft attuale non va sbloccato modificandolo.
6. Raccogliere checkpoint finale, parità dopo ricarica, consumo di ogni riga e
   massa per lignaggio, guardie e export. Questo chiude il checkpoint tecnico;
   promozione e submission rimangono decisioni distinte.

La lettura minima degli effetti può consentire una decisione sul fit tecnico;
non viene aggiunto il banco a sei membri come prerequisito nuovo a quel fit.
Il banco resta necessario per la successiva promozione secondo le regole
congelate. PASS tecnico non equivale a beneficio.

DATI sta confrontando gli accessi nativi df11/MX senza nuove estrazioni né
locator. Il consenso105+12 era limitato ai quattro pilot: eventuali input
production richiedono una specifica concreta. La parte preparabile senza
questa dipendenza è già eseguita nel draft. Nessun acquisto, corpus ridotto,
nuovo seme, griglia o sostituzione dell'ancora.
