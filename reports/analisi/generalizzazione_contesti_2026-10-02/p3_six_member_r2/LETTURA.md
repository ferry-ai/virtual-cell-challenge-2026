# I bracci P3 sui sei membri ufficiali, HepG2 (sviluppo)

3 ottobre 2026, corsa `six_member_r2` dalle 05:34:53 alle 06:03:36 CEST (orari letti con `date` e dal log), comando
`six_member_hepg2.py --cube cube_r1 --run p3_c_r2 --protocol PROTOCOLLO.json --max-controls 2048`. **Deviazione
dichiarata:** controlli ridotti a 2.048 (campione stabile) perché la prima corsa (`six_member_r1`, 2/10) con tutti i 4.976
si era fermata a 4,2 GB di memoria privata; il resto come il protocollo (150 bersagli con almeno 50 cellule, 64 cellule
per bersaglio, verità = metà A, replica = metà B, baseline = profilo generico dello scorer). Parità: adattamenti
riprodotti a 4,4e-16, esportazione e generatore identici bit per bit (`fitting_parity.json`, `export_parity.json`).
Scala locale (u − b)/(r − b), **non un punteggio VCC**; uscite complete nella radice dati (`six_member_r2/`).

| Braccio | PDS | NMAE | FID | REACH | JAC | Media locale | Chiamate/bersaglio |
|---|---:|---:|---:|---:|---:|---:|---:|
| transfer | 0,950 | 0,124 | 0,462 | 0,037 | −0,180 | **0,232** | 100,8 |
| `m2` | 0,832 | 0,084 | 0,439 | −0,063 | −0,190 | 0,184 | 81,8 |
| `m2_0` | 0,923 | 0,019 | 0,416 | −0,093 | −0,207 | 0,176 | 64,4 |
| `m2_swap` | 0,954 | 0,009 | 0,391 | −0,108 | −0,220 | 0,171 | 60,8 |
| `tm0` | 0,437 | −0,145 | 0,209 | −0,274 | −0,311 | −0,014 | 8,8 |
| `m1` | 0,453 | −0,103 | 0,202 | −0,243 | −0,321 | −0,002 | 8,1 |
| generico | −0,032 | −0,159 | 0,196 | −0,234 | −0,327 | −0,093 | 7,4 |
| nullo | −0,054 | −0,209 | 0,220 | −0,269 | −0,326 | −0,106 | 9,2 |

Il membro MSE vale 0 in scala locale per ogni braccio (non discrimina qui). Avviso dello scorer: 13 bersagli su 150 non
risolti a un gene misurato e quindi valutati senza esclusione del proprio gene, uguale per tutti i bracci.

**Misurato:** sui sei membri il transfer resta il migliore su HepG2. Le calibrazioni senza contesto (`tm0`, `m1`), che
sugli indici degli effetti alzavano il coseno, crollano in PDS e nelle chiamate (8–9 per bersaglio contro 101): la
risposta comune che reintroducono appiattisce le differenze fra bersagli. Le correzioni bilineari restano sotto il
transfer. **Interpretazione:** conferma con lo scorer ufficiale la regola di P3 (nessuna adozione) e la lettura del
limite della primaria (il coseno premia la risposta comune).
