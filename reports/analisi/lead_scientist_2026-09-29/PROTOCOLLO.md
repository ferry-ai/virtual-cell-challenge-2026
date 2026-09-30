# Revisione operativa del 29 settembre: previsione, generazione e scelta del candidato

**Stato:** in corso. **Responsabile:** Codex, chat `01a0ee03-b357-7012-81a9-e8d7de767478`.
Mandato del proprietario del 29/09: rivedere evidenze e bias, analizzare i dati e realizzare un
candidato competitivo entro le 02:00 italiane del 30/09. Le vecchie scelte metodologiche sono
riesaminabili; i risultati storici restano immutati. Protocollo scritto prima dei nuovi esperimenti.

## Ambito e separazione dal lavoro esistente

La sessione Claude `f2abd9a6` sta preparando t27 e il banco K562 dell'azione 4 di R-REV.
Questa revisione non modifica quei file o processi. Il t27 conserva il suo stato di candidato
senza autorizzazione all'invio. Le nuove analisi scrivono solo in questa cartella o in nuove
destinazioni della radice dati. Nessun upload, acquisto cloud o push è implicito in questo protocollo.

## Ipotesi da discriminare

1. **H-ampiezza:** il plateau documentato non identifica ancora l'ottimo di ampiezza della ricetta
   corrente: alcuni confronti cambiano più fattori. Confrontare le ricette effettive e, se utile,
   ampiezze della stessa direzione, con generatore e seme fissi.
2. **H-generazione:** parte del disallineamento con il vero nasce fra effetti e cellule, oppure
   dalla differenza fra media dei CPM per cellula e composizione dei conteggi aggregati. Misurare
   separatamente profilo atteso, profilo realizzato, distribuzione dei controlli e chiamate DE.
3. **H-piattaforma:** i dati Flex e le normalizzazioni sull'asse comune contengono informazione
   utile non usata. Quantificare copertura, affidabilità e differenze prima di costruire un modello.

## Lettura dei risultati

- Le analisi dei punteggi passati sono retrospettive. Una sola differenza fra semi non è una stima
  precisa della variabilità; ±0,005 resta una soglia decisionale operativa, non un intervallo statistico.
- I proxy non sono punteggi VCC. Il banco a sei metriche richiede anche un controllo di supporto
  genico, numerosità e forza degli effetti: usare lo scorer corretto non elimina il cambio di dominio.
- Una nuova ipotesi sceglie metrica, controllo, supporto e regola prima del calcolo che la giudica.
  Un'esplorazione successiva è dichiarata tale; non viene trasformata in conferma indipendente.
- Una proposta di invio espone guadagno atteso, rischio, confronto con t25/t22 e informazione
  ottenibile; conserva ricetta, manifest, hash e predizione registrata prima della generazione.
- La competitività si misura con un risultato ufficiale; preparazione e convalida del file non
  dimostrano miglioramento del punteggio.

## Evidenza iniziale

- `docs/PROGETTO.md`, `docs/piani/revisione-critica.md` e `docs/REGISTRO.md`.
- `reports/invii/lezioni_invii_2026-09-28/` e confronti degli invii t22–t26.
- `reports/trasferimento/risposta_comune_2026-09-26/`.
- `reports/generatore_e_banchi/banco_k562_pannello_2026-09-29/RISULTATI.md`.
- Scorer pubblico: https://github.com/ArcInstitute/cell-eval2/blob/main/docs/vcc2026_metrics/vcc2026-metrics.md

I file successivi di questa cartella distinguono misure, interpretazioni e proposte.
