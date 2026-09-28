# Strato a programmi: la proiezione sui programmi condivisi perde il riconoscimento del bersaglio

26 settembre 2026, notte. Prova dell'ipotesi H1 ("i programmi si trasferiscono meglio dei
singoli geni", [IPOTESI](../ipotesi_trasferimento_2026-09-24/IPOTESI.md)) nella forma più
semplice che si può misurare oggi, sul trasferimento dello stesso bersaglio. **Proxy nello spazio
degli effetti contro sorgenti pubbliche tenute fuori, non punteggi VCC.** Script
`programs_bench.py`, uscita `r1/`.

## Che cosa si è fatto

Banco "una famiglia di sorgenti fuori" (K562, CD4, HCT116, HEK293T), con il caricatore e la media
dello stadio 100, nelle due forme di produzione: t16 (effetti grezzi × 0,788) e t19 (ristretti ×
1,576). I programmi si imparano **solo dalle sorgenti che predicono**, mai da quella tenuta fuori:

- `stack_r`: vettori singolari destri delle matrici impilate delle sorgenti predittrici (effetti
  del pannello meno la media sui bersagli, come fa gamma 1), nella geometria `log1p` dello scorer
  (pesi x/(1+x), x = 0,05 · CPM medio di A/B/C), sui geni ≥ 1 CPM; la previsione è proiettata sui
  primi r e riportata indietro;
- `self_r`: la stessa proiezione con la base della matrice prevista stessa (SVD troncata fra
  bersagli);
- `half_stack_r`: proiezione più metà del residuo;
- `random_r`: controllo, base ortonormale casuale dello stesso rango.

Ranghi 10, 20, 40, 80 e 160; bootstrap appaiato sui bersagli (2.000 ricampionamenti).

## Risultati (r1, `summary.csv`)

PDS proxy meno la previsione di partenza, intervallo dei quattro bench:

| Braccio | forma t16 | forma t19 |
|---|---|---|
| `stack_r10` | −0,13…−0,21 | −0,14…−0,22 |
| `stack_r160` | −0,05…−0,11 | −0,06…−0,11 |
| `half_stack_r160` | −0,018…−0,035 | −0,018…−0,029 |
| `self_r160` | −0,026…−0,045 | −0,031…−0,046 |
| `random_r10…r160` | −0,09…−0,21 | −0,11…−0,29 |

- **Misurato:** tutti i bracci di proiezione perdono PDS proxy, a ogni rango e su ogni sorgente
  tenuta fuori; ogni intervallo al 95% sta sotto zero. Anche la precisione dei segni sui primi 200
  geni scende (per esempio K562, forma t16: 0,529 → 0,507 a rango 10).
- **Misurato:** il rapporto d'errore quadratico si avvicina a 1 (per esempio K562, forma t16:
  1,072 → 1,011 a rango 10) perché la proiezione toglie energia (tiene il 32–93%), come abbassare
  l'ampiezza. Non è un miglioramento delle previsioni: resta sopra 1.
- **Misurato:** la base casuale perde più delle basi imparate ai ranghi bassi; le basi imparate
  catturano quindi struttura vera, ma non quella che distingue un bersaglio dall'altro.

## Che cosa se ne ricava

- **Interpretazione:** nel trasferimento dello stesso bersaglio l'informazione che riconosce il
  bersaglio sta nel dettaglio fuori dai programmi condivisi. I programmi spiegano molta energia
  comune a molti bersagli, e proprio per questo non discriminano. Un esito simile, con la
  proiezione sulla variazione naturale dei controlli, è riportato nel repository pubblico di
  un'altra squadra (esperimento E15, copiato nella cartella di lavoro della sessione `76a3a45e`):
  letto, non rifatto.
- **Ipotesi H1 contraddetta in questa forma lineare** (proiezione su un sottospazio comune). Non è
  contraddetta come caratteristica per i bersagli **nuovi**, dove l'effetto misurato del bersaglio
  non c'è e si possono solo predire le sue coordinate sui programmi da descrittori del bersaglio:
  quella prova resta da fare, nel regime T/J di [GENERALIZZAZIONE](../../docs/GENERALIZZAZIONE.md).
- **Decisione proposta:** nessuno strato a programmi nel modello d'invio del 26 settembre.

## Che cosa non si è fatto

Nessuna base dai 10.000 knockdown del K562 genome-wide (la memoria libera, circa 0,5 GB, non
reggeva la matrice); nessuna proiezione pesata per bersaglio o per programma; nessun modello del
generatore su questi bracci, inutile dato il segno delle differenze.
