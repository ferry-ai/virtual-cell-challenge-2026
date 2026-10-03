# Rete sulle sorgenti r1: esito del voto secondo il protocollo registrato

3 ottobre 2026, verso le 22:40, ora del PC. Kernel `alfredo2003bit/rete-sorgenti-r1`:
- lanciato alle 13:35 UTC e finito COMPLETE alle 19:18 UTC;
- codice al commit 23d6475, tutti e quattro i passi con codice di uscita 0 ([steps.json](esito_r1/steps.json)).

Il protocollo è [PROTOCOLLO_R1.md](PROTOCOLLO_R1.md), registrato prima di ogni numero. **Questo voto arriva dopo il
punteggio ufficiale della stessa rete** (t30, +0,027878, [CP-0056](../../../docs/checkpoints/0056-t30-punteggio-ufficiale.md)):
il proprietario aveva deciso di inviare senza aspettarlo.

I file piccoli sono in [esito_r1/](esito_r1/), con gli hash dell'intero output scaricato in `manifest_output.json`.
**Tutti i numeri sono di un banco locale:** scala (u − b)/(r − b), non punteggi VCC.

## 1. È la stessa rete inviata

L'addestramento di questo kernel e quello del kernel corto `rete-sorgenti-r1-train`, da cui viene il t30, hanno
scritto `monitor.jsonl` e `done.json` **identici byte per byte**. Stesso codice, stessi dati, stesso seme.

Gli sha256 di `ckpt_best.pt` non sono confrontati, perché i checkpoint di questo kernel sono rimasti su Kaggle. Con
monitor identici a ogni passo, la rete votata è quella inviata. È un'inferenza, non un hash confrontato.

## 2. Esito secondo la regola

| Voce | Esito |
|---|---|
| Cancello del banco | HepG2 passa: 6 membri su 6, pannello di 150 bersagli |
| **H1** | **non leggibile:** 11 bersagli ammessi, sotto il minimo di 20 ([linee.json](esito_r1/linee.json)) |
| Cancello della rete | `done.json` presente e 31 valutazioni; il controllo `net0 ≈ all` su H1 non si può fare, perché H1 non è leggibile |
| **Regola della rete** | **non passa:** richiede H1, che non è leggibile. Su HepG2 `net − all` (cioè `cross`) = **−0,217 [−0,287; −0,133]** |

**Perché H1 non è leggibile:** è un errore di disegno del protocollo, non dell'esecuzione.
- `--exclude-groups kolf jurkat` toglie KOLF dalle sorgenti dello stesso tipo di H1.
- Il pannello chiede che ogni braccio copra ogni bersaglio, e con le sorgenti rimaste i bersagli comuni scendono da
  51 a 11.

Non l'avevo verificato prima di registrare, e andava fatto. Lezione per i prossimi protocolli: contare i bersagli
ammessi con le esclusioni scelte prima di registrare.

## 3. Descrittivi su HepG2 (non decidono)

Bootstrap appaiato sui 150 bersagli, 10.000 ricampionamenti, seme 0, con le funzioni del banco della strada C:

| Confronto | Differenza media [IC 95%] |
|---|---|
| `net − net0` | **−0,247 [−0,315; −0,162]** |
| `net − cross` | −0,217 [−0,287; −0,133] |
| `net0 − cross` | +0,030 [−0,020; +0,074] |
| `net0 − cross_a2` | +0,009 [−0,035; +0,060] |
| `net0 − normrest` | +0,045 [−0,004; +0,091] |
| `net0 − k562` | +0,147 [+0,083; +0,204] |

Medie dei sei ([scaled_local_hepg2.csv](esito_r1/scaled_local_hepg2.csv)):

| Braccio | Media |
|---|---|
| `net` | 0,030 |
| `net0` | 0,277 |
| `cross` | 0,247 |
| `cross_a2` | 0,268 |
| `null` | −0,063 |

Geni significativi per bersaglio: `net` 0,17, quasi quanti ne ha `null` (0,17); `net0` 111,9.

## 4. Lettura

- **Misurato:** la rete imparata perde 0,25 contro il proprio punto di partenza su HepG2, una linea mai vista. Il suo
  profilo è quello di un braccio a effetto quasi nullo: quasi nessun gene significativo, PDS 0,42.
- **Coerente con quanto già misurato:**
  - nel t30 in classifica;
  - nel confronto locale della [r2](../rete_sorgenti_r2_2026-10-03/ESITO_LOCALE.md): ampiezza appresa che crolla;
    pesi che non aiutano la direzione.
- **`net0` va bene su HepG2.** È la media a pesi uguali per gruppo sulle 25 chiavi di addestramento: K562, RPE1, HipSci
  e Tian, senza KOLF, Jurkat né H1. Non è distinguibile da `cross` né da `cross_a2`, ma batte `k562` di +0,147.
  - Interpretazione: la media di più linee aiuta su HepG2, come già nella r1 della strada C (`cross − k562` +0,119).
  - È una sola linea, ed è descrittivo.
- **Previsioni registrate:**

  | Previsione | Atteso | Esito |
  |---|---|---|
  | La rete passa la regola | fiducia 0,3 | non passa |
  | `net − all` su H1 | da −0,02 a +0,05 | non leggibile |
  | Arresto anticipato prima di 3.000 passi | fiducia 0,5 | no |
  | Entropia normalizzata a fine corsa | 0,6–0,95 | 0,898, sì |

## 5. Che cosa segue

- **La rete sulle sorgenti resta ferma** ([ESITO_LOCALE della r2](../rete_sorgenti_r2_2026-10-03/ESITO_LOCALE.md)).
- **La leva da misurare è l'ampiezza della media di più linee, contro la ricetta del t22.** Va fatto su un banco con lo
  scorer vero e con la forma del t22, cioè la strada B: serve lo slug del dataset r9 di Davide.
