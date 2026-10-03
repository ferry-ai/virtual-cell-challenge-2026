# Training r1: esito

2 ottobre 2026, 23:05 CEST. Il kernel `alfredo2003bit/rlead-training-r1` versione 2 è finito alle 23:02 con stato
COMPLETE: codice 0, 8.195 secondi. La lettura è quella registrata in [PROTOCOLLO.md](PROTOCOLLO.md), fatta con
[`read_training.py`](read_training.py); l'uscita è [lettura.json](lettura.json).

## Il cancello tecnico non passa

| Condizione | Esito |
|---|---|
| codice di uscita 0 | sì |
| `resume_check.json` passato | sì |
| valutazione completa per entrambi i bracci | sì |
| `ident`, mediana di `pi_mean` sui gruppi C sopra 0,05 | **no: 8,1·10⁻¹³** |

**Per la regola del protocollo, nessun confronto (Q1–Q4) viene letto.** Lo script non li calcola.

## Che cosa è successo (misurato dai file scaricati)

- **La miscela si chiude subito, in entrambi i bracci.**
  - `ident`: `pi_mean` 0,50–0,65 fino al passo 300, 0,00045 al passo 400.
  - `gen`: 0,50 al passo 400, 4·10⁻⁶ al passo 500.
  - Da lì `pert_gain` vale 0 o −10⁻⁸, e non risale più in 41.292 passi (10 epoche).
- **In valutazione la rete non prevede alcun effetto:**
  - `ident`, `pi_mean` mediano: 8·10⁻¹³ su C, T e J;
  - `gen`: circa 1,2·10⁻⁹;
  - `cos_model` mediano di `ident`: 0,0 in ogni classe.
- **I default corretti del passo A** (`--mixture logits`, `--loss-norm global`, `pi_floor` 0) non hanno impedito il
  collasso già visto in r3. Una volta che `pi` è vicino a 0, il gradiente verso la componente perturbata è
  trascurabile e la rete resta sul solo controllo.

**File:**
- scaricati solo `.json`, `.jsonl` e `.log` in `vcc2026-data/kaggle/rlead-training-r1_v2_2026-10-02/` (1,7 MB);
- sha256 di `train/train_log.jsonl`: `df67d164…`; di `train/ident/eval.json`: `72c340e8…`; di `train/gen/eval.json`:
  `c0cfd3f5…`;
- checkpoint e modelli restano su Kaggle.

## Conseguenze

- **Discriminazione.** La misura registrata in [DISCRIMINAZIONE.md](DISCRIMINAZIONE.md) non ha senso su questo
  checkpoint: un braccio che non sposta niente ha profili nulli. Il kernel `--eval-from` **non va lanciato**.
- **Prossimo tentativo.** Ogni nuovo training della rete richiede almeno:
  - un `pi_floor` positivo, oppure `pi` fissato per le prime epoche;
  - un controllo che fermi il job se `pi_mean` scende sotto 0,05 nei primi 1.000 passi, invece di consumare 2 ore e
    mezza di GPU.

  È una proposta, da registrare prima.
- **Priorità.** Questo esito si somma alla revisione del 2 ottobre
  ([letteratura e strade](../../analisi/letteratura_strade_2026-10-02/README.md)): la rete scende di priorità rispetto
  al generatore e al trasferimento.
