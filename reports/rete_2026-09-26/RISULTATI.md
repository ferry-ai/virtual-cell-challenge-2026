# Lisciamento con i partner di rete, per i bersagli misurati: effetto piccolo

26 settembre 2026, notte. **Proxy contro sorgenti pubbliche tenute fuori, non punteggi VCC.**
Script `network_smoothing.py`, uscita `r1/`; `network_smoothing_self.py`, uscita `r2/`, rifà r1 con la
media dei partner dello stadio 100, che toglie il gene di ciascun partner (r1 conteneva il knockdown
di ogni partner su sé stesso).

## Domanda e metodo

Le subunità di uno stesso complesso danno risposte simili al knockdown. Per un bersaglio che le
sorgenti hanno misurato, la risposta media dei suoi partner fisici STRING (punteggio ≥ 700),
presa dalla [cache universo del K562](../universo_2026-09-26/RISULTATI.md) senza il bersaglio
stesso e centrata sulla media dei bersagli K562, aggiunge qualcosa al t20 (t19 + modulo cis)?
Braccio `t20like + λ × partner`, λ 0,05–0,4; controllo con la media dei partner di un altro
bersaglio. Sorgenti tenute fuori CD4, HCT116 e HEK293T; K562 esclusa, perché i partner K562
porterebbero dentro il suo stesso contesto. 180 bersagli del pannello hanno almeno un partner
misurato.

## Risultati (r1)

| Sorgente fuori | λ 0,1 | λ 0,2 | controllo λ 0,2 |
|---|---|---|---|
| CD4 | +0,0022 (+0,0002…+0,0044) | +0,0032 (−0,0004…+0,0070) | +0,0014 |
| HCT116 | +0,0005 (−0,0009…+0,0021) | +0,0010 (−0,0016…+0,0038) | +0,0000 |
| HEK293T | +0,0009 (−0,0008…+0,0028) | +0,0023 (−0,0012…+0,0059) | −0,0024 |

- **Misurato:** il guadagno è piccolo, e solo CD4 a λ 0,1 ha l'intervallo sopra zero; il braccio
  vero supera sempre il proprio controllo, di 0,001–0,005.
- **Misurato (r2, media corretta):** stesso quadro; CD4 a λ 0,1 +0,0023 (+0,0004…+0,0045),
  HCT116 +0,0008, HEK293T +0,0011, intervalli attraverso lo zero.
- **Interpretazione:** per un bersaglio misurato il suo effetto trasferito domina; la rete aiuta
  soprattutto dove l'effetto manca ([bersagli nuovi](../bersagli_nuovi_2026-09-26/RISULTATI.md)).
- **Decisione proposta:** nessun invio su questo braccio da solo; tenerlo come candidato da
  combinare, da riprovare sul banco con lo scorer vero.
