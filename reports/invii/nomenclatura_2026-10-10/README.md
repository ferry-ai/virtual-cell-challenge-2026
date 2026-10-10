# Nomenclatura degli invii: autore + nome storico + entry

10 ottobre 2026. Claude Code per Alfredo, su proposta di Davide: i numeri t36–t39 sono stati usati due volte, sul
`main` di Davide e sul branch `codex/teammate-rlead` di Alfredo. **I nomi storici non si cambiano.** Da qui in poi un
invio si cita come **autore · nome · entry**, ad esempio `Alfredo·t39·oeRXw89O`.

## Tabella di riconciliazione

| Citazione | Che cosa è | Punteggio | Dove sta la ricevuta |
|---|---|---|---|
| `Davide·t36·JLcMRGEx` | transfer con la banca estesa | **0,147249** | `main` locale di Davide: `reports/invii/trial_2026-10-06/status_JLcMRGExhXKk77XVds7x_0138.json` (non ancora su GitHub) |
| `Davide·t38` | transfer CRISPRi + KO | **0,148922**, massimo osservato del team | `main` locale di Davide: `reports/invii/prediction_t38_2026-10-09/comparison.json` (entry da riportare qui) |
| `Davide·t39` | T3 + riempimento ESM2 | da riportare | `main` locale di Davide |
| `Alfredo·t36·LgakrSXj` | cubo `all` + correzione R (CellNet), emissione t28 | 0,141392 | [status](../trial_rlead_2026-10-06/status_LgakrSXj3X2nAtN5P4Yk.json) |
| `Alfredo·t37` | cubo `all` senza R, emissione t28 | non inviato | pacchetto locale |
| `Alfredo·t38·5GhXxaCD` | `Alfredo·t36` con ampiezza 1,0 | 0,131078 | [status](../trial_rlead_2026-10-07/status_5GhXxaCDRuPnHv4UwU8S.json) |
| `Alfredo·t39·oeRXw89O` | rete ponte JEPA + SIGReg | 0,140816 | [status](../trial_rlead_2026-10-09/status_oeRXw89O1hefFsdCwifD.json) |

## Che cosa cambia nelle letture già scritte

Le letture registrate restano com'erano. Quello che segue è il loro aggiornamento, dato ciò che ora sappiamo.

- **Il riferimento del team è `Davide·t38` (0,148922).** Secondo Davide il miglioramento non è conclusivo rispetto
  alla sua soglia registrata. Contro questo riferimento:
  - `Alfredo·t39` è a **−0,0081**;
  - `Alfredo·t36` è a −0,0075.
- **Lo 0,1472 è confermato come `Davide·t36`:** la base estesa senza R. Il confronto con `Alfredo·t36` (−0,0059) però
  **non isola R**, perché le due basi sono diverse (banca estesa contro cubo `all`). R resta senza un test pulito sul
  sito.
- **Le conclusioni su `Alfredo·t38` restano:** a parità di tutto il resto, l'ampiezza 1,5 batte 1,0.
- **Su `Alfredo·t39`:**
  - il segnale del banco è incoraggiante, ma il trasferimento alla gara non è dimostrato, e il t39 perde sul totale
    e sul PDS;
  - la spiegazione della risposta comune è un'**ipotesi**;
  - il possibile +0,01 della variante centrata è una **stima da verificare**, non un guadagno atteso registrato.

## Da completare

Davide riporta le entry di `Davide·t38` e `Davide·t39` e pusha su `main` le ricevute che oggi sono solo locali.
Dopo il merge, i documenti nuovi di entrambi usano la citazione autore·nome·entry.
