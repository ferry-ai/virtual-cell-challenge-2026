# Rete sulle sorgenti r2: esito del confronto locale

3 ottobre 2026, verso le 21, ora del PC. Il piano è in [PIANO_LOCALE.md](PIANO_LOCALE.md), commit 77fc26b, scritto
prima del lancio.
- **Corse:** cinque varianti in parallelo sul PC di Alfredo, seme 0, uscite in
  `vcc2026-data/processed/rete_r2_locale_2026-10-03/<variante>/`.
- **Divisione:** 22 chiavi di addestramento; un episodio di validazione su RPE1, con 256 bersagli e 2.048 geni.

Tutte e cinque partono dallo stesso punto: coseno 0,1162, dimensione 0,524, la media a pesi uguali.

## Misurato (validazione su RPE1, metriche fisse)

| Variante | Passi fatti | Checkpoint migliore | Δ coseno all'ultimo passo | Δ coseno al migliore | Dimensione all'ultimo passo | Dimensione al migliore |
|---|---|---|---|---|---|---|
| `r1` | 2.600 | 100 | −0,0095 | +0,0002 | 0,024 | 0,087 |
| `fix` | 800 | 300 | −0,0009 | +0,0004 | 0,520 | 0,525 |
| `cos` | 500 | 0 | −0,0005 | 0 | 0,696 | 0,524 |
| `fixcos_top` | 500 | 0 | −0,0006 | 0 | 0,536 | 0,524 |
| `fix_top` | 1.300 | 600 | −0,0018 | −0,0001 | 0,529 | 0,533 |

- **Come leggere la tabella:**
  - Δ coseno è il coseno della rete meno quello della media a pesi uguali, su tutti i geni;
  - la dimensione è |ŷ| / |verità| sui geni osservati, e per la media a pesi uguali vale sempre 0,524.
- **Arresto anticipato:** è scattato in quattro varianti su cinque. Erano cinque valutazioni di fila peggiori della
  media.
- **La r1 rifatta riproduce il difetto del t30 su una linea indipendente:** la dimensione crolla da 0,524 a 0,024.

## Lettura secondo il piano

- **Primo punto del criterio** (Δ coseno ≥ +0,01): **nessuna variante lo supera.** Il massimo è +0,0004.
- **Conseguenza scritta nel piano:** i pesi appresi non aiutano oltre la media. Il candidato per il banco è `net0`, cioè
  la media a pesi uguali con l'ampiezza della ricetta, e **la rete resta ferma.**
- **Interpretazione:** sulle linee e sulle chiavi di questo corpus, i profili dei controlli non dicono di quale
  sorgente fidarsi più di quanto faccia la media. Ogni guadagno della perdita della r1 veniva dall'ampiezza.
  - L'ampiezza fissa elimina il difetto, ma non aggiunge direzione.
  - La perdita a solo coseno lascia l'ampiezza libera, che sale fino a 0,70.
- **Altro misurato, che orienta:** già la media a pesi uguali, con il norm-match, prevede su RPE1 effetti grandi circa
  metà del vero (0,524). Va nello stesso verso:
  - dei bracci ×2 della strada C r1, migliori su H1;
  - della storia dei punteggi: t15 ×2, t16 ×4, t22 ×1,576.

  Interpretazione: la leva è l'ampiezza, non la scelta delle sorgenti.

## Limiti

- Una sola linea di validazione e un solo seme.
- Il coseno non è lo scorer.
- Le linee di validazione della r1 (KOLF, Jurkat) e quelle di test (H1, HepG2) non erano in locale.

Un controllo sulle chiavi complete del kernel lungo resta possibile. Con differenze fra −0,01 e +0,0004, però, non mi
aspetto che cambi la lettura.
