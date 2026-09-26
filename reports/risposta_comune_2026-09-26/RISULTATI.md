# La risposta comune a tutti i knockdown: quanto pesa nell'errore quadratico, e se si trasferisce

26 settembre 2026, pomeriggio. Filone della scheda [R-V2](../../docs/piani/modello-v2.md), sulla
domanda del membro `mse` (scalato a 0 in ogni nostro invio, grezzo 3,88 per il t20).
**Proxy nello spazio degli effetti contro sorgenti pubbliche tenute fuori, non punteggi VCC.**

## La domanda

La ricetta d'invio toglie a ogni sorgente la sua risposta comune (la media su tutti i bersagli,
gamma 1), quindi nessuna previsione contiene la parte di risposta che tutti i knockdown condividono.
Il membro `mse` invece confronta con la risposta intera. Se la parte comune fosse grande e si
trasferisse da una linea all'altra, aggiungerla abbasserebbe l'errore quadratico.

## Come

`common_response.py` (uscita `r1/`) legge le previsioni salvate dal banco isolato r5
(`processed/lct_r5_predictions_2026-09-26`, t20like e verità per ciascuna sorgente tenuta fuori) e
calcola, con i pesi `log1p` dei banchi (x = 0,05 × CPM medio di A/B/C, geni del pannello esclusi):
- la quota dell'energia della verità spiegata dalla **sua** media sui bersagli (oracolo: quanto è
  grande la parte comune);
- la correlazione, gene per gene, fra la risposta comune delle sorgenti d'ingresso e quella della
  verità;
- il rapporto di errore quadratico sul "nessun cambiamento" di t20like, della sola risposta comune
  e della loro somma, con scale stimate sulle **altre** tre sorgenti (e, accanto, stimate sulla
  sorgente stessa, oracolo);
- il PDS proxy di t20like e di t20like più la risposta comune alle scale stimate.

## Risultati

| Sorgente fuori | quota comune (oracolo) | correlazione della risposta comune | t20like alla scala d'invio | t20like, scala stimata | + risposta comune | PDS: t20like → con la comune |
|---|---|---|---|---|---|---|
| K562 | 0,013 | 0,11 | 1,082 | 0,9994 | 0,9990 | 0,779 → 0,744 |
| CD4 | 0,143 | 0,05 | 1,262 | 0,9993 | 0,9996 | 0,692 → 0,610 |
| HCT116 | 0,078 | 0,06 | 1,259 | 0,9997 | 1,0000 | 0,708 → 0,648 |
| HEK293T | 0,058 | 0,06 | 1,456 | 0,9999 | 0,9995 | 0,677 → 0,669 |

- **Misurato:** nelle sorgenti pubbliche la parte comune vale l'1–14 % dell'energia della verità, e
  quella delle altre linee non la predice (correlazione 0,05–0,11).
- **Misurato:** aggiungere la risposta comune delle sorgenti d'ingresso non abbassa l'errore
  quadratico (rapporti 0,999–1,000 con le scale stimate, 0,998–1,000 con quelle oracolo) e toglie
  PDS proxy (−0,008…−0,082).
- **Misurato, conferma di [banco_varianti r10](../banco_varianti_2026-09-25/MSE.md):** alla scala che
  minimizza l'errore il trasferimento batte il "nessun cambiamento" di meno dello 0,1 %.
- **Interpretazione:** la risposta comune è specifica della linea, o dell'esperimento. Togliere la
  media a ogni sorgente (gamma 1) resta giusto per il trasferimento. La `mse` ufficiale non si
  recupera così: le voci con `mse` grezza 0,6–0,85 in classifica devono avere un'informazione che il
  trasferimento fra linee diverse non dà (ipotesi, non verificata: dati della stessa linea, o una
  struttura propria dei dati ufficiali).
- **Limite:** la verità è una sorgente pubblica rumorosa, che spinge ogni rapporto verso 1; il
  membro ufficiale si calcola su cellule generate, con correzioni di campionamento (vedi il rapporto
  di claude2 sul membro `mse`, quando arriva).

## r2: la `mse` ufficiale si predice dall'energia prevista

Su proposta di claude2 ([analisi del membro](agenti/membro_mse_claude2.md), esperimento 1), `mse_energy.py`
(uscita `r2/`) calcola per ogni file di effetti inviato l'energia prevista nello spazio dello scorer,
E = Σ bersagli Σ geni (log1p(5·10⁴ · composizione prevista) − log1p(5·10⁴ · composizione dei controlli))²,
gene del bersaglio escluso, con il passo di profilo del trial-01 (taglio a |log2 FC| 6, composizione
rinormalizzata), media sui tre contesti; poi la confronta con la `mse` grezza pubblicata dei sei invii
col generatore del trial-01 che hanno entrambe le cose ([energy.csv](r2/energy.csv)).

| Invio | E | `mse` grezza ufficiale | 1 + E / 4786 |
|---|---|---|---|
| t11 | 747 | 1,129 | 1,156 |
| t08 | 858 | 1,152 | 1,179 |
| t10 | 1.367 | 1,297 | 1,286 |
| t17 | 2.631 | 1,502 | 1,550 |
| t15 | 2.978 | 1,579 | 1,622 |
| t20 | 13.675 | 3,878 | 3,857 |
| t22 (non ancora inviato) | 10.029 | — | 3,095 |

- **Misurato:** una retta per l'origine, u − 1 = E / D con D = 4786, riproduce le sei `mse` ufficiali con
  scarto massimo 0,048; con intercetta (u = 0,969 + 0,000212 E) lo scarto massimo è 0,038.
- **Interpretazione:** nel modello u ≈ 1 + (‖d̂‖² − 2⟨d̂, d⟩) / D il termine incrociato fra previsione
  e verità è trascurabile per tutti i nostri invii: le previsioni sono quasi ortogonali agli effetti
  reali in questo spazio, e la `mse` misura solo quanta energia mettiamo. D ≈ 4.800 è l'energia degli
  effetti reali dei 300 bersagli per contesto; il t20 ne mette 2,9 volte tanta.
- **Conseguenza (interpretazione):** con l'attuale qualità di direzione nessuna ampiezza porta la `mse`
  sotto il suo zero ufficiale (0,986–0,992); per scendere servirebbe un coseno aggregato con la verità di
  almeno 0,12 (claude2, §3). La formula serve da predittore locale della `mse` di ogni candidato.
- **Limite:** sei punti, un solo generatore; D è una media sui tre contesti e la combinazione dei tre
  rapporti per contesto nel numero pubblicato non è verificata.
