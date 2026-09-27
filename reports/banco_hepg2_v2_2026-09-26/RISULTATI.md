# Banco HepG2 con lo scorer vero (F2 di R-V2): r1

## Che cosa è girato

Job Colab `046_bench_hepg2_v2`, finito alle 16:16 UTC del 27/09. Uscite copiate da Drive in `r1/`, log compreso
(`job_046.log`).

- **Stadio 75.** 299 bersagli HepG2 (Nadig 2024) con almeno 50 cellule, misurati anche nel K562 genome-wide. Le
  cellule di ogni bersaglio sono divise in due metà: la verità è la metà A, la replica la metà B (mediana 36
  cellule per metà), con 4.976 controlli.
- **Ancore locali.** La replica vale 1, la risposta media del contesto (baseline) vale 0.
- **Membri.** I sei membri dello scorer; l'MSE è tosato a 0 in tutti i bracci.
- **Bracci.** Costruiti da `build_effects.py` con il codice di produzione e il **solo K562** come sorgente:
  - `t16like`: raw × 0,788;
  - `t19like`: shrunk × 1,576;
  - `cisonly`: la testa cis;
  - `a`: moltiplica l'ampiezza della forma.
- **Nessuna regola di decisione registrata.** La scheda di R-V2 chiedeva un rapporto descrittivo, quindi qui si
  misura e non si decide.

## Membri scalati (misurato, `r1/scaled_local.csv`)

| Braccio | PDS | NMAE | FID | REACH | JAC | Media |
|---|---|---|---|---|---|---|
| `t16like` × 0 | 0,011 | −0,258 | 0,211 | −0,190 | −0,465 | −0,115 |
| `t16like` × 0,5 | 0,725 | −0,157 | 0,274 | −0,051 | −0,434 | 0,059 |
| `t16like` × 1 | 0,878 | −0,094 | 0,422 | 0,047 | −0,363 | 0,148 |
| `t16like` × 2 | 0,925 | −0,149 | 0,653 | 0,106 | −0,302 | 0,206 |
| `t19like` × 0,5 | 0,792 | −0,108 | 0,350 | −0,012 | −0,385 | 0,106 |
| `t19like` × 1 | 0,874 | −0,129 | 0,540 | 0,079 | −0,317 | 0,174 |
| `t19like` × 2 | 0,933 | −0,315 | 0,683 | 0,130 | −0,296 | 0,189 |
| `t19like` × 1 + cis × 1 (forma t20) | 0,867 | −0,141 | 0,519 | 0,075 | −0,321 | 0,166 |
| `t19like` × 1 + cis × 2 | 0,887 | −0,114 | 0,534 | 0,084 | −0,321 | 0,178 |
| `t16like` × 1 + cis × 1 | 0,879 | −0,090 | 0,433 | 0,014 | −0,357 | 0,146 |

## Contrasti appaiati (misurato, `confronti.py`, `r1/confronti.csv`)

Differenze per bersaglio sulla scala delle ancore, bootstrap sui bersagli (2.000 estrazioni); la media dei membri
conta l'MSE come 0. La media dei valori per bersaglio riproduce gli aggregati del job (scarto massimo 1e-16).

| Confronto | Media dei membri | Intervallo al 95 % |
|---|---|---|
| `t16like` × 2 − × 1 | +0,057 | +0,037…+0,076 |
| `t19like` × 2 − × 1 | +0,015 | −0,012…+0,039 |
| `t19like` × 1 − `t16like` × 1 | +0,026 | +0,009…+0,041 |
| `t19like` × 1 + cis × 1 − `t19like` × 1 | −0,008 | −0,026…+0,011 |
| `t19like` × 1 + cis × 2 − `t19like` × 1 | +0,004 | −0,011…+0,021 |
| `t16like` × 1 + cis × 1 − `t16like` × 1 | −0,002 | −0,015…+0,011 |
| `t19like` × 1 − × 0,5 | +0,068 | +0,048…+0,086 |
| `t16like` × 1 − × 0,5 | +0,089 | +0,073…+0,104 |

## Che cosa se ne ricava

**Misurato:**
- la forma del t19 (shrunk × 1,576) batte quella del t16 (raw × 0,788): +0,026, intervallo sopra zero. Stesso verso
  del punteggio ufficiale dal t16 al t20, dove però c'era anche la testa cis;
- raddoppiare l'ampiezza della forma raw aiuta chiaramente (+0,057). Raddoppiare quella del t19 dà +0,015 con
  l'intervallo che comprende lo zero: guadagnano PDS, FID e REACH, peggiora l'NMAE (da −0,129 a −0,315);
- la testa cis non si vede su HepG2: fra −0,008 e +0,004, intervalli attorno allo zero;
- JAC è negativo in tutti i bracci. I grezzi vanno da 0,005 a 0,042 contro 0,105 della risposta media: gli insiemi
  DE previsti dal K562 si sovrappongono alla verità meno di quelli della risposta media del contesto.

**Interpretazione, non verificata:**
- su questo contesto tenuto fuori la forma di produzione è vicina all'ampiezza oltre la quale raddoppiare non paga
  più con chiarezza;
- il deficit di JAC indica che la risposta comune del contesto porta geni DE che il trasferimento dal K562 non ha.

**Cautele:**
- ancore locali su una verità a metà profondità, non punteggi VCC;
- un solo contesto, bersagli essenziali (effetti forti), il solo K562 come sorgente;
- il log segnala che `allow_fractional_counts=True` era necessario al controllo del tipo d'ingresso del lato
  previsto: vale per questo banco locale, e qui non se ne deduce altro.
