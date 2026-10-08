# Verifica della consegna: manifest, versioni, hash, riproduzione

8 ottobre 2026, VALIDAZIONE (Claude Code `8a8ca58a`). Che cosa esiste, dove sta e come è stato verificato. La
scelta fra i candidati è nella [raccomandazione](../RACCOMANDAZIONE.md); questa pagina dice solo che cosa è
consegnabile e come lo si ricostruisce. **Nessun invio è stato fatto o preparato da questa sessione.**

## 1. Artefatti di produzione

| Artefatto | Dove | Identità | Verifica di oggi |
|---|---|---|---|
| **t36, riserva** | `vcc2026-data/submissions/t31_frozen_bank_2026-10-06/prediction.vcc` | 4.163.225.600 byte, sha256 `ea41ddf1…4af7`; entry `JLcMRGExhXKk77XVds7x`, punteggio ufficiale 0,147249 | sha256 ricalcolato sul file e uguale a quello registrato prima dell'upload, al prodotto locale e al manifest di generazione; dimensione uguale a quella ricevuta dal server; ricetta `3109a6d9…`; i sei membri pubblicati danno la media pubblicata: [riserva_t36_r1.json](riserva_t36_r1.json), dieci controlli su dieci |
| Effetti di t36 | kernel `davideferrante11/vcc-fit-banca-canonica-r1` (riferimento) | sha256 `08fdfd28…4c57`, uguali per A, B, C | riprodotti dal banco in tre corse indipendenti (r1, r2, r3) |
| **T1, candidato di DATI-TRANSFER** | `vcc2026-data/processed/dati_transfer_2026-10-08_01a11c34/t1_r1/effects/` | effetti sha256 `28f15de7…a6f5`; release `277ae344…ffd8` | riprodotti dal banco dalla release, stesso sha256. **Non esiste un pacchetto `.vcc` di T1**: generazione e impacchettamento spettano a DATI-TRANSFER e si fanno solo dopo una promozione |

Gli effetti non dipendono dal contesto (A, B, C hanno lo stesso sha256): il contesto entra nel generatore.

## 2. Artefatti di validazione (non sono produzione e non si inviano)

Tutti privati, con il prefisso `vcc-validazione-` e la sigla della sessione; ogni lancio ha `prepared.json`,
`launch.json` e, a corsa conclusa, `verification.json` o le ricevute raccolte.

| Che cosa | Kernel o dataset | Cartella |
|---|---|---|
| Livello A, corse r1–r5 | `davideferrante11/vcc-validazione-logo-8a8ca58a-r{1,2,3,4,5}` | `banco/r1` … `banco/r5` |
| Vettori comuni di T2, copia per il kernel | dataset `davideferrante11/vcc-validazione-t2-vettori-8a8ca58a-r1` (i vettori sono di DATI-TRANSFER, copiati senza modifiche) | `banco/t2_vettori_r1` |
| Cellule vere dei fold | `davidmaisterx/vcc-validazione-celle-{k562,ipsc}-8a8ca58a-r1` | `banco/celle_k562_r1`, `banco/celle_ipsc_r1` |
| Effetti dei fold per il livello B | dataset `davidmaisterx/vcc-validazione-effetti-{k562,ipsc}-8a8ca58a-r1` e `…-k562-8a8ca58a-x1` | `banco/livello_b_*/effetti.json` |
| Livello B | `davidmaisterx/vcc-validazione-banco-{ipsc,k562}-8a8ca58a-r1`, esplorativo `…-banco-k562-8a8ca58a-x1` | `banco/livello_b_ipsc_r1`, `banco/livello_b_k562_r1`, `banco/livello_b_k562_x1` |
| Copie locali degli effetti dei fold e tabelle per bersaglio | — | `vcc2026-data/processed/validazione_indipendente_8a8ca58a_2026-10-08/` |

Gli effetti a lignaggio escluso prevedono un contesto **senza** le sue fonti: usarli per un invio darebbe una
previsione più povera di quella di produzione. Stanno in cartelle e dataset distinti proprio per questo.

## 3. Versioni e dipendenze

| Dove | Versioni |
|---|---|
| Livello A (Kaggle CPU, 4 CPU, 31 GB) | Python 3.13, numpy 2.1.3, scipy 1.16.3, pandas 2.3.3, anndata 0.13.3.post0 ([runtime_versions.json](../banco/r1/completion/runtime_versions.json)); stadio 100 e moduli identici alla repo (stessi byte del pacchetto del fit r1) |
| Livello B (Kaggle CPU) | Python 3.13.15, `cell-eval2` **0.16.0**, numpy 2.1.3, scipy 1.16.3, pandas 2.3.3, polars 1.35.2, anndata 0.13.4 ([env.json](../banco/livello_b_ipsc_r1/completion/env.json)); `bench_v2.py` sha256 `06966c0b…0c08`, non modificato |
| Portatile | Python 3.12.3, numpy 2.5.3, `cell-eval2` 0.16.0: usato per test, lettura e ricalcolo delle misure, non per i fit |

Il ricalcolo locale delle misure del fold C-K562 coincide con quello del cloud alla precisione di macchina
([ricalcolo](../banco/r1/ricalcolo_locale_k562_r1.json)), con numpy diverso. La parità degli effetti al byte è
dimostrata su Kaggle, non sul portatile.

## 4. Come si riproduce

Dalla radice della repo, con `.\scripts\py.cmd` e i token Kaggle configurati. Ogni uscita si scrive una volta:
una ripetizione vuole un nome di revisione nuovo.

```powershell
$b = "reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/banco"
.\scripts\py.cmd -m unittest $b/test_metrics.py $b/test_bench_core.py      # 16 prove su effetti sintetici
.\scripts\py.cmd $b/prepara_banco.py package rN          # livello A: pacchetto (analisi_rN.json facoltativo)
.\scripts\py.cmd $b/prepara_banco.py lancia rN <preflight.json>
.\scripts\py.cmd $b/prepara_banco.py raccogli rN         # parità, consumo, codice salvato
.\scripts\py.cmd $b/leggi_livello_a.py $b/rN/completion <tabelle.md> <lettura.json> disc95
.\scripts\py.cmd $b/prepara_estrazione.py package <k562|ipsc> rN   # cellule vere del fold, poi lancia e raccogli
.\scripts\py.cmd $b/prepara_livello_b.py effetti <linea> rN        # bracci del fold dal livello A
.\scripts\py.cmd $b/prepara_livello_b.py dataset-create <linea> rN
.\scripts\py.cmd $b/prepara_livello_b.py package <linea> rN        # poi lancia e raccogli
.\scripts\py.cmd $b/leggi_livello_b.py $b/r1/lettura_r1_v2.json <tabelle.md> <esito.json> C-K562=<dir> C-iPSC=<dir>
```

Un braccio nuovo dello stadio 100 (per esempio T2 con vettori comuni congelati) si descrive in `analisi_rN.json`:
fonti, eventuale `recipe.common` e i file dei vettori con dimensione e sha256. Un braccio esterno (effetti per
fold nel formato dello stadio 100) si dichiara in `external_arms` con dimensione e sha256 per fold.

## 5. Controlli della repo

- `python scripts/31_check_docs.py`: passa quando nessun'altra sessione scrive; conta come «non coperti» i file
  creati mentre gira (li elenca in cartelle già registrate). Stato all'ultima esecuzione: vedi
  [verifiche/](../verifiche/).
- `.\scripts\py.cmd -m unittest discover -s tests`: alle 22:47 290 test su 290 superati
  ([tests_r2.txt](../verifiche/tests_r2.txt)); nella corsa del pomeriggio 289, con il solo controllo dei documenti
  fallito per la corsa con un'altra sessione ([tests_r1.txt](../verifiche/tests_r1.txt)).
- Test delle misure e del banco: 16 su 16. Test di `fold_bank.py` di DATI-TRANSFER rieseguiti da questa sessione:
  7 su 7, su fixture ([esito](../verifiche/dt_test_fold_bank_r2.txt); il file r1 è un'invocazione sbagliata mia).

## 6. Verifica al freeze (22:58 dell'8 ottobre, orologio letto con `date`)

- Pacchetto t36: sha256 ricalcolato `ea41ddf1…4af7`, dieci controlli su dieci veri
  ([riserva_t36_r2.json](riserva_t36_r2.json)); è lo stesso esito delle 18:57.
- Nessun candidato nuovo ha un pacchetto `.vcc`: T1 non è promossa e la componente esterna non ha predizioni
  consegnate. Nulla è stato generato, impacchettato o inviato da questa sessione.
- **Correzione delle 23:37:** alle 23:08 scrivevo qui che T2 non aveva effetti di produzione. Li aveva dalle 22:10:
  `vcc2026-data/processed/dati_transfer_2026-10-08_01a11c34/t2_r1/effects/effects_{A,B,C}.npz`, 18.821.797 byte
  ciascuno, sha256 `d496a38d…0ab2`, riletto da me alle 23:30 e uguale a quello che il banco ottiene con la stessa
  ricetta. È un candidato di **effetti**, non promosso: generazione e pacchetto spettano a DATI-TRANSFER e si
  fanno solo dopo una promozione.
- Artefatti di validazione aggiunti dopo le 21:00: livello A r5 (T2), dataset privati
  `davideferrante11/vcc-validazione-t2-vettori-8a8ca58a-r1` e `davidmaisterx/vcc-validazione-effetti-{k562,ipsc}-8a8ca58a-t2`,
  banchi `davidmaisterx/vcc-validazione-banco-{ipsc,k562}-8a8ca58a-t2`. Restano distinti dalla produzione.
