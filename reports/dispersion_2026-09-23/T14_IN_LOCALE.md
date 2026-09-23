# Il t14 e il t09 sul portatile invece che su Colab — 23 settembre 2026

Scritto verso le 18:00 UTC del 23 settembre, **prima di eseguire qualunque pilota del t14**.
Autore: agente (Claude).

## Perché

Il proprietario lo ha scelto in chat, il 23 settembre, fra due opzioni: far girare qui t09 e
t14, oppure riavviare lui il notebook Colab. Il dispatcher di Colab taceva dal 19 settembre
alle 14:18 UTC, e i job 044 (t09) e 045 (t14) aspettavano in coda.

Che la macchina basti è una misura, non un'ipotesi. Su Colab la generazione con
`ControlModel` usava da 1 a 3 GiB di RAM, anche con due job insieme: job 011, 012, 014–016,
040 e 042, righe `alive` di `G:\Il mio Drive\vcc2026\runs\jobs\dispatcher.log`. Ogni
generazione richiedeva circa un'ora. Il portatile ha 7,8 GiB di RAM e 8 thread.

## Che cosa non cambia

- **La regola**: `PRIMA_T14.md`, com'è stata scritta prima dei piloti.
- **Il codice**: stadi 76, 83 e 48, con i parametri del job 045 (stato `kde`, `knn` 30,
  `n_draw` 4000, seme 2026, `--keep-effects-target`, termini cis e di trasferimento a zero).
- **Gli input**: gli stessi file del job, verificati per sha256 contro le copie su Drive:
  - effetti del t08 (`processed/effects_t08_2026-09-22/`);
  - coordinate GENCODE v50;
  - `K562_gwps_raw_bulk_01.h5ad`;
  - controlli ufficiali.

  `k562_neighbour_pairs.csv` mancava in locale ed è stato copiato da Drive, con sha256
  identico.

## Che cosa cambia

- **La sede:** il portatile invece del runtime Colab.
- **Le cartelle di lavoro:** stanno sotto `C:/Users/ferra/vcc2026-data/artifacts/t14_pilots/`.
  I conteggi e la scelta si scrivono in `reports/dispersion_2026-09-23/t14_pilots/`, invece
  che su Drive.
- **La coda Colab:** i job 044 e 045 sono in `runs/queue/ritirati/`, perché non girino due
  volte. Per rimetterli in coda basta spostarli di nuovo in `runs/queue/`.
- **Il carico:** l'upload del t11 (`vcc submit --resume`) gira nello stesso momento. È un
  lavoro di rete; i piloti sono piccoli, 20 bersagli per contesto.

## Che cosa segue

- Il t09 è il caso `--a-effects 1`. Se la regola sceglie 1, t09 e t14 coincidono e si genera
  una volta sola.
- La generazione completa parte dopo l'upload del t11, un lavoro pesante alla volta.
- Nessun invio discende da questa nota: ogni invio passa dall'autorizzazione del
  proprietario e da una previsione registrata prima.
