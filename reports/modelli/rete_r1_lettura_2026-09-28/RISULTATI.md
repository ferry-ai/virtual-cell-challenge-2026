# La regola di r1 letta sui tre semi

29 settembre 2026, notte. Scrive Claude (app desktop, sessione `f2abd9a6`); orari letti da `date`. Rete e regola:
[rete_contesti_2026-09-27](../rete_contesti_2026-09-27/RISULTATI.md), regola fissata alle 22:03 del 27/09. Scheda
[R-V2](../../../docs/piani/modello-v2.md).

Etichette: **misurato**, **interpretazione**. Nessun numero qui è un punteggio VCC.

## Come si è letta

- **Previsioni:** i tre semi di ogni disegno, mediati su Kaggle (kernel `vcc-rete-r1-avg`, finito il 28/09 alle 18:43)
  e scaricati in `kaggle/out_r1_avg/avg_r1/` della radice dati.
- **Punteggi:** `score_pred.py` su ciascuno dei nove disegni, dalle 18:51 alle 23:xx del 28/09, uscite in
  `kaggle/score_r1_avg/`. Lanciato dalla sessione `f4f38e58`, finito dopo il suo arresto.
- **Lettura:** `leggi_r1.py` (scritto dalla sessione `f4f38e58` prima dei risultati), il 29/09 alle 00:1x:

  ```bash
  scripts/py.cmd reports/modelli/rete_r1_lettura_2026-09-28/leggi_r1.py --scores <kaggle>/score_r1_avg \
      --seeds <kaggle>/out_r1_s0_v2 <kaggle>/out_r1_s1_metrics <kaggle>/out_r1_s2_metrics \
      --out reports/modelli/rete_r1_lettura_2026-09-28/r1
  ```

  Tabelle in [`r1/contrasts.csv`](r1/contrasts.csv) e [`r1/readout.json`](r1/readout.json).

## Esito (misurato)

**Condizione dei semi: regge.** Il segno di rete − cieca, nello spazio degli effetti, è lo stesso nei tre semi su 5
verità su 5 (tutti positivi).

**E1, uso del contesto (rete − cieca), proxy combinato: non passa.**

| Verità | Δ | Intervallo al 95 % |
|---|---|---|
| K562 | −0,0008 | [−0,0055; +0,0041] |
| CD4 a riposo | +0,0031 | [−0,0023; +0,0086] |
| HCT116 | +0,0029 | [−0,0002; +0,0060] |
| HEK293T | +0,0074 | [+0,0034; +0,0113] |
| KOLF2.1J | −0,0040 | [−0,0092; +0,0012] |

Positivo su 3 verità su 5, intervallo sopra zero su una: la regola ne chiede 4 e 2.

**E1, candidato (rete − `excl`): non passa. Passa al contrario.**
- La rete perde contro il trasferimento `excl`, con l'intervallo sotto −0,002, su tre verità:
  - K562 −0,0374;
  - HCT116 −0,0117;
  - HEK293T −0,0132.
- È positiva solo su KOLF2.1J (+0,0037, intervallo sullo zero).

**Diagnostica, rete − scambio:** positiva su 4 verità su 5, con nessun intervallo sopra zero. Il contesto giusto non si
distingue da uno sbagliato.

**E2: non passa su nessuna coppia.**
- Orion: correlazione media 0,0013 [−0,0017; +0,0042], quantile 97,5 % delle permutazioni 0,0040.
- CD4 a riposo contro 48 ore: −0,0006 [−0,0071; +0,0062].

**J (rete − ripiego: 0,1 × partner STRING + testa cis): passa.**
- K562 +0,0015 [+0,0002; +0,0029].
- HCT116 +0,0010 [−0,0002; +0,0022].

Positivo su entrambe, con l'intervallo sopra zero su una.

## Che cosa ne segue, per la regola scritta prima

- **Uso del contesto ed E2 non passano:** nessuna prova che la rete recuperi dai controlli una parte dell'interazione
  bersaglio × contesto.
- **Il candidato non passa, e al contrario la rete peggiora il trasferimento** su tre linee: non sostituisce `excl`.
- **J passa:** valore per i bersagli nuovi del set finale, «con la stessa trafila». Cioè candidato per il banco sul
  pannello e per il banco con lo scorer vero, ciascuno con una regola sua.
  - Dopo [CP-0041](../../../docs/checkpoints/0041-proxy-contro-ufficiale.md) il proxy non basta per scegliere.
  - I guadagni sono di un millesimo o due.

## Interpretazione

- È coerente con la diagnosi del disegno della rete relazionale
  ([DISEGNO](../rete_relazionale_2026-09-28/DISEGNO.md), §1): la rete impara una parte comune a tutti i bersagli, e
  perde la discriminazione che il trasferimento aveva.
- Sui bersagli nuovi (J) il confronto è con un ripiego debole, e il guadagno è piccolo.
