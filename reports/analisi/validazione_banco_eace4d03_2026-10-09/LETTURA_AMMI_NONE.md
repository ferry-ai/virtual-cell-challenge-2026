# AMMI `none`: lettura nello spazio degli effetti contro la propria ancora, prima dei fit `cells`

9 ottobre 2026, VALIDAZIONE (Claude Code `eace4d03`). **Scritto prima di aprire un export AMMI**: di quei file ho
letto solo le ricevute di MODELLI-ESTERNI (dimensione, sha256, diagnostiche del produttore). Vale il
[contratto v3](PROTOCOLLO_v3.md); qui si fissano bracci, contrasti e parole. Lettura **descrittiva di livello A**:
non promuove, non boccia, non sostituisce i confronti a sei membri né i fit `cells`, che proseguono come autorizzati.

## Che cosa si confronta, e perché tre bracci

I due fit `none` (seme 17) sono il ramo **senza contesto**: predicono l'ancora più un residuo appreso dal solo
bersaglio. Per ogni fold ci sono tre previsioni diverse per gli stessi 300 bersagli, e vanno tenute distinte:

| Braccio | Che cos'è | Lignaggi esclusi dalle sue fonti |
|---|---|---|
| `T0` | il transfer del fold del banco (t36 senza il lignaggio del fold) | C-K562: K562. C-iPSC: iPSC |
| `A0` | l'**ancora annidata** del fit AMMI: lo stesso transfer senza i lignaggi che il fit esclude | C-K562: K562, CD4T e HepG2 (`anchor_06187e0c13b5`). C-iPSC: iPSC, K562 e Jurkat (`anchor_2d6b02f91ebe`). HepG2 e Jurkat non hanno bersagli del pannello: di fatto manca un lignaggio votante in più. Dalle ricevute di DATI-TRANSFER, `ammi_anchors_verified_r1.json` |
| `AN` | l'export AMMI `none`: `A0` più il residuo, stessa maschera di `A0` | come `A0` |

`A0` non è `T0`: gli manca un lignaggio in più (quello tenuto per le guardie interne del fit). Confrontare `AN` con
`T0` mescolerebbe il costo di quell'esclusione con il contributo del modello.

| Contrasto | Che cosa isola | Si legge come |
|---|---|---|
| `AN` − `A0` | il residuo appreso, a maschera identica | **il contributo del modello** |
| `A0` − `T0` | togliere un lignaggio in più dalle fonti | costo dell'ancora annidata; maschere diverse, quindi anche nella vista del generatore |
| `AN` − `T0` | i due insieme | solo descrittivo, non attribuibile |
| `AN` − `AN` a bersagli scambiati | se la previsione conosce i bersagli | controllo di specificità del braccio |

Regime: **C** sul lignaggio del fold (K562 per il fit C-K562, iPSC per il fit C-iPSC), verità primaria del fold
(`k562`, `kolf_pan_genome`). Misure del banco congelato com'è (`bench_core.measure`, sha256 `ffbc0dba…95ee`), più
copertura e vista del generatore per i contrasti fra maschere diverse. Parità richiesta prima di leggere: `disc95`
di `T0` uguale a quello della corsa di chiusura entro 1e-6; `A0` con lo sha256 della ricevuta di parità a residuo
zero del fit.

## Che cosa ci si aspetta, detto prima

Dalle ricevute del produttore il residuo vale circa il 3 % dell'ampiezza dell'ancora su C-K562 (`rms_ratio` 0,029)
e la loss si muove dello 0,7 % in due epoche: l'attesa è che `AN` − `A0` sia **piccolo e non risolto**. Non è una
soglia.

## Parole fissate ora

| Affermazione | Si scrive solo se |
|---|---|
| «il ramo senza contesto migliora la propria ancora» | `AN` − `A0` su `disc95` risolto positivo nel fold, senza regressioni risolte di `r_spec` e `sign50` |
| «la peggiora» | `AN` − `A0` su `disc95` risolto negativo nel fold |
| «non la distingue» | ogni altro caso |
| «l'ancora annidata costa» | `A0` − `T0` su `disc95` risolto negativo, anche nella vista del generatore |

Un seme di training: qualunque differenza è un'osservazione a un seme, non una proprietà del modello. Guardie
tecniche superate (perdita, quota comune del residuo, parità) non sono beneficio, e questa lettura non le
sostituisce. Se `AN` − `A0` è risolto negativo su `disc95` in un fold lo si scrive subito a MODELLI-ESTERNI e al
Lead: è il sintomo di S-006, e va saputo prima di leggere `cells`.

## Precedenti

- **S-006** (rete ancorata v4: peggiora la propria ancora): il primo contrasto è contro l'ancora, non contro il
  riferimento; il residuo si legge a maschera identica.
- **S-009** (banco diverso dall'esportazione): si legge il file esportato, con lo sha256 della ricevuta, e l'ancora
  è quella che il fit ha usato davvero, non T0.
- **S-013**, **S-015** (ridge senza contesto; riempimento): un ramo senza contesto può portare solo una risposta
  comune; il controllo a bersagli scambiati e la quota comune dicono se c'è altro.
- ERRORI: confrontare bracci con copertura diversa sul proprio supporto (CP-0075); una media che copre la perdita
  del membro che pesa di più (CP-0064).

**Segnale precoce e arresto:** se la parità di `T0` o lo sha256 di `A0` non tornano, nessun contrasto si legge. Se
`AN` e `A0` non hanno la stessa maschera, il contrasto `AN` − `A0` si legge solo nella vista del generatore e lo si
segnala a MODELLI-ESTERNI.
