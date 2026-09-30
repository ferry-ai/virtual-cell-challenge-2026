# Conferma del generatore: entrambi i finalisti passano

29 settembre 2026. **Misurato sul banco pubblico HepG2, non sul servizio VCC.**
Il job 062 ha concluso alle 18:50:23 UTC con codice 0. I 41 report piccoli copiati
in `generator_confirmation_r3/` sono identificati dal relativo `COPY_MANIFEST.json`.
L'analizzatore indipendente in `confirmation_analysis/` ha ricostruito la decisione,
le aggregazioni e il bootstrap; `results_r1/analysis.json` riporta esito positivo.

## Confronto preregistrato

96 bersagli diversi dai 48 usati per selezionare, tre semi, riferimento ampiezza 1
e dispersione 0. Tutta la verità perturbata disponibile; 2.000 controlli e 400
cellule previste per bersaglio. La proiezione somma cinque variazioni con le pendenze
delle ancore ufficiali e divide per sei, lasciando il contributo MSE a zero.

| Ampiezza | Scala dispersione | Delta locale | Semi 1 / 2 / 3 | IC appaiato 97,5% | Regola |
|---|---|---|---|---|---|
| 1,5 | 1 | +0,028918 | +0,034250 / +0,023373 / +0,029130 | [0,019526; 0,039342] | passa |
| 1,5 | 0,5 | +0,023031 | +0,028788 / +0,016329 / +0,023977 | [0,013354; 0,033183] | passa |

Entrambi superano +0,005, restano positivi in ciascun seme e hanno limite inferiore
sopra zero. Il bootstrap ricalcolato con frequenze invece di indicizzazione differisce
di meno di 4,2e-17. Il primo finalista era già primo nello sviluppo ed è il candidato
scelto per la generazione completa; non viene proposta una nuova combinazione.

## Che cosa migliora, e che cosa peggiora

Per ampiezza 1,5 / dispersione 1, i contributi alla proiezione sono:
PDS −0,000014, NMAE −0,003274, fedeltà +0,028302, reach +0,007670,
Jaccard −0,003766. Il guadagno riguarda quindi soprattutto la fedeltà direzionale;
non è un miglioramento uniforme delle sei metriche. La MSE grezza peggiora in media
di 0,381556. La deviazione standard dei tre delta è 0,005442: la singola coppia di
semi storica non descrive questa variabilità locale.

73 dei 96 bersagli hanno contributo positivo. I primi cinque spiegano il 26,7% del
guadagno netto; togliendoli e ricalcolando i denominatori il delta resta +0,022330.
Questa sensibilità è descrittiva e non sostituisce la regola fissata prima della prova.
La precisione direzionale aggregata passa da circa 0,549 a 0,580; il numero di chiamate
cresce insieme al numero di accordi. Non è precisione rispetto alla significatività DE.

## Portata della decisione

Si registra t28: effetti t25 originali moltiplicati integralmente per 1,5, inclusi
i termini già incorporati negli NPZ, e generatore con dispersione per gene alla
scala 1. La dispersione sarà stimata dai controlli del contesto da prevedere.
La decisione D-047 distingue la scelta di questa combinazione dall'attribuzione
causale ai suoi due fattori.

Il banco usa una sola linea pubblica, bersagli diversi dal pannello ufficiale e
K562 come sorgente; t28 usa la miscela t25. L'intervallo non copre il cambio di
linea, saggio, profondità o ricetta. Non è una previsione di +0,028918 in gara.
La competitività richiede un risultato ufficiale. Generazione, packaging e invio
sono stati separati; l'invio resta soggetto al via del proprietario.
