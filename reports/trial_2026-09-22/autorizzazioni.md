# Autorizzazioni del proprietario — 23 settembre 2026, poco dopo mezzanotte

Risposte date in chat a quattro domande dell'agente, trascritte senza cambiare il senso.

1. **Invio del t08:** «Sì, e anche le prossime ablazioni». Il t08 si invia. Le varianti
   successive a un solo fattore si inviano senza chiedere ogni volta. Restano due vincoli:
   - previsione registrata prima di ogni invio;
   - al massimo 2 invii al giorno.
2. **Orion (CC-BY-NC-SA-4.0):** «Sì, usalo». Il proprietario ammette Orion anche nelle
   sottomissioni. Chiude la riserva D-004 (d) per decisione del proprietario, non per
   verifica della licenza presso gli organizzatori.
3. **Colab:** «Riavvio io il notebook». Il job 044 (t09) resta in coda su Drive.
4. **Disco:** «decidi tu cosa cancellare». Le cancellazioni fatte sono elencate sotto.

## Cancellazioni

- `C:/Users/ferra/vcc2026-data/artifacts/t08gen/prediction.h5ad` (4,06 GB, sha256
  `f78fba9c…75f45f`). Intermedio del t08: il `.vcc` in `artifacts/t08pack_r2` ne contiene gli
  array X identici bit per bit (verifica dello stadio 48,
  `reports/trial_2026-09-22/t08_packaging.json`). Il file si rigenera dallo stadio 45 con gli
  stessi effetti e lo stesso seme.
- Non cancellati:
  - `q00full`: D-017 lo tiene come unico riferimento di dispersione reale;
  - `q01full`: intermedio di trial-01, il migliore finora. Resta finché lo spazio basta.

## Cancellazioni del 23 settembre, prima del t10

Servono circa 12 GB per generare e impacchettare il t10, e ne restavano 7,1. Cancellati due file
riproducibili:
- `artifacts/q01full/prediction.h5ad` (4,0 GB): l'intermedio di trial-01. Il suo `.vcc`
  resta in `artifacts/k01pack`, verificato bit per bit contro questo file il 13 settembre
  (CP-0005).
- `artifacts/t08pack_r2/prediction.vcc` (4,2 GB): il t08 già inviato. Il server ne ha
  verificato l'md5 all'upload. Si rigenera con lo stadio 45 dagli effetti in
  `processed/effects_t08_2026-09-22` con il seme 20260912, e si reimpacchetta con lo stadio
  48. Manifesti e sha256 restano in `reports/trial_2026-09-22/`.

## Cancellazione del 23 settembre, prima del t11

- `artifacts/q00full/prediction.h5ad` (4,2 GB): trial-00, ricampionamento dei controlli.
  D-017 lo tiene come riferimento di dispersione. Resta **rigenerabile esattamente**: in
  `artifacts/q00full/provenance_{A,B,C}.npz` ci sono le righe di controllo scelte per ogni
  perturbazione, e lo stadio 45 (`trial-00-controls`, seme 20260912) le rilegge. Restano anche
  diagnostica, validazione e manifesti. Motivo: il file di paging di Windows è cresciuto a
  13,2 GB e il disco era sceso a 5,2 GB liberi, contro i circa 12 che servono per generare e
  impacchettare il t11.

## Cancellazione del 23 settembre, dopo l'invio del t10

- `artifacts/t10pack/prediction.vcc` (4,2 GB): il t10 già inviato, con md5 verificato dal
  server. Lo rimuove la catena del t11 solo dopo che l'invio del t10 è terminato. Si rigenera
  dagli effetti in `processed/effects_t10_2026-09-23`, con lo stadio 45 e il seme 20260912.

## Incidente di spazio del 23 settembre, 03:27 locali

L'impacchettamento del t11 si è fermato con `OSError: [Errno 28] No space left on device`.
Tre lavori pesanti giravano insieme (streaming Orion HEK293T, stadio 83, stadio 48) con 0,5 GB
di RAM libera, e il file di paging di Windows è salito a 15,9 GB. Nessun dato perso:
`artifacts/t11gen/prediction.h5ad` è intatto. Rimosso solo il payload temporaneo
dell'impacchettamento fallito (`artifacts/t11pack/prediction.payload.h5ad`, 4,26 GB, un file
di lavoro dello stadio 48). Da qui in poi i lavori pesanti girano uno alla volta.

## Spazio liberato la sera del 23 settembre, dall'agente

Il proprietario, in chat: «libera un bel po' di spazio tu, non toccare file di sistema o che
possono compromettere le funzioni del pc». L'agente non cancella file in modo definitivo:
li ha **spostati nel Cestino di Windows** (capienza 25,8 GB su C:, `NukeOnDelete` = 0), da cui
si ripristinano. Lo spazio torna libero quando il proprietario svuota il Cestino.

- `artifacts/t11pack_r2/prediction.vcc` (4.205.076.480 byte, sha256 `ce3bb366…ada3c`): il t11,
  già valutato, md5 verificato dal server. Si rigenera dagli effetti in
  `processed/effects_t11_2026-09-23` con lo stadio 45, seme 20260912, e lo stadio 48.
- `artifacts/k01pack/prediction.vcc` (4.203.520.000 byte): trial-01, inviato il 13 settembre e
  superato da t08 e t11. Manifesti e sha256 restano in `reports/trial_2026-09-13/`.
- `predictions/smoke.h5ad` (43 MB): la prova di formato del writer, già candidata alla pulizia
  nel registro.
- `%LOCALAPPDATA%\pip\cache` (464 MB): la cache dei download di pip, che si ricostruisce da sola.

Provata e annullata: la compressione NTFS di `artifacts/t14gen/prediction.h5ad` dà un rapporto
1,0 a 1 (il file è già compresso al suo interno). Non toccati: file di sistema (paging,
ibernazione), macchine virtuali, Download, OneDrive, modelli di LM Studio, dati delle app
Claude e Codex, cache di Unreal Engine.

Più tardi, la stessa sera, il proprietario ha scelto in chat di spostare nel Cestino anche le
cache di Unreal Engine. Nessun processo di Unreal o di `zenserver` era attivo. Sono state
spostate:
- `%LOCALAPPDATA%\UnrealEngine\Common\DerivedDataCache`, 3,57 GB;
- `%LOCALAPPDATA%\UnrealEngine\Common\Zen`, 6,77 GB.

Si rigenerano da sole, ma la prossima apertura di un progetto Unreal ricompilerà gli shader. Il
Cestino dell'utente contiene ora 19,04 GB.

Il proprietario ha anche autorizzato in chat l'invio del t14 appena la quota del 24 settembre lo
permette. Una catena in background prima aspetta che il disco si liberi e impacchetta il t14,
poi lo invia dopo le 00:05 UTC, tenendo sveglio il portatile.

## Spazio liberato il 24 settembre, dopo il punteggio del t15

Con lo stesso mandato del 23 sera («libera un bel po' di spazio tu»), l'agente ha spostato nel
Cestino i file intermedi di due invii già valutati, con l'md5 verificato dal server:
- `artifacts/t14gen/prediction.h5ad` (4.222.536.680 byte) e `artifacts/t14pack/prediction.vcc`
  (4.170.444.800 byte): il t14, rigenerabile con lo stadio 76 dagli effetti del t08 × 2,5;
- `artifacts/t15gen/prediction.h5ad` (4.260.551.478 byte): l'intermedio del t15. Il suo `.vcc`,
  identico bit per bit e pari al miglior invio, resta in `artifacts/t15pack/`.

Il Cestino contiene 11,8 GB, entro la sua capienza di 25,8 GB. Servono per generare e
impacchettare t16 e t17.

## Autorizzazione del 24 settembre per t16 e t17

Il proprietario, in chat, alla domanda se inviare t16 e t17 appena si apre la quota del 25
settembre: «OK SI HAI IL VIA». Una catena in background aspetta che siano impacchettati e che
siano passate le 00:05 UTC del 25. Poi li invia uno dopo l'altro, prima il t16 e poi il t17,
tenendo sveglio il portatile, con i testi di `reports/trial_2026-09-24/submission_texts.md`.

## Spazio liberato il 25 settembre, notte

Il proprietario, in chat verso le 00:40 del 25 settembre: «puoi liberare spazio anche in modo
più aggressivo». Il disco C: aveva 5,56 GB liberi e il Cestino era vuoto (capienza 26.428 MB,
NukeOnDelete 0). Le cache comuni del profilo sono piccole (pip, npm, uv, CrashDumps, NVIDIA:
meno di 1 GB ciascuna); le voci grandi sono i modelli di LM Studio (11,96 GB) e i dati delle
app in `AppData\Local\Packages` (18,03 GB), esclusi dalla regola del 23 settembre. Spostati nel
Cestino verso le 00:41, con il metodo `SendToRecycleBin`:
- `artifacts/t14_pilots/` (1.411.603.105 byte): i cinque piloti del t14, già valutato; le
  chiamate e la scelta restano in `reports/dispersion_2026-09-23/t14_pilots/`;
- `artifacts/t15pack/` (4.205.159.113 byte): il `.vcc` del t15, valutato dal server con md5
  verificato; si rigenera con gli stadi 100, 45 e 48 dalla ricetta `configs/recipes/t15.json`.

Dopo il punteggio del t17 sono candidati anche `t16gen`, `t16pack`, `t17gen` e `t17pack`
(circa 16 GB), che la catena di invio usa fino ad allora.

Alle 00:45 il Cestino risultava vuoto e C: aveva 10,74 GB liberi (erano 5,56).
