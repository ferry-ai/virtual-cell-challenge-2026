Non ho trovato bug che alterino silenziosamente le predizioni del pilot, ma il pilot non sostiene la produzione e c'è un rischio interpretativo nuovo. Direzione prompt→query, unità e appaiamento per cardinalità coincidono con l'API Stack ufficiale al commit `cacc2e4`. Il rischio nuovo: ogni braccio Stack è una sola estrazione casuale di conteggi, con un controllo sintetico condiviso da 8 target su 12 e riprodotto identico dalla conferma. Trovo anche due difetti minori verificati.

**Cosa ho fatto** [misurato]
- Ho letto per intero gli 8 file.
- Ho letto il codice ufficiale al commit congelato via WebFetch: `models/core/inference.py`, `models/core/base.py`, `models/utils.py`, `cli/generation.py`, `configs/finetuning/ft_parsecg.yaml`, `data/finetuning/datasets.py`, README.
- WebFetch riassume il contenuto con un modello: le righe decisive le ho riconfermate con richieste mirate.
- Nessun comando shell, nessun dato, nessun artefatto di risultato: non affermo che qualcosa abbia girato o migliorato.

## Contratto verificato, senza difetti
- **Direzione** [misurato]: nella CLI ufficiale `--base-adata` è "containing donor cells" (il prompt) e `--test-adata` è "to generate for" (la query). L'adapter passa K562 come base e i controlli HepG2 come test (`stack_pilot.py:260-264`).
  - `mode="mdm"` finisce nel ramo che genera, come il default della CLI; anche `.25/.4/.2` e 5 passi sono i default.
  - `mask_rate` non entra nel calcolo dei passi: innocuo.
- **Unità** [misurato]: upstream non maschera nessun gene (`n_genes_to_mask = 0`), applica `log1p` internamente e calcola la profondità sui conteggi grezzi.
  - L'output è un campionamento negative binomial (NB) con media = softmax sui geni × profondità della query: conteggi interi.
  - È coerente con `validate_counts` (`:145-148, 269`) e con la normalizzazione su S (`:234-245`).
- **Padding e allineamento** [misurato]: upstream restituisce solo le cellule query reali, senza padding. Il controllo di forma è a `:267-268`.
- **Appaiamento** [misurato]: stessa numerosità n, stessi 512 controlli, stesso seed; upstream il seed fissa la stessa permutazione della base (`:353-357`). I due bracci usano le stesse librerie e lo stesso RNG (`:361-365`).
- **Simboli duplicati** [misurato]: la politica "prima colonna" è la stessa in prepare, infer e scorer (`stack_pilot.py:174-175, 201-203`; `score_stack_pilot.py:150-152`).

## Rilievi, dal più grave

**1. P2 — inferenza (meccanismo misurato upstream). Il rapporto `d` viene da un'unica estrazione casuale per braccio, non da un valore atteso.**
- **Evidenza:**
  - `corrected_profile` somma conteggi NB campionati una sola volta per braccio (`stack_pilot.py:234-245`).
  - Il controllo sintetico viene calcolato una volta per ogni n (`:354-356`). Dai conteggi di `stack_plan_r1.json:17-30`, 8 target su 12 hanno n=128 e ne condividono uno.
  - Upstream, l'ordine in cui le cellule vengono rigenerate dipende dal prompt (`is_masked[new_test_logit>0] = True`). Le due traiettorie divergono e il seed comune decorrela solo in parte [inferito].
- **Anche la conferma lo riusa:** copia identici `source_00.h5ad` e `destination_controls.h5ad` (`stack_confirmation_pack.py:25, 135-138`), con le stesse etichette di campionamento (`stack_pilot.py:322, 355`) e lo stesso seed. Per n=128 produce quindi lo stesso controllo sintetico del pilot, salvo nondeterminismo GPU [input misurati, output inferito].
- **Conseguenza** [inferito]:
  - Il braccio Stack ha rumore in più su tutti i geni di S, che il transfer non ha. Con circa 50 conteggi totali, la sola componente Poisson dà circa 14% per braccio, confrontabile con effetti reali modesti.
  - Questo errore è correlato fra gli 8 target e il bootstrap (`score_stack_pilot.py:70-79`) lo ignora.
  - L'esito di pilot e conferma può dipendere da una sola estrazione, e su questo punto la conferma non è indipendente.
- **Diagnostica minima** (senza verità e senza toccare le predizioni congelate):
  - Rigenerare 2–3 controlli sintetici con seed o sottoinsiemi di controlli diversi per ogni n.
  - Calcolare la RMS del log-rapporto controllo/controllo su S, con la stessa normalizzazione, e confrontarla con `shared_lfc_rms` dei file `diagnostic_XX.json`.
  - Registrare per braccio `(test_logit>0).mean()`: oggi viene scartato a `:265`.

**2. P2 — inferenza. Anche con una conferma positiva, il pilot non sostiene la produzione.**
- **Evidenza** [misurato]:
  - Il pilot prende i prompt dal file K562 originale, esplicitamente non dalla selezione x002 (`stack_pilot.py:72, 176, 198`).
  - La produzione usa invece gli shard x002, con eleggibilità sui conteggi x002 (`stack_production_pack.py:1-4, 80-99`). Usa anche i controlli ufficiali dei contesti A/B/C (`:114-127`) e la baseline t25 per contesto (`:128-138`).
  - Il bundle di produzione ha un formato diverso (`:214-226`) che l'adapter congelato non sa leggere (`stack_pilot.py:309-312, 345-349`).
  - L'adapter di produzione non è nel pacchetto (`STACK_ALLOWLIST.json:11`).
  - La regola del pilot porta solo a una conferma distinta (`score_stack_pilot.py:81`), sempre su HepG2 e con gli stessi controlli.
- **Dal codice upstream** [letto via WebFetch; l'implicazione è inferita]: il checkpoint Aligned è addestrato a trasferire stato di donatore/sample tra cellule dello stesso tipo (`ft_parsecg.yaml`: `replacement_ratio: 0.75`, colonne `sample:cell_type`). Un prompt K562 su una query HepG2 o A/B/C è fuori da questo regime, quindi va misurato contesto per contesto.
- **Minimo necessario:**
  - un adapter di produzione rivisto con lo stesso contratto;
  - un confronto ponte fra prompt x002 e prompt originali, sugli stessi target e controlli HepG2, contro il pavimento di rumore del punto 1;
  - diagnostiche per contesto senza verità;
  - una regola go/no-go per contesto, fissata prima.

**3. P2 per impatto, da verificare. La regola di decisione legge il PDS per posizione di colonna.**
- `pds_delta` usa `a[:, 0]` (`score_stack_pilot.py:69`), cioè presume che `FIVE[0]` sia `"pds_cosine"`.
- `FIVE` segue l'ordine di `SCORED` (`:22`), che è in `vcc2026.bench` e non è nel pacchetto. `per_target` controlla solo che `pds_cosine` esista (`:92`).
- **Conseguenza:** se l'ordine è diverso, la regola a `:81` decide sulla metrica sbagliata.
- **Correzione a costo nullo:** `FIVE.index("pds_cosine")`. Verifica immediata: l'ordine delle chiavi di `member_contributions` nell'output.

**4. P3 — comportamento verificato nel codice, impatto inferito. L'intersezione S azzera geni misurati negli input di Stack.**
- `align_shared` mette a zero ogni gene fuori da S in entrambi gli input (`stack_pilot.py:220-229, 315-321`). Un gene misurato in HepG2 ma assente in K562 finisce quindi a zero anche nella query HepG2.
- L'allineatore ufficiale mette a zero solo i geni assenti dal dataset stesso (`_align_genes_to_target_list`), e upstream non esiste una maschera per i geni mancanti.
- Se gli assi dei dati sono filtrati per espressione [non verificato], la query perde marcatori abbondanti di HepG2 e parte della profondità. È un rischio di efficacia (falso negativo), non di validità: non è il caveat noto sulla copertura di S.
- **Diagnostica:** per cella, la frazione di conteggi fuori da S nei controlli HepG2 e nei controlli K562, più i 20 geni esclusi con più massa.

**5. P3 — verificato nel codice, impatto inferito. S distingue maiuscole e minuscole; Stack ufficiale no.**
- L'adapter confronta i nomi così come sono (`stack_pilot.py:224, 238, 315`); upstream li porta tutti in maiuscolo prima del confronto.
- I metadati sorgente contengono simboli misti come `C7orf26` (`stack_confirmation_pack.py:24`). Questi geni escono da S anche se il modello ha `C7ORF26` e ricevono zeri. Nessun disallineamento: S è solo più piccolo.
- `REVIEW_STACK.md:125-128` aveva verificato solo la lista geni del modello. La produzione eredita lo stesso comportamento (`stack_production_pack.py:111-112`).
- **Diagnostica:** quanti geni guadagnerebbe S con il confronto in maiuscolo, più un controllo delle collisioni.

**6. P3 — bug verificato, che fallisce con un errore esplicito. Il bundle di conferma non funziona con lo scorer del pilot.**
- `score_stack_pilot.py:142` legge `bundle["destination_size"]`, ma il manifest della conferma non contiene quel campo (`stack_confirmation_pack.py:72-87, 144-150`; nel pilot sta a `stack_pilot.py:208`). Riusando lo scorer si ottiene un `KeyError`.
- Inoltre la verità è riconosciuta solo dalla dimensione del file.
- **Minimo:** copiare `destination_size` e uno SHA256 della verità dal bundle del pilot, oppure usare uno scorer di conferma rivisto.

## Domande aperte
- L'unità di `lfc` nel transfer congelato e in t25 è logaritmo naturale o log2? `:358` presume il naturale; `predicted_profile` e `sample_counts` non sono nel pacchetto e nessun manifest registra l'unità.
- Il transfer è stato calibrato sulla verità HepG2 dei target "development"? I 12 del pilot vengono da lì (`stack_pilot.py:74`). Se sì, il braccio transfer ha un vantaggio in-sample, a sfavore di Stack, e pilot e conferma (`stack_confirmation_pack.py:33`) non sono confrontabili alla pari.
- Il transfer congelato del pilot e t25 sono la stessa ricetta? Con quale criterio è stata fatta la selezione x002?
- Quanto vale `model.n_cells`? Se è 512 come nel fine-tuning, ogni cellula del prompt si ripete circa 1,8–3,7 volte per set: l'appaiamento regge, ma è fuori dalla distribuzione di addestramento.
- Nei simboli duplicati, la "prima colonna" di K562 e quella di HepG2 corrispondono allo stesso Ensembl ID?

## Cosa non ho fatto
- Nessuna esecuzione.
- Non ho letto dati, file fuori dal pacchetto o il modulo `vcc2026` (`predicted_profile`, `sample_counts`, `Bench`, `SCORED`).
- Per il codice upstream cito i nomi di funzione, non i numeri di riga.
- Alcuni server MCP (engineering:*, runpod) richiedono autorizzazione e blender non si è connesso. Non erano necessari per questo lavoro.
