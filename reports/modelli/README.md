# modelli — modelli appresi su molti contesti

La scheda [R-V2](../../docs/piani/modello-v2.md), filoni F9 e F10: modelli che imparano come il
contesto, letto solo dai controlli, cambia la risposta a un knockdown. Tutti si provano con le
stesse domande:
- **E1**: batte la sua versione cieca (contesto medio) su una famiglia di linee tenuta fuori?
- **scambio**: batte la stessa rete con il contesto di un'altra linea? Se no, il guadagno viene
  dalla forma del modello, non dal contesto giusto;
- **E2**: prevede la differenza fra due linee tenute fuori?

Indice generale: [../README.md](../README.md). Precedenti chiusi: il predittore neurale
condizionato del 18–19/09 ([storico/conditioned_2026-09-18](../storico/conditioned_2026-09-18/),
CP-0026), che con due contesti di training non generalizzava.

**Dove siamo (misurato, 28/09):** nessun modello passa la sua regola. Dove un modello batte la
versione cieca, **non batte lo scambio**: il contesto giusto non aiuta più di uno sbagliato. La
perdita sulla famiglia tenuta fuori è minima nei primi 50–100 passi e poi sale, mentre quella di
training scende: quello che la rete impara oltre il trasferimento calibrato è specifico delle
linee viste. Con 48 linee di Tahoe, copiare le linee simili perde contro la media di tutte.

| Data | Cartella | Nocciolo | Vale? | Peso oggi |
|---|---|---|---|---|
| 28/09 | [encoder_contesto_2026-09-28/](encoder_contesto_2026-09-28/) | Encoder dei profili basali innestato nella rete; autoverifica 17 su 17. Prima tornata, parte Orion: nessuna condizione passa, guadagni di un millesimo, con l'embedding di un'altra linea la rete va meglio; la parte K562/CD4 è finita su Kaggle ma **non è ancora scaricata né letta** | sì per la parte Orion; regola completa non ancora letta; seme 0 solo | ★★ |
| 28/09 | [rete_contesti_r2_2026-09-28/](rete_contesti_r2_2026-09-28/) | Dataset r2 con 12 contesti CRISPRi (in più K562 essential, VIPerturb-seq, RPE1, due schermi HIPSCI) e la regola della tornata r2 fissata prima; varianti descrittive di r1: il minimo sulla famiglia tenuta fuori è entro i primi 100 passi | in corso: r2 lanciata su Kaggle il 28/09 alle 10:06, esito non ancora letto | ★★ |
| 28/09 | [tahoe_bracci_2026-09-28/](tahoe_bracci_2026-09-28/) | I farmaci di Tahoe-100M come perturbazioni in 48 linee: T1 ridotto non passa. I vicini giusti battono quelli sbagliati (+0,06), ma copiarli perde contro la media di tutte le linee (−0,14) | sì; farmaci, non knockdown; effetto di piastra non separabile | ★★ |
| 27/09 | [rete_contesti_2026-09-27/](rete_contesti_2026-09-27/) | La rete su molti contesti (disegno di claude2, autoverifica 14 su 14): la corsa di produzione si ferma al passo 250; la perdita sulla famiglia tenuta fuori sale appena la rete impara oltre il trasferimento. La regola di r1 chiede tre semi: **il seme 2 non è stato lanciato**, quindi r1 non si legge ancora | in parte: r1 incompleta | ★★ |
| 27/09 | [modello_contesto_2026-09-27/](modello_contesto_2026-09-27/) | Modello a cancelli a quattro parametri, con la letteratura verificata da grok. r1: E1 non passa, E2 parziale (coppia Orion sì, r ≈ 0,002; CD4 no); dove batte il cieco non batte lo scambio | sì, esito negativo per l'adozione | ★★ |

## Rischi da tenere presenti (interpretazione)

- **Poche famiglie di contesti**: nella fase di training di E1 la rete vede 4 contesti di 2
  famiglie. Un vettore di contesto imparato da così pochi punti non generalizza, con o senza
  encoder.
- **Laboratorio e piattaforma confusi con la linea**: le due Orion sono dello stesso studio e le
  sorgenti sono quasi tutte in 3'. Un modello può imparare lo studio invece della biologia.
- **Un seme solo** nelle tornate del 28/09: l'intervallo bootstrap sui bersagli non contiene la
  varianza fra semi.
