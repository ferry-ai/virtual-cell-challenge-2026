# gara — le regole del gioco e i contesti A/B/C

Che cosa misura lo scorer, come si convertono i grezzi negli scalati, che cosa mostra la
classifica e che cellule sono i contesti di validazione. Le identità di linea di A/B/C sono
**ipotesi da marcatori**, non misure. Indice generale: [../README.md](../README.md).

| Data | Cartella | Nocciolo | Vale? | Peso oggi |
|---|---|---|---|---|
| 22/09 | [context_fingerprints_2026-09-22/](context_fingerprints_2026-09-22/) | Stadio 99. L'asse ufficiale è un pannello di sonde 10x Flex (18.533 geni, nessun RPL/RPS, HLA, XIST, MALAT1); i controlli di A/B/C si somigliano più fra loro che con K562/RPE1 in 3'; impronte genetiche per sesso, zeri omozigoti e bracci cromosomici | sì; le identità di linea restano ipotesi | ★★★ (serve di nuovo il 22/10 per D/E/F) |
| 17/09 | [anchors_2026-09-17/](anchors_2026-09-17/) | Le ancore ufficiali (base e replica) di cinque membri su sei, risolte da due invii e verificate fuori campione su un terzo (`three_points/`); la `mse` resta indeterminata | sì, per il pannello `vcc2026-val-1` | ★★★ (ogni conversione grezzo → scalato) |
| 17/09 | [contexts_2026-09-17/](contexts_2026-09-17/) | Stadio 85: A è un linfocita T (CD3D nel 100% delle cellule), B cheratine+ / E-caderina− / vimentina alta, C epiteliale coeso; nessun marcatore eritroide, epatocitario o pluripotente | sì; i nomi di linea sono ipotesi | ★★ |
| 16/09 | [leaderboard_2026-09-16/](leaderboard_2026-09-16/) | Fotografia a mano della classifica delle 11:31Z (prime dieci e la nostra riga) e una stima delle ancore per adattamento lineare | storico: la classifica del 28/09 è riassunta in [lezioni_invii](../invii/lezioni_invii_2026-09-28/RISULTATI.md) | ★ |
| 12/09 | [scorer_2026-09-12/](scorer_2026-09-12/) | Il contratto delle sei metriche estratto da `cell-eval2` 0.16.0: definizioni, pesi, tosature | sì | ★★ |
| 11/09 | [scorer/](scorer/) | La prima estrazione dello stesso contratto: il campo `floor_note` è sbagliato (scheda R-002) | superato da `scorer_2026-09-12/` | ★ |
| 11/09 | [context_identity/](context_identity/) | Marcatori e test di contrasto della prima identificazione di A/B/C; le cautele sono dentro il JSON | in parte: la lettura «occhio» di B è un'ipotesi debole (R-001) | ★ |
| ≤12/09 | [external_compat/](external_compat/) | Struttura delle 46 guide NTC dei controlli ufficiali e contratto di compatibilità con i dati esterni | sì | ★ |

## Che cosa sapere prima di usarle

- **Lo zero della scala è un oracolo**: la risposta media vera delle perturbazioni del
  contesto. Uno scalato 0 non vuol dire «nessuna abilità».
- **Le ancore valgono per questo pannello.** Il set finale D/E/F avrà ancore sue: nessun numero
  di qui si trasferisce per costruzione.
- **La `mse` non è risolta** dalle ancore: le stime dalla classifica (≈0,99 la base, ≈0,035 la
  replica) sono interpretazioni in [lezioni_invii](../invii/lezioni_invii_2026-09-28/RISULTATI.md).
