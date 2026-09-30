# CP-0050 — Le ancore aggregate non sono esatte e la riserva HepG2 era gia valutata

- **Data:** 2026-09-29
- **Tipo:** correzione
- **Redatto da:** Codex, sessione 01a0ee03-b357-7012-81a9-e8d7de767478
- **Revisione umana:** no
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Quali punteggi attribuiti ai modelli sono riproducibili e quali sostengono davvero
una previsione dello score ufficiale o una validazione indipendente?

## 2. Cosa è stato fatto

Riletti codice del banco, scorer installato, protocolli, nove CSV della conferma
generatore e quattro status ufficiali. Eseguito `audit_score_credibility.py` in
`reports/analisi/lead_scientist_2026-09-29/`, con output nuovo `score_credibility_r1/`.
L'audit dati ha confrontato le liste dei target con undici CSV di un banco storico
già completo, senza usarne i valori per selezionare nuovi candidati.

## 3. Cosa si è osservato

**Misurato:** le cinque ancore aggregate ricostruiscono i due invii usati per il fit,
ma non il terzo: media ricostruita t03 0,0204226230 contro ufficiale 0,0196924079.
Per t25 danno 0,1410636230 contro 0,1402380609. Stesso pannello e stessa versione
delle ancore nei JSON. Fonte:
`reports/analisi/lead_scientist_2026-09-29/score_credibility_r1/arithmetic.json`.

**Verificato:** i nove CSV del generatore hanno gli stessi 96 target, nessun duplicato
o infinito; medie dei cinque membri e MSE come rapporto delle somme coincidono con
gli aggregati entro 1e-12. Bootstrap ricostruito con frequenze dei target: t28
delta +0,0289177105 e CI97,5% [0,0195256349;0,0393418955]. Il criterio congelato è
superato. Stessa fonte; nessun nuovo scoring o mutamento delle soglie.

**Misurato dall'audit dati:** 48/48 target di sviluppo e 95/96 di conferma erano già
valutati in undici CSV di un banco concluso il 27/09. Solo RPS15 non compare nella
lista storica. Fonte:
`reports/analisi/lead_scientist_2026-09-29/score_bias_dati_r1/historical_overlap.json`.

## 4. Interpretazione e incertezza

La normalizzazione per contesto seguita dalla media non è in generale ricostruibile
con una sola trasformazione affine della media dei grezzi. I pesi storici rimangono
una definizione valida dell'indice locale congelato, ma la loro esattezza come
conversione ufficiale è smentita dalle misure.

La conferma è disgiunta dal dev48 odierno, non intatta rispetto all'intera ricerca.
La presenza dei risultati storici non dimostra quali valori una persona abbia letto;
impedisce però di rivendicare una nuova riserva mai valutata. L'intervallo non corregge
la storia delle scelte, né l'incertezza fra contesti e controlli. I valori ufficiali
pubblicati e l'aritmetica del confronto locale restano validi.

## 5. Spiegazione semplice

Un righello ricavato da due esempi li misura perfettamente per costruzione: occorre
vedere se funziona sugli altri. Qui non è esatto. Inoltre tenere da parte alcuni
esercizi oggi non li rende nuovi se erano già stati usati nella preparazione precedente.

## 6. Conseguenze

Leggere i sei scalati pubblicati dallo status completo per giudicare un invio.
Etichettare i delta locali come indici e verificare l'intero storico prima di
dichiarare una riserva indipendente. Il test ufficiale t28 resta un esperimento
registrato di trasferibilità; questo checkpoint non lo dichiara riuscito.
La scheda operativa e i criteri dei nuovi esperimenti stanno in
[modello-competitivo](../piani/modello-competitivo.md), senza promesse di risultato.

## 7. Cosa corregge

Corregge la portata dell'esattezza delle ancore in CP-0021 e della verifica sul terzo
punto in CP-0022, oltre alle sintesi negli indici e in LAVORO. Il JSON delle ancore
rimane immutato, con revisione R-022 nel registro. Precisa CP-0047: il superamento
del criterio e i numeri sono confermati, «tenuti da parte» si riferisce allo split
odierno, non a target mai valutati. Non modifica punteggi ufficiali o soglie.

## 8. Domanda di comprensione

Perché un delta locale calcolato correttamente non basta a certificare un guadagno
ufficiale né una nuova prova indipendente?
