# Per Davide: `ta 40`–`ta 42` e il nuovo massimo del team (12–15 ottobre)

15 ottobre 2026. Claude Code per Alfredo. Nomi secondo D-058 (`ta` = Alfredo, `td` = Davide). Tutto è sul branch
`codex/teammate-rlead`. **I dati e i pacchetti stanno fuori da Git** (`vcc2026-data/` sul PC di Alfredo); qui ci sono
hash, percorsi e codice.

## In breve

**`ta 42` = 0,159396 (rango 437), +0,0105 su `td 38`: è il nuovo massimo del team.**

- **Che cos'è:** per ogni bersaglio, 0,7 × T3 (i tuoi effetti di `td 38`) + 0,3 × la nostra rete centrata (`ta 40`).
  Le due parti sono prese a norma unitaria e poi riportate alla norma di T3, quindi rispetto a `td 38` cambia solo la
  direzione. Emissione identica.
- **Il guadagno è quasi tutto PDS:**
  - scalato 0,654 contro 0,590 di `ta 40`;
  - coseno grezzo 0,7955, il più alto del team.

  I membri DE restano dove erano.
- **Perché funziona (interpretazione):** `ta 40` e T3 avevano punteggi vicini (0,1467 e 0,1489) ma direzioni poco
  correlate (coseno 0,48 sui geni comuni). Gli errori in parte indipendenti si cancellano nella media.

## I tuoi dati che ho usato (dataset Kaggle pubblici, scaricati il 15/10)

- **`davideferrante11/vcc-rsb-inputs-70dc-r1`:**
  - `T3_production.npz` (sha256 `b8c61f6d…f6a6`, lo stesso file di `td 38`);
  - `T3f__C-K562`, `C-iPSC`, `C-HCT116`, `C-HEK293`: T3 senza quel lignaggio, usati per il banco.
- **`davideferrante11/vcc-td41-effects-70dc-r1`:** effetti di `td 41` ("RS"), **solo letti**. Hanno coseno 0,51 con T3
  e 0,22 con `ta 40`, e norma 0,12 volte T3.

Il kernel `dt-t3-fit-generate-01a11c34-r1` risulta privato.

## Come è stato deciso (registrato prima dei numeri)

**Banco sui fold:** [rete_su_t3_2026-10-15](../../modelli/rete_su_t3_2026-10-15/README.md).
- Per ogni fold (K562, iPSC, HCT116, HEK293T del cubo r2) la rete è riaddestrata senza quel lignaggio.
- Si confronta con T3f dello stesso fold, sui bersagli del pannello che il lignaggio misura.
- Regola nel commit `a88497a`.

| Media sui 4 fold | Coseno | Indice PDS |
|---|---|---|
| T3 | 0,085 | 0,355 |
| 0,7 T3 + 0,3 rete | 0,097 | **0,366** |
| 0,5 T3 + 0,5 rete | **0,101** | 0,360 |
| T3 + residuo della rete | 0,084 | 0,305 (peggio) |

**Mescolare le direzioni aiuta; aggiungere a T3 il residuo della rete no.**

**Previsione del sito:** [prediction_ta42](../../invii/prediction_ta42_2026-10-15/prediction.json), regola a ±0,005 su
`td 38`, pushata prima di generare. Esito: [ESITO_TA42](../../modelli/rete_su_t3_2026-10-15/ESITO_TA42.md).

**Codice per rifarlo:** [esporta_ens.py](../../modelli/rete_su_t3_2026-10-15/esporta_ens.py) `--w 0.7`, con
`T3_production.npz` e gli effetti di `ta 40`. Poi lo stadio 45 con `--effects-scale 1.5 --gene-dispersion
--gene-dispersion-scale 1.0`.

## Gli altri invii di Alfredo in questi giorni

| Invio | Che cosa | Punteggio | Lettura |
|---|---|---|---|
| `ta 40` | Rete ponte col residuo centrato sul pannello | 0,146722 | +0,0059 su `ta 39`: la risposta comune spiegava la perdita di PDS ([esito](../../modelli/rete_centrata_2026-10-12/ESITO.md)) |
| `ta 41` | `ta 40` col tetto sulle magnitudini | 0,147376 | +0,0007; nMAE e PDS si sono mossi come previsto dal banco: **il banco del cubo è tarato per le magnitudini** ([esito](../../generatore_e_banchi/budget_chiamate_2026-10-13/ESITO_TA41.md)) |
| **`ta 42`** | Miscela T3 + rete | **0,159396** | **+0,0105 su `td 38`** |

## Otto prove sul banco che non vale la pena rifare

Dettagli in [budget_chiamate_2026-10-13](../../generatore_e_banchi/budget_chiamate_2026-10-13/README.md):
- **ridurre le chiamate:** la verità ha centinaia di geni significativi per bersaglio, e la soglia fa crollare la
  fedeltà;
- **denoising a basso rango o deflazione dei programmi condivisi:** il PDS crolla;
- **ampiezza:** 1,5 è vicina all'ottimo, 2,0 perde; l'ampiezza per bersaglio perde;
- **«un voto per lignaggio»:** perde in modo monotono. **Più sorgenti è meglio:** PDS 0,59 con 1 gruppo, 0,78 con 9;
- **inverso della varianza:** pari o peggio.

## Che cosa ti chiediamo

1. **I punteggi di `td 39`, `td 40` e `td 41`,** con gli entry ID: da qui non si vedono. Se `td 41` ("RS") è buono, è
   il terzo ingrediente naturale della miscela, perché è poco correlato con la nostra rete.
2. **La tua base più recente,** se è migliore di T3: la miscela si rifà in pochi minuti con `esporta_ens.py`.
3. **Per la finale D/E/F (dal 22/10):** proponiamo che il candidato sia una miscela dei modelli dei due autori. Il peso
   (0,5 o 0,7) e un eventuale terzo predittore vanno provati uno alla volta, con regola registrata.
