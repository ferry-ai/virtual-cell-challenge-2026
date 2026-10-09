# Quale misura vale su quale fold

Scritto da `banco/validita_misure.py` da `reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/banco/r1/completion/results.json`, senza nuovi calcoli. Per ogni fold e ogni misura: il transfer di riferimento T0 si distingue (bootstrap appaiato sui bersagli, risolto) da tre previsioni degeneri costruite da T0 stesso? **sì** = risolto a favore di T0; **no** = non risolto; **contro** = risolto a sfavore di T0. Una misura che non vede il braccio scambiato su un fold non può dire, lì, che un braccio conosce i suoi bersagli. Spazio degli effetti, lignaggi di sviluppo: non sono punteggi VCC.

## Contro T0 a bersagli scambiati (specificità)

| Fold | Verità | Bersagli | Geni confidenti (mediana) | `disc95` | `disc` | `r_spec` | `sign50` | `reach` | `nmae_conf` | `mse_ratio` |
|---|---|---:|---:|---|---|---|---|---|---|---|
| C-CD4T | `cd4_Rest` | 293 | 364 | sì | sì | sì | sì | sì | sì | sì |
| C-H1 | `h1` | 17 | 1284 | sì | sì | sì | sì | **no** | sì | sì |
| C-HCT116 | `orion_hct116` | 293 | 91 | sì | sì | sì | sì | sì | sì | sì |
| C-HEK293 | `orion_hek293t` | 299 | 114 | sì | sì | sì | sì | sì | sì | sì |
| C-K562 | `k562` | 272 | 34 | sì | **no** | sì | sì | sì | sì | sì |
| C-iPSC | `kolf_pan_genome` | 282 | 174 | sì | sì | sì | sì | **no** | sì | **no** |

## Contro la sola media di T0 (parte comune)

| Fold | Verità | Bersagli | Geni confidenti (mediana) | `disc95` | `disc` | `r_spec` | `sign50` | `reach` | `nmae_conf` | `mse_ratio` |
|---|---|---:|---:|---|---|---|---|---|---|---|
| C-CD4T | `cd4_Rest` | 293 | 364 | sì | sì | — | sì | sì | **contro** | **contro** |
| C-H1 | `h1` | 17 | 1284 | sì | sì | — | sì | **no** | **no** | **contro** |
| C-HCT116 | `orion_hct116` | 293 | 91 | sì | sì | — | sì | sì | sì | **contro** |
| C-HEK293 | `orion_hek293t` | 299 | 114 | sì | sì | — | sì | sì | **no** | **contro** |
| C-K562 | `k562` | 272 | 34 | sì | **no** | — | sì | sì | sì | **contro** |
| C-iPSC | `kolf_pan_genome` | 282 | 174 | sì | sì | — | sì | sì | **no** | **contro** |

## Contro nessun effetto

| Fold | Verità | Bersagli | Geni confidenti (mediana) | `disc95` | `disc` | `r_spec` | `sign50` | `reach` | `nmae_conf` | `mse_ratio` |
|---|---|---:|---:|---|---|---|---|---|---|---|
| C-CD4T | `cd4_Rest` | 293 | 364 | sì | sì | — | sì | sì | **contro** | **contro** |
| C-H1 | `h1` | 17 | 1284 | sì | sì | — | sì | sì | **no** | **contro** |
| C-HCT116 | `orion_hct116` | 293 | 91 | sì | sì | — | sì | sì | sì | **contro** |
| C-HEK293 | `orion_hek293t` | 299 | 114 | sì | sì | — | sì | sì | **contro** | **contro** |
| C-K562 | `k562` | 272 | 34 | sì | **no** | — | sì | sì | sì | **contro** |
| C-iPSC | `kolf_pan_genome` | 282 | 174 | sì | sì | — | sì | sì | **no** | **contro** |

## In breve

| Misura | Fold su cui vede il braccio scambiato |
|---|---|
| `disc95` | C-CD4T, C-H1, C-HCT116, C-HEK293, C-K562, C-iPSC |
| `disc` | C-CD4T, C-H1, C-HCT116, C-HEK293, C-iPSC |
| `r_spec` | C-CD4T, C-H1, C-HCT116, C-HEK293, C-K562, C-iPSC |
| `sign50` | C-CD4T, C-H1, C-HCT116, C-HEK293, C-K562, C-iPSC |
| `reach` | C-CD4T, C-HCT116, C-HEK293, C-K562 |
| `nmae_conf` | C-CD4T, C-H1, C-HCT116, C-HEK293, C-K562, C-iPSC |
| `mse_ratio` | C-CD4T, C-H1, C-HCT116, C-HEK293, C-K562 |
