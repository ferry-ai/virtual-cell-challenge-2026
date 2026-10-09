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
- **23:56:** T2 ha ora l'esito con due fold a sei membri: valido e **sfavorevole**
  ([risultati](../RISULTATI_T2.md), §6). Non è un candidato della consegna. La consegna verificata resta t36.

## 7. Dopo il freeze: la corsia rapida (letta da questa sessione, che non genera e non invia)

Scritto alle 00:45 del 9 ottobre. Il proprietario ha chiesto nella chat lead un invio esplorativo di un refit su tutte
le fonti entro le 02:00; il percorso fino all'invio è di DATI-TRANSFER.

| Oggetto | Stato alla lettura | Che cosa ho verificato io |
|---|---|---|
| t37 = T1 | previsione del Lead delle 23:47, **superata prima di ogni generazione** alle 23:55; nessun invio | cartelle a registro e nell'indice degli invii |
| t38 = T3 (T1 più cinque voti KO a peso 0,25 su 34 bersagli) | previsione di DATI-TRANSFER delle 00:19, prima del fit; fit concluso alle 00:29; generazione in recupero | un file di effetti riletto, sha256 `b8c61f6d…f6a6` uguale alla ricevuta; [scheda tecnica](schede/t3_contro_t1_r1.json) contro T1; segnalazione DT-5 nei [messaggi](../MESSAGGI.md) |
| T2 | effetti consegnati, esito valido e sfavorevole | identità con lo stimatore valutato; non è un candidato |
| t36 | resta la consegna verificata | [riserva_t36_r2.json](riserva_t36_r2.json) |

T3 **non** è valutato sui fold: la sua combinazione non è una ricetta dello stadio 100 e il banco non può rifarla
senza gli effetti per fold. Per la validazione è un invio esplorativo con attesa «indistinguibile da t36».

**Controlli della repo alle 00:41:** 290 test, uno fallito ([tests_r3.txt](../verifiche/tests_r3.txt)): l'indice
degli invii non elencava le due cartelle del t37, appena tracciate da un'altra sessione. Corretto alle 00:42; il
test dell'albero vivo e il controllo dei documenti passano. I 16 test del banco passano.

## 8. Verifica della consegna alle 02:00 del 9 ottobre

Orologio letto con `date`; scritto alle 02:02.

| Che cosa | Stato | Prova |
|---|---|---|
| **Consegna valutata: t36** | pacchetto con lo sha256 registrato prima dell'upload, dieci controlli su dieci, alle 01:52 | [riserva_t36_r3.json](riserva_t36_r3.json) |
| Nuove entry sul sito | **nessuna**: t37 mai generato; t38 non impacchettato e non caricato; nessun upload pendente nello stato locale del client alle 01:52 | `reports/invii/trial_2026-10-08/NO_SUBMIT_T1_r1.json`, `deadline_incident_r1.json` di DATI-TRANSFER |
| Candidati di effetti esistenti e non promossi | T1 (inconcludente), T2 (valido e sfavorevole), T3 (non valutato sui fold) | [raccomandazione](../RACCOMANDAZIONE.md), §8; [schede](schede/t3_contro_t1_r1.json) |
| Artefatti di validazione | separati dalla produzione, tutti privati, nessuno usato per un invio | §2 e §6 |

Dopo le 01:55 la direzione è cambiata per decisione del proprietario: priorità alle reti
([CP-0071](../../../../docs/checkpoints/0071-corsia-rapida-senza-invio-priorita-alle-reti.md)). Questa verifica chiude la parte dell'incarico legata al freeze.

## 9. Dopo le 02:00: le prime letture delle reti, e che cosa resta aperto

Scritto alle 02:57 del 9 ottobre. Dopo il cambio di priorità del proprietario questa sessione ha letto il ridge ESM2
di MODELLI-ESTERNI nei regimi T e J ([risultati](../RISULTATI_ESM2_T.md)). Nessun artefatto di produzione nuovo.

| Artefatto di validazione aggiunto | Dove | Cartella |
|---|---|---|
| Livello A, corse r6 e r7 (ridge ESM2, regimi T e J) | `davideferrante11/vcc-validazione-logo-8a8ca58a-r{6,7}`, privati | `banco/r6`, `banco/r7` |
| Predizioni ESM2 convertite nel formato del banco | dataset privati `davideferrante11/vcc-validazione-esm2-t-8a8ca58a-r2` e `…-esm2-jk562-8a8ca58a-r1` (privacy verificata via API) | `banco/esm2_t_r2`, `banco/esm2_jk562_r1` |
| Copie locali delle conversioni e tabelle per bersaglio | — | `vcc2026-data/processed/validazione_indipendente_8a8ca58a_2026-10-08/` |

I file nativi dei fit restano di MODELLI-ESTERNI, nella radice dati, letti senza modifiche e con lo sha256 delle
loro ricevute. Un file di effetti di T3 è stato recuperato in sola lettura dal kernel di DATI-TRANSFER.

**Letture ancora da fare, quando i fit finiscono** (in corsa a questa scrittura: produzione, C-K562, C-iPSC;
J-iPSC non partito):

```powershell
$b = "reports/analisi/validazione_indipendente_8a8ca58a_2026-10-08/banco"
# 1. aggiungere il fit a FITS in prepara_esm2_t.py (job, tag, prefisso dei bracci), poi:
.\scripts\py.cmd $b/prepara_esm2_t.py esamina r1 <fit>        # nessuna verità letta; deve dare usable: true
.\scripts\py.cmd $b/prepara_esm2_t.py converti r1 <fit>
.\scripts\py.cmd $b/prepara_esm2_t.py dataset-create r1 <fit>
# 2. scrivere analisi_rN.json (external_arms con dimensione e sha256, contrasti) e un piano prima dei numeri
.\scripts\py.cmd $b/prepara_banco.py package rN ; preflight ; lancia rN <preflight.json> ; raccogli rN
.\scripts\py.cmd $b/leggi_esm2_t.py $b/rN/completion <livelli.md> <livelli.json> <bracci…>
.\scripts\py.cmd $b/leggi_contrasti.py [--regime-j] $b/rN/completion <contrasti.md> <contrasti.json> <id=titolo…>
```

Per i fit C la query è il pannello del fold (non i 66 bersagli nascosti): `converti` va adattato a leggere tutte le
righe del pannello, i bracci si dichiarano sui fold `C-*` e la regola è il §8, con il banco a sei membri su K562 e
iPSC. La regola di combinazione con il transfer va scritta prima dei numeri.

**Controlli finali** (letti alle 11:25): suite della repo 290 test su 290 ([tests_r4.txt](../verifiche/tests_r4.txt);
partita alle 02:58, interrotta dalla sospensione del portatile e conclusa alle 11:09); 16 test del banco su 16;
controllo dei documenti: 71 checkpoint, 13 strade, registro e link coerenti
([docs_check_r7.txt](../verifiche/docs_check_r7.txt)); test dell'albero vivo superato.
