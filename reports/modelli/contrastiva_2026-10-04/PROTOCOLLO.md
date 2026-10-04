# Rete contrastiva sugli effetti: protocollo registrato prima di ogni numero

4 ottobre 2026, pomeriggio. Ora esatta: il commit che aggiunge questo file. Su richiesta del proprietario («registra la
contrastiva e lanciala»). Viene dall'[esito r3](../adattatore_contesto_2026-10-04/ESITO_R3.md): tutti i modelli a
livello di effetti provati (r1, r2, r3, denoiser) riducono la discriminazione fra bersagli. La perdita usata (coseno più
errore relativo) premia la risposta generica. È la quinta prova in due giorni, quindi si usa una divisione nuova dei
bersagli (seme 4). Nessun numero di questa prova è stato calcolato.

## 1. Domanda

Se si addestra la stessa rete residua della r3 con una perdita **contrastiva**, la previsione batte la copia di K562 su
una linea mai vista senza perdere discriminazione? La perdita contrastiva chiede che l'effetto previsto di un bersaglio
sia più vicino al proprio effetto vero che a quelli degli altri bersagli della stessa linea, come fa il PDS.

## 2. Che cosa resta uguale alla r3, e che cosa cambia

**Uguale:**
- dati: le 25 chiavi e le 7 in più;
- spazio: bulk-lognorm a 50.000;
- pieghe: un gruppo tenuto fuori a turno fra `h1`, `kolf`, `rpe1`, `hepg2`, `jurkat`, con il gruppo interno successivo
  per l'arresto e le chiavi HipSci `kolf_*` tolte nella piega `kolf`;
- campionamento bilanciato per gruppo, batch di 64 bersagli di una linea;
- rete: `Adapter` inizializzato alla copia, correzione centrata sui bersagli;
- ottimizzatore; al massimo 3.000 passi, valutazione ogni 100, pazienza 10.

**Cambia:**
- **Perdita:** InfoNCE sul batch. Il logit ij è il coseno fra il previsto i e il vero j sui geni non NaN del vero j,
  diviso per τ = 0,1; la classe giusta è j = i. Si aggiunge 0,5 × (1 − coseno ii). Niente errore relativo.
- **Arresto anticipato:** si prende il passo con il coseno interno più alto **fra quelli** la cui discriminazione interna
  è almeno quella della copia meno 0,005. Se nessun passo dopo lo 0 rispetta il vincolo, la piega usa la copia.
- **Divisione dei bersagli:** seme 4 (60/15/25).

## 3. Bracci

| Braccio | Che cos'è |
|---|---|
| `k562` | la copia |
| `contr` | la rete con la perdita contrastiva (il candidato) |
| `cosloss` | la stessa rete con la perdita e l'arresto della r3, sulla stessa divisione: controllo dell'obiettivo |
| `contr_swap` | `contr` con il basale della linea di test sostituito dalla media d'addestramento |

## 4. Misure

Come nella r3: coseno medio sulle coppie di test, macro sulle cinque pieghe, bootstrap appaiato per piega (10.000,
seme 0), discriminazione (l'analogo del PDS), quota comune prima della centratura, sottoinsieme del pannello
(descrittivo).

## 5. Regola, fissata ora

- **Cancello tecnico:** almeno 40 bersagli di test per piega; nessun NaN.
- **Passa** se tutte e tre le condizioni valgono:
  1. la macro `contr − k562` ≥ **+0,01**, con il limite inferiore dell'IC 95% sopra 0;
  2. almeno 3 pieghe su 5 hanno media positiva;
  3. la macro della discriminazione `contr − k562` ≥ **−0,01**.
- **`contr − cosloss`** si riporta e non decide. Dice se è l'obiettivo a fare la differenza.
- **Se passa (fase 2):** come nella r3:
  1. addestramento su tutti i gruppi;
  2. esportazione A, B, C e quota comune della correzione: **sopra 0,5 non si invia**;
  3. previsione registrata con il numero concordato con Davide.

  **L'invio resta al proprietario.**
- **Se non passa:** la strada dei modelli a livello di effetti con questi dati si chiude del tutto. Restano i dati
  genome-wide di Davide (CD4, HCT116, HEK293T).

## 6. Previsioni, prima di ogni numero

| Quantità | Atteso | Fiducia |
|---|---|---|
| Macro `contr − k562` | da −0,005 a +0,02, centro +0,005 | — |
| Passa | — | 0,25 |
| Macro della discriminazione `contr − k562` | da −0,02 a +0,02 | — |
| Macro `contr − cosloss` (coseno) | da −0,01 a +0,01 | — |
| Pieghe in cui l'arresto torna alla copia | 1–3 su 5 | — |

## 7. Limiti

Gli stessi della r3:
- le linee di test non sono A, B, C né D, E, F;
- un banco locale ha già sovrastimato la gara tre volte;
- HepG2 e Jurkat sono schermi su geni essenziali;
- il contesto entra solo dal basale.
