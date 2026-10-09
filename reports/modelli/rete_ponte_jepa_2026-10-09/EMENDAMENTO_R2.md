# Emendamento r2: il residuo centrato sul pannello

9 ottobre 2026, 17:55 CEST. **Scritto dopo aver visto r1 e prima di ogni numero di r2.** È una variante dichiarata a
posteriori. La regola del [protocollo](PROTOCOLLO.md) resta la stessa, applicata al nuovo braccio; r1 resta letto con
la sua regola: **non passa**.

## Che cosa ha detto r1 (misurato, `processed/rete_ponte_jepa_2026-10-09/r1`)

- **Coseno `rete − all`:** media **+0,0169**, con l'IC sopra 0 su 4 linee. È il miglior guadagno su questo banco
  (lo stadio 1 aveva +0,013).
- **PDS `rete − all`:** media −0,0166, e **H1 −0,108**. La guardia del PDS fallisce.
- **Il braccio `rete_pesi`** (solo l'attenzione, senza residuo) non guadagna coseno: il guadagno viene dal residuo.
- **L'arresto anticipato** scatta presto (epoche 4–6, validazione migliore all'epoca 1–2): la rete sovradatta in
  fretta.

## Ipotesi

Il residuo a basso rango ha imparato soprattutto una **risposta comune della linea nuova**, uguale per tutti i
bersagli. È lo stesso scambio della [diagnosi del modo comune](../guadagno_appreso_2026-10-05/DIAGNOSI_MODO_COMUNE.md):
la parte comune alza il coseno e abbassa il PDS.

## Che cosa cambia

- **Braccio nuovo `rete_centrata`:** `P = base + (res − media di res sui bersagli del pannello)`. Il centramento usa
  solo le previsioni, mai la verità, ed è applicabile ad A/B/C (il pannello di 300 bersagli).
- **Seme 1,** per non leggere il braccio sullo stesso rumore di r1. Si riportano anche `rete` e `rete_pesi` al seme 1,
  come controllo della stabilità.
- **Tutto il resto è identico a r1:** dati, architettura, perdite, arresto anticipato e misure.

## Regola

È quella del protocollo, sul braccio `rete_centrata` contro `all`:
- coseno medio ≥ **+0,015**;
- almeno 3 linee con il limite inferiore dell'IC sopra 0;
- PDS medio ≥ 0 e nessuna linea sotto −0,02.

## Previsione (soggettiva)

| Braccio | Coseno | PDS |
|---|---|---|
| `rete_centrata` | fra +0,000 e +0,015 (perde parte del guadagno di r1) | fra −0,01 e +0,03 |

Probabilità che passi: **0,2**.
