# Propagazione nel contesto: protocollo registrato prima di ogni numero

4 ottobre 2026, verso le 2:30, ora del PC. Ora esatta di registrazione: il commit che aggiunge questo file. Su richiesta
del proprietario: «scrivi il protocollo del punto 3». Nessun braccio è stato calcolato. L'unico conto fatto prima è
l'[inventario](inventario.json) dei bersagli e dei geni disponibili ([inventario.py](inventario.py)): usa solo gli
effetti veri aggregati, non le previsioni.

## 1. Domanda

Gli effetti misurati in K562 coprono 7.681 geni su 18.533. Se li propaghiamo agli altri geni usando le co-espressioni
dei **controlli della linea bersaglio**, la direzione prevista si avvicina a quella vera su una linea mai vista?

## 2. Perché

- **[CP-0058](../../../docs/checkpoints/0058-t31-solo-k562.md):** sul pannello ufficiale il t31 è il solo K562 gwps (260
  bersagli su 272). Il 61% delle coppie bersaglio–gene è previsto a zero, e A, B, C ricevono effetti identici.
- **[Margini all'orizzonte](../../analisi/margini_orizzonte_2026-10-04/README.md):** il coseno della nostra direzione
  è circa 0,11–0,13. Per far contare l'MSE ne serve almeno 0,22, e circa 0,06 dei 0,074 di distacco dalle prime 100
  dipende dalla direzione.
- **Inventario (misurato):** nello spazio bulk-lognorm a 50.000, quello di MSE e PDS, sui geni che K562 non misura
  (insieme U) cade il **39%** dell'energia dell'effetto vero (HipSci, 7.067 coppie linea–bersaglio) e il **46%** (neuroni
  Tian 2021, 143 bersagli). Queste quote includono il rumore di campionamento della verità (mediana 83 e 164 cellule per
  bersaglio).

## 3. Metodo

Per un bersaglio t e una linea L:

1. **Sorgente:** `δ_M` = effetto K562 gwps (lfc in ln) sui geni M che misurano sia K562 sia L.
2. **Spazio:** `δ_M` si porta nello spazio log1p dei controlli di L (CPM a 1e4) con le medie dei controlli di L:
   `Δx_g = log1p(1e4 p_g e^{lfc_g}) − log1p(1e4 p_g)`.
3. **Modello dei controlli di L:** sulle cellule di controllo di L (log1p, geni centrati), si calcolano le prime k
   componenti principali dei geni M (`V_k`) e una regressione ridge dalle k coordinate ai geni U (`B`).
4. **Propagazione:** `Δx_U = B · V_kᵀ Δx_M`. Poi si torna in lfc con le medie dei controlli, tagliando a ±10.
5. **Iperparametri:** k ∈ {10, 20, 50, 100} e λ su una griglia logaritmica di 13 valori fra 1e-3 e 1e3. Si scelgono
   **solo** con validazione incrociata a 5 pieghe sulla ricostruzione dei geni U dei controlli dai geni M, senza
   guardare alcun effetto perturbato. Seme 0.

## 4. Bracci

| Braccio | Geni M | Geni U | A che cosa serve |
|---|---|---|---|
| `k562` | effetto K562 | 0 | la forma del t31 |
| `imp` | effetto K562 | propagati coi controlli di L | il candidato |
| `imp_other` | effetto K562 | propagati coi controlli dell'altra linea del banco | dice se il guadagno è specifico del contesto |
| `imp_perm` | effetto K562 | i valori di `imp` permutati fra i geni U, per bersaglio, seme 0 | controllo: separa la struttura dalla sola energia |
| `oracle_U` | effetto K562 | verità | tetto, descrittivo |

## 5. Banco

- **Primaria:** HipSci, 19 chiavi in un unico gruppo. 372 bersagli in comune con K562 gwps; 10.832 geni U. La verità
  per bersaglio è la media fra le linee che lo misurano. Il modello dei controlli usa i controlli HipSci di tutte le
  linee insieme, perché quelli per libreria sono pochi (al massimo 23, prepass r1).
- **Replica:** neuroni Tian 2021, 143 bersagli in comune, 10.712 geni U.
- **Controlli:** le cellule di controllo vengono dagli shard rlab su Kaggle. Il passo 0 conta le cellule disponibili:
  - se HipSci ha meno di 300 controlli in tutto, la primaria diventa Tian 2021 e HipSci passa a replica;
  - se nessuna delle due linee arriva a 300, il banco non si fa.
- **Sorgente:** il solo K562 gwps, come il t31 sul pannello. Nessun bersaglio del pannello ufficiale entra nel banco.

## 6. Misure

- **Primaria:** media sui bersagli del coseno fra effetto previsto e vero su tutti i geni che L misura (M ∪ U). Si
  calcola nello spazio bulk-lognorm a 50.000: `d = log1p(5e4 p e^{lfc}) − log1p(5e4 p)`, con `p` dalle medie dei
  controlli di L.
- **Secondarie:** coseno sui soli geni U; rapporto delle norme previsto/vero su U; R² della validazione incrociata.
- **Incertezza:** bootstrap appaiato sui bersagli, 10.000 ricampionamenti, seme 0.

## 7. Regola, fissata ora

- **Cancello tecnico:** R² della validazione incrociata sui geni U maggiore di 0 per la scelta di k e λ; almeno 100
  bersagli sulla linea primaria; nessun NaN nelle previsioni. Se il cancello fallisce, il banco non si legge.
- **Passa** se, sulla linea primaria:
  1. `imp − k562` ≥ **+0,02**, con il limite inferiore dell'IC 95% sopra 0;
  2. `imp − imp_perm` ha il limite inferiore dell'IC 95% sopra 0;
  3. sulla replica, `imp − k562` ha media positiva (l'IC non è richiesto).
- **Se passa:**
  1. **seconda fase:** sei membri con lo scorer vero sulla stessa linea, con il generatore del t22, bracci `k562` e
     `imp`, con un protocollo proprio;
  2. **poi, solo se la seconda fase passa:** un candidato ufficiale. È l'esportazione del t31 con la propagazione fatta
     coi controlli di A, B, C: un solo fattore cambiato contro il t31, con previsione registrata a parte.
- **Se non passa:** la propagazione non si usa, e l'esito si scrive.
- **`imp_other` non decide.** Se `imp ≈ imp_other`, il guadagno è generico e non specifico del contesto: resta
  utilizzabile, ma cambia l'interpretazione.

## 8. Previsioni, prima di ogni numero

| Quantità (linea primaria) | Atteso | Fiducia |
|---|---|---|
| `imp − k562` | da 0,00 a +0,05, centro +0,02 | — |
| La regola passa | — | 0,4 |
| `oracle_U − k562` | da +0,10 a +0,35 | — |
| `imp − imp_other` | da −0,01 a +0,02 | — |
| R² della validazione incrociata su U | da 0,02 a 0,15 | — |

## 9. Limiti

- La verità è rumorosa (83 e 164 cellule per bersaglio in mediana), e il rumore tiene bassi tutti i coseni.
- La propagazione suppone che lo spostamento indotto da una perturbazione segua le co-variazioni dei controlli. Non è
  garantito: le perturbazioni possono muovere programmi che nei controlli non variano.
- HipSci pooled mescola 19 donatori. Le sue 372 chiavi sono un pannello mirato, non i 300 bersagli ufficiali.
- Le linee del banco non sono A, B, C né D, E, F. Un coseno del banco non è un punteggio VCC (CP-0027, CP-0058).
- Una sola sorgente, K562 gwps. La forma con le sorgenti della ricetta richiede le cache r9.

## 10. Che cosa serve per lanciarlo

- **Le cellule di controllo** di HipSci e Tian 2021 dagli shard rlab su Kaggle: un kernel CPU o un download. Servono
  l'ok del proprietario in chat e il lancio da parte sua, perché il classificatore blocca il push da qui.
- **Calcolo:** CPU, nessuna quota d'invio.
- **Codice:** da scrivere in questa cartella con un test sintetico, prima del lancio e dopo questa registrazione.
