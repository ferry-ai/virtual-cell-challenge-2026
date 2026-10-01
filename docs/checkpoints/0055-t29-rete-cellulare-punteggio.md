# CP-0055 — t29: la rete addestrata sulle singole cellule sulla classifica, -0,030

- **Data:** 2026-10-01
- **Tipo:** esperimento
- **Redatto da:** Claude Code (sessione 07ebf08b)
- **Revisione umana:** no
- **Stato:** immutabile

> Un checkpoint è una fotografia datata. Non si riscrive: se una sua conclusione
> risulta sbagliata, si scrive un checkpoint nuovo e si aggiorna la colonna
> "Corretto da" in `docs/checkpoints/INDICE.md`.

## 1. Domanda

Che cosa vale sulla classifica di validazione (contesti A, B, C) la rete addestrata direttamente sui conteggi delle
singole cellule (R-LAB), quando i suoi effetti prendono il posto di quelli della ricetta t22 e il resto, generatore
compreso, resta quello del t22? È un invio autorizzato dal proprietario in chat (1/10, 00:29; «invia appena puoi»
alle 15:05 circa).

## 2. Cosa è stato fatto

- **Modello:** il braccio `desc` del secondo training (`rlab-cellnet-r2`, Kaggle GPU, 1/10 05:57-08:23 CEST). Un
  seme, 3,8 epoche, 3.354.670 cellule di training, HepG2 tenuto fuori. Esito tecnico in
  `reports/modelli/cellnet_esteso_2026-10-01/ESITO.md`; `model.pt` sha256 `f4dbc3e5…`.
- **Registrazione** prima dell'esportazione e della generazione (12:06 UTC):
  `reports/invii/prediction_t29_2026-10-01/prediction.json`. Banda −0,02…+0,10, centro 0,04. Regola:
  - ≥ 0,137: alla pari della ricetta;
  - 0,06-0,137: segnale da trasferimento ad ampiezza naturale;
  - < 0,06: più debole del trasferimento semplice, nessun nuovo invio della rete senza un banco locale a sei membri.
- **Effetti:** `export_effects.py` (commit `652787e`), 2.048 controlli ufficiali per contesto, asse e bersagli
  del t22. Manifest in `reports/invii/trial_2026-10-01/t29_effects_manifest.json`.
- **Stadi 45 e 48** in locale, con le impostazioni del t22. Manifest, diagnostica e log sono in
  `reports/invii/trial_2026-10-01/`. Il pacchetto passa tutti i controlli, il validatore ufficiale e la verifica bit
  per bit; sha256 `4562a813…`.
- **Upload:** come processo separato, dalle 13:28 alle 15:16 UTC, sul Wi-Fi di casa (0,2-1 MB/s). Entry
  `K6Q36uGCaEwQ1wRLmBLp`, MD5 verificato dal server.
- **Lettura:** `read_t29_score.py`, scritto e committato prima del punteggio.

## 3. Cosa si è osservato

Dallo status pubblicato (`reports/invii/trial_2026-10-01/status_K6Q36uGCaEwQ1wRLmBLp_final.json`) e dal confronto
(`reports/invii/prediction_t29_2026-10-01/comparison.json`):

- **Punteggio:** −0,029625, rango 893. La media dei sei scalati coincide con lo `score_avg`. È fuori dalla banda
  registrata (sotto −0,02), ramo **c** della regola.
- **Contro il t22** (+0,141250): −0,1709.

| Membro | t29 grezzo | t22 grezzo | t29 scalato | t22 scalato |
|---|---|---|---|---|
| PDS (coseno) | 0,503 | 0,787 | 0,007 | 0,634 |
| MSE | 10,24 | 3,06 | 0 | 0 |
| NMAE delle LFC | 1,095 | 0,927 | −0,157 | 0,120 |
| Fedeltà della direzione | 0,510 | 0,497 | −0,011 | −0,052 |
| Reach della direzione | 0,057 | 0,195 | −0,026 | 0,131 |
| Jaccard dei significativi | 0,034 | 0,036 | 0,009 | 0,014 |

## 4. Interpretazione e incertezza

- **Misura:** il PDS crolla da 0,79 a 0,50. La discriminazione fra perturbazioni vale circa il caso.
- **Interpretazione:** gli effetti esportati per i 300 bersagli si somigliano tutti. La rete prevede soprattutto una
  risposta comune del contesto, con poca parte specifica del bersaglio. Era già visibile su HepG2: guadagno
  specifico +0,0037 per gene, coseno 0,27 contro 0,39 del trasferimento (`cellnet_esteso_2026-10-01/ESITO.md`).
  L'MSE e la reach peggiorano perché la risposta comune è sbagliata o mal calibrata sui contesti A, B, C. La fedeltà
  della direzione, invece, è pari a quella della ricetta.
- **Incertezza:** un invio, un seme, un modello di 3,8 epoche non tarato. Il risultato chiude questa
  formulazione (effetti della rete al posto della ricetta, ampiezza naturale), non la strada della rete. Non si sa
  ancora quanto dipenda dal braccio, dalle epoche, dalla miscela (`pi` medio 0,59-0,67 sui contesti, che rimpicciolisce
  gli effetti) o dall'esportazione dai soli 2.048 controlli.

## 5. Spiegazione semplice

La classifica premia soprattutto chi sa dire che il knockdown del gene X fa una cosa diversa da quello del gene Y.
Questa rete ha imparato bene come «si muove» una cellula perturbata in generale, ma quasi niente di ciò che distingue
un bersaglio dall'altro. È come un medico che riconosce che il paziente sta male, ma non di quale malattia.

## 6. Conseguenze

- **Regola registrata, ramo c:** nessun nuovo invio della rete finché un banco locale a sei membri sui contesti
  pubblici non la mostra almeno al livello del trasferimento.
- **Riferimenti:** la ricetta t22 resta il riferimento, e il t28 (+0,144845) il massimo osservato. PROGETTO §0 non
  cambia.
- **Prossimi passi della rete (R-LAB),** in ordine:
  - misurare in locale la parte specifica del bersaglio (PDS sui contesti tenuti fuori);
  - provare la rete come correzione della ricetta invece che al suo posto;
  - più epoche e il pavimento su `pi` (`cellnet_terza_ondata_2026-10-01/PROTOCOLLO.md`).

## 7. Cosa corregge

Nessuna conclusione precedente. Il punteggio sta sotto la banda registrata, che era soggettiva e dichiarata non
calibrata.

## 8. Domanda di comprensione

Perché un modello che azzecca la direzione dei geni che cambiano (fedeltà pari alla ricetta) può prendere un
punteggio negativo?
