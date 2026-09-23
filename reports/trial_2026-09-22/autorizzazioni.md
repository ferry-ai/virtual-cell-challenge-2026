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
