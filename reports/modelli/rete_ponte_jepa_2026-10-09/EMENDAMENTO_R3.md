# Emendamento r3: insieme di cinque semi

9 ottobre 2026, 17:58 CEST. **Scritto dopo r1 e r2 e prima di ogni numero di r3.** È una variante dichiarata a
posteriori. La regola del [protocollo](PROTOCOLLO.md) non cambia; r1 e r2 restano letti con la loro regola (**nessuno
dei due passa**).

## Che cosa hanno detto r1 e r2 (misurato)

| Corsa | Braccio | Coseno medio `− all` | PDS medio | PDS H1 | PDS K562 |
|---|---|---|---|---|---|
| r1, seme 0 | `rete` | +0,0169 | −0,0166 | −0,108 | −0,020 |
| r2, seme 1 | `rete` (controllo) | ≈ +0,021 | ≈ −0,007 | −0,096 | −0,074 |
| r2, seme 1 | `rete_centrata` (regola) | +0,0104 | +0,0023 | −0,084 | −0,029 |

- **Il guadagno di coseno è stabile fra i semi.**
- **Il PDS cambia molto fra un seme e l'altro su HepG2, RPE1, Jurkat e K562,** mentre su H1 perde in entrambi i semi.

## Che cosa cambia

- **Braccio di regola `rete`** (senza centramento): la media delle previsioni di cinque reti addestrate con i semi
  2, 3, 4, 5 e 6, che non sono stati usati prima.
- **Si riporta anche `rete_centrata`** dello stesso insieme, senza che decida.
- **Tutto il resto è identico.**

## Previsione (soggettiva)

- **Coseno:** fra +0,012 e +0,022.
- **PDS:** media fra −0,02 e +0,02.
- **H1:** sotto −0,05 di PDS, quindi la regola **non passa** (probabilità che passi 0,1). Un insieme riduce la
  varianza, non la perdita sistematica su H1.
