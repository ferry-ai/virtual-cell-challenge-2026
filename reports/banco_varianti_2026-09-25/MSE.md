# Ampiezza ed errore quadratico: che cosa costa salire, e perché la MSE non si recupera abbassando

25 settembre 2026, mattina, su domanda del proprietario: alzare l'ampiezza (t16 → t18) rende
fragile il ragionamento, se un giorno si vorrà far uscire dallo zero la `mse`, oggi tagliata?
**Proxy nello spazio degli effetti su sorgenti pubbliche tenute fuori, non punteggi VCC.**
Script `mse_tradeoff.py`, uscita `r10/`; stesso caricatore dello stadio 100 e stesse sorgenti
escluse di `sweep_v2.py`.

## Che cosa si misura

`mse_ratio`: errore quadratico della previsione diviso quello di "nessun cambiamento", con i
pesi del `log1p` a 5·10⁴ e i geni del pannello esclusi; sotto 1 la previsione batte il nulla.
`a*`: l'ampiezza che lo minimizza. `rilevabili`: mediana per bersaglio dei geni sopra la soglia
grezza di `sweep_v3.py`. La verità è una sorgente pubblica rumorosa, che spinge ogni rapporto
verso 1: conta l'ordine, non il livello.

## Risultati (r10)

| Sorgente esclusa | grezzi 0,788 (t16) | grezzi 1,576 (t18) | ristretti 1,576 (t19) | a* grezzi, rapporto | a* ristretti, rapporto |
|---|---|---|---|---|---|
| K562 | 1,072 (285) | 1,319 (1.212) | 1,082 (298) | 0,074, 0,9992 | 0,162, 0,9989 |
| CD4 | 1,427 (342) | 2,760 (1.786) | 1,262 (294) | 0,022, 0,9996 | 0,078, 0,9993 |
| HCT116 | 1,215 (468) | 1,893 (1.697) | 1,259 (483) | 0,027, 0,9997 | 0,054, 0,9997 |
| HEK293T | 1,380 (472) | 2,562 (1.709) | 1,454 (486) | 0,020, 0,9997 | 0,042, 0,9997 |

Fra parentesi i geni rilevabili per bersaglio.

## Che cosa se ne ricava

- **Misurato sul proxy:** l'ampiezza che minimizza l'errore quadratico è minuscola (0,02–0,16), e
  anche lì la previsione batte "nessun cambiamento" di meno dello 0,11%. La linea di base
  ufficiale della `mse` sta allo 0,996 (PROGETTO §4, punto 1: stima su due righe, non misura),
  cioè lo 0,4% sotto il nulla. **Con la qualità attuale delle previsioni la `mse` resta a zero a
  qualunque ampiezza:** è affondata dalla precisione del modello, non dalla scelta dell'ampiezza.
- **Misurato sul proxy:** salire da 0,788 a 1,576 con gli effetti grezzi porta l'errore da
  1,07–1,43 a 1,32–2,76 volte il nulla. Gli effetti ristretti a 1,576 muovono tanti geni quanti il
  t16 con un errore simile al t16 (1,08–1,45).
- **Interpretazione:** il conflitto fra `mse` (vuole ampiezze piccole) e membri DE (vogliono
  ampiezze grandi) oggi è estremo, e si ridurrà solo se le previsioni migliorano: l'ampiezza
  ottima per l'errore quadratico cresce con la correlazione fra previsione e verità. Gonfiare
  l'ampiezza lo nasconde, perché il membro resta a zero e non si vede se le ampiezze migliorano.

## Proposta

- Tenere separati **modello** e **calibrazione dell'invio**: i modelli si confrontano sui banchi
  alla loro ampiezza ottima per l'errore quadratico (`a*`, rapporto sul nulla) e sul PDS proxy;
  l'ampiezza d'invio è uno strato di calibrazione per la metrica, dichiarato come tale.
- Salvare la `mse` grezza di ogni invio anche se tagliata (LAVORO §2, punto 6), per vedere se
  le ampiezze migliorano da un invio all'altro.
- Preferire le modifiche che alzano i membri DE senza gonfiare l'errore quadratico: la
  restrizione del t19 è una di queste.
