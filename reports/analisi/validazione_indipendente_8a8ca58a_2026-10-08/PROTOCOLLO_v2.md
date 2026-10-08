# Contratto sperimentale della validazione indipendente — v2 (emendamento)

**Stato: congelato** con il commit che contiene questo testo, l'8 ottobre 2026 (orologio letto con `date`: 18:50
Europe/Rome). Autore: VALIDAZIONE, Claude Code `8a8ca58a`. Sostituisce il [contratto v1](PROTOCOLLO_v1.md) **solo
nei tre punti sotto**; tutto il resto di v1 vale com'è scritto, e v1 non è riscritto. Manifest:
[manifest_fold_v2.json](manifest_fold_v2.json) (sha256 `a54ff614…ac3da`), scritto da
[build_manifest_v2.py](build_manifest_v2.py), che fallisce se un fold si sposta.

**Che cosa era già noto quando è stato scritto.** I numeri del livello A della corsa r1 erano letti
([tabelle v1](TABELLE_LIVELLO_A_r1.md)); **nessun numero del livello B esisteva** (i due banchi a sei membri erano
in corsa, nessuna uscita raccolta). Nessun candidato nuovo (T2, componente esterna) era stato consegnato. La
modifica 1 nasce da un controllo che v1 aveva registrato prima dei numeri e che è fallito su un fold; non sposta
nessuna soglia.

## 1. Misura primaria di discriminazione: `disc95` al posto di `disc`

**Il difetto (misurato).** v1 calcolava `disc` sui geni validi per **tutti** i bersagli confrontati. Nel fold
C-K562 la tabella di verità ha maschere diverse per bersaglio e resta **un solo gene** comune ai 272: T0 vale 0,492,
il braccio a bersagli permutati 0,498, differenza −0,005 [−0,046; +0,037]. Il «segnale precoce» di v1 dice che in
quel caso il banco non vede la specificità: su C-K562 `disc` non è utilizzabile. Sugli altri cinque fold il
controllo passa.

**La correzione.** `disc95`: stesso rango per coseno, sui geni validi per **almeno il 95 %** dei bersagli
confrontati nei bracci del manifest; una coppia non valida conta 0 da entrambe le parti. Era calcolata nella
stessa corsa r1 come sensibilità dichiarata nel codice. Con `disc95` il controllo a bersagli permutati passa su
tutti e sei i fold (differenze fra +0,060 e +0,438, tutte risolte; C-K562 +0,302).

**Regola.** Nel §8 di v1, lettera (c) e nelle definizioni di «sfavorevole» e di «segnale precoce», `disc` si legge
`disc95`. Una misura di discriminazione vale su un fold solo se lì il suo controllo a bersagli permutati è risolto
positivo. `disc` resta secondaria dove il suo controllo passa. Nient'altro del §8 cambia.

**Confronti da rileggere:** K0, K1 e K1 (r1) del livello A. Non serve rieseguire nulla: le due misure stanno nello
stesso `results.json`. La rilettura è in [TABELLE_LIVELLO_A_r1_v2.md](TABELLE_LIVELLO_A_r1_v2.md):

| Contrasto | Lettura con v1 (`disc`) | Lettura con v2 (`disc95`) |
|---|---|---|
| K1, T1 − T0 | nessun arresto; macro +0,0005 [−0,0001; +0,0011]; C-K562 non utilizzabile | nessun arresto; macro +0,0004 [−0,0005; +0,0013]; sei fold utilizzabili, nessuno risolto |
| K1 (r1), R1 − T0 | nessun arresto; macro +0,0006 [+0,0000; +0,0013] | nessun arresto; macro +0,0003 [−0,0006; +0,0013] |
| K0, T0 − P4 | nessun fold risolto negativo; macro −0,0037 [−0,0144; +0,0074] | **C-HEK293 risolto negativo** (−0,0301 [−0,0549; −0,0047]); C-iPSC risolto positivo; macro −0,0079 [−0,0182; +0,0027] |

La lettura di K1, che è il confronto su cui si decide stanotte, **non cambia**. Cambia quella di K0, che non è una
decisione aperta (t36 è già inviato) ma una misura del passato: si riportano entrambe.

## 2. Alias di lignaggio

Dal lignaggio HCT116 esce il motivo di nome `dld`: DLD-1 è un'altra linea del colon. Nessuna tabella DLD-1 esiste
in alcuna release, quindi nessun fold e nessun risultato di v1 cambia.

## 3. Livello B: due fold con cellule vere

Il livello B si esegue come scritto in [LIVELLO_B.md](LIVELLO_B.md), prima dei suoi numeri, su:

| Fold | Cellule vere | Bersagli | Cellule per bersaglio (min, mediana, max) | Geni |
|---|---|---:|---|---:|
| C-K562 | `replogle_k562_gwps`, estrazione `…celle-k562-8a8ca58a-r1`, sha256 `2c5e7c88…34fd` | 272 | 13, 128, 128 | 7.679 |
| C-iPSC | `kolf_strong_perturbations`, estrazione `…celle-ipsc-8a8ca58a-r1`, sha256 `81a37495…9381` | 55 | 33, 110, 128 | 18.106 |

Il banco scarta i bersagli con meno di 4 cellule vere (nessuno, qui). CD4T, HCT116 e HEK293 non hanno cellule vere
estratte: la macro del livello B è una media su due lignaggi.

## 4. Precedenti

- **S-009** e ERRORI, «una media che copre la perdita del membro che pesa di più»: la misura di discriminazione è
  la guardia contro quel guasto; una guardia che su un fold non distingue un braccio dai suoi bersagli permutati
  non protegge nulla. Per questo ogni misura porta il proprio controllo, fold per fold.
- **S-006**, **S-010**: restano come nel §9 di v1.
- ERRORI, «la soglia non si sposta dopo aver visto il numero» (CP-0030): qui non si sposta una soglia; si cambia la
  definizione di una misura dopo che un controllo preregistrato l'ha dichiarata inutilizzabile, e si riportano le
  due letture affiancate.

**Segnale precoce e arresto:** se su un fold il controllo a bersagli permutati di `disc95` non è risolto positivo,
quel fold non entra nella lettera (c) del §8 e lo si dichiara. Se il controllo del livello B (T0 contro T0 a righe
scambiate) non abbassa il PDS locale, il banco a sei membri di quel fold è invalido e non si legge.
