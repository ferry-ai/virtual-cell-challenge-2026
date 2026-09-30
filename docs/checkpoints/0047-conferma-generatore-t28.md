# CP-0047 — Conferma pubblica del generatore e registrazione t28

- **Data:** 2026-09-29
- **Tipo:** osservazione
- **Redatto da:** Codex, sessione 01a0ee03-b357-7012-81a9-e8d7de767478
- **Revisione umana:** no
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

La combinazione di ampiezza e dispersione scelta sui 48 bersagli di sviluppo
mantiene il vantaggio su 96 bersagli disgiunti e tre semi del generatore?

## 2. Cosa è stato fatto

Il job Colab 062 ha eseguito riferimento e due finalisti su HepG2 pubblico, con
effetti sorgente K562 congelati e scorer cell-eval2 0.16.0. Ha terminato alle
18:50:23 UTC con codice 0. Protocolli, 41 report originali e ricostruzione indipendente:
`reports/analisi/lead_scientist_2026-09-29/PROTOCOLLO_GENERATORE.md`, relativi emendamenti,
`generator_confirmation_r3/` e `confirmation_analysis/results_r1/` nella stessa cartella.

## 3. Cosa si è osservato

**Misurato:** ampiezza1,5/dispersione1 guadagna +0,028918 nella proiezione locale,
IC appaiato97,5% [0,019526;0,039342]; tutti i semi sono positivi. Ampiezza1,5/dispersione0,5
guadagna +0,023031, IC [0,013354;0,033183], anch'esso positivo nei tre semi. Entrambi
passano la regola preregistrata. Fonte:
`reports/analisi/lead_scientist_2026-09-29/generator_confirmation_r3/confirmation/selection.json`.

**Verificato:** aggregazioni, pairing, eleggibilità, MSE come rapporto di somme e
bootstrap indipendente riproducono il risultato. Per il primo finalista, 73/96
bersagli hanno contributo positivo, i primi cinque spiegano il26,7% del guadagno;
senza quei cinque il delta ricalcolato è +0,022330. La MSE grezza peggiora di0,381556;
la deviazione standard dei tre delta è0,005442. Fonte:
`reports/analisi/lead_scientist_2026-09-29/confirmation_analysis/results_r1/analysis.json`.

## 4. Interpretazione e incertezza

**Interpretazione:** il vantaggio è soprattutto fedeltà direzionale e reach; NMAE e
Jaccard peggiorano, PDS rimane quasi invariato. L'interazione locale giustifica
valutare ampiezza e dispersione insieme (D-047), non attribuire il guadagno a una sola.

**Limite:** il banco vede un contesto pubblico, altri bersagli e solo K562 come
sorgente. La produzione usa quattro sorgenti t25 e i controlli ufficiali. Il delta
non è un punteggio VCC né una previsione calibrata del suo incremento. L'intervallo
non misura l'incertezza fra contesti e tecnologie.

## 5. Spiegazione semplice

Prevedere più variabilità fra cellule può aiutare quando cambia anche la forza
del segnale. La combinazione scelta ha funzionato su bersagli tenuti da parte;
ora occorre verificare se il beneficio si trasferisce alle cellule della gara.

## 6. Conseguenze

Il primo finalista, già primo nello sviluppo, è registrato come t28 prima della
generazione completa: effetti t25 ×1,5 e dispersione per gene ×1, seme20260912,
300 bersagli ×400 cellule ×3 contesti. Banda ufficiale soggettiva [0,135;0,180],
regola di lettura a ±0,005 contro t25. Fonte:
`reports/invii/prediction_t28_2026-09-29/prediction.json`, scritto alle18:56UTC,
SHA256 `a2081b9cd615a1020a962def21eafa54d7116db79285887f56c775033d61e192`.

Seguono generazione e packaging convalidato. Nessun invio autorizzato da questo
checkpoint. Le due vie neurali proseguono; t28 non contiene una correzione neurale.

## 7. Cosa corregge

Nessun punteggio storico. Completa la prova annunciata in CP-0046. Sostiene la
revisione metodologica D-047 del vincolo assoluto a cambiare un solo fattore:
quel vincolo non era sufficiente per esplorare interazioni.

## 8. Domanda di comprensione

Perché una conferma su altri bersagli della stessa linea non dimostra ancora un
guadagno sui contesti ufficiali?
