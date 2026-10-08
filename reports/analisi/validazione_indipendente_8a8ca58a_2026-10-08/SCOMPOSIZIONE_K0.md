# Scomposizione di K0: che cosa ha fatto, pezzo per pezzo, l'ampliamento da quattro linee a t36

8 ottobre 2026, VALIDAZIONE (Claude Code `8a8ca58a`). **Piano scritto prima dei numeri di questa corsa**
(orologio letto con `date`: 19:02 Europe/Rome). È un'analisi **descrittiva e retrospettiva** del livello A: non
valuta un candidato, non ha una regola di adozione e non cambia il contratto v2. Serve al §3 del mandato: separare
le cause.

## Che cosa si sa già (misurato, corsa r1)

K0 = T0 − P4 mette insieme tre cose diverse: il lignaggio iPSC che entra una volta (`kolf_pan_genome`, 282
bersagli), la linea H1 (17 bersagli) e KOLF2.1J che vota di nuovo con altre tre tabelle (`kolf_strong`,
`kolf_chromatin`, `kolf_metabolic`: 64 bersagli con più voti dello stesso lignaggio). Le quattro tabelle senza
bersagli del pannello non contano. Nella corsa r1 la correlazione specifica scende, risolta, su CD4T, HCT116,
HEK293 e K562 e sale su iPSC e H1.

## Bracci e contrasti

Stesso stadio 100, stesse tabelle, stessi fold e stesse misure della corsa r1; cambiano solo le fonti.

| Braccio | Fonti |
|---|---|
| P4 | `k562`, `cd4_mix`, `orion_hct116`, `orion_hek293t` |
| P4k | P4 + `kolf_pan_genome` |
| P4kh | P4k + `h1` |
| T0 | P4kh + `kolf_strong`, `kolf_chromatin`, `kolf_metabolic` (+ le quattro tabelle senza bersagli) |

| Contrasto | Che cosa isola |
|---|---|
| Q1 = P4k − P4 | il lignaggio iPSC che entra con un voto |
| Q2 = P4kh − P4k | H1, sui suoi 17 bersagli |
| Q3 = T0 − P4kh | KOLF2.1J che vota di nuovo: la pseudo-replica |

Q1 + Q2 + Q3 = K0 per costruzione, bersaglio per bersaglio. Nei fold che tengono fuori un lignaggio alcuni
contrasti sono vuoti (in C-iPSC Q1 e Q3, in C-H1 Q2): lo si riporta, non si riempie.

## Come si legge

Per fold e in macro: `disc95` e `r_spec` con l'intervallo appaiato sui bersagli, più le secondarie. Nessuna
soglia: si dice quale pezzo porta il calo di specificità visto in K0 e quale il guadagno d'ampiezza. Linee di
sviluppo, proxy nello spazio degli effetti: non è un punteggio e non decide un invio.

**Precedenti:** S-010 (più fonti lette come un pacchetto solo); ERRORI, «attribuire a un fattore l'effetto di un
intervento che ne cambia diversi» (D-047). **Segnale precoce e arresto:** se la parità di T0 o la somma
Q1 + Q2 + Q3 = K0 non tornano, la corsa non si legge.
