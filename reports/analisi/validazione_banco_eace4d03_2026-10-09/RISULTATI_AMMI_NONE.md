# AMMI `none` contro la propria ancora: risultati

9 ottobre 2026, VALIDAZIONE (Claude Code `eace4d03`). [Piano](LETTURA_AMMI_NONE.md) committato alle 21:54 prima di
aprire un export; checkpoint [CP-0076](../../../docs/checkpoints/0076-ammi-none-contro-ancora-annidata.md). Spazio
degli effetti, due lignaggi di sviluppo, **un seme di training**: non sono punteggi VCC e non decidono nulla sui
fit `cells`.

## In breve

Il ramo senza contesto **non si distingue dalla propria ancora** su nessuno dei due fold. Non la peggiora (il
sintomo delle reti precedenti qui non c'è) e non la migliora. Le guardie tecniche che i fit hanno superato dicono
che il training è corretto, non che serve.

## Tre bracci, da non confondere

| Braccio | Che cos'è | `disc95` su C-K562 | `disc95` su C-iPSC |
|---|---|---:|---:|
| `T0` | il transfer del fold del banco | 0,7721 | 0,5637 |
| `A0` | l'ancora annidata del fit AMMI: lo stesso transfer con un lignaggio votante in meno (CD4T per C-K562, K562 per C-iPSC) | 0,7705 | 0,5674 |
| `AN` | l'export AMMI `none`: `A0` più il residuo appreso | 0,7716 | 0,5680 |

## I contrasti

| Contrasto | Misura | C-K562 | C-iPSC |
|---|---|---|---|
| `AN` − `A0`: **il contributo del modello** | `disc95` | +0,0011 [−0,0015; +0,0038] | +0,0005 [−0,0012; +0,0023] |
| | `r_spec`, `sign50`, `reach` | non risolti | non risolti |
| | `nmae_conf` (meno è meglio) | −0,0002, non risolto | **−0,0003** [−0,0004; −0,0001] |
| | `mse_ratio` (meno è meglio) | **+0,0006** [+0,0002; +0,0010] | non risolto |
| `A0` − `T0`: costo dell'ancora annidata | `disc95` | −0,0016 [−0,019; +0,016] | +0,0038 [−0,0018; +0,0093] |
| | altre, risolte | `r_spec` −0,003, `mse_ratio` +0,06; nella vista del generatore anche `sign50` −0,016 | `reach` +0,0007, `mse_ratio` +0,006 |
| `AN` contro `AN` a bersagli scambiati | `disc95` | +0,290, risolto | +0,069, risolto |

`AN` e `A0` hanno la stessa maschera: il confronto fra loro non ha problemi di copertura. Fra `A0` e `T0` no
(132.473 e 53.146 coppie previste solo da T0), e per questo si legge anche la vista del generatore. Uscite:
[C-K562](ammi/cloud_r2/completion/ammi_none_C-K562.json), [C-iPSC](ammi/cloud_r2/completion/ammi_none_C-iPSC.json);
C-K562 ricalcolato sul portatile ([esito](ammi/ammi_none_C-K562_r1.json)) coincide a meno di 1e-16.

## Che cosa cambia per la lettura di `cells`

1. **L'ancora di confronto è `A0`, non `T0`.** Su C-K562 `A0` perde rispetto a `T0` in misure secondarie perché le
   manca CD4T fra le fonti: un `cells` − `T0` conterrebbe quella perdita e sembrerebbe un difetto del modello.
2. **`none` vale la sua ancora:** `cells` − `none` e `cells` − `A0` daranno quasi lo stesso numero. Se differiscono
   di più di qualche millesimo, è un fatto da capire prima di leggere altro.
3. **Un seme.** Una differenza fra `cells` e `none` a un seme è un'osservazione; per dire «il contesto aiuta»
   servono almeno tre semi per braccio, come scritto nella revisione del protocollo AMMI.
4. **Il lettore è pronto:** [ammi/lettura_esterni.py](ammi/lettura_esterni.py) accetta qualunque braccio nel
   formato dello stadio 100; per i due fold bastano i file `cells` e a contesto scambiato con la loro ricevuta.
