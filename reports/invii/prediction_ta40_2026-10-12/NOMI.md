# Nomi in questa cartella (D-058)

12 ottobre 2026, 21:55 CEST. La previsione è stata registrata come `t40` nel commit `351cfce`, prima di generare. Solo
dopo ho letto la regola **D-058** di `main` (commit `c361c0ba` di Davide, 10/10): `ta XX` per i modelli di Alfredo,
`td XX` per quelli di Davide, e `taXX` negli identificatori tecnici nuovi.

**Che cosa ho cambiato:**
- la cartella, creata oggi e non ancora pushata, è stata rinominata da `prediction_t40_2026-10-12` a
  `prediction_ta40_2026-10-12`;
- il lettore si chiama ora `leggi_ta40.py`, con le chiavi rinominate;
- **la regola, la banda e i numeri non sono cambiati.** `prediction.json` è identico byte per byte a quello del commit
  `351cfce`.

**Come si leggono i nomi di `prediction.json`:**

| In `prediction.json` | D-058 | Entry |
|---|---|---|
| t40 | `ta 40` | da assegnare al caricamento |
| t39, `Alfredo·t39` | `ta 39` | `oeRXw89O1hefFsdCwifD` |
| t36 | `ta 36` | `LgakrSXj3X2nAtN5P4Yk` |
| t28 | `td 28` (invio di `main`) | `ZvrYZ4UazadAyuq4AsDB` |
| `Davide·t38` | `td 38` | sul `main` di Davide |

Gli artefatti nella cartella dei dati mantengono i nomi tecnici con cui sono stati generati, `t40gen` e `t40pack`,
perché erano già in scrittura.
