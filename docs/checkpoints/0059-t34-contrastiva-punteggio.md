# CP-0059 — t34: la rete contrastiva in classifica, non conclusiva

- **Data:** 2026-10-04
- **Tipo:** esperimento
- **Redatto da:** Claude Code per Alfredo
- **Revisione umana:** no
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

**Numeri:**
- t34 è un numero provvisorio. Su main esistono il t30 di Davide e un suo t31 previsto, mentre su questo branch t30 e
  t31 sono gli invii di Alfredo del 3/10.
- Anche questo checkpoint (0059) va riconciliato al momento del merge: su main lo 0059 manca, ma 0056–0058 hanno altri
  contenuti.

## 1. Domanda

La rete contrastiva sugli effetti ha passato il banco locale e l'addendum 1
([ESITO](../../reports/modelli/contrastiva_2026-10-04/ESITO.md)). Applicata al transfer K562 del t31, migliora il
punteggio ufficiale?

## 2. Cosa è stato fatto

- **Registrazione:** previsione e regola registrate prima dell'esportazione del candidato
  ([prediction.json](../../reports/invii/prediction_t34_2026-10-04/prediction.json), commit b37dedc). Banda +0,06…+0,11;
  regola a ±0,005 contro il t31.
- **Esportazione:** `esporta_d.py`, nello spazio `d` del contesto, con ampiezza uguagliata in `d` a quella del t31 e geni
  non espressi esclusi. La quota comune della correzione vale 0,016–0,017 e il coseno `d` con il t31 è 0,90
  ([t34_effects_manifest.json](../../reports/invii/trial_rlead_2026-10-04/t34_effects_manifest.json)).
- **Generazione e pacchetto:** stadi 45 e 48 come per il t31 (`--effects-scale 2.0`); validatore ufficiale superato,
  sha256 `46149a6c…`.
- **Invio:** su richiesta del proprietario in chat («gradalo prima»). Upload dalle 14:37 alle 15:47 UTC; entry
  `SjJp6tuHoMRL7VlQEvFY`, MD5 verificato; nella ricevuta l'email è sostituita da un segnaposto.

## 3. Cosa si è osservato

- **Punteggio:** stato `published`, **score_avg +0,076732**, rango 674
  ([status](../../reports/invii/trial_rlead_2026-10-04/status_SjJp6tuHoMRL7VlQEvFY.json)). La media ricalcolata dai
  sei membri coincide ([comparison.json](../../reports/invii/prediction_t34_2026-10-04/comparison.json)).
- **t34 − t31 = −0,0020:** è il **ramo b**, non conclusivo, dentro la banda registrata.
- **Membri scalati, t34 − t31:**

  | Membro | Differenza |
  |---|---|
  | PDS | **−0,021** (coseno grezzo 0,742 contro 0,752) |
  | MSE | 0 (grezzo 7,65 contro 7,73) |
  | nMAE | −0,008 |
  | fedeltà | **+0,012** |
  | reach | +0,002 |
  | Jaccard | +0,003 |

## 4. Interpretazione e incertezza

- **Misurato:** il guadagno del banco (+0,015 di coseno, discriminazione tenuta) non si vede in gara. La media scende di
  0,002, dentro il rumore del seme.
- **Misurato:** in gara il PDS scende (−0,021 scalato), mentre sul banco la discriminazione era quasi invariata
  (−0,007). È lo stesso membro che ha fatto scendere il t30 di Davide (−0,042).
- **Interpretazione:** è il quarto caso in cui un banco locale sovrastima la gara: t28, il nostro t31, il t30 di Davide
  e ora il t34. Il PDS ufficiale si calcola fra i 300 bersagli del pannello, nei contesti della gara, e risponde in
  modo diverso dall'analogo locale fatto su altri bersagli e altre linee.
- **Non separabile:** contro il t31 cambiano insieme la direzione del modello, la definizione dell'effetto in `d` e
  l'esclusione dei geni non espressi.

## 5. Spiegazione semplice

Il modello aveva migliorato il compito di prova, ma all'esame vero il voto è rimasto lo stesso, con un po' meno nella
materia che pesa di più (distinguere un intervento dall'altro). Un po' più di punti sui geni che salgono o scendono
non compensa.

## 6. Conseguenze

- **Secondo la regola:** nessun altro invio di questo modello sul solo K562.
- **Proposta:** prima di un altro invio di un modello, il banco deve misurare il PDS come lo misura la gara, cioè sui
  bersagli del pannello o simili, con lo scorer vero e la forma del t22. È la strada B: servono le cache r9 o le
  tabelle del cubo di Davide.
- **PROGETTO §0 non cambia:** il massimo osservato resta il t28.

## 7. Cosa corregge

Nessuna conclusione precedente. Precisa la portata dell'esito del banco della contrastiva: vale sul banco locale, non
si è trasferito alla gara in questa forma.

## 8. Domanda di comprensione

Perché un modello che sul banco non perde discriminazione può perdere PDS in gara?
