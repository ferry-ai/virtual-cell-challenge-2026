# Adattatore di contesto r3: linee varie e correzione a media zero

4 ottobre 2026, pomeriggio. Ora esatta: il commit che aggiunge questo file. Su richiesta del proprietario («registra il
protocollo r3 e lancialo»). Viene dopo [r1](ESITO_R1.md), [r2](ESITO_R2.md) e il [denoiser](../denoiser_k562_2026-10-04/ESITO.md),
tutti negativi, e dopo il t30 di Davide (main, entry `lDMS…`, t30 − t25 = −0,005, PDS −0,042). Nessun numero della r3 è
stato calcolato. L'unico conto fatto prima è l'inventario delle chiavi nuove: bersagli, geni, cellule.

## 1. Che cosa cambia e perché

| Cambio | Motivo misurato |
|---|---|
| Sette chiavi in più: H1 2025 train e val (non il test), HepG2, Jurkat, KOLF strong, chromatin e metabolic (`vcc2026-data/kaggle/rete_sorgenti_r1_chiavi_extra/chiavi`) | r1: il modello imparava le linee viste (validazione fino a +0,054, test ≤ 0) con 19 HipSci quasi uguali in addestramento |
| Campionamento bilanciato **per gruppo** di linee, non per coppia | stesso motivo: HipSci dominava le coppie |
| Arresto anticipato su un **gruppo interno tenuto fuori**, non sulle linee d'addestramento | r1: la validazione sulle linee viste sovrastimava |
| **Correzione a media zero sui bersagli:** previsione = copia K562 + (uscita − copia − la sua media sui bersagli della stessa linea) | t30 di Davide: su A/B/C la correzione era per il 63–70% comune ai bersagli, e il PDS è sceso |
| Formulazione residua: si parte esattamente dalla copia | r1: il modello perdeva sui geni che K562 misura |

## 2. Pieghe: un gruppo tenuto fuori a turno

Gruppi di test: `h1`, `kolf`, `rpe1`, `hepg2`, `jurkat`. Per ogni piega:
- si addestra su tutti gli altri gruppi (HipSci e Tian sempre in addestramento);
- nella piega `kolf` si tolgono dall'addestramento anche le chiavi HipSci `kolf_2` e `kolf_3`, perché KOLF2.1J viene da
  quel donatore;
- il gruppo interno per l'arresto anticipato è il successivo nell'ordine `h1 → kolf → rpe1 → hepg2 → jurkat → h1`.
  È escluso anch'esso dall'addestramento, e si usano le sue coppie con i bersagli di validazione.

**Bersagli:** divisione nuova con il seme 3, 60/15/25 sull'unione dei bersagli condivisi con K562 gwps. Un bersaglio
di test non compare mai in addestramento né nell'arresto.

## 3. Bracci

| Braccio | Che cos'è |
|---|---|
| `k562` | la copia |
| `adapter3` | copia + correzione appresa centrata sui bersagli (il candidato) |
| `adapter3_nocenter` | lo stesso modello letto senza centratura: descrittivo, misura che cosa toglie il vincolo |
| `adapter3_swap` | `adapter3` con il basale della linea di test sostituito dalla media dei basali d'addestramento: controllo del contesto |

**Rete:**
- l'`Adapter` della r1, inizializzato alla copia, con le stesse ottimizzazioni e la stessa perdita (1 − coseno + 0,1 ×
  errore relativo), ma calcolata sulla previsione centrata;
- al massimo 3.000 passi, valutazione ogni 100, pazienza 10;
- un seme per piega.

## 4. Misure

- **Primaria:** per piega, il coseno medio sulle coppie di test, nello spazio bulk-lognorm a 50.000, sui geni non NaN.
- **Macro:** la media delle cinque pieghe.
- **Incertezza:** bootstrap appaiato sui bersagli dentro ogni piega, 10.000 ricampionamenti, seme 0. La macro si
  ricampiona piega per piega con gli stessi indici di ripetizione.
- **Discriminazione:** l'analogo del PDS del denoiser.
- **Quota comune della correzione sulla linea di test:** ‖media sui bersagli‖² × n / Σ‖correzione‖², prima della
  centratura.
- **Descrittivo:** il coseno sui soli bersagli del pannello presenti fra quelli di test (KOLF, H1).

## 5. Regola, fissata ora

- **Cancello tecnico:** in ogni piega almeno 40 bersagli di test e nessun NaN. L'arresto anticipato deve trovare un
  passo migliore della copia nel gruppo interno, altrimenti la piega vale 0 di guadagno (si usa la copia).
- **Passa** se tutte e tre le condizioni valgono:
  1. la macro `adapter3 − k562` ≥ **+0,01**, con il limite inferiore dell'IC 95% sopra 0;
  2. almeno 3 pieghe su 5 hanno media positiva;
  3. la macro della discriminazione non scende più di 0,01 sotto quella di `k562`.
- **Se passa (fase 2):**
  1. si addestra il modello su tutti i gruppi, con il numero di passi pari alla mediana dei migliori passi delle
     pieghe;
  2. si esportano A, B, C con il basale dei loro controlli e si misura la quota comune della correzione prima della
     centratura. **Se supera 0,5 su un contesto, non si invia**, anche se il banco passa;
  3. la previsione del candidato si registra con il numero concordato con Davide.

  **L'invio resta al proprietario.**
- **Se non passa:** la strada dell'adattatore a livello di effetti si chiude, e l'esito si scrive.

## 6. Previsioni, prima di ogni numero

| Quantità | Atteso | Fiducia |
|---|---|---|
| Macro `adapter3 − k562` | da −0,005 a +0,03, centro +0,008 | — |
| Passa | — | 0,35 |
| Pieghe positive | 2–4 su 5 | — |
| Quota comune prima della centratura, sulle linee di test | da 0,1 a 0,4 | — |
| `adapter3 − adapter3_swap` (macro) | da −0,005 a +0,01 | — |

## 7. Limiti

- Le linee di test non sono A, B, C né D, E, F. Il coseno non è lo scorer, e un banco locale ha già sovrastimato la gara
  tre volte (t28, il nostro t31, il t30 di Davide).
- HepG2 e Jurkat sono schermi su geni essenziali; KOLF, H1 e HipSci sono pluripotenti e simili fra loro.
- Il contesto si legge solo dal basale medio.
