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
