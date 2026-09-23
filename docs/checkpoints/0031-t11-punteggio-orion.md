# CP-0031 — Il t11 in classifica: +0,071, nuovo migliore; con Orion HCT116 la regola scritta prima dice che Orion aggiunge informazione, ma i pesi di K562 e CD4 sono cambiati insieme

- **Data:** 2026-09-23
- **Tipo:** esperimento
- **Redatto da:** agente (Claude Opus 5.5)
- **Revisione umana:** no. La ripresa dell'upload è stata autorizzata dal proprietario in chat,
  il 23 settembre.
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

A generatore fisso, aggiungere Orion HCT116 alle sorgenti del t08 cambia il punteggio
ufficiale? In che direzione, per ognuno dei sei membri?

## 2. Cosa è stato fatto

- **Regola scritta prima** di qualunque numero su Orion, alle 00:58 locali del 23 settembre
  (`reports/orion_2026-09-23/PRIMA_DEI_RISULTATI.md`):
  - sorgenti `k562`, `cd4_mix` e `orion_hct116`, **a pesi uguali**;
  - HEK293T, non ancora finalizzato, rinviato a un t12.
- **Ricetta** `configs/recipes/t11.json`:
  - cache dello stadio 98, run r4, che riproduce la r3 per K562 e CD4;
  - effetti grezzi, γ = 1, affidabilità n/(n+100), ampiezza 0,197;
  - generatore di trial-01 (stadio 45, `trial-ext-profile`), seme 20260912.
- **Previsione registrata prima** della generazione: banda +0,055…+0,075 e regola di lettura
  (`reports/prediction_t11_2026-09-23/prediction.json`).
- **Impacchettamento** con lo stadio 48: 24 controlli ufficiali e contenitore verificato,
  archivio con sha256 `ce3bb366…ada3c` (`reports/trial_2026-09-23/t11_packaging.json`).
- **Invio in quattro tentativi** (`reports/trial_2026-09-23/submit_t11_*`):
  1. alle 02:11Z il server risponde `create_failed`;
  2. il sonno del portatile interrompe l'upload, e l'entry viene annullata;
  3. alle 05:17Z nasce l'entry `FEBhtilNLpSm2kGiHB71`. L'upload si ferma, e il processo esce
     con `exit 1` alle 13:23Z lasciando l'entry in `uploading`
     (`status_FEBhtilNLpSm2kGiHB71_uploading.json`);
  4. alle 17:57Z `vcc submit --resume` riprende la stessa entry. Prima lo sha256
     dell'archivio è verificato contro il report dello stadio 48, e il processo tiene il
     portatile sveglio. Il server verifica l'md5 e pubblica il punteggio alle 18:25Z.

  Output verbatim: `submit_FEBhtilNLpSm2kGiHB71.json` e `status_FEBhtilNLpSm2kGiHB71.json`.

## 3. Cosa si è osservato

**Misurato — il punteggio.** **+0,070777**, rango 560, entry `FEBhtilNLpSm2kGiHB71`,
dentro la banda registrata. Il t08 aveva +0,060370.

**Misurato — i sei grezzi** (`reports/prediction_t11_2026-09-23/comparison.json`):

| membro | trial-01 | t10 | t08 | t11 | t11 − t08 | scalato t08 | scalato t11 |
|---|---|---|---|---|---|---|---|
| `pds_cosine` | 0,6870 | 0,6938 | 0,7103 | 0,7392 | +0,0289 | +0,466 | +0,530 |
| `expr_mse_unbiased_capped_norm` | 1,2313 | 1,2970 | 1,1524 | 1,1290 | −0,0233 (meglio) | 0 (tosato) | 0 (tosato) |
| `de_wilcoxon_lfc_nmae` | 0,9849 | 0,9804 | 0,9774 | 0,9774 | ≈ 0 | +0,039 | +0,039 |
| fedeltà direzionale | 0,4580 | 0,4610 | 0,4594 | 0,4582 | −0,0011 | −0,178 | −0,182 |
| `reach` | 0,0980 | 0,0913 | 0,1099 | 0,1129 | +0,0031 | +0,035 | +0,038 |
| Jaccard | 0,0291 | 0,0293 | 0,0304 | 0,0298 | −0,0005 | −0,000 | −0,002 |

**Misurato — le ancore reggono su un sesto punto.** Applicate ai grezzi del t11
(`reports/anchors_2026-09-17/anchors.json`), riproducono gli scalati pubblicati con uno scarto
massimo di 0,00026 (stesso file, campo `anchor_check_on_t11`).

**Misurato — i pesi delle sorgenti.** Il t08 pesava K562 0,433 e CD4 0,567
(`configs/recipes/t08.json`). Il t11 dà peso 1 a ciascuna delle tre sorgenti
(`configs/recipes/t11.json`), come fissava la regola al punto 2.

## 4. Interpretazione e incertezza

**Esito della regola scritta prima.** t11 − t08 = +0,0104, sopra la soglia di +0,005: «Orion
aggiunge informazione sui contesti ufficiali».

**Interpretazione:**
- **Il guadagno è quasi tutto nella discriminazione fra bersagli.** `pds_cosine` sale di
  0,029 grezzo, e lo scalato passa da +0,466 a +0,530: circa +0,011 sulla media. Gli altri
  membri si muovono poco; fedeltà e Jaccard un poco in giù.
- **La base ufficiale della `mse` è buona almeno quanto 1,1290.** La MSE grezza scende a
  1,1290 e lo scalato resta 0. È un limite più stretto di quello di
  [CP-0021](0021-ancore-ufficiali-e-troppe-chiamate.md) (1,2313).
- **La fedeltà non si muove** (0,458), come previsto da
  [CP-0030](0030-t10-attribuzione-cd4.md): resta legata al generatore.

**Incertezza:**
- **L'attribuzione a Orion non è pulita.** Rispetto al t08 cambiano due cose:
  - si aggiunge HCT116;
  - il rapporto fra K562 e CD4 passa da 0,433 : 0,567 a 1 : 1.

  La regola parlava di «un solo fattore» e fissava i pesi uguali. Il suo esito va letto
  come «HCT116 aggiunto, con le sorgenti a pesi uguali», non come l'effetto del solo HCT116.
- **Un solo invio**, senza intervallo.
- **Il perché del guadagno non è misurato.** Nello spazio degli effetti, mediare due
  sorgenti non alzava la proxy di discriminazione fra sorgenti
  ([CP-0028](0028-cd4-sorgente-flex-trasferimento.md)). Qui invece la PDS ufficiale sale. La
  proxy misura l'accordo fra le sorgenti, non con i contesti ufficiali.

## 5. Spiegazione semplice

Abbiamo aggiunto una terza fonte di esempi: una linea di cellule di colon (HCT116), spenta
gene per gene nell'atlante pubblico Orion. Adesso le tre fonti contano allo stesso modo. Il
modo di fabbricare le cellule è rimasto quello del t08.

Il voto è salito da 0,060 a 0,071. Il miglioramento sta quasi tutto nella capacità di
distinguere un gene spento dall'altro. Non possiamo dire quanto venga dalla fonte nuova e
quanto dall'aver dato a tutte lo stesso peso.

## 6. Conseguenze

- **Il t11 è il nuovo riferimento da battere**, al posto del t08.
- **Il t12** (il t11 più HEK293T) è registrato da prima di questo punteggio
  (`reports/prediction_t12_2026-09-23/prediction.json`). La sua regola si legge contro il
  t11, cioè contro +0,070777.
- **Un'ablazione pulirebbe l'attribuzione:** il t08 con K562 e CD4 a pesi uguali. È una
  proposta, non registrata.
- **La fedeltà resta la leva più grande:** −0,182 scalato su una media di +0,071. È il
  fattore del t09 e del t14 (`ControlModel`), che girano sul portatile
  (`reports/dispersion_2026-09-23/T14_IN_LOCALE.md`).
- **D-041**: Orion HCT116 entra come sorgente per bersaglio.

## 7. Cosa corregge

- Nessun checkpoint.
- Aggiorna il riferimento di PROGETTO.md §0: il migliore è il t11, non più il t08.
- Stringe, senza correggerlo, il limite sulla base della `mse` di CP-0021: da 1,2313 a 1,1290.

## 8. Domanda di comprensione

Se nello spazio degli effetti mediare le sorgenti non alza la discriminazione fra sorgenti,
come può la PDS ufficiale salire aggiungendone una?
