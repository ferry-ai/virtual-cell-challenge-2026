# La rete centrata insieme a T3 di Davide: banco sui fold a lignaggio escluso

15 ottobre 2026, 18:20 CEST. Claude Code per Alfredo, che ha riferito in chat che i Kaggle di Davide sono pubblici e ha
chiesto di prendere i dati che servono e procedere.

## Dati (scaricati il 15/10, dataset pubblici di Davide)

**`davideferrante11/vcc-rsb-inputs-70dc-r1`**, in `vcc2026-data/kaggle_in/dt_vcc-rsb-inputs-70dc-r1/`:
- `T3_production.npz`: sha256 `b8c61f6d…f6a6`, **lo stesso file di effetti di `td 38`** (ricevute sul `main`, CP-0071);
- `T3f__C-K562`, `C-iPSC`, `C-HCT116`, `C-HEK293`: T3 riadattato senza quel lignaggio;
- tutti 300 bersagli × 18.533 geni, in log naturale, con l'ampiezza 1,576 e il cis già applicati.

**`davideferrante11/vcc-td41-effects-70dc-r1`**: gli effetti di produzione di `td 41` ("RS"), solo come confronto.
**Il punteggio di `td 41` non è noto da qui.**

## Che cosa si sa prima del banco (misurato sui file di produzione, 15/10)

**Fra le direzioni** (coseno mediano per bersaglio, senza il gene bersaglio):

| Coppia | Coseno |
|---|---|
| `ta 40`, T3 | 0,33–0,34 |
| `ta 40`, `td 41` | 0,22 |
| `td 41`, T3 | 0,51 |

**Fra le norme:**
- `ta 40` ha 0,68 volte la norma di T3;
- `td 41` ne ha 0,12.

**La parte comune di T3 sul pannello** è lo 0,04% dell'energia.

**Ipotesi:**
- `ta 40` (0,1467) e `td 38` (0,1489) hanno punteggi vicini con direzioni poco correlate, quindi colgono parti diverse
  della verità;
- per due predittori di qualità simile e correlazione 0,34, la media guadagna circa il 20% di coseno, se gli errori
  sono indipendenti.

## Protocollo e regola (fissati prima dei numeri)

[banco_t3.py](banco_t3.py). Per ogni fold h (K562, iPSC, HCT116, HEK293T del cubo r2), sui bersagli del pannello che
h misura (almeno 30 cellule):

| Braccio | Che cos'è |
|---|---|
| `all` | il transfer del cubo senza h |
| `rete_c` | la rete ponte riaddestrata senza h, semi 2–6, residuo centrato (il braccio di `ta 40`) |
| `t3` | T3f del fold |
| `t3_res` | T3 più il residuo centrato della rete |
| `ens_0.5`, `ens_0.7` | T3 e `rete_c` a norma unitaria, mescolati 0,5 : 0,5 e 0,7 : 0,3 |

**Misure:**
- coseno e indice PDS del banco (`guadagno.measures`);
- proxy DE di [budget_chiamate](../../generatore_e_banchi/budget_chiamate_2026-10-13/README.md), alla norma di T3.

**Regola:** un braccio diventa il candidato per il sito se, in media sui quattro fold:
- il coseno è ≥ quello di `t3` + 0,010;
- l'indice PDS è ≥ quello di `t3`.

Fra `ens_0.5`, `ens_0.7` e `t3_res` si manda quello che passa con l'indice PDS medio più alto. **Se nessuno passa, da
questo banco non si manda nulla.**

**Cautela nota:** il banco del cubo ha sopravvalutato il PDS del sito per i cambi di direzione (5 casi su 5), mentre
ha previsto bene i cambi di magnitudine (`ta 41`).
